from pydantic import BaseModel, HttpUrl, Field, ValidationError
from typing import List, Optional, Any # Added Any for potential complex inputs

# --- Pydantic Models for Workflow Data ---
# Models like SourceAnalysis, PersonaResearch, etc., are now imported from .podcast_models
from .podcast_models import SourceAnalysis, PersonaResearch, OutlineSegment, DialogueTurn, PodcastOutline, PodcastEpisode
from .common_exceptions import LLMProcessingError

# Placeholder for the input data model to generate_podcast_from_source
# This will likely be defined more concretely when we build the API endpoint (Task 1.8)
class PodcastRequest(BaseModel):
    source_urls: List[HttpUrl] = Field(default_factory=list, description="List of URLs to extract content from (maximum 3)")
    source_pdf_path: Optional[str] = None # Assuming a path if a PDF is uploaded
    custom_prompt_for_outline: Optional[str] = None
    custom_prompt_for_dialogue: Optional[str] = None
    prominent_persons: Optional[List[str]] = Field(default=None, description="List of prominent person names for targeted research.")
    desired_podcast_length: int = Field(default=5, description="Desired length of the podcast in minutes.")
    # Add other user inputs if needed
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

        llm_source_analysis_filepaths: List[str] = []
        llm_persona_research_filepaths: List[str] = []
        llm_podcast_outline_filepath: Optional[str] = None
        llm_dialogue_script_filepath: Optional[str] = None # Path for the full dialogue script
        llm_dialogue_turns_filepath: Optional[str] = None

        source_analyses_content: List[str] = []
        persona_research_docs_content: List[str] = []

        podcast_title = "Generation Incomplete"
        podcast_summary = "Full generation pending or failed at an early stage."
        podcast_transcript = "Transcript generation pending."
        warnings_list: List[str] = []
        podcast_episode_data: dict = {} # Initialize the dictionary

        with tempfile.TemporaryDirectory(prefix="podcast_job_") as tmpdir_path:
            logger.info(f"Created temporary directory for podcast job: {tmpdir_path}")

            # 2. Content Extraction
            extracted_texts: List[str] = []
            extraction_errors: List[str] = []
            
            # Handle multiple URLs
            if request_data.source_urls:
                if len(request_data.source_urls) > 3:
                    logger.warning(f"Too many URLs provided: {len(request_data.source_urls)}. Using only the first 3.")
                    request_data.source_urls = request_data.source_urls[:3]
                
                for url in request_data.source_urls:
                    try:
                        text = await extract_content_from_url(str(url))
                        if text:
                            extracted_texts.append(text)
                            logger.info(f"Successfully extracted text from URL: {url}")
                        else:
                            extraction_errors.append(f"Empty content extracted from URL: {url}")
                    except ExtractionError as e:
                        error_msg = f"Content extraction from URL {url} failed: {e}"
                        extraction_errors.append(error_msg)
                        logger.error(error_msg)
                
                if not extracted_texts and extraction_errors:
                    return PodcastEpisode(title="Error", summary="Content Extraction Failed", transcript="", audio_filepath="", 
                                         source_attributions=[], warnings=[f"Failed to extract content from URLs: {'; '.join(extraction_errors)}"])
            elif request_data.source_pdf_path:
                try:
                    pdf_path_str = str(request_data.source_pdf_path)
                    text = await extract_text_from_pdf_path(pdf_path_str)
                    if text:
                        extracted_texts.append(text)
                        logger.info(f"Successfully extracted text from PDF path: {pdf_path_str}")
                    else:
                        logger.error(f"Empty content extracted from PDF path: {pdf_path_str}")
                        return PodcastEpisode(title="Error", summary="Empty Content Extracted", transcript="", 
                                             audio_filepath="", source_attributions=[], 
                                             warnings=[f"Empty content extracted from PDF: {pdf_path_str}"])
                except ExtractionError as e:
                    logger.error(f"Content extraction from PDF path {request_data.source_pdf_path} failed: {e}")
                    return PodcastEpisode(title="Error", summary="Content Extraction Failed", transcript="", 
                                         audio_filepath="", source_attributions=[], 
                                         warnings=[f"Failed to extract content from PDF: {e}"])
            else:
                logger.warning("No source URLs or PDF path provided for content extraction.")
                return PodcastEpisode(title="Error", summary="No Source Provided", transcript="", 
                                     audio_filepath="", source_attributions=[], 
                                     warnings=["No source URLs or PDF path provided."])

            if not extracted_texts:
                logger.error("Content extraction resulted in empty texts.")
                return PodcastEpisode(title="Error", summary="Empty Content Extracted", transcript="", 
                                     audio_filepath="", source_attributions=[], 
                                     warnings=["Content extraction resulted in empty texts."])
                
            # Combine all extracted texts with clear separation
            extracted_text = "\n\n===== SOURCE SEPARATOR =====\n\n".join(extracted_texts)

            # 3. LLM - Source Analysis
            source_analysis_obj: Optional[SourceAnalysis] = None
            try:
                # llm_service.analyze_source_text_async now returns a SourceAnalysis object directly or raises an error
                source_analysis_obj = await self.llm_service.analyze_source_text_async(extracted_text)
                if source_analysis_obj:
                    logger.info("Source analysis successful.")
                    source_analyses_content.append(source_analysis_obj.model_dump_json()) # For LLM input
                    llm_source_analysis_filepath = os.path.join(tmpdir_path, "source_analysis.json")
                    with open(llm_source_analysis_filepath, 'w') as f:
                        json.dump(source_analysis_obj.model_dump(), f, indent=2) # Save the model dump
                    logger.info(f"Source analysis saved to {llm_source_analysis_filepath}")
                    llm_source_analysis_filepaths.append(llm_source_analysis_filepath)
                else:
                    # This case should ideally not be reached if analyze_source_text_async raises an error on failure
                    logger.error("LLM source analysis returned no data (or None unexpectedly).")
                    warnings_list.append("LLM source analysis returned no data.")
            except LLMProcessingError as llm_e: # Catch specific LLM errors from the service
                logger.error(f"LLM processing error during source analysis: {llm_e}")
                warnings_list.append(f"LLM source analysis failed: {llm_e}")
            except ValidationError as val_e: # Catch Pydantic validation errors if they occur here
                logger.error(f"Validation error during source analysis processing: {val_e}")
                warnings_list.append(f"Source analysis validation failed: {val_e}")
            except Exception as e: # Catch any other unexpected errors
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

            # 4.5. Assign Invented Names and Genders to Personas
            MALE_INVENTED_NAMES = ["Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas", "Henry", "Theodore"]
            FEMALE_INVENTED_NAMES = ["Olivia", "Emma", "Charlotte", "Amelia", "Sophia", "Isabella", "Ava", "Mia", "Evelyn", "Luna"]
            NEUTRAL_INVENTED_NAMES = ["Kai", "Rowan", "River", "Phoenix", "Sage", "Justice", "Remy", "Dakota", "Skyler", "Alexis"]
            
            persona_details_map: dict[str, dict[str, str]] = {}
            # Ensure Host is always in the map
            persona_details_map["Host"] = {
                "invented_name": "Host",
                "gender": "Male", # Default Host gender, can be made more dynamic
                "real_name": "Host"
            }

            last_assigned_gender_index = -1 # -1 for Male, 0 for Female for personas to alternate
            male_name_idx = 0
            female_name_idx = 0
            neutral_name_idx = 0

            processed_persona_research_objects: List[PersonaResearch] = []
            for pr_json_str in persona_research_docs_content:
                try:
                    pr_data = json.loads(pr_json_str)
                    # Assuming PersonaResearch model can be instantiated from this dict
                    # This helps if we need the full object later, not just the map
                    processed_persona_research_objects.append(PersonaResearch(**pr_data))
                    person_id = pr_data.get("person_id")
                    real_name = pr_data.get("name", "Unknown Persona")

                    if person_id:
                        assigned_gender = ""
                        invented_name = ""
                        
                        # Round-robin gender for personas (Male, Female, Male, Female...)
                        # Host is already set, this applies to other personas
                        if last_assigned_gender_index == -1: # Assign Male first to persona
                            assigned_gender = "Male"
                            last_assigned_gender_index = 0
                            if male_name_idx < len(MALE_INVENTED_NAMES):
                                invented_name = MALE_INVENTED_NAMES[male_name_idx]
                                male_name_idx += 1
                            else: # Cycle through names if list exhausted
                                invented_name = MALE_INVENTED_NAMES[male_name_idx % len(MALE_INVENTED_NAMES)]
                                male_name_idx += 1 
                        elif last_assigned_gender_index == 0: # Assign Female
                            assigned_gender = "Female"
                            last_assigned_gender_index = -1 # Next will be male
                            if female_name_idx < len(FEMALE_INVENTED_NAMES):
                                invented_name = FEMALE_INVENTED_NAMES[female_name_idx]
                                female_name_idx += 1
                            else:
                                invented_name = FEMALE_INVENTED_NAMES[female_name_idx % len(FEMALE_INVENTED_NAMES)]
                                female_name_idx += 1
                        
                        # Fallback if name lists are empty or gender assignment is odd
                        if not invented_name:
                            invented_name = NEUTRAL_INVENTED_NAMES[neutral_name_idx % len(NEUTRAL_INVENTED_NAMES)]
                            neutral_name_idx +=1
                            if not assigned_gender: assigned_gender = "Neutral"

                        persona_details_map[person_id] = {
                            "invented_name": invented_name,
                            "gender": assigned_gender,
                            "real_name": real_name
                        }
                        logger.info(f"Assigned to {person_id} ({real_name}): Invented Name='{invented_name}', Gender='{assigned_gender}'")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse PersonaResearch JSON for name/gender assignment: {e}. Content: {pr_json_str[:100]}")
                except Exception as e:
                    logger.error(f"Error processing persona for name/gender assignment: {e}. Persona data: {pr_json_str[:100]}")
            logger.info(f"Final persona_details_map: {persona_details_map}")

            # 5. LLM - Podcast Outline Generation
            podcast_outline_obj: Optional[PodcastOutline] = None
            if extracted_text: # Only proceed if we have text
                try:
                    num_persons = len(request_data.prominent_persons) if request_data.prominent_persons else 0
                    # Convert podcast length from integer to string format for LLM
                    desired_length_str = f"{request_data.desired_podcast_length} minutes"
                    podcast_outline_obj = await self.llm_service.generate_podcast_outline_async(
                        source_analyses=source_analyses_content, # List of JSON strings
                        persona_research_docs=persona_research_docs_content, # List of JSON strings
                        desired_podcast_length_str=desired_length_str,
                        num_prominent_persons=num_persons,
                        names_prominent_persons_list=request_data.prominent_persons,
                        persona_details_map=persona_details_map,
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
            dialogue_turns_list: Optional[List[DialogueTurn]] = None
            if podcast_outline_obj and extracted_text:
                try:
                    # We already have the persona_details_map with invented names and gender
                    # No need to build prominent_persons_details_for_dialogue anymore
                    
                    # Convert podcast length from integer to string format for LLM (though not needed now)
                    # desired_length_str = f"{request_data.desired_podcast_length} minutes"
                    
                    dialogue_turns_list = await self.llm_service.generate_dialogue_async(
                        podcast_outline=podcast_outline_obj,  # Pass the actual object, not JSON string
                        source_analyses=source_analyses_content, 
                        persona_research_docs=persona_research_docs_content,
                        persona_details_map=persona_details_map,
                        user_custom_prompt_for_dialogue=request_data.custom_prompt_for_dialogue
                    )

                    if dialogue_turns_list:
                        logger.info(f"Podcast dialogue turns generated successfully ({len(dialogue_turns_list)} turns).")
                        
                        # Save dialogue turns to JSON file
                        llm_dialogue_turns_filepath = os.path.join(tmpdir_path, "dialogue_turns.json")
                        serialized_turns = [turn.model_dump() for turn in dialogue_turns_list]
                        with open(llm_dialogue_turns_filepath, 'w') as f:
                            json.dump(serialized_turns, f, indent=2)
                        logger.info(f"Dialogue turns saved to {llm_dialogue_turns_filepath}")
                        podcast_episode_data['llm_dialogue_turns_path'] = llm_dialogue_turns_filepath
                        
                        # Construct transcript string from dialogue turns using invented names
                        transcript_parts = []
                        for turn in dialogue_turns_list:
                            speaker_id = turn.speaker_id
                            # Look up invented name from persona_details_map
                            if speaker_id in persona_details_map and "invented_name" in persona_details_map[speaker_id]:
                                speaker_display_name = persona_details_map[speaker_id]["invented_name"]
                            else:
                                # Fallback to raw speaker_id if not found (which shouldn't happen if setup correctly)
                                logger.warning(f"No invented name found for speaker_id '{speaker_id}' in persona_details_map. Using raw ID.")
                                speaker_display_name = speaker_id
                                
                            transcript_parts.append(f"{speaker_display_name}: {turn.text}")
                        podcast_transcript = "\n".join(transcript_parts)
                        logger.info("Transcript constructed from dialogue turns.")
                        podcast_episode_data['transcript'] = podcast_transcript
                    else:
                        logger.error("Dialogue generation returned None or empty list of turns.")
                        warnings_list.append("Dialogue generation failed to produce turns.")
                        podcast_transcript = "Error: Dialogue generation failed."
                        podcast_episode_data['transcript'] = podcast_transcript

                except LLMProcessingError as e:
                    logger.error(f"LLMProcessingError during dialogue generation: {e}")
                    warnings_list.append(f"LLM processing error during dialogue generation: {e}")
                    podcast_episode_data['transcript'] = f"Error: LLM processing failed during dialogue generation. Details: {e}"
                except Exception as e:
                    logger.error(f"Unexpected error during dialogue generation: {e}", exc_info=True)
                    warnings_list.append(f"Critical error during dialogue generation: {e}")
                    podcast_transcript = f"Error: Critical error during dialogue generation. Details: {e}"
                    podcast_episode_data['transcript'] = podcast_transcript
            else:
                warnings_list.append("Skipping dialogue generation as outline or extracted_text is missing.")
                podcast_transcript = "Dialogue generation skipped due to missing prerequisites."
                podcast_episode_data['transcript'] = podcast_transcript

            # (Future steps: TTS, audio stitching, final attributions)

            return PodcastEpisode(
                title=podcast_title,
                summary=podcast_summary,
                transcript=podcast_transcript,
                audio_filepath="placeholder.mp3", # Placeholder for now
                source_attributions=[], # Placeholder for now, will be populated from dialogue turns later
                warnings=warnings_list,
                llm_source_analysis_paths=llm_source_analysis_filepaths if llm_source_analysis_filepaths else None,
                llm_persona_research_paths=llm_persona_research_filepaths if llm_persona_research_filepaths else None,
                llm_podcast_outline_path=llm_podcast_outline_filepath,
                llm_dialogue_turns_path=llm_dialogue_turns_filepath
            )

# Example usage (for testing purposes, can be removed later)
async def main_workflow_test():
    generator = PodcastGeneratorService()
    sample_request = PodcastRequest(source_urls=["http://example.com/article"], desired_podcast_length=7)
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

