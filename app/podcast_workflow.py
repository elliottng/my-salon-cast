from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Any # Added Any for potential complex inputs

# --- Pydantic Models for Workflow Data ---
# Models like SourceAnalysis, PersonaResearch, etc., are now imported from .podcast_models
from .podcast_models import SourceAnalysis, PersonaResearch, OutlineSegment, DialogueTurn, PodcastOutline, PodcastEpisode

# Placeholder for the input data model to generate_podcast_from_source
# This will likely be defined more concretely when we build the API endpoint (Task 1.8)
class PodcastRequest(BaseModel):
    source_url: Optional[HttpUrl] = None
    source_pdf_path: Optional[str] = None # Assuming a path if a PDF is uploaded
    custom_prompt_for_outline: Optional[str] = None
    prominent_persons: Optional[List[str]] = Field(default=None, description="List of prominent person names for targeted research.")
    # Add other user inputs, e.g., podcast length preference
    # For now, let's keep it simple


# --- Podcast Generation Service ---
import tempfile
import os
import json
import logging

# Assuming these services are in the same app directory
from .llm_service import GeminiService as LLMService, LLMNotInitializedError
from .tts_service import GoogleCloudTtsService # Will be used later
from .content_extractor import (
    extract_content_from_url, 
    extract_text_from_pdf_path, 
    extract_transcript_from_youtube, # Added for completeness, though not used yet
    ExtractionError
)

logger = logging.getLogger(__name__)

class PodcastGeneratorService:
    def __init__(self):
        try:
            self.llm_service = LLMService()
            logger.info("LLMService initialized successfully.")
        except LLMNotInitializedError as e:
            logger.error(f"Failed to initialize LLMService: {e}")
            # Depending on desired behavior, could re-raise or set self.llm_service to None
            # For now, let's allow it to be None and handle it in generate_podcast_from_source
            self.llm_service = None 
        self.tts_service = GoogleCloudTtsService() # Assuming it can be initialized without immediate errors
        # ContentExtractionService is no longer instantiated; its functions are called directly.
        logger.info("PodcastGeneratorService initialized with LLM and TTS services.")

    async def generate_podcast_from_source(
        self,
        request_data: PodcastRequest
    ) -> PodcastEpisode:
        """
        Main orchestration method to generate a podcast episode.
        Follows the sequence outlined in designdoc1-7.md.
        """
        if not self.llm_service:
            logger.error("LLMService not available. Cannot generate podcast.")
            # Return a placeholder or raise an error. For now, returning a dummy error state.
            return PodcastEpisode(
                title="Error", summary="LLM Service Not Initialized", transcript="", audio_filepath="",
                source_attributions=[], warnings=["LLM Service failed to initialize."]
            )

        # Initialize paths for downloadable LLM outputs
        llm_source_analysis_filepath: Optional[str] = None
        # ... other llm output paths will be initialized here later

        # 1. Initialize temporary directory for this job
        with tempfile.TemporaryDirectory(prefix="podcast_job_") as tmpdir_path:
            logger.info(f"Created temporary directory for podcast job: {tmpdir_path}")

            # 2. Content Extraction
            extracted_text: Optional[str] = None
            if request_data.source_url:
                try:
                    extracted_text = await extract_content_from_url(str(request_data.source_url))
                    logger.info(f"Successfully extracted text from URL: {request_data.source_url}")
                except ExtractionError as e:
                    logger.error(f"Content extraction from URL {request_data.source_url} failed: {e}")
                    return PodcastEpisode(title="Error", summary="Content Extraction Failed", transcript="", audio_filepath="", source_attributions=[], warnings=[f"Failed to extract content from URL: {e}"])
            elif request_data.source_pdf_path:
                try:
                    pdf_path_str = str(request_data.source_pdf_path) # Ensure it's a string
                    extracted_text = await extract_text_from_pdf_path(pdf_path_str)
                    logger.info(f"Successfully extracted text from PDF path: {pdf_path_str}")
                except ExtractionError as e:
                    logger.error(f"Content extraction from PDF path {request_data.source_pdf_path} failed: {e}")
                    return PodcastEpisode(title="Error", summary="Content Extraction Failed", transcript="", audio_filepath="", source_attributions=[], warnings=[f"Failed to extract content from PDF: {e}"])
            else:
                logger.warning("No source URL or PDF path provided for content extraction.")
                return PodcastEpisode(title="Error", summary="No Source Provided", transcript="", audio_filepath="", source_attributions=[], warnings=["No source URL or PDF path provided."])

            if not extracted_text:
                logger.error("Content extraction resulted in empty text.")
                return PodcastEpisode(title="Error", summary="Empty Content Extracted", transcript="", audio_filepath="", source_attributions=[], warnings=["Content extraction resulted in empty text."])

            # 3. LLM - Source Analysis
            source_analysis_obj: Optional[SourceAnalysis] = None
            try:
                # Assuming analyze_source_text_async returns a dictionary that can be parsed into SourceAnalysis
                # Or that it directly returns a SourceAnalysis object if LLMService is updated
                analysis_dict = await self.llm_service.analyze_source_text_async(extracted_text)
                
                if analysis_dict and "error" not in analysis_dict:
                    try:
                        source_analysis_obj = SourceAnalysis(**analysis_dict)
                        logger.info("Source analysis successful and parsed into Pydantic model.")
                        
                        llm_source_analysis_filepath = os.path.join(tmpdir_path, "source_analysis.json")
                        with open(llm_source_analysis_filepath, 'w') as f:
                            json.dump(source_analysis_obj.model_dump(), f, indent=2)
                        logger.info(f"Source analysis saved to {llm_source_analysis_filepath}")
                    except Exception as pydantic_error: # Catch Pydantic validation errors or other issues
                        logger.error(f"Failed to parse LLM analysis_dict into SourceAnalysis model: {pydantic_error}")
                        logger.error(f"LLM analysis_dict: {analysis_dict}")
                        # Decide if this is a critical failure, for now, we'll nullify the object and path
                        source_analysis_obj = None
                        llm_source_analysis_filepath = None
                elif analysis_dict and "error" in analysis_dict:
                    logger.error(f"LLM source analysis failed (JSON parsing or other error from LLMService): {analysis_dict.get('error')}")
                    logger.error(f"Raw response from LLMService: {analysis_dict.get('raw_response')}")
                    # Decide if this is a critical failure
                else: # analysis_dict is None or empty
                    logger.error("LLM source analysis returned no data (None or empty dict).")
                    # Decide if this is a critical failure

            except Exception as e: # Catching a broad exception for now
                logger.error(f"LLM Source Analysis failed: {e}", exc_info=True)
                # Potentially return an error episode or try to continue without it
                # For now, let's treat it as non-critical for the dummy response but log it
                pass # Allow to proceed to dummy response for now

            # Step 4: LLM - Persona Research
            llm_persona_research_filepaths: List[str] = []
            if request_data.prominent_persons and extracted_text:
                logger.info(f"Starting persona research for: {request_data.prominent_persons}")
                for person_name in request_data.prominent_persons:
                    try:
                        logger.info(f"Researching persona: {person_name}")
                        persona_profile: PersonaResearch = await self.llm_service.research_persona_async(
                            source_text=extracted_text,
                            person_name=person_name
                        )
                        
                        persona_filepath = os.path.join(tmpdir_path, f"persona_research_{persona_profile.person_id}.json")
                        with open(persona_filepath, 'w') as f:
                            json.dump(persona_profile.model_dump(), f, indent=2)
                        llm_persona_research_filepaths.append(persona_filepath)
                        logger.info(f"Persona research for '{person_name}' saved to {persona_filepath}")
                    except ValueError as ve:
                        logger.error(f"ValueError during persona research for '{person_name}': {ve}", exc_info=True)
                        # Decide how to handle, e.g., skip this persona, add a warning
                    except Exception as e:
                        logger.error(f"Unexpected error during persona research for '{person_name}': {e}", exc_info=True)
                        # Decide how to handle
            elif not extracted_text and request_data.prominent_persons:
                logger.warning("Cannot perform persona research: no extracted text available.")
            else:
                logger.info("No prominent persons requested for research or no extracted text.")

            # ... Steps 5-13 will be implemented here ...

            # Placeholder implementation - This will be replaced by actual generated content
            logger.info("Proceeding with placeholder podcast episode generation.")
            return PodcastEpisode(
                title="Placeholder Title",
                summary="Placeholder Summary",
                transcript=extracted_text[:500] + "... (truncated for placeholder)" if extracted_text else "No text extracted.",
                audio_filepath=os.path.join(tmpdir_path, "placeholder_audio.mp3"), # Dummy path
                source_attributions=["Placeholder Source 1"],
                warnings=["This is a placeholder response."],
                llm_source_analysis_path=llm_source_analysis_filepath, # Use the actual path if available
                llm_persona_research_paths=llm_persona_research_filepaths if llm_persona_research_filepaths else None,
                llm_podcast_outline_path=None, # Placeholder
                llm_dialogue_turns_path=None # Placeholder
            )

# Example usage (for testing purposes, can be removed later)
async def main_workflow_test():
    generator = PodcastGeneratorService()
    sample_request = PodcastRequest(source_url="http://example.com/article")
    episode = await generator.generate_podcast_from_source(sample_request)
    print("--- Generated Episode ---")
    print(episode.model_dump_json(indent=2))

if __name__ == "__main__":
    import asyncio
    # To run the async main_workflow_test
    # asyncio.run(main_workflow_test())
    # For now, just print that the module is loaded if run directly
    print(f"{__file__} loaded. Contains PodcastGeneratorService and Pydantic models.")
    print("Uncomment asyncio.run(main_workflow_test()) in __main__ to test basic structure.")

