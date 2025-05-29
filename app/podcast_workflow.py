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
    desired_podcast_length_str: Optional[str] = Field(default="5-7 minutes", description="Desired length of the podcast (e.g., '5-7 minutes', '10-15 minutes').")
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
            return PodcastEpisode(
                title="Error", summary="LLM Service Not Initialized", transcript="", audio_filepath="",
                source_attributions=[], warnings=["LLM Service failed to initialize."]
            )

        llm_source_analysis_filepath: Optional[str] = None
        llm_persona_research_filepaths: List[str] = []
        llm_podcast_outline_filepath: Optional[str] = None
        llm_dialogue_script_filepath: Optional[str] = None # Path for the full dialogue script

        source_analyses_content: List[str] = []
        persona_research_docs_content: List[str] = []

        podcast_title = "Generation Incomplete"
        podcast_summary = "Full generation pending or failed at an early stage."
        podcast_transcript = "Transcript generation pending."
        warnings_list: List[str] = []

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
                    pdf_path_str = str(request_data.source_pdf_path)
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
                analysis_dict = await self.llm_service.analyze_source_text_async(extracted_text)
                if analysis_dict and "error" not in analysis_dict:
                    try:
                        source_analysis_obj = SourceAnalysis(**analysis_dict)
                        logger.info("Source analysis successful and parsed.")
                        source_analyses_content.append(source_analysis_obj.model_dump_json())
                        llm_source_analysis_filepath = os.path.join(tmpdir_path, "source_analysis.json")
                        with open(llm_source_analysis_filepath, 'w') as f:
                            json.dump(source_analysis_obj.model_dump(), f, indent=2)
                        logger.info(f"Source analysis saved to {llm_source_analysis_filepath}")
                    except Exception as p_error:
                        logger.error(f"Failed to parse LLM analysis into SourceAnalysis: {p_error}")
                        warnings_list.append(f"Source analysis parsing failed: {p_error}")
                elif analysis_dict and "error" in analysis_dict:
                    logger.error(f"LLM source analysis failed: {analysis_dict.get('error')}")
                    warnings_list.append(f"LLM source analysis error: {analysis_dict.get('error')}")
                else:
                    logger.error("LLM source analysis returned no data.")
                    warnings_list.append("LLM source analysis returned no data.")
            except Exception as e:
                logger.error(f"Error during source analysis: {e}")
                warnings_list.append(f"Critical error during source analysis: {e}")

            # 4. LLM - Persona Research
            if request_data.prominent_persons and extracted_text:
                for person_name in request_data.prominent_persons:
                    try:
                        persona_profile = await self.llm_service.research_persona_async(
                            source_text=extracted_text, person_name=person_name
                        )
                        logger.info(f"Persona research successful for {person_name}.")
                        persona_research_docs_content.append(persona_profile.model_dump_json())
                        filepath = os.path.join(tmpdir_path, f"persona_research_{persona_profile.person_id}.json")
                        with open(filepath, 'w') as f:
                            json.dump(persona_profile.model_dump(), f, indent=2)
                        llm_persona_research_filepaths.append(filepath)
                        logger.info(f"Persona research for {person_name} saved to {filepath}")
                    except ValueError as e:
                        logger.error(f"Persona research for {person_name} failed (ValueError): {e}")
                        warnings_list.append(f"Persona research for {person_name} failed: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error during persona research for {person_name}: {e}")
                        warnings_list.append(f"Unexpected error in persona research for {person_name}: {e}")
            else:
                logger.info("No prominent persons requested or no extracted text for persona research.")

            # 5. LLM - Podcast Outline Generation
            podcast_outline_obj: Optional[PodcastOutline] = None
            if extracted_text: # Only proceed if we have text
                try:
                    num_persons = len(request_data.prominent_persons) if request_data.prominent_persons else 0
                    podcast_outline_obj = await self.llm_service.generate_podcast_outline_async(
                        source_analyses=source_analyses_content, # List of JSON strings
                        persona_research_docs=persona_research_docs_content, # List of JSON strings
                        desired_podcast_length_str=request_data.desired_podcast_length_str or "5-7 minutes",
                        num_prominent_persons=num_persons,
                        names_prominent_persons_list=request_data.prominent_persons,
                        user_provided_custom_prompt=request_data.custom_prompt_for_outline
                    )
                    if podcast_outline_obj:
                        logger.info("Podcast outline generated successfully.")
                        podcast_title = podcast_outline_obj.title_suggestion
                        podcast_summary = podcast_outline_obj.summary_suggestion
                        llm_podcast_outline_filepath = os.path.join(tmpdir_path, "podcast_outline.json")
                        with open(llm_podcast_outline_filepath, 'w') as f:
                            json.dump(podcast_outline_obj.model_dump(), f, indent=2)
                        logger.info(f"Podcast outline saved to {llm_podcast_outline_filepath}")
                    else:
                        logger.error("Podcast outline generation returned None.")
                        warnings_list.append("Podcast outline generation failed to produce an outline.")
                except Exception as e:
                    logger.error(f"Error during podcast outline generation: {e}")
                    warnings_list.append(f"Critical error during podcast outline generation: {e}")
            else:
                warnings_list.append("Skipping outline generation as extracted_text is empty.")

            # 6. LLM - Dialogue Generation
            if podcast_outline_obj and extracted_text:
                try:
                    # Construct prominent_persons_details for dialogue generation
                    # This is a simplified version; gender might need more sophisticated handling for TTS
                    prominent_persons_details_for_dialogue: List[Tuple[str, str, str]] = []
                    if request_data.prominent_persons:
                        for name in request_data.prominent_persons:
                            initial = name[0].upper() if name else "X"
                            # For now, gender is 'neutral'. This might need to come from PersonaResearch or user input for TTS.
                            prominent_persons_details_for_dialogue.append((name, initial, "neutral")) 
                    
                    generated_dialogue_script = await self.llm_service.generate_dialogue_async(
                        podcast_outline_str=podcast_outline_obj.model_dump_json(), # Pass outline as JSON string
                        source_analyses=source_analyses_content,
                        persona_research_docs=persona_research_docs_content,
                        prominent_persons_details=prominent_persons_details_for_dialogue
                    )
                    if generated_dialogue_script:
                        logger.info("Podcast dialogue generated successfully.")
                        podcast_transcript = generated_dialogue_script
                        llm_dialogue_script_filepath = os.path.join(tmpdir_path, "dialogue_script.txt")
                        with open(llm_dialogue_script_filepath, 'w') as f:
                            f.write(generated_dialogue_script)
                        logger.info(f"Dialogue script saved to {llm_dialogue_script_filepath}")
                    else:
                        logger.error("Dialogue generation returned None or empty script.")
                        warnings_list.append("Dialogue generation failed to produce a script.")
                except Exception as e:
                    logger.error(f"Error during dialogue generation: {e}")
                    warnings_list.append(f"Critical error during dialogue generation: {e}")
            else:
                warnings_list.append("Skipping dialogue generation as outline or extracted_text is missing.")

            # (Future steps: TTS, audio stitching, final attributions)

            return PodcastEpisode(
                title=podcast_title,
                summary=podcast_summary,
                transcript=podcast_transcript,
                audio_filepath="placeholder.mp3", # Placeholder for now
                source_attributions=[], # Placeholder for now, will be populated from dialogue turns later
                warnings=warnings_list,
                llm_source_analysis_path=llm_source_analysis_filepath,
                llm_persona_research_paths=llm_persona_research_filepaths if llm_persona_research_filepaths else None,
                llm_podcast_outline_path=llm_podcast_outline_filepath,
                llm_dialogue_turns_path=llm_dialogue_script_filepath # Using this field for the full script path for now
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

