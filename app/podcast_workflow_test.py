import asyncio
import json
import logging
import os
import tempfile
import sys
from typing import List, Optional, Any, Tuple
from pydantic import ValidationError

# Add the project root to the Python path so we can import modules correctly
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from app directly
from .podcast_models import SourceAnalysis, PersonaResearch, OutlineSegment, DialogueTurn, PodcastOutline, PodcastEpisode, BaseModel
from .common_exceptions import LLMProcessingError, ExtractionError
from .content_extractor import extract_content_from_url, extract_text_from_pdf_path
from .llm_service import GeminiService
from .tts_service import GoogleCloudTtsService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Placeholder for the input data model to generate_podcast_from_source
class PodcastRequest(BaseModel):
    source_urls: Optional[List[str]] = None  # Support for multiple source URLs
    source_pdf_path: Optional[str] = None
    prominent_persons: Optional[List[str]] = None
    desired_podcast_length_str: Optional[str] = None
    custom_prompt_for_outline: Optional[str] = None
    host_invented_name: Optional[str] = None # Added for host persona customization
    host_gender: Optional[str] = None # Added for host persona customization
    custom_prompt_for_dialogue: Optional[str] = None # Added for dialogue generation customization
    
    @property
    def has_valid_sources(self) -> bool:
        """Check if the request has at least one valid source."""
        return (self.source_urls and len(self.source_urls) > 0) or (self.source_pdf_path is not None)

class PodcastGeneratorService:
    def __init__(self):
        # Initialize services
        try:
            self.llm_service = GeminiService()
            logger.info("LLM Service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Service: {e}")
            self.llm_service = None

        try:
            self.tts_service = GoogleCloudTtsService()
            logger.info("TTS Service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize TTS Service: {e}")
            self.tts_service = None

    async def _stitch_audio_segments_async(self, audio_file_paths: List[str], output_dir: str) -> Optional[str]:
        """
        Stitch multiple audio segments into a single audio file.
        """
        if not audio_file_paths:
            logger.error("No audio file paths provided for stitching.")
            return None

        try:
            # Import pydub inside the method to avoid importing issues if not available
            from pydub import AudioSegment
            
            combined = None
            
            for audio_path in audio_file_paths:
                if not os.path.exists(audio_path):
                    logger.warning(f"Audio file not found: {audio_path}")
                    continue
                    
                try:
                    segment = AudioSegment.from_mp3(audio_path)
                    if combined is None:
                        combined = segment
                    else:
                        combined += segment
                except Exception as e:
                    logger.error(f"Error processing audio file {audio_path}: {e}")
            
            if combined is None:
                logger.error("No valid audio segments could be processed.")
                return None
                
            output_path = os.path.join(output_dir, "final_podcast.mp3")
            combined.export(output_path, format="mp3")
            logger.info(f"Successfully stitched audio to: {output_path}")
            return output_path
            
        except ImportError as e:
            logger.error(f"Required audio processing library not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error during audio stitching: {e}")
            return None

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
        llm_dialogue_turns_filepath: Optional[str] = None
        individual_turn_audio_paths: List[str] = [] # NEW: To hold paths to individual dialogue turn audio files

        source_analyses_content: List[str] = []
        persona_research_docs_content: List[str] = []

        podcast_title = "Generation Incomplete"
        podcast_summary = "Full generation pending or failed at an early stage."
        podcast_transcript = "Transcript generation pending."
        warnings_list: List[str] = []
        podcast_episode_data: dict = {} # Initialize the dictionary

        # Create a non-cleaning temporary directory for testing
        tmpdir_path = tempfile.mkdtemp(prefix="podcast_job_")
        logger.info(f"Created NON-CLEANING temporary directory for podcast job: {tmpdir_path}")
        
        try:
            logger.info(f"STEP_ENTRY: generate_podcast_from_source for request_data.source_urls: {request_data.source_urls}, request_data.source_pdf_path: {request_data.source_pdf_path}")
            
            # 2. Content Extraction
            logger.info("STEP: Starting Content Extraction...")
            extracted_texts: List[str] = []
            source_attributions: List[str] = []
            
            # Process multiple URLs if provided
            if request_data.source_urls:
                for url in request_data.source_urls:
                    try:
                        text = await extract_content_from_url(str(url))
                        if text:
                            extracted_texts.append(text)
                            source_attributions.append(url)
                            logger.info(f"Successfully extracted text from URL: {url}")
                        else:
                            logger.warning(f"Empty content extracted from URL: {url}")
                    except ExtractionError as e:
                        logger.error(f"Content extraction from URL {url} failed: {e}")
                        warnings_list.append(f"Failed to extract content from URL {url}: {e}")
            
            # Process PDF if provided (as a fallback or additional source)
            if request_data.source_pdf_path and not extracted_texts:  # Only use PDF if no URLs worked
                try:
                    pdf_path_str = str(request_data.source_pdf_path)
                    text = await extract_text_from_pdf_path(pdf_path_str)
                    if text:
                        extracted_texts.append(text)
                        source_attributions.append(pdf_path_str)
                        logger.info(f"Successfully extracted text from PDF path: {pdf_path_str}")
                    else:
                        logger.warning(f"Empty content extracted from PDF: {pdf_path_str}")
                except ExtractionError as e:
                    logger.error(f"Content extraction from PDF path {request_data.source_pdf_path} failed: {e}")
                    warnings_list.append(f"Failed to extract content from PDF: {e}")
            
            # Combine all extracted texts with source markers
            combined_text = ""
            if extracted_texts:
                for i, text in enumerate(extracted_texts):
                    source_marker = f"\n\n--- SOURCE {i+1}: {source_attributions[i]} ---\n\n"
                    combined_text += source_marker + text
                logger.info(f"Combined {len(extracted_texts)} sources into a single text for analysis.")
            else:
                logger.warning("No content could be extracted from any sources.")
                return PodcastEpisode(title="Error", summary="No Content Extracted", transcript="", audio_filepath="", 
                                     source_attributions=[], warnings=["No content could be extracted from any sources."])
                
            extracted_text = combined_text  # Use the combined text for subsequent processing

            logger.info("STEP: Text extraction phase complete. Extracted text is present. Moving to Source Analysis.")
            
            # 3. LLM - Source Analysis
            logger.info("STEP: Starting Source Analysis...")
            source_analysis_obj: Optional[SourceAnalysis] = None
            try:
                logger.info("STEP: Attempting LLM Source Analysis...")
                # llm_service.analyze_source_text_async now returns a SourceAnalysis object directly or raises an error
                source_analysis_obj = await self.llm_service.analyze_source_text_async(extracted_text)
                
                if source_analysis_obj:
                    logger.info("Source analysis successful.")
                    source_analyses_content.append(source_analysis_obj.model_dump_json()) # For LLM input
                    llm_source_analysis_filepath = os.path.join(tmpdir_path, "source_analysis.json")
                    with open(llm_source_analysis_filepath, 'w') as f:
                        json.dump(source_analysis_obj.model_dump(), f, indent=2) # Save the model dump
                    logger.info(f"Source analysis saved to {llm_source_analysis_filepath}")
                    logger.info(f"STEP: Source Analysis object created successfully: {source_analysis_obj is not None}")
                else:
                    # This case should ideally not be reached if analyze_source_text_async raises an error on failure or returns None
                    logger.error("LLM source analysis returned no data (or None unexpectedly).")
                    warnings_list.append("LLM source analysis returned no data.")

            except LLMProcessingError as llm_e: # Catch specific LLM errors from the service
                logger.error(f"LLM processing error during source analysis: {llm_e}")
                warnings_list.append(f"LLM source analysis failed: {llm_e}")
            except ValidationError as val_e: # Catch Pydantic validation errors (e.g., if service returns malformed data that passes initial parsing but fails model validation)
                logger.error(f"Validation error during source analysis processing: {val_e}")
                warnings_list.append(f"Source analysis validation failed: {val_e}")
            except Exception as e: # Catch any other unexpected errors
                logger.error(f"Error during source analysis: {e}", exc_info=True)
                warnings_list.append(f"Critical error during source analysis: {e}")

            logger.info("STEP: Source Analysis phase complete.")
            
            # 4. LLM - Persona Research (Iterative)
            logger.info("STEP: Starting Persona Research...")
            persona_research_objects: List[PersonaResearch] = []
            if request_data.prominent_persons and extracted_text:
                for person_name in request_data.prominent_persons:
                    try:
                        logger.info(f"STEP: Attempting Persona Research for '{person_name}'...")
                        persona_research_obj = await self.llm_service.research_persona_async(
                            source_text=extracted_text, person_name=person_name
                        )
                        if persona_research_obj:
                            logger.info(f"STEP: Persona Research for '{person_name}' successful. Object created.")
                            persona_research_docs_content.append(persona_research_obj.model_dump_json())
                            # Save persona research to file
                            persona_research_filepath = os.path.join(tmpdir_path, f"persona_research_{persona_research_obj.person_id}.json")
                            with open(persona_research_filepath, "w") as f:
                                json.dump(json.loads(persona_research_obj.model_dump_json()), f, indent=2)
                            llm_persona_research_filepaths.append(persona_research_filepath)
                            logger.info(f"Persona research for {person_name} saved to {persona_research_filepath}")
                            
                            # Print detailed information about the PersonaResearch object
                            print(f"\n============ PersonaResearch for {person_name} ============")
                            print(f"Person ID: {persona_research_obj.person_id}")
                            print(f"Name: {persona_research_obj.name}")
                            # Print the first 500 characters of the detailed profile, then first 50 chars of each additional 1000 chars
                            profile = persona_research_obj.detailed_profile
                            print(f"Detailed Profile (first 500 chars):\n{profile[:500]}...")
                            
                            # For very long profiles, print previews of each section
                            if len(profile) > 500:
                                sections = ["PART 1:", "PART 2:", "PART 3:", "PART 4:", "PART 5:"]
                                for section in sections:
                                    pos = profile.find(section)
                                    if pos > -1:
                                        print(f"\n{section} Preview: {profile[pos:pos+100]}...")
                            
                            print(f"Full PersonaResearch saved to: {persona_research_filepath}")
                            print("="*60 + "\n")
                        else:
                            logger.error(f"Persona research for {person_name} returned None.")
                            warnings_list.append(f"Persona research for {person_name} failed to produce a result.")
                    except ValueError as e:
                        logger.error(f"Persona research for {person_name} failed (ValueError): {e}", exc_info=True)
                        warnings_list.append(f"Persona research for {person_name} failed: {e}")
                        logger.error(f"STEP: Persona Research for '{person_name}' FAILED.")
                    except Exception as e:
                        logger.error(f"Unexpected error during persona research for {person_name}: {e}", exc_info=True)
                        warnings_list.append(f"Unexpected error in persona research for {person_name}: {e}")
            else:
                logger.info("No prominent persons requested or no extracted text for persona research.")

            logger.info(f"STEP: Persona Research complete. Found {len(persona_research_docs_content)} personas researched.")

            # 4.5. Assign Invented Names and Genders to Personas (mirroring podcast_workflow.py)
            logger.info("STEP: Assigning invented names and genders to personas...")
            persona_details_map: dict[str, dict[str, str]] = {}
            # Ensure Host is always in the map with a default or assigned invented name/gender
            persona_details_map["Host"] = {
                "invented_name": request_data.host_invented_name or "Alex",
                "gender": request_data.host_gender or "neutral",
                "real_name": "Host"
            }

            MALE_INVENTED_NAMES = ["Liam", "Noah", "Oliver", "Elijah", "James", "William", "Benjamin", "Lucas", "Henry", "Theodore"]
            FEMALE_INVENTED_NAMES = ["Olivia", "Emma", "Charlotte", "Amelia", "Sophia", "Isabella", "Ava", "Mia", "Evelyn", "Luna"]
            NEUTRAL_INVENTED_NAMES = ["Kai", "Rowan", "River", "Phoenix", "Sage", "Justice", "Remy", "Dakota", "Skyler", "Alexis"]
            used_male_names = set()
            used_female_names = set()
            used_neutral_names = set()

            for idx, pr_json_str in enumerate(persona_research_docs_content):
                try:
                    pr_data = json.loads(pr_json_str)
                    persona_research_obj_temp = PersonaResearch(**pr_data)
                    person_id = persona_research_obj_temp.person_id
                    real_name = persona_research_obj_temp.name
                    # Defaulting gender as current PersonaResearch model has no 'attributes' field for gender
                    assigned_gender = "neutral"
                    
                    invented_name = "Unknown Person"
                    if assigned_gender == "male":
                        available_names = [name for name in MALE_INVENTED_NAMES if name not in used_male_names]
                        if not available_names: available_names = MALE_INVENTED_NAMES # fallback if all used
                        invented_name = available_names[idx % len(available_names)]
                        used_male_names.add(invented_name)
                    elif assigned_gender == "female":
                        available_names = [name for name in FEMALE_INVENTED_NAMES if name not in used_female_names]
                        if not available_names: available_names = FEMALE_INVENTED_NAMES
                        invented_name = available_names[idx % len(available_names)]
                        used_female_names.add(invented_name)
                    else: # neutral or unknown
                        available_names = [name for name in NEUTRAL_INVENTED_NAMES if name not in used_neutral_names]
                        if not available_names: available_names = NEUTRAL_INVENTED_NAMES
                        invented_name = available_names[idx % len(available_names)]
                        used_neutral_names.add(invented_name)

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
            logger.info("STEP: Starting Podcast Outline Generation...")
            podcast_outline_obj: Optional[PodcastOutline] = None
            if extracted_text:
                try:
                    logger.info("STEP: Attempting LLM Podcast Outline Generation...")
                    num_persons = len(request_data.prominent_persons) if request_data.prominent_persons else 0
                    # Use desired_podcast_length_str directly from request_data as PodcastRequest model defines it as such
                    desired_length_str = request_data.desired_podcast_length_str

                    podcast_outline_obj = await self.llm_service.generate_podcast_outline_async(
                        source_analyses=source_analyses_content, 
                        persona_research_docs=persona_research_docs_content,
                        desired_podcast_length_str=desired_length_str or "5-7 minutes",
                        num_prominent_persons=num_persons,
                        names_prominent_persons_list=request_data.prominent_persons,
                        persona_details_map=persona_details_map, # ADDED THIS ARGUMENT
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
                        
                        # Display the formatted outline in the terminal
                        print("\n=== Generated Podcast Outline ===\n")
                        print(podcast_outline_obj.format_for_display())
                        print("\n=== End of Outline ===\n")
                    else:
                        logger.error("Podcast outline generation returned None.")
                        warnings_list.append("Podcast outline generation failed to produce an outline.")
                except Exception as e:
                    logger.error(f"Error during podcast outline generation: {e}", exc_info=True)
                    warnings_list.append(f"Critical error during podcast outline generation: {e}")
            else:
                warnings_list.append("Skipping outline generation as extracted_text is empty.")

            logger.info("STEP: Podcast Outline Generation phase complete.")
            
            # 6. LLM - Dialogue Turns Generation
            logger.info("STEP: Starting Dialogue Turns Generation...")
            dialogue_turns_list: Optional[List[DialogueTurn]] = None
            if podcast_outline_obj and extracted_text:
                try:
                    logger.info("STEP: Attempting LLM Dialogue Turns Generation...")
                    prominent_persons_details_for_dialogue: List[Tuple[str, str, str]] = []
                    if request_data.prominent_persons:
                        for name in request_data.prominent_persons:
                            initial = name[0].upper() if name else "X"
                            gender_for_tts = "neutral" # Default
                            prominent_persons_details_for_dialogue.append((name, initial, gender_for_tts))
                    
                    logger.info("STEP: Attempting LLM Dialogue Turns Generation...")

                    # Convert JSON strings to Pydantic objects for generate_dialogue_async
                    source_analysis_objects = []
                    if source_analyses_content: # Should always be true if we reached here
                        try:
                            sa_data = json.loads(source_analyses_content[0]) # Expecting only one source analysis doc
                            source_analysis_objects.append(SourceAnalysis(**sa_data))
                        except (json.JSONDecodeError, TypeError, ValidationError) as e:
                            logger.error(f"Failed to parse source_analyses_content for dialogue generation: {e}", exc_info=True)
                            warnings_list.append("Failed to process source analysis for dialogue generation.")
                            # Potentially raise or handle error to prevent proceeding with bad data
                    
                    persona_research_objects_for_dialogue = []
                    for pr_json_str in persona_research_docs_content:
                        try:
                            pr_data = json.loads(pr_json_str)
                            persona_research_objects_for_dialogue.append(PersonaResearch(**pr_data))
                        except (json.JSONDecodeError, TypeError, ValidationError) as e:
                            logger.error(f"Failed to parse a persona_research_doc for dialogue generation: {e}", exc_info=True)
                            warnings_list.append("Failed to process one or more persona research docs for dialogue.")
                            # Potentially skip this persona or handle error

                    dialogue_turns_list = await self.llm_service.generate_dialogue_async(
                        podcast_outline=podcast_outline_obj,
                        source_analyses=source_analysis_objects, 
                        persona_research_docs=persona_research_objects_for_dialogue,
                        persona_details_map=persona_details_map,
                        user_custom_prompt_for_dialogue=request_data.custom_prompt_for_dialogue
                    )

                    if dialogue_turns_list:
                        logger.info(f"Podcast dialogue turns generated successfully ({len(dialogue_turns_list)} turns).")
                        llm_dialogue_turns_filepath = os.path.join(tmpdir_path, "dialogue_turns.json")
                        serialized_turns = [turn.model_dump() for turn in dialogue_turns_list]
                        with open(llm_dialogue_turns_filepath, 'w') as f:
                            json.dump(serialized_turns, f, indent=2)
                        logger.info(f"Dialogue turns saved to {llm_dialogue_turns_filepath}")
                        
                        transcript_parts = [f"{turn.speaker_id}: {turn.text}" for turn in dialogue_turns_list]
                        podcast_transcript = "\n".join(transcript_parts)
                        logger.info("Transcript constructed from dialogue turns.")
                    else:
                        logger.error("Dialogue generation returned None or empty list of turns.")
                        warnings_list.append("Dialogue generation failed to produce turns.")
                        podcast_transcript = "Error: Dialogue generation failed."

                except LLMProcessingError as e:
                    logger.error(f"LLMProcessingError during dialogue generation: {e}", exc_info=True)
                    warnings_list.append(f"LLM processing error during dialogue generation: {e}")
                    podcast_transcript = f"Error: LLM processing failed during dialogue generation. {e}"
                except Exception as e:
                    logger.error(f"Unexpected error during dialogue generation: {e}", exc_info=True)
                    warnings_list.append(f"Critical error during dialogue generation: {e}")
                    podcast_transcript = f"Error: Critical error during dialogue generation. {e}"
            else:
                warnings_list.append("Skipping dialogue generation as outline or extracted_text is missing.")
                podcast_transcript = "Dialogue generation skipped due to missing prerequisites."

            logger.info("STEP: Dialogue Turns Generation phase complete.")
            
            # 7. TTS Generation for Dialogue Turns
            logger.info("STEP: Starting TTS generation for dialogue turns...")
            if dialogue_turns_list and self.tts_service:
                audio_segments_dir = os.path.join(tmpdir_path, "audio_segments")
                os.makedirs(audio_segments_dir, exist_ok=True)
                logger.info(f"Created directory for audio segments: {audio_segments_dir}")

                for i, turn in enumerate(dialogue_turns_list):
                    turn_audio_filename = f"turn_{i:03d}_{turn.speaker_id.replace(' ','_')}.mp3"
                    turn_audio_filepath = os.path.join(audio_segments_dir, turn_audio_filename)
                    logger.info(f"Generating TTS for turn {i} (Speaker: {turn.speaker_id}): {turn.text[:50]}...")
                    try:
                        logger.info(f"STEP: Attempting TTS for turn {i}...")
                        success = await self.tts_service.text_to_audio_async(
                            text_input=turn.text,
                            output_filepath=turn_audio_filepath,
                            speaker_gender=turn.speaker_gender if hasattr(turn, 'speaker_gender') else "neutral"
                        )
                        if success:
                            individual_turn_audio_paths.append(turn_audio_filepath)
                            logger.info(f"STEP: TTS for turn {i} successful. Audio saved to {turn_audio_filepath}")
                            logger.info(f"Generated audio for turn {i}: {turn_audio_filepath}")
                        else:
                            logger.warning(f"STEP: TTS for turn {i} FAILED. Skipping audio for this turn.")
                            logger.warning(f"TTS generation failed for turn {i}. Skipping audio for this turn.")
                            warnings_list.append(f"TTS failed for turn {i}: {turn.text[:30]}...")
                    except Exception as e:
                        logger.error(f"Error during TTS for turn {i}: {e}", exc_info=True)
                        warnings_list.append(f"TTS critical error for turn {i}: {e}")
                
                logger.info(f"STEP: TTS generation for all turns complete. {len(individual_turn_audio_paths)} audio files generated.")
            else:
                logger.warning("No dialogue turns available for TTS processing or TTS service missing.")
                warnings_list.append("TTS skipped: No dialogue turns or TTS service missing.")
                logger.info("STEP: Skipping TTS generation as no dialogue turns are available or tts_service is missing.")
            
            # 8. Audio Stitching
            logger.info("STEP: Starting audio stitching...")
            final_audio_filepath = "placeholder_error.mp3"  # Default in case of issues
            if individual_turn_audio_paths:
                logger.info(f"Attempting to stitch {len(individual_turn_audio_paths)} audio segments.")
                logger.info(f"STEP: Attempting to stitch {len(individual_turn_audio_paths)} audio segments...")
                stitched_audio_path = await self._stitch_audio_segments_async(individual_turn_audio_paths, tmpdir_path)
                if stitched_audio_path and os.path.exists(stitched_audio_path):
                    final_audio_filepath = stitched_audio_path
                    logger.info(f"STEP: Audio stitching successful. Final audio at {final_audio_filepath}")
                else:
                    logger.error("STEP: Audio stitching FAILED or produced no output.")
                    logger.error("Audio stitching failed or no audio segments were available.")
                    warnings_list.append("Audio stitching failed or produced no output.")
            else:
                logger.warning("No individual audio segments to stitch.")
                warnings_list.append("Audio stitching skipped: No audio segments available.")
            logger.info("STEP: Audio stitching phase complete.")

            # Final PodcastEpisode construction
            podcast_episode = PodcastEpisode(
                title=podcast_title,
                summary=podcast_summary,
                transcript=podcast_transcript,
                audio_filepath=final_audio_filepath, 
                source_attributions=source_attributions,  # Now includes all source URLs
                warnings=warnings_list,
                llm_source_analysis_path=llm_source_analysis_filepath,
                llm_persona_research_paths=llm_persona_research_filepaths if llm_persona_research_filepaths else None,
                llm_podcast_outline_path=llm_podcast_outline_filepath,
                llm_dialogue_turns_path=llm_dialogue_turns_filepath,
                dialogue_turn_audio_paths=individual_turn_audio_paths
            )
            logger.info(f"STEP_COMPLETED_TRY_BLOCK: PodcastEpisode object created. Title: {podcast_episode.title}, Audio: {podcast_episode.audio_filepath}, Warnings: {len(podcast_episode.warnings)}")
            return podcast_episode

        except Exception as main_e:
            logger.critical(f"STEP_CRITICAL_FAILURE: Unhandled exception in generate_podcast_from_source: {main_e}", exc_info=True)
            warnings_list.append(f"CRITICAL FAILURE: {main_e}")
            # Return a minimal error episode
            return PodcastEpisode(
                title="Critical Generation Error",
                summary=f"A critical error occurred: {main_e}",
                transcript="",
                audio_filepath=final_audio_filepath, # Might still be placeholder
                source_attributions=source_attributions if source_attributions else 
                    ([str(request_data.source_pdf_path)] if request_data.source_pdf_path else []),
                warnings=warnings_list
            )
        finally:
            logger.info(f"STEP_FINALLY: Temporary directory (NOT cleaned up): {tmpdir_path}")
            # Note: We're NOT removing tmpdir_path for debugging purposes

# Example usage for testing
async def main_workflow_test():
    # Configure logging if not already configured by the module-level basicConfig
    # logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Initializing PodcastGeneratorService for test run...")
    generator = PodcastGeneratorService()
    
    logger.info("Defining sample request data...")
    sample_request = PodcastRequest(
        source_urls=[
            "https://www.britannica.com/event/Battle-of-Jutland",
            "https://en.wikipedia.org/wiki/Battle_of_Jutland",
            "https://www.naval-history.net/WW1Battle1605Jutland1.htm"  # Third source for more detailed naval history
        ],
        prominent_persons=["Bernard Montgomery", "Erwin Rommel"],
        desired_podcast_length_str="17 minutes"
    )
    print(f"Starting podcast generation test with URLs: {sample_request.source_urls}, Persons: {sample_request.prominent_persons}, Length: {sample_request.desired_podcast_length_str}")
    try:
        episode = await generator.generate_podcast_from_source(sample_request)
        print("\n--- Podcast Generation Test Complete ---")
        print(f"Episode Title: {episode.title}")
        print(f"Episode Summary: {episode.summary}")
        print(f"Audio File Path: {episode.audio_filepath}")
        if episode.warnings:
            print("Warnings:")
            for warning in episode.warnings:
                print(f"  - {warning}")
        else:
            print("Warnings: None")
        
        print("\n--- Generated Transcript ---")
        print(episode.transcript)
        print("--- End of Transcript ---")

        # The temporary directory path is logged by the generate_podcast_from_source method's finally block.
        # Search for 'Temporary directory (NOT cleaned up)' in the logs.
        print("\nIntermediate files (JSON, audio segments) are in the temporary directory logged above (search for 'podcast_job_').")
    except Exception as e:
        print(f"An error occurred during the test workflow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main_workflow_test())
