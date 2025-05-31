from pydantic import BaseModel, HttpUrl, Field, ValidationError
from typing import List, Optional, Any, Dict, Tuple, Set, Union
import asyncio
import json
import logging
import os
import random
import tempfile
import shutil
import uuid
from datetime import datetime
from pathlib import Path

# --- Pydantic Models for Workflow Data ---
# Models like SourceAnalysis, PersonaResearch, etc., are now imported from podcast_models
from app.podcast_models import SourceAnalysis, PersonaResearch, OutlineSegment, DialogueTurn, PodcastOutline, PodcastEpisode
from app.common_exceptions import LLMProcessingError

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
from app.llm_service import GeminiService as LLMService, LLMNotInitializedError
from app.tts_service import GoogleCloudTtsService # Will be used later
from app.audio_utils import AudioPathManager, AudioStitchingService
from app.content_extractor import (
    extract_content_from_url, 
    extract_text_from_pdf_path, 
    extract_transcript_from_youtube, # Added for completeness, though not used yet
    ExtractionError
)

logger = logging.getLogger(__name__)

class PodcastGeneratorService:
    def __init__(self):
        # Initialize TTS service first so we can pass it to the LLM service
        self.tts_service = GoogleCloudTtsService() # Initialize TTS service with voice caching
        logger.info("TTS service initialized with voice cache support")
        
        # Now initialize LLM service with TTS service for voice profile selection
        try:
            self.llm_service = LLMService(tts_service=self.tts_service)
            logger.info("LLMService initialized successfully with TTS service integration")
        except LLMNotInitializedError as e:
            logger.error(f"Failed to initialize LLMService: {e}")
            # Depending on desired behavior, could re-raise or set self.llm_service to None
            # For now, let's allow it to be None and handle it in generate_podcast_from_source
            self.llm_service = None
        
        # Initialize audio stitching services
        self.path_manager = AudioPathManager()
        self.audio_stitching_service = AudioStitchingService(
            tts_service=self.tts_service,
            path_manager=self.path_manager
        )
        
        # ContentExtractionService is no longer instantiated; its functions are called directly.
        logger.info("PodcastGeneratorService initialized with LLM, TTS, and Audio Stitching services.")
    
    async def _process_audio_for_podcast(self, 
                                      dialogue_turns: List[DialogueTurn],
                                      podcast_id: str,
                                      persona_details_map: dict,
                                      persona_research_map: Optional[Dict[str, PersonaResearch]] = None,
                                      silence_duration_ms: int = 500) -> str:
        """
        Process audio for all dialogue turns and stitch them together.
        
        Args:
            dialogue_turns: List of dialogue turns to process
            podcast_id: Unique identifier for this podcast
            persona_details_map: Map of speaker IDs to details (for gender)
            silence_duration_ms: Duration of silence between turns in milliseconds
            
        Returns:
            Path to the final stitched audio file, or empty string if failed
        """
        logger.info(f"[AUDIO_STITCH] Starting audio processing for podcast {podcast_id}")
        
        # Create directory structure
        podcast_dir, segments_dir = self.path_manager.create_podcast_directories(podcast_id)
        logger.info(f"[AUDIO_STITCH] Created directory structure at {podcast_dir}")
        
        # Generate audio for each turn
        segment_paths = []
        failed_segments = []
        
        for turn in dialogue_turns:
            # If we have the enhanced PersonaResearch map, use it (preferred method)
            if persona_research_map is not None and turn.speaker_id in persona_research_map:
                success, segment_path = await self.audio_stitching_service.generate_audio_for_dialogue_turn(
                    turn, podcast_id, persona_details_map, persona_research_map
                )
            else:
                # Fallback to the traditional method using only persona_details_map
                success, segment_path = await self.audio_stitching_service.generate_audio_for_dialogue_turn(
                    turn, podcast_id, persona_details_map
                )
            
            if success:
                segment_paths.append(segment_path)
                logger.info(f"[AUDIO_STITCH] Generated audio for turn {turn.turn_id}: {segment_path}")
            else:
                failed_segments.append(turn.turn_id)
                logger.error(f"[AUDIO_STITCH] Failed to generate audio for turn {turn.turn_id}")
        
        # If all segments failed, return error
        if not segment_paths:
            logger.error("[AUDIO_STITCH] All audio segments failed to generate")
            return ""
        
        if failed_segments:
            logger.warning(f"[AUDIO_STITCH] Failed to generate audio for {len(failed_segments)} segments: {failed_segments}")
        
        # Stitch audio segments
        final_audio_path = self.path_manager.get_final_audio_path(podcast_id)
        success = await self.audio_stitching_service.stitch_audio_segments(
            segment_paths, final_audio_path, silence_duration_ms
        )
        
        if success:
            logger.info(f"[AUDIO_STITCH] Successfully stitched {len(segment_paths)} audio segments to {final_audio_path}")
            return final_audio_path
        else:
            logger.error("[AUDIO_STITCH] Failed to stitch audio segments")
            # Return first segment as fallback if available, otherwise empty string
            return segment_paths[0] if segment_paths else ""

    def copy_audio_files_from_temp(self, tmp_dir: str, podcast_id: str) -> bool:
        """
        Copy audio files from temporary directory to permanent outputs location.
        
        Args:
            tmp_dir: Path to the temporary directory containing audio files
            podcast_id: Unique identifier for the podcast
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"[AUDIO_COPY] Copying audio files from {tmp_dir} to permanent location")
            
            # Create podcast directories
            podcast_dir, segments_dir = self.path_manager.create_podcast_directories(podcast_id)
            
            # Check if we have a final podcast file to copy
            temp_final_path = os.path.join(tmp_dir, "final_podcast.mp3")
            if os.path.exists(temp_final_path):
                final_path = self.path_manager.get_final_audio_path(podcast_id)
                shutil.copy2(temp_final_path, final_path)
                logger.info(f"[AUDIO_COPY] Copied final podcast audio to {final_path}")
            else:
                logger.warning(f"[AUDIO_COPY] Final podcast audio not found at {temp_final_path}")
                return False
                
            # Copy segment files if they exist
            temp_segments_dir = os.path.join(tmp_dir, "audio_segments")
            if os.path.exists(temp_segments_dir) and os.path.isdir(temp_segments_dir):
                for filename in os.listdir(temp_segments_dir):
                    if filename.endswith(".mp3"):
                        src_path = os.path.join(temp_segments_dir, filename)
                        # Extract turn_id from filename
                        try:
                            turn_id = int(filename.split("_")[1].split(".")[0])
                            dest_path = self.path_manager.get_segment_path(podcast_id, turn_id)
                            shutil.copy2(src_path, dest_path)
                            logger.info(f"[AUDIO_COPY] Copied segment {filename} to {dest_path}")
                        except (IndexError, ValueError):
                            # If filename doesn't match expected format, copy to segments dir with original name
                            dest_path = os.path.join(segments_dir, filename)
                            shutil.copy2(src_path, dest_path)
                            logger.info(f"[AUDIO_COPY] Copied segment with original name {filename} to {dest_path}")
            
            return True
        except Exception as e:
            logger.error(f"[AUDIO_COPY] Error copying audio files: {e}")
            return False

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
            
            # Initialize persona details map with default Host entry
            persona_details_map: dict[str, dict[str, str]] = {}
            persona_details_map["Host"] = {
                "invented_name": "Alex",  # Use a neutral name for the Host
                "gender": "neutral", # Default Host gender, using neutral for better inclusivity
                "real_name": "Host"
            }
            
            # Initial processing of persona research JSON into objects
            initial_persona_research_objects: List[PersonaResearch] = []
            for pr_json_str in persona_research_docs_content:
                try:
                    pr_data = json.loads(pr_json_str)
                    # Create PersonaResearch object from the JSON data
                    initial_persona_research_objects.append(PersonaResearch(**pr_data))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse PersonaResearch JSON: {e}. Content: {pr_json_str[:100]}")
                except Exception as e:
                    logger.error(f"Error processing persona research: {e}. Data: {pr_json_str[:100]}")

            # Assign names and genders, and populate enhanced PersonaResearch objects
            male_name_idx = 0
            female_name_idx = 0
            neutral_name_idx = 0
            processed_persona_research_objects: List[PersonaResearch] = []
            
            for pr_obj in initial_persona_research_objects:
                try:
                    person_id = pr_obj.person_id
                    real_name = pr_obj.name
                    
                    # Default to neutral gender for all personas
                    assigned_gender = "neutral"
                    
                    # Select invented name based on gender
                    if assigned_gender.lower() == "male":
                        invented_name = MALE_INVENTED_NAMES[male_name_idx % len(MALE_INVENTED_NAMES)]
                        male_name_idx += 1
                    elif assigned_gender.lower() == "female":
                        invented_name = FEMALE_INVENTED_NAMES[female_name_idx % len(FEMALE_INVENTED_NAMES)]
                        female_name_idx += 1
                    else:  # neutral or anything else
                        invented_name = NEUTRAL_INVENTED_NAMES[neutral_name_idx % len(NEUTRAL_INVENTED_NAMES)]
                        neutral_name_idx += 1
                    
                    # Create an enhanced PersonaResearch object with the new fields
                    enhanced_pr_obj = PersonaResearch(
                        **pr_obj.model_dump(),  # Get all existing fields
                        invented_name=invented_name,
                        gender=assigned_gender,
                        creation_date=datetime.now(),
                        # We're not setting tts_voice_id yet - will be part of future enhancement
                    )
                    processed_persona_research_objects.append(enhanced_pr_obj)
                    
                    # Also maintain the persona_details_map for backward compatibility
                    persona_details_map[person_id] = {
                        "invented_name": invented_name,
                        "gender": assigned_gender,
                        "real_name": real_name
                    }
                    
                    logger.info(f"Assigned to {person_id} ({real_name}): Invented Name='{invented_name}', Gender='{assigned_gender}'")
                except Exception as e:
                    logger.error(f"Error building persona details for {pr_obj.person_id}: {e}")
                    # Still add the original object to maintain the workflow
                    processed_persona_research_objects.append(pr_obj)
            
            logger.info(f"Final persona_details_map: {persona_details_map}")
            logger.info(f"Processed {len(processed_persona_research_objects)} persona research objects with extended fields")

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
                        persona_research_docs=processed_persona_research_objects,  # Use the processed objects instead of JSON strings
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
                        
                        # Process audio for the podcast
                        try:
                            # Generate a unique ID for this podcast
                            podcast_id = str(uuid.uuid4())
                            logger.info(f"[AUDIO_STITCH] Generated podcast ID: {podcast_id}")
                            
                            # Configure silence duration between segments (in milliseconds)
                            silence_duration_ms = 500
                            
                            # Process audio for the podcast
                            audio_filepath = await self._process_audio_for_podcast(
                                dialogue_turns_list, 
                                podcast_id,
                                persona_details_map,
                                silence_duration_ms
                            )
                            
                            if audio_filepath:
                                logger.info(f"Final podcast audio available at: {audio_filepath}")
                                podcast_episode_data['audio_filepath'] = audio_filepath
                            else:
                                warnings_list.append("Failed to generate stitched audio file")
                                logger.error("Audio stitching failed, no audio file produced")
                                podcast_episode_data['audio_filepath'] = "" # Empty string if audio generation failed
                        except Exception as e:
                            logger.error(f"Error during audio processing: {e}", exc_info=True)
                            warnings_list.append(f"Audio processing error: {e}")
                            podcast_episode_data['audio_filepath'] = "" # Empty string if audio generation failed
                    else:
                        logger.error("Dialogue generation returned None or empty list of turns.")
                        warnings_list.append("Dialogue generation failed to produce turns.")
                        podcast_transcript = "Error: Dialogue generation failed."
                        podcast_episode_data['transcript'] = podcast_transcript
                        podcast_episode_data['audio_filepath'] = "" # Empty string if dialogue generation failed

                except LLMProcessingError as e:
                    logger.error(f"LLMProcessingError during dialogue generation: {e}")
                    warnings_list.append(f"LLM processing error during dialogue generation: {e}")
                    podcast_episode_data['transcript'] = f"Error: LLM processing failed during dialogue generation. Details: {e}"
                    podcast_episode_data['audio_filepath'] = "" # Empty string if dialogue generation failed
                except Exception as e:
                    logger.error(f"Unexpected error during dialogue generation: {e}", exc_info=True)
                    warnings_list.append(f"Critical error during dialogue generation: {e}")
                    podcast_transcript = f"Error: Critical error during dialogue generation. Details: {e}"
                    podcast_episode_data['transcript'] = podcast_transcript
                    podcast_episode_data['audio_filepath'] = "" # Empty string if dialogue generation failed
            else:
                warnings_list.append("Skipping dialogue generation as outline or extracted_text is missing.")
                podcast_transcript = "Dialogue generation skipped due to missing prerequisites."
                podcast_episode_data['transcript'] = podcast_transcript
                podcast_episode_data['audio_filepath'] = "" # Empty string if dialogue generation was skipped

            # Return the final podcast episode
            return PodcastEpisode(
                title=podcast_title,
                summary=podcast_summary,
                transcript=podcast_transcript,
                audio_filepath=podcast_episode_data.get('audio_filepath', ""),
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

