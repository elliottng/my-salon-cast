from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Any # Added Any for potential complex inputs

# --- Pydantic Models for Workflow Data ---

class PodcastEpisode(BaseModel):
    title: str
    summary: str
    transcript: str
    audio_filepath: str
    source_attributions: List[str]
    warnings: List[str]
    llm_source_analysis_path: Optional[str] = None
    llm_persona_research_paths: Optional[List[str]] = None
    llm_podcast_outline_path: Optional[str] = None
    llm_dialogue_turns_path: Optional[str] = None

class SourceAnalysis(BaseModel):
    key_themes: List[str]
    facts: List[str]
    summary_points: Optional[List[str]] = None
    potential_biases: Optional[List[str]] = None
    counter_arguments_or_perspectives: Optional[List[str]] = None
    # Add other fields as identified by LLM or needed by workflow

class PersonaResearch(BaseModel):
    person_id: str # To identify which prominent person this research is for
    name: str
    viewpoints: List[str]
    speaking_style: str
    # Add other fields as identified by LLM or needed by workflow

class OutlineSegment(BaseModel):
    segment_title: Optional[str] = None
    speaker_id: str # e.g., "Host", "PersonA_Name", "Follower_PersonA_1_Name"
    content_cue: str # What the speaker should talk about, or a specific question
    estimated_duration_seconds: Optional[int] = None

class DialogueTurn(BaseModel):
    speaker_id: str
    speaker_gender: str # "Male", "Female", "Neutral" (or as per TTS options)
    text: str
    source_mentions: Optional[List[str]] = []

# Placeholder for the input data model to generate_podcast_from_source
# This will likely be defined more concretely when we build the API endpoint (Task 1.8)
class PodcastRequest(BaseModel):
    source_url: Optional[HttpUrl] = None
    source_pdf_path: Optional[str] = None # Assuming a path if a PDF is uploaded
    custom_prompt_for_outline: Optional[str] = None
    # Add other user inputs, e.g., desired number of prominent persons, podcast length preference
    # For now, let's keep it simple
    pass


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
    extract_text_from_pdf,
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
                # Assuming source_pdf_path is an absolute path or accessible relative path
                # For a real app, this path would come from a file upload mechanism
                try:
                    # PDF extraction in content_extractor is async now, so ensure it's awaited if used.
# For now, assuming the workflow might primarily use URL or direct text input.
# If PDF path is used, it should be: extracted_text = await extract_text_from_pdf_path_wrapper(request_data.source_pdf_path)
# where extract_text_from_pdf_path_wrapper handles opening file and passing to extract_text_from_pdf(UploadFile)
# OR, PodcastRequest changes to accept UploadFile directly for PDFs.
# For this iteration, let's assume source_pdf_path implies a direct path that needs handling.
# The original extract_text_from_pdf expects an UploadFile. We need a wrapper or change.
# Let's simplify for now and assume if source_pdf_path is given, it's a path to a local file.
# We will need to adjust content_extractor.extract_text_from_pdf or add a new function for file paths.

# TEMPORARY: To avoid blocking, let's assume for now PDF path means we'd need a different handling
# or that the ContentExtractionService would have a specific method for file paths.
# For the current structure of extract_text_from_pdf expecting UploadFile, direct path usage is problematic.
# We will defer proper PDF path handling or adjust extract_text_from_pdf later.
# For now, this path will likely lead to an error or be unused if not an UploadFile.
# This part needs to be revisited based on how PDF files are actually supplied to the workflow.
# For the sake of making tests pass with current structure, we'll assume this path is not hit often
# or extract_text_from_pdf is mocked appropriately in tests to not care about UploadFile type.

# Given extract_text_from_pdf now takes UploadFile, and this workflow takes a path,
# this is a mismatch. We'll need to address this. For now, let's comment out direct call
# and rely on URL or make a note to fix PDF handling.
# extracted_text = await extract_text_from_pdf(request_data.source_pdf_path) 
# ^ This is incorrect as extract_text_from_pdf expects UploadFile.
# We'll assume for now that if a PDF path is given, it's an error or needs a different function.
# This will be caught by the 'No source URL or PDF path provided' or subsequent 'extracted_text is None'.
# To make it more explicit, let's log a warning if pdf_path is used with current setup.

                    logger.warning(f"PDF path ({request_data.source_pdf_path}) provided, but current implementation of extract_text_from_pdf expects UploadFile. This path will be ignored unless handled by a wrapper.")
                    # To simulate a failure for this path for now:
                    raise ExtractionError(f"PDF file path handling not fully implemented for {request_data.source_pdf_path}. Expects UploadFile.")
                    logger.info(f"Successfully extracted text from PDF: {request_data.source_pdf_path}")
                except ExtractionError as e:
                    logger.error(f"Content extraction from PDF {request_data.source_pdf_path} failed: {e}")
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
                logger.error(f"LLM Source Analysis failed: {e}")
                # Potentially return an error episode or try to continue without it
                # For now, let's treat it as non-critical for the dummy response but log it
                pass # Allow to proceed to dummy response for now

            # ... Steps 4-13 will be implemented here ...

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
                llm_persona_research_paths=None, # Placeholder
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

