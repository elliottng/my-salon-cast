import asyncio
import glob
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pydantic import ValidationError
import aiohttp
from .database import PodcastStatusDB
from .common_exceptions import PodcastGenerationError
from .status_manager import get_status_manager
from .storage_utils import ensure_directory_exists
from app.podcast_models import SourceAnalysis, PersonaResearch, OutlineSegment, DialogueTurn, PodcastOutline, PodcastEpisode, BaseModel, PodcastRequest, PodcastDialogue
from app.common_exceptions import LLMProcessingError, ExtractionError
from app.content_extractor import (
    extract_content_from_url, 
    extract_text_from_pdf_path, 
    extract_transcript_from_youtube
)
from app.llm_service import GeminiService
from app.tts_service import GoogleCloudTtsService
from app.task_runner import get_task_runner
from app.storage import CloudStorageManager
from app.config import setup_environment
from app.http_utils import send_webhook_with_retry, build_webhook_payload
from app.validations import is_valid_youtube_url
from app.utils.migration_helpers import (
    get_persona_by_id,
    convert_legacy_dialogue_json
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodcastGeneratorService:
    """
    Asynchronous podcast generation service for MySalonCast.
    
    This service provides a fully async-only architecture for generating podcasts from various content sources.
    It uses background task processing with status tracking, cancellation support, and webhook notifications.
    
    Key Features:
    - Async-only podcast generation with immediate task_id return
    - Background processing with real-time status updates
    - Support for multiple content sources (URLs, PDFs)
    - AI-powered persona research and dialogue generation
    - Text-to-speech with voice differentiation
    - Audio segment stitching for final podcast creation
    - Cancellation support and error handling
    - Cloud storage integration for artifacts
    
    Usage:
        service = PodcastGeneratorService()
        task_id = await service.generate_podcast_async(request_data)
        # Track progress via status API using task_id
    """
    def __init__(self):
        # Initialize configuration
        try:
            self.config = setup_environment()
            logger.info(f"Configuration initialized for environment: {self.config.environment}")
        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            self.config = None
            
        # Initialize TTS service first
        try:
            self.tts_service = GoogleCloudTtsService()
            logger.info("TTS Service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize TTS Service: {e}")
            self.tts_service = None

        # Initialize LLM service with TTS service dependency injection
        try:
            self.llm_service = GeminiService(tts_service=self.tts_service)
            logger.info("LLM Service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Service: {e}")
            self.llm_service = None

        try:
            self.cloud_storage_manager = CloudStorageManager()
            logger.info("Cloud Storage Manager initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage Manager: {e}")
            self.cloud_storage_manager = None
            
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

    async def generate_podcast_async(
        self,
        request_data: PodcastRequest
    ) -> str:
        """
        Generate a podcast episode asynchronously.
        Returns immediately with a task_id for status tracking.
        This is the single entry point for async podcast generation.
        
        Returns:
            str - The task_id for status tracking
        """
        # Generate new task ID
        task_id = str(uuid.uuid4())
        status_manager = get_status_manager()
        
        # Create initial status with request data
        status = status_manager.create_status(task_id, request_data.dict())
        logger.info(f"Created podcast generation task with ID: {task_id}")
        
        # Update status to preprocessing
        status_manager.update_status(
            task_id,
            "preprocessing_sources",
            "Validating request and preparing sources",
            5.0
        )
        
        # Check if we can accept a new task
        task_runner = get_task_runner()
        if not task_runner.can_accept_new_task():
            logger.warning(f"Task runner at capacity, cannot accept task {task_id}")
            status_manager.set_error(
                task_id,
                "System at capacity",
                f"Maximum concurrent podcast generations ({task_runner.max_workers}) reached. Please try again later."
            )
            # Task ID is still returned but with error status
            return task_id
        
        # Submit the task to run in the background
        try:
            # Submit async task directly to core processing method
            await task_runner.submit_async_task(
                task_id,
                self._run_podcast_generation_async,
                task_id,
                request_data
            )
            logger.info(f"Task {task_id} submitted for background processing")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to submit task {task_id} for background processing: {str(e)}")
            status_manager.set_error(
                task_id,
                "Failed to start background processing",
                str(e)
            )
            # Return task ID even on submission failure so user can check status
            return task_id
        
    async def _run_podcast_generation_async(self, task_id: str, request_data: PodcastRequest) -> None:
        """
        Wrapper function that runs podcast generation in a background task.
        This function is designed to be executed by the TaskRunner in a separate thread.
        
        Args:
            task_id: The unique identifier for this generation task
            request_data: The podcast generation request parameters
        """
        status_manager = get_status_manager()
        
        # Initialize variables that will be used in finally block
        import threading
        current_thread = threading.current_thread()
        
        try:
            logger.info(f"Starting background podcast generation for task {task_id}")
            
            # Set the task_id in a thread-local variable so we can check for cancellation
            current_thread.task_id = task_id  # type: ignore  # Dynamic attribute assignment for task tracking
            
            # Call the new core processing method directly
            podcast_episode = await self._execute_podcast_generation_core(task_id, request_data)
            
            logger.info(f"Background generation complete for task {task_id}")
            
            # Send webhook notification if configured
            if request_data.webhook_url:
                await self._send_webhook_notification(
                    request_data.webhook_url,
                    task_id,
                    "completed",
                    podcast_episode
                )
            
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} was cancelled")
            status_manager.update_status(
                task_id,
                "cancelled",
                "Task was cancelled by user request",
                progress=None  # Fixed: use 'progress' instead of 'progress_percentage'
            )
            
            # Send webhook notification for cancellation
            if request_data.webhook_url:
                await self._send_webhook_notification(
                    request_data.webhook_url,
                    task_id,
                    "cancelled",
                    None
                )
            
            raise  # Re-raise to properly handle cancellation
            
        except Exception as e:
            logger.error(f"Background task {task_id} failed with error: {str(e)}")
            status_manager.set_error(task_id, f"Background generation failed: {str(e)}")
            # Log the full traceback for debugging
            logger.exception("Exception details:")
            
            # Send webhook notification for failure
            if request_data.webhook_url:
                await self._send_webhook_notification(
                    request_data.webhook_url,
                    task_id,
                    "failed",
                    None,
                    error=str(e)
                )
            
        finally:
            logger.info(f"Background task {task_id} execution completed (success or failure)")
            # Clean up thread-local variable
            if hasattr(current_thread, 'task_id'):
                delattr(current_thread, 'task_id')
    
    async def _send_webhook_notification(
        self,
        webhook_url: str,
        task_id: str,
        status: str,
        podcast_episode: Optional[PodcastEpisode],
        error: Optional[str] = None
    ) -> None:
        """
        Send a webhook notification about task completion.
        
        Args:
            webhook_url: The URL to send the notification to
            task_id: The task ID
            status: The final status (completed, failed, cancelled)
            podcast_episode: The generated episode (if successful)
            error: Error message (if failed)
        """
        result = None
        
        if status == "completed" and podcast_episode:
            result = {
                "title": podcast_episode.title,
                "summary": podcast_episode.summary,
                "audio_filepath": podcast_episode.audio_filepath,
                "has_transcript": bool(podcast_episode.transcript),
                "source_count": len(podcast_episode.source_attributions),
                "warnings": podcast_episode.warnings
            }
        
        payload = build_webhook_payload(
            task_id=task_id,
            status=status,
            result=result,
            error=error
        )
        
        # Use the retry utility
        await send_webhook_with_retry(
            url=webhook_url,
            payload=payload,
            identifier=task_id
        )

    def _check_cancellation(self, task_id: Optional[str] = None) -> None:
        """
        Check if the current task has been cancelled.
        Raises CancelledError if the task was cancelled.
        
        Args:
            task_id: Optional task ID to check. If not provided, checks current async task.
        """
        if not task_id:
            # For async tasks, we'll need to get the task_id from context
            # This is simplified since we're moving away from thread-based execution
            return
        
        # Check if this task has been cancelled
        task_runner = get_task_runner()
        if task_id in task_runner._running_tasks:
            task = task_runner._running_tasks[task_id]
            if task.cancelled():
                raise asyncio.CancelledError(f"Task {task_id} was cancelled")

    def _select_host_voice(self, gender: str, used_voice_ids: set[str]) -> Tuple[str, Dict[str, float]]:
        """Select a host voice profile from the TTS cache avoiding conflicts."""
        default_profile = {"voice_id": "en-US-Chirp3-HD-Achird", "speaking_rate": 1.0}
        if not self.tts_service:
            logger.warning("TTS service unavailable, using fallback host voice")
            return default_profile["voice_id"], {
                "speaking_rate": default_profile["speaking_rate"]
            }
        try:
            voices = self.tts_service.get_voices_by_gender(gender)
            logger.debug(f"Retrieved {len(voices)} voices for host gender '{gender}'")
            available = [v for v in voices if v.get("voice_id") not in used_voice_ids]
            if not available:
                logger.debug("All host voices in use; allowing reuse")
                available = voices
            if not available:
                logger.warning(f"No voices available for gender '{gender}', using default")
                return default_profile["voice_id"], {
                    "speaking_rate": default_profile["speaking_rate"]
                }
            chosen = random.choice(available)
            voice_id = chosen.get("voice_id", default_profile["voice_id"])
            params = {
                "speaking_rate": chosen.get("speaking_rate", default_profile["speaking_rate"])
            }
            logger.debug(
                f"Host voice selected: {voice_id}, Params: {{'speaking_rate': {params['speaking_rate']}}}"
            )
            return voice_id, params
        except Exception as e:
            logger.error(f"Error selecting host voice: {e}")
            return default_profile["voice_id"], {
                "speaking_rate": default_profile["speaking_rate"]
            }

    async def _execute_podcast_generation_core(self, task_id: str, request_data: PodcastRequest) -> PodcastEpisode:
        """
        Core processing logic for podcast generation without task submission logic.
        This method does the actual work: content extraction, LLM analysis, persona research, 
        outline generation, dialogue generation, TTS, audio stitching.
        
        Args:
            task_id: Task identifier for status tracking and cancellation
            request_data: The podcast generation request parameters
            
        Returns:
            PodcastEpisode: The completed podcast episode
        """
        status_manager = get_status_manager()
        
        # Initialize variables used in exception handling
        source_attributions: List[str] = []  # Initialize to prevent unbound variable errors
        warnings_list: List[str] = []  # Initialize warnings list
        
        # Check for cancellation at the start
        self._check_cancellation(task_id)
        
        # Continue with processing logic 
        if not self.llm_service:
            logger.error("LLMService not available. Cannot generate podcast.")
            status_manager.set_error(
                task_id,
                "LLM Service Not Initialized",
                "The LLM service failed to initialize properly"
            )
            error_episode = PodcastEpisode(
                title="Error", 
                summary="LLM Service Not Initialized", 
                transcript="", 
                audio_filepath="",
                source_attributions=[], 
                warnings=["LLM Service failed to initialize."]
            )
            # Update the status with the error episode
            status_manager.set_episode(task_id, error_episode)
            return error_episode

        # Initialize containers for intermediate data - use Pydantic objects directly (Phase 5)
        source_analysis_obj: Optional[SourceAnalysis] = None  # Direct Pydantic object storage
        persona_research_objects: List[PersonaResearch] = []  # Direct Pydantic object storage
        llm_podcast_outline_filepath: Optional[str] = None
        llm_dialogue_turns_filepath: Optional[str] = None
        llm_transcript_filepath: Optional[str] = None
        individual_turn_audio_paths: List[str] = [] # NEW: To hold paths to individual dialogue turn audio files

        podcast_title = "Generation Incomplete"
        podcast_summary = "Full generation pending or failed at an early stage."
        podcast_transcript = "Transcript generation pending."
        podcast_episode_data: dict = {} # Initialize the dictionary

        # Create a non-cleaning temporary directory for testing
        tmpdir_path = tempfile.mkdtemp(prefix="podcast_job_")
        logger.info(f"Created NON-CLEANING temporary directory for podcast job: {tmpdir_path}")
        
        try:
            logger.info(f"STEP_ENTRY: Core processing for request_data.source_urls: {request_data.source_urls}, request_data.source_pdf_path: {request_data.source_pdf_path}")
            
            # Add cancellation checkpoint before content extraction
            self._check_cancellation(task_id)
            
            # 2. Content Extraction
            logger.info("STEP: Starting Content Extraction...")
            extracted_texts: List[str] = []
            source_attributions = []
            
            # Process multiple URLs if provided
            if request_data.source_urls:
                for url in request_data.source_urls:
                    try:
                        # Check if this is a YouTube URL and handle accordingly
                        if is_valid_youtube_url(str(url)):
                            logger.info(f"Detected YouTube URL, extracting transcript: {url}")
                            text = await extract_transcript_from_youtube(str(url))
                        else:
                            logger.info(f"Processing general URL: {url}")
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
                error_msg = "No content could be extracted from any sources."
                
                # Update status to failed before returning
                status_manager.set_error(task_id, error_msg)
                
                return PodcastEpisode(
                    title="Error", 
                    summary="No Content Extracted", 
                    transcript="", 
                    audio_filepath="", 
                    source_attributions=[], 
                    warnings=[error_msg]
                )
                
            extracted_text = combined_text  # Use the combined text for subsequent processing

            logger.info("STEP: Text extraction phase complete. Extracted text is present. Moving to Source Analysis.")
            
            # Update status after content extraction
            status_manager.update_status(
                task_id,
                "analyzing_sources",
                "Content extracted successfully, analyzing sources",
                15.0
            )
            status_manager.update_artifacts(
                task_id,
                source_content_extracted=True
            )
            
            # Check for cancellation after content extraction
            if task_id:
                self._check_cancellation(task_id)
            
            # 3. LLM - Source Analysis
            logger.info("STEP: Starting Source Analysis...")
            
            status_manager.add_progress_log(
                task_id,
                "analyzing_sources",
                "llm_source_analysis_start",
                f"Analyzing {len(extracted_text):,} characters of content"
            )
            
            try:
                logger.info("STEP: Attempting LLM Source Analysis...")
                status_manager.add_progress_log(
                    task_id,
                    "analyzing_sources",
                    "llm_processing",
                    "Sending content to LLM for analysis"
                )
                
                # llm_service.analyze_source_text_async now returns a SourceAnalysis object directly or raises an error
                source_analysis_obj = await self.llm_service.analyze_source_text_async(
                    extracted_text, 
                    analysis_instructions=""  # Using empty string as default analysis instructions
                )
                
                if source_analysis_obj:
                    logger.info("Source analysis successful.")
                    status_manager.add_progress_log(
                        task_id,
                        "analyzing_sources",
                        "llm_analysis_success",
                        f"✓ Generated analysis with {len(source_analysis_obj.summary_points)} points"
                    )
                    
                    logger.info(f"Source analysis created successfully: {source_analysis_obj is not None}")
                    
                    status_manager.add_progress_log(
                        task_id,
                        "analyzing_sources",
                        "analysis_saved",
                        f"Analysis saved to memory"
                    )
                else:
                    # This case should ideally not be reached if analyze_source_text_async raises an error on failure or returns None
                    logger.error("LLM source analysis returned no data (or None unexpectedly).")
                    warnings_list.append("LLM source analysis returned no data.")
                    status_manager.add_progress_log(
                        task_id,
                        "analyzing_sources",
                        "analysis_empty",
                        "⚠ LLM returned empty analysis"
                    )

            except LLMProcessingError as llm_e: # Catch specific LLM errors from the service
                logger.error(f"LLM processing error during source analysis: {llm_e}")
                warnings_list.append(f"LLM source analysis failed: {llm_e}")
                status_manager.add_progress_log(
                    task_id,
                    "analyzing_sources",
                    "llm_processing_error",
                    f"✗ LLM processing failed: {llm_e}"
                )
            except ValidationError as val_e: # Catch Pydantic validation errors (e.g., if service returns malformed data that passes initial parsing but fails model validation)
                logger.error(f"Validation error during source analysis processing: {val_e}")
                warnings_list.append(f"Source analysis validation failed: {val_e}")
                status_manager.add_progress_log(
                    task_id,
                    "analyzing_sources",
                    "validation_error", 
                    f"✗ Response validation failed: {val_e}"
                )
            except Exception as e: # Catch any other unexpected errors
                logger.error(f"Error during source analysis: {e}", exc_info=True)
                warnings_list.append(f"Critical error during source analysis: {e}")
                status_manager.add_progress_log(
                    task_id,
                    "analyzing_sources",
                    "critical_error",
                    f"✗ Critical error: {e}"
                )

            logger.info("STEP: Source Analysis phase complete.")
            
            # Update status after source analysis
            if source_analysis_obj:
                status_manager.update_status(
                    task_id,
                    "researching_personas",
                    f"Source analysis complete, researching personas with {len(source_analysis_obj.summary_points)} key points",
                    30.0
                )
                status_manager.update_artifacts(
                    task_id,
                    source_analysis_complete=True
                )
            
            # Check for cancellation after source analysis
            if task_id:
                self._check_cancellation(task_id)
            
            # 4. LLM - Persona Research (Iterative)
            logger.info("STEP: Starting Persona Research...")
            if request_data.prominent_persons and extracted_text:
                status_manager.add_progress_log(
                    task_id,
                    "researching_personas",
                    "persona_research_start",
                    f"Researching {len(request_data.prominent_persons)} person(s): {', '.join(request_data.prominent_persons)}"
                )
                
                for person_name in request_data.prominent_persons:
                    try:
                        logger.info(f"STEP: Attempting Persona Research for '{person_name}'...")
                        status_manager.add_progress_log(
                            task_id,
                            "researching_personas",
                            "persona_research_individual",
                            f"Researching {person_name}"
                        )
                        
                        persona_research_obj = await self.llm_service.research_persona_async(
                            source_text=extracted_text, person_name=person_name
                        )
                        if persona_research_obj:
                            logger.info(f"STEP: Persona Research for '{person_name}' successful. Object created.")
                            status_manager.add_progress_log(
                                task_id,
                                "researching_personas",
                                "persona_research_success",
                                f"✓ Generated persona research for {person_name}"
                            )
                            
                            persona_research_objects.append(persona_research_obj)
                            logger.info(f"Persona research for {person_name} saved to memory")
                            logger.info(f"STEP: Persona Research object created successfully: {persona_research_obj is not None}")
                            
                            status_manager.add_progress_log(
                                task_id,
                                "researching_personas",
                                "persona_saved",
                                f"Research saved to memory: {person_name}"
                            )
                        else:
                            logger.error(f"Persona research for {person_name} returned None.")
                            warnings_list.append(f"Persona research for {person_name} failed to produce a result.")
                            status_manager.add_progress_log(
                                task_id,
                                "researching_personas",
                                "persona_research_empty",
                                f"⚠ Persona research for {person_name} returned no data"
                            )
                    except ValueError as e:
                        logger.error(f"Persona research for {person_name} failed (ValueError): {e}", exc_info=True)
                        warnings_list.append(f"Persona research for {person_name} failed: {e}")
                        logger.error(f"STEP: Persona Research for '{person_name}' FAILED.")
                        status_manager.add_progress_log(
                            task_id,
                            "researching_personas",
                            "persona_research_error",
                            f"✗ Persona research failed for {person_name}: {e}"
                        )
            else:
                logger.info("No prominent persons requested or no extracted text for persona research.")

            logger.info(f"STEP: Persona Research complete. Found {len(persona_research_objects)} personas researched.")

            # Update status after persona research
            status_manager.update_status(
                task_id,
                "generating_outline",
                f"Researched {len(persona_research_objects)} personas, generating outline",
                45.0
            )
            status_manager.update_artifacts(
                task_id,
                persona_research_complete=True
            )

            # Check for cancellation after persona research
            if task_id:
                self._check_cancellation(task_id)
            
            # 4.5. Assign Invented Names and Genders to Personas
            logger.info("STEP: Assigning invented names and genders to personas...")
            # Create a map of PersonaResearch objects for easy lookup by person_id
            persona_research_map: dict[str, PersonaResearch] = {}
            
            for pr in persona_research_objects:
                person_id = pr.person_id
                real_name = pr.name
                
                # Use LLM service assignments (service layer provides reliable fallbacks)
                assigned_gender = pr.gender
                invented_name = pr.invented_name

                logger.info(f"Using persona assignments for {real_name}: gender='{assigned_gender}', invented_name='{invented_name}'")
                
                # Add to persona_research_map for efficient lookups by ID
                persona_research_map[person_id] = pr
                
            # Now create the Host persona using the TTS voice cache
            used_voice_ids = {
                details.tts_voice_id
                for details in persona_research_map.values()
                if details.tts_voice_id
            }
            host_voice_id, host_voice_params = self._select_host_voice(
                request_data.host_gender or "Female", used_voice_ids
            )
            
            # Create the Host persona and add to maps
            host_persona = PersonaResearch(
                person_id="Host",
                name="Host",
                detailed_profile="The podcast host is an engaging personality who is intellectually inquisitive and interested in fostering debate and viewpoint diversity",
                invented_name=request_data.host_invented_name or "Bridgette",
                gender=request_data.host_gender or "Female",
                tts_voice_id=host_voice_id,
                tts_voice_params=host_voice_params,
                source_context="Host persona created for podcast generation",  # Added missing parameter
                creation_date=datetime.now()  # Added missing parameter
            )
            
            # Add Host to maps
            persona_research_map["Host"] = host_persona
            persona_research_objects.append(host_persona)
            logger.info(
                f"Assigned to Host (Host): Invented Name='{request_data.host_invented_name or 'Bridgette'}', Gender='{request_data.host_gender or 'Female'}', Voice='{host_voice_id}', Params: {host_voice_params}"
            )
            
            logger.info(f"Final persona_research_map: {persona_research_map}")
            
            # Build persona_details_map from persona_research_map for backward compatibility
            # This provides the expected data structure for both outline and dialogue generation
            persona_details_map = {
                person_id: {
                    "invented_name": pr.invented_name,
                    "gender": pr.gender,
                    "real_name": pr.name
                }
                for person_id, pr in persona_research_map.items()
            }
            logger.info(f"Built persona_details_map for backward compatibility: {persona_details_map}")
            
            # 5. LLM - Podcast Outline Generation
            logger.info("STEP: Starting Podcast Outline Generation...")
            podcast_outline_obj: Optional[PodcastOutline] = None
            if extracted_text:
                # Check if we have source analysis data
                has_source_analysis = bool(source_analysis_obj)
                if not has_source_analysis:
                    logger.warning("Source analysis failed, but continuing with outline generation using extracted text only")
                    warnings_list.append("Outline generated without source analysis due to LLM processing errors")
                
                status_manager.add_progress_log(
                    task_id,
                    "generating_outline",
                    "outline_generation_start",
                    f"Generating outline from {len(persona_research_objects)} personas"
                )
                
                try:
                    logger.info("STEP: Attempting LLM Podcast Outline Generation...")
                    num_persons = len(request_data.prominent_persons) if request_data.prominent_persons else 0
                    # Use desired_podcast_length_str directly from request_data as PodcastRequest model defines it as such
                    desired_length_str = request_data.desired_podcast_length_str
                    
                    status_manager.add_progress_log(
                        task_id,
                        "generating_outline",
                        "outline_llm_processing",
                        f"Requesting outline for {desired_length_str or '5-7 minutes'} podcast with {num_persons} persons"
                    )

                    # If source analysis is missing, create a minimal fallback analysis from extracted text
                    fallback_source_analyses = [source_analysis_obj] if source_analysis_obj else []
                    if not has_source_analysis and extracted_text:
                        logger.info("Creating fallback source analysis for outline generation")
                        # Create a simple analysis structure that the outline generation can use
                        fallback_analysis = SourceAnalysis(
                            summary_points=["Content extracted from provided sources"],
                            detailed_analysis="Analysis of provided content extracted from available sources"
                        )
                        fallback_source_analyses = [fallback_analysis]
                        
                        status_manager.add_progress_log(
                            task_id,
                            "generating_outline",
                            "fallback_analysis_created",
                            "⚠ Created fallback analysis for outline generation"
                        )

                    # Fix None parameter passing issues for generate_podcast_outline_async method call
                    podcast_outline_obj = await self.llm_service.generate_podcast_outline_async(
                        source_analyses=fallback_source_analyses or [],  # Ensure never None
                        persona_research_docs=persona_research_objects,
                        desired_podcast_length_str=desired_length_str or "5-7 minutes",
                        num_prominent_persons=num_persons,
                        names_prominent_persons_list=request_data.prominent_persons or [],
                        persona_details_map=persona_details_map,
                        user_provided_custom_prompt=request_data.custom_prompt_for_outline or ""
                    )
                    if podcast_outline_obj:
                        logger.info("Podcast outline generated successfully.")
                        status_manager.add_progress_log(
                            task_id,
                            "generating_outline",
                            "outline_generation_success",
                            f"✓ Generated outline: {podcast_outline_obj.title_suggestion}"
                        )
                        
                        podcast_title = podcast_outline_obj.title_suggestion
                        podcast_summary = podcast_outline_obj.summary_suggestion
                        llm_podcast_outline_filepath = os.path.join(tmpdir_path, "podcast_outline.json")
                        with open(llm_podcast_outline_filepath, 'w') as f:
                            json.dump(podcast_outline_obj.model_dump(), f, indent=2)
                        logger.info(f"Podcast outline saved to {llm_podcast_outline_filepath}")
                        
                        status_manager.add_progress_log(
                            task_id,
                            "generating_outline",
                            "outline_saved",
                            f"Outline saved: {os.path.basename(llm_podcast_outline_filepath)}"
                        )
                        
                        # Display the formatted outline in the terminal
                        print("\n=== Generated Podcast Outline ===\n")
                        print(podcast_outline_obj.format_for_display())
                        print("\n=== End of Outline ===\n")
                    else:
                        logger.error("Podcast outline generation returned None.")
                        warnings_list.append("Podcast outline generation failed to produce an outline.")
                        status_manager.add_progress_log(
                            task_id,
                            "generating_outline",
                            "outline_generation_empty",
                            "⚠ Outline generation returned no data"
                        )
                except Exception as e:
                    logger.error(f"Error during podcast outline generation: {e}", exc_info=True)
                    warnings_list.append(f"Critical error during podcast outline generation: {e}")
                    status_manager.add_progress_log(
                        task_id,
                        "generating_outline",
                        "outline_generation_error",
                        f"✗ Outline generation failed: {e}"
                    )
            else:
                warnings_list.append("Skipping outline generation as extracted_text is empty.")
                status_manager.add_progress_log(
                    task_id,
                    "generating_outline",
                    "outline_skipped",
                    "⚠ Skipping outline generation - no content available"
                )

            logger.info("STEP: Podcast Outline Generation phase complete.")
            
            # Update status after outline generation
            if podcast_outline_obj:
                status_manager.update_status(
                    task_id,
                    "generating_dialogue",
                    "Outline complete, generating dialogue script",
                    60.0
                )
                status_manager.update_artifacts(
                    task_id,
                    podcast_outline_complete=True
                )
            
            # Check for cancellation after outline generation
            if task_id:
                self._check_cancellation(task_id)
            
            # 6. LLM - Dialogue Turns Generation
            logger.info("STEP: Starting Dialogue Turns Generation...")
            dialogue_turns_list: Optional[List[DialogueTurn]] = None
            if podcast_outline_obj and extracted_text:
                status_manager.add_progress_log(
                    task_id,
                    "generating_dialogue",
                    "dialogue_generation_start",
                    f"Generating dialogue for outline: '{podcast_outline_obj.title_suggestion}'"
                )
                
                try:
                    logger.info("STEP: Attempting LLM Dialogue Turns Generation...")
                    prominent_persons_details_for_dialogue: List[Tuple[str, str, str]] = []
                    if request_data.prominent_persons:
                        for name in request_data.prominent_persons:
                            initial = name[0].upper() if name else "X"
                            gender_for_tts = "Neutral" # Default
                            prominent_persons_details_for_dialogue.append((name, initial, gender_for_tts))
                    
                    logger.info("STEP: Attempting LLM Dialogue Turns Generation...")
                    
                    status_manager.add_progress_log(
                        task_id,
                        "generating_dialogue",
                        "dialogue_preprocessing",
                        f"Processing {len(persona_research_objects)} persona docs"
                    )

                    # Convert JSON strings to Pydantic objects using migration helpers for safe transition
                    source_analysis_objects = []
                    if source_analysis_obj: # Should always be true if we reached here
                        # Use migration helper for safe conversion
                        try:
                            source_analysis_objects = [source_analysis_obj]
                            if not source_analysis_objects:
                                logger.warning("No valid source analyses found after parsing")
                                warnings_list.append("Failed to process source analysis for dialogue generation.")
                                status_manager.add_progress_log(
                                    task_id,
                                    "generating_dialogue",
                                    "source_analysis_parse_warning",
                                    "⚠ No valid source analyses found"
                                )
                        except Exception as e:
                            logger.error(f"Failed to parse source_analyses_content for dialogue generation: {e}", exc_info=True)
                            warnings_list.append("Failed to process source analysis for dialogue generation.")
                            status_manager.add_progress_log(
                                task_id,
                                "generating_dialogue",
                                "source_analysis_parse_error",
                                f"✗ Failed to parse source analysis: {e}"
                            )
                     
                    # Use migration helper for safe persona research conversion
                    persona_research_objects_for_dialogue = persona_research_objects
                    
                    status_manager.add_progress_log(
                        task_id,
                        "generating_dialogue",
                        "dialogue_llm_processing",
                        f"Sending outline and context to LLM for dialogue generation with {len(source_analysis_objects)} sources and {len(persona_research_objects_for_dialogue)} personas"
                    )

                    # PHASE 3: Use new generate_with_fallback method for robust dialogue generation
                    dialogue_turns_list = await self.llm_service.generate_dialogue_async(
                        podcast_outline=podcast_outline_obj,
                        source_analyses=source_analysis_objects, 
                        persona_research_docs=persona_research_objects_for_dialogue,
                        persona_details_map=persona_details_map,  # Keep for backward compatibility during transition
                        user_custom_prompt_for_dialogue=request_data.custom_prompt_for_dialogue or ""
                    )
                    if dialogue_turns_list:
                        logger.info(f"Podcast dialogue turns generated successfully ({len(dialogue_turns_list)} turns).")
                        status_manager.add_progress_log(
                            task_id,
                            "generating_dialogue",
                            "dialogue_generation_success",
                            f"✓ Generated {len(dialogue_turns_list)} dialogue turns"
                        )
                        
                        llm_dialogue_turns_filepath = os.path.join(tmpdir_path, "dialogue_turns.json")
                        serialized_turns = [turn.model_dump() for turn in dialogue_turns_list]
                        with open(llm_dialogue_turns_filepath, 'w') as f:
                            json.dump(serialized_turns, f, indent=2)
                        logger.info(f"Dialogue turns saved to {llm_dialogue_turns_filepath}")
                        
                        status_manager.add_progress_log(
                            task_id,
                            "generating_dialogue",
                            "dialogue_saved",
                            f"Dialogue saved: {os.path.basename(llm_dialogue_turns_filepath)}"
                        )
                        
                        # Create PodcastDialogue object for better data management
                        try:
                            podcast_dialogue = PodcastDialogue(turns=dialogue_turns_list)
                            logger.info(f"Created PodcastDialogue with {podcast_dialogue.turn_count} turns, {len(podcast_dialogue.speaker_list)} speakers")
                            
                            status_manager.add_progress_log(
                                task_id,
                                "generating_dialogue",
                                "dialogue_object_created",
                                f"✓ Created dialogue object: {podcast_dialogue.turn_count} turns, {podcast_dialogue.total_word_count} words, ~{podcast_dialogue.estimated_duration_seconds}s duration"
                            )
                        except Exception as e:
                            logger.error(f"Failed to create PodcastDialogue object: {e}", exc_info=True)
                            warnings_list.append(f"Failed to create dialogue object: {e}")
                            # Fallback to legacy approach
                            podcast_dialogue = None
                        
                        # Generate transcript using PodcastDialogue if available, fallback to legacy method
                        if podcast_dialogue:
                            podcast_transcript = podcast_dialogue.to_transcript()
                            logger.info(f"Transcript generated using PodcastDialogue: {len(podcast_transcript)} characters")
                        else:
                            # Legacy fallback
                            transcript_parts = [f"{turn.speaker_id}: {turn.text}" for turn in dialogue_turns_list]
                            podcast_transcript = "\n".join(transcript_parts)
                            logger.info("Transcript generated using legacy method")
                        
                        # Save transcript to file
                        llm_transcript_filepath = os.path.join(tmpdir_path, "transcript.txt")
                        with open(llm_transcript_filepath, 'w', encoding='utf-8') as f:
                            f.write(podcast_transcript)
                        logger.info(f"Transcript saved to {llm_transcript_filepath}")
                        
                        status_manager.add_progress_log(
                            task_id,
                            "generating_dialogue",
                            "transcript_constructed",
                            f"✓ Transcript created: {len(podcast_transcript)} characters, {'using PodcastDialogue' if podcast_dialogue else 'using legacy method'}"
                        )
                    else:
                        logger.error("Dialogue generation returned None or empty list of turns.")
                        warnings_list.append("Dialogue generation failed to produce turns.")
                        podcast_transcript = "Error: Dialogue generation failed."
                        status_manager.add_progress_log(
                            task_id,
                            "generating_dialogue",
                            "dialogue_generation_empty",
                            "⚠ Dialogue generation returned no turns"
                        )

                except LLMProcessingError as e:
                    logger.error(f"LLMProcessingError during dialogue generation: {e}", exc_info=True)
                    warnings_list.append(f"LLM processing error during dialogue generation: {e}")
                    podcast_transcript = f"Error: LLM processing failed during dialogue generation. {e}"
                    status_manager.add_progress_log(
                        task_id,
                        "generating_dialogue",
                        "dialogue_llm_error",
                        f"✗ LLM processing failed: {e}"
                    )
                except Exception as e:
                    logger.error(f"Unexpected error during dialogue generation: {e}", exc_info=True)
                    warnings_list.append(f"Critical error during dialogue generation: {e}")
                    podcast_transcript = f"Error: Critical error during dialogue generation. {e}"
                    status_manager.add_progress_log(
                        task_id,
                        "generating_dialogue",
                        "dialogue_critical_error",
                        f"✗ Critical error: {e}"
                    )
            else:
                warnings_list.append("Skipping dialogue generation as outline or extracted_text is missing.")
                podcast_transcript = "Dialogue generation skipped due to missing prerequisites."

            logger.info("STEP: Dialogue Turns Generation phase complete.")
            
            # Update status after dialogue generation
            if dialogue_turns_list:
                status_manager.update_status(
                    task_id,
                    "generating_audio_segments",
                    f"Generated {len(dialogue_turns_list)} dialogue turns, creating audio",
                    75.0
                )
                status_manager.update_artifacts(
                    task_id,
                    dialogue_script_complete=True
                )
            
            # Check for cancellation after dialogue generation
            if task_id:
                self._check_cancellation(task_id)
            
            # 7. TTS Generation for Dialogue Turns
            logger.info("STEP: Starting TTS generation for dialogue turns...")
            if dialogue_turns_list and self.tts_service:
                status_manager.add_progress_log(
                    task_id,
                    "generating_audio_segments",
                    "tts_generation_start",
                    f"Generating TTS audio for {len(dialogue_turns_list)} dialogue turns"
                )
                
                audio_segments_dir = os.path.join(tmpdir_path, "audio_segments")
                ensure_directory_exists(audio_segments_dir)
                logger.info(f"Created directory for audio segments: {audio_segments_dir}")
                
                status_manager.add_progress_log(
                    task_id,
                    "generating_audio_segments",
                    "audio_directory_created",
                    f"Created audio directory: {os.path.basename(audio_segments_dir)}"
                )

                total_turns = len(dialogue_turns_list)
                for i, turn in enumerate(dialogue_turns_list):
                    # Update status with incremental progress
                    progress = 75.0 + (15.0 * (i / total_turns))  # Progress from 75% to 90%
                    status_manager.update_status(
                        task_id,
                        "generating_audio_segments",
                        f"Generating audio {i+1}/{total_turns} - {turn.speaker_id}",
                        progress
                    )
                    
                    status_manager.add_progress_log(
                        task_id,
                        "generating_audio_segments",
                        "tts_turn_start",
                        f"Processing turn {i+1}/{total_turns}: {turn.speaker_id}"
                    )
                    
                    turn_audio_filename = f"turn_{i:03d}_{turn.speaker_id.replace(' ','_')}.mp3"
                    turn_audio_filepath = os.path.join(audio_segments_dir, turn_audio_filename)
                    logger.info(f"Generating TTS for turn {i} (Speaker: {turn.speaker_id}): {turn.text[:50]}...")
                    try:
                        logger.info(f"STEP: Attempting TTS for turn {i}...")
                        
                        # Initialize voice parameters
                        voice_name = None
                        speaker_gender = None
                        voice_params = None
                        
                        # Try to find matching persona with voice info
                        if turn.speaker_id in persona_research_map:
                            pr = persona_research_map[turn.speaker_id]
                            # Priority 1: Use specific voice ID if available
                            if pr.tts_voice_id:
                                voice_name = pr.tts_voice_id
                                logger.info(f"Using specific voice ID for {turn.speaker_id}: {voice_name}")
                            # Priority 2: Use gender if no specific voice
                            elif pr.gender:
                                speaker_gender = pr.gender
                                logger.info(f"Using gender from PersonaResearch for {turn.speaker_id}: {speaker_gender}")
                            # Priority 3: Use voice params if available
                            if pr.tts_voice_params:
                                voice_params = pr.tts_voice_params
                        # Fallback to turn.speaker_gender if no persona found
                        elif hasattr(turn, 'speaker_gender') and turn.speaker_gender:
                            speaker_gender = turn.speaker_gender
                            logger.info(f"Falling back to turn.speaker_gender for {turn.speaker_id}: {speaker_gender}")
                        # No PersonaResearch or speaker_gender available - log warning and use default
                        else:
                            logger.warning(f"No PersonaResearch or speaker_gender found for {turn.speaker_id}. Using default Neutral voice.")
                            speaker_gender = "Neutral"
                            logger.warning(f"No voice information found for {turn.speaker_id}, defaulting to Neutral gender")
                        
                        # Make the TTS call with all available voice parameters
                        success = await self.tts_service.text_to_audio_async(
                            text_input=turn.text,
                            output_filepath=turn_audio_filepath,
                            speaker_gender=speaker_gender or "Neutral",  # Provide default
                            voice_name=voice_name or "",  # Provide default
                            voice_params=voice_params or {}  # Provide default
                        )
                        if success:
                            individual_turn_audio_paths.append(turn_audio_filepath)
                            logger.info(f"STEP: TTS for turn {i} successful. Audio saved to {turn_audio_filepath}")
                            logger.info(f"Generated audio for turn {i}: {turn_audio_filepath}")
                            status_manager.add_progress_log(
                                task_id,
                                "generating_audio_segments",
                                "tts_turn_success",
                                f"✓ Generated audio for turn {i+1}: {turn.speaker_id}"
                            )
                            # Upload the individual audio segment to cloud storage
                            if self.cloud_storage_manager:
                                try:
                                    logger.info(f"Uploading individual audio segment to cloud storage: {turn_audio_filepath}")
                                    await self.cloud_storage_manager.upload_audio_segment_async(turn_audio_filepath)
                                    logger.info(f"Individual audio segment uploaded to cloud storage successfully: {turn_audio_filepath}")
                                except Exception as e:
                                    logger.error(f"Error uploading individual audio segment to cloud storage: {e}")
                                    warnings_list.append(f"Error uploading individual audio segment to cloud storage: {e}")
                        else:
                            logger.warning(f"STEP: TTS for turn {i} FAILED. Skipping audio for this turn.")
                            logger.warning(f"TTS generation failed for turn {i}. Skipping audio for this turn.")
                            warnings_list.append(f"TTS failed for turn {i}: {turn.text[:30]}...")
                            status_manager.add_progress_log(
                                task_id,
                                "generating_audio_segments",
                                "tts_turn_failed",
                                f"✗ TTS failed for turn {i+1}: {turn.speaker_id}"
                            )
                    except Exception as e:
                        logger.error(f"Error during TTS for turn {i}: {e}", exc_info=True)
                        warnings_list.append(f"TTS critical error for turn {i}: {e}")
                        status_manager.add_progress_log(
                            task_id,
                            "generating_audio_segments",
                            "tts_turn_error",
                            f"✗ Critical TTS error for turn {i+1}: {e}"
                        )
                
                logger.info(f"STEP: TTS generation for all turns complete. {len(individual_turn_audio_paths)} audio files generated.")
                status_manager.add_progress_log(
                    task_id,
                    "generating_audio_segments",
                    "tts_generation_complete",
                    f"✓ TTS complete: {len(individual_turn_audio_paths)}/{len(dialogue_turns_list)} audio files generated"
                )
            else:
                logger.warning("No dialogue turns available for TTS processing or TTS service missing.")
                warnings_list.append("TTS skipped: No dialogue turns or TTS service missing.")
                logger.info("STEP: Skipping TTS generation as no dialogue turns are available or tts_service is missing.")
                status_manager.add_progress_log(
                    task_id,
                    "generating_audio_segments",
                    "tts_skipped",
                    "⚠ TTS skipped: No dialogue turns or TTS service missing"
                )
            
            # Check for cancellation after TTS generation
            if task_id:
                self._check_cancellation(task_id)
            
            # 8. Audio Stitching
            logger.info("STEP: Starting audio stitching...")
            final_audio_filepath = "placeholder_error.mp3"  # Default in case of issues
            if individual_turn_audio_paths:
                status_manager.add_progress_log(
                    task_id,
                    "stitching_audio",
                    "audio_stitching_start",
                    f"Stitching {len(individual_turn_audio_paths)} audio segments into final podcast"
                )
                
                logger.info(f"Attempting to stitch {len(individual_turn_audio_paths)} audio segments.")
                logger.info(f"STEP: Attempting to stitch {len(individual_turn_audio_paths)} audio segments...")
                stitched_audio_path = await self._stitch_audio_segments_async(individual_turn_audio_paths, tmpdir_path)
                if stitched_audio_path and os.path.exists(stitched_audio_path):
                    final_audio_filepath = stitched_audio_path
                    logger.info(f"STEP: Audio stitching successful. Final audio at {final_audio_filepath}")
                    status_manager.add_progress_log(
                        task_id,
                        "stitching_audio",
                        "audio_stitching_success",
                        f"✓ Successfully stitched final podcast: {os.path.basename(final_audio_filepath)}"
                    )
                    
                    # Upload the final stitched audio to cloud storage
                    if self.cloud_storage_manager:
                        try:
                            logger.info(f"Uploading final stitched audio to cloud storage: {final_audio_filepath}")
                            cloud_url = await self.cloud_storage_manager.upload_audio_file_async(
                                final_audio_filepath, 
                                f"episodes/{task_id}/final_podcast.mp3"
                            )
                            if cloud_url:
                                # Update the final_audio_filepath to use the cloud URL
                                final_audio_filepath = cloud_url
                                logger.info(f"Final stitched audio uploaded to cloud storage successfully: {cloud_url}")
                                status_manager.add_progress_log(
                                    task_id,
                                    "stitching_audio",
                                    "cloud_upload_success",
                                    f"✓ Final podcast uploaded to cloud storage: {os.path.basename(cloud_url)}"
                                )
                        except Exception as e:
                            logger.error(f"Error uploading final stitched audio to cloud storage: {e}")
                            warnings_list.append(f"Error uploading final stitched audio to cloud storage: {e}")
                            status_manager.add_progress_log(
                                task_id,
                                "stitching_audio",
                                "cloud_upload_failed",
                                f"✗ Failed to upload to cloud storage: {e}"
                            )
                    else:
                        # For local environments, copy the audio file to the static serving directory
                        try:
                            local_audio_dir = f"./outputs/audio/{task_id}"
                            os.makedirs(local_audio_dir, exist_ok=True)
                            local_audio_path = os.path.join(local_audio_dir, "final.mp3")
                            
                            import shutil
                            shutil.copy2(final_audio_filepath, local_audio_path)
                            
                            # Update the final_audio_filepath to use the local serving path
                            final_audio_filepath = local_audio_path
                            logger.info(f"Copied final audio to local serving directory: {local_audio_path}")
                            status_manager.add_progress_log(
                                task_id,
                                "stitching_audio",
                                "local_copy_success",
                                f"✓ Final podcast copied to local serving directory"
                            )
                        except Exception as e:
                            logger.error(f"Error copying audio to local serving directory: {e}")
                            warnings_list.append(f"Error copying audio to local serving directory: {e}")
                            status_manager.add_progress_log(
                                task_id,
                                "stitching_audio",
                                "local_copy_failed",
                                f"✗ Failed to copy to local serving directory: {e}"
                            )
                else:
                    logger.error("STEP: Audio stitching FAILED or produced no output.")
                    logger.error("Audio stitching failed or no audio segments were available.")
                    warnings_list.append("Audio stitching failed or produced no output.")
                    status_manager.add_progress_log(
                        task_id,
                        "stitching_audio",
                        "audio_stitching_failed",
                        "✗ Audio stitching failed or produced no output"
                    )
            else:
                logger.warning("No individual audio segments to stitch.")
                warnings_list.append("Audio stitching skipped: No audio segments available.")
                status_manager.add_progress_log(
                    task_id,
                    "stitching_audio",
                    "audio_stitching_skipped",
                    "⚠ Audio stitching skipped: No audio segments available"
                )
            logger.info("STEP: Audio stitching phase complete.")

            # Update status after audio stitching
            if final_audio_filepath != "placeholder_error.mp3":
                status_manager.update_status(
                    task_id,
                    "postprocessing_final_episode",
                    "Audio stitched successfully, finalizing episode",
                    95.0
                )
                status_manager.update_artifacts(
                    task_id,
                    final_podcast_audio_available=True
                )
                status_manager.add_progress_log(
                    task_id,
                    "postprocessing_final_episode",
                    "episode_finalization_start",
                    "Creating final podcast episode with all components"
                )

            # Final PodcastEpisode construction
            podcast_episode = PodcastEpisode(
                title=podcast_title,
                summary=podcast_summary,
                transcript=podcast_transcript,
                audio_filepath=final_audio_filepath, 
                source_attributions=source_attributions,  # Now includes all source URLs
                warnings=warnings_list,
                llm_source_analysis_paths=None,  # Fixed parameter name
                llm_persona_research_paths=None,
                llm_podcast_outline_path=llm_podcast_outline_filepath,
                llm_dialogue_turns_path=llm_dialogue_turns_filepath,
                llm_transcript_path=llm_transcript_filepath,
                dialogue_turn_audio_paths=individual_turn_audio_paths
            )
            logger.info(f"STEP_COMPLETED_TRY_BLOCK: PodcastEpisode object created. Title: {podcast_episode.title}, Audio: {podcast_episode.audio_filepath}, Warnings: {len(podcast_episode.warnings)}")
            
            # Upload text files to cloud storage if available
            if self.cloud_storage_manager:
                try:
                    logger.info("Uploading text files to cloud storage...")
                    
                    # Upload podcast outline
                    if llm_podcast_outline_filepath and os.path.exists(llm_podcast_outline_filepath):
                        try:
                            # Read the outline data
                            with open(llm_podcast_outline_filepath, 'r') as f:
                                outline_data = json.load(f)
                            
                            # Upload to cloud storage
                            outline_cloud_url = await self.cloud_storage_manager.upload_outline_async(
                                outline_data, task_id
                            )
                            if outline_cloud_url:
                                # Update the final_audio_filepath to use the cloud URL
                                podcast_episode.llm_podcast_outline_path = outline_cloud_url
                                logger.info(f"Podcast outline uploaded to cloud storage: {outline_cloud_url}")
                                status_manager.add_progress_log(
                                    task_id,
                                    "postprocessing_final_episode",
                                    "outline_cloud_upload_success",
                                    f"✓ Outline uploaded to cloud storage"
                                )
                        except Exception as e:
                            logger.error(f"Error uploading podcast outline to cloud storage: {e}")
                            warnings_list.append(f"Error uploading podcast outline to cloud storage: {e}")
                    
                    # Upload persona research files
                    if persona_research_objects:
                        updated_research_paths = []
                        for pr in persona_research_objects:
                            try:
                                # Extract person_id from the research data or filename
                                person_id = pr.person_id
                                
                                # Upload to cloud storage
                                research_cloud_url = await self.cloud_storage_manager.upload_persona_research_async(
                                    pr.model_dump(), task_id, person_id
                                )
                                if research_cloud_url:
                                    updated_research_paths.append(research_cloud_url)
                                    logger.info(f"Persona research for {person_id} uploaded to cloud storage: {research_cloud_url}")
                                else:
                                    logger.warning(f"Failed to upload persona research for {person_id} to cloud storage")
                            except Exception as e:
                                logger.error(f"Error uploading persona research to cloud storage: {e}")
                                warnings_list.append(f"Error uploading persona research to cloud storage: {e}")
                        if updated_research_paths:
                            podcast_episode.llm_persona_research_paths = updated_research_paths
                            
                        status_manager.add_progress_log(
                            task_id,
                            "postprocessing_final_episode",
                            "research_cloud_upload_success",
                            f"✓ {len([p for p in updated_research_paths if p])} persona research files uploaded to cloud storage"
                        )
                
                except Exception as e:
                    logger.error(f"Error during text file cloud uploads: {e}")
                    warnings_list.append(f"Error during text file cloud uploads: {e}")
            
            status_manager.add_progress_log(
                task_id,
                "postprocessing_final_episode",
                "episode_creation_success",
                f"✓ Created episode: '{podcast_episode.title}' with {len(podcast_episode.warnings)} warnings"
            )
            
            # Update status to completed with final episode
            status_manager.update_status(
                task_id,
                "completed",
                f"Podcast generation complete: {podcast_episode.title}",
                100.0
            )
            status_manager.update_artifacts(
                task_id,
                final_podcast_transcript_available=True
            )
            
            status_manager.add_progress_log(
                task_id,
                "completed",
                "workflow_completed",
                f"✓ Podcast generation workflow completed successfully"
            )
            
            # Update the result in the status
            status_manager.set_episode(task_id, podcast_episode)
            
            return podcast_episode

        except Exception as main_e:
            logger.critical(f"STEP_CRITICAL_FAILURE: Unhandled exception in core processing: {main_e}", exc_info=True)
            warnings_list.append(f"CRITICAL FAILURE: {main_e}")
            
            # Update status to failed
            status_manager.set_error(task_id, str(main_e))
            
            # Return a minimal error episode with safe defaults
            return PodcastEpisode(
                title="Critical Generation Error",
                summary=f"A critical error occurred: {main_e}",
                transcript="",
                audio_filepath="placeholder_error.mp3",  # Safe default
                source_attributions=source_attributions,
                warnings=warnings_list
            )
        finally:
            if 'tmpdir_path' in locals():
                logger.info(f"STEP_FINALLY: Temporary directory (NOT cleaned up): {tmpdir_path}")
            # Note: We're NOT removing tmpdir_path for debugging purposes

# Example usage (for development testing)
