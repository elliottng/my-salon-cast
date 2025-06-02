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
from typing import List, Optional, Any, Tuple
from pydantic import ValidationError
import aiohttp

# Add the project root to the Python path so we can import modules correctly
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from app directly
from app.podcast_models import SourceAnalysis, PersonaResearch, OutlineSegment, DialogueTurn, PodcastOutline, PodcastEpisode, BaseModel, PodcastTaskCreationResponse, PodcastStatus, PodcastRequest
from app.common_exceptions import LLMProcessingError, ExtractionError
from app.content_extractor import extract_content_from_url, extract_text_from_pdf_path
from app.llm_service import GeminiService
from app.tts_service import GoogleCloudTtsService
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        Main orchestration method to generate a podcast episode synchronously.
        Maintains backwards compatibility with existing REST API.
        
        Returns:
            PodcastEpisode - The completed podcast episode
        """
        # Use the async method internally but only return the episode
        task_id, episode = await self._generate_podcast_internal(request_data, async_mode=False)
        return episode
    
    async def generate_podcast_async(
        self,
        request_data: PodcastRequest
    ) -> str:
        """
        Generate a podcast episode asynchronously.
        Returns immediately with a task_id for status tracking.
        
        Returns:
            str - The task_id for status tracking
        """
        task_id, _ = await self._generate_podcast_internal(request_data, async_mode=True)
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
        
        try:
            logger.info(f"Starting background podcast generation for task {task_id}")
            
            # Set the task_id in a thread-local variable so we can check for cancellation
            import threading
            current_thread = threading.current_thread()
            current_thread.task_id = task_id
            
            # Call the existing _generate_podcast_internal with async_mode=False
            # We set async_mode=False here because we're already running asynchronously via the task runner
            _, podcast_episode = await self._generate_podcast_internal(request_data, async_mode=False, background_task_id=task_id)
            
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
                progress_percentage=None
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
        payload = {
            "task_id": task_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if status == "completed" and podcast_episode:
            payload["result"] = {
                "title": podcast_episode.title,
                "summary": podcast_episode.summary,
                "audio_filepath": podcast_episode.audio_filepath,
                "has_transcript": bool(podcast_episode.transcript),
                "source_count": len(podcast_episode.source_attributions),
                "warnings": podcast_episode.warnings
            }
        elif status == "failed" and error:
            payload["error"] = error
        
        # Attempt to send webhook with retry logic
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10.0)
                    ) as response:
                        if response.status < 300:
                            logger.info(f"Webhook notification sent successfully for task {task_id}")
                            return
                        else:
                            logger.warning(
                                f"Webhook returned status {response.status} for task {task_id}, "
                                f"attempt {attempt + 1}/{max_retries}"
                            )
            except Exception as e:
                logger.warning(
                    f"Webhook notification failed for task {task_id}, "
                    f"attempt {attempt + 1}/{max_retries}: {str(e)}"
                )
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
        
        logger.error(f"Failed to send webhook notification for task {task_id} after {max_retries} attempts")
    
    def _run_podcast_generation_sync_wrapper(self, task_id: str, request_data: PodcastRequest) -> None:
        """
        Synchronous wrapper for _run_podcast_generation_async to be used by ThreadPoolExecutor.
        Creates a new event loop in the thread to run the async function.
        
        Args:
            task_id: The unique identifier for this generation task
            request_data: The podcast generation request parameters
        """
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async function in the new event loop
            loop.run_until_complete(self._run_podcast_generation_async(task_id, request_data))
        finally:
            # Clean up the event loop
            loop.close()
    
    def _check_cancellation(self, task_id: Optional[str] = None) -> None:
        """
        Check if the current task has been cancelled.
        Raises CancelledError if the task was cancelled.
        
        Args:
            task_id: Optional task ID to check. If not provided, checks thread-local task_id.
        """
        if not task_id:
            # Try to get task_id from thread-local storage
            import threading
            current_thread = threading.current_thread()
            if hasattr(current_thread, 'task_id'):
                task_id = current_thread.task_id
            else:
                return  # No task_id, not a background task
        
        # Check if this task has been cancelled
        task_runner = get_task_runner()
        if task_id in task_runner._running_tasks:
            task = task_runner._running_tasks[task_id]
            if task.cancelled():
                raise asyncio.CancelledError(f"Task {task_id} was cancelled")
    
    async def _generate_podcast_internal(
        self,
        request_data: PodcastRequest,
        async_mode: bool = False,
        background_task_id: Optional[str] = None
    ) -> Tuple[str, PodcastEpisode]:
        """
        Internal method that handles both sync and async podcast generation.
        
        Args:
            request_data: The podcast generation request
            async_mode: If True, will return immediately and process in background (future implementation)
            background_task_id: The task ID for background tasks, used for cancellation checks
        
        Returns:
            Tuple of (task_id, PodcastEpisode)
        """
        # Use provided task_id for background tasks, otherwise create a new one
        task_id = background_task_id if background_task_id else str(uuid.uuid4())
        status_manager = get_status_manager()
        
        # Only create initial status if this is a new task (not a background continuation)
        if not background_task_id:
            # Create initial status with request data
            status = status_manager.create_status(task_id, request_data.dict())
            logger.info(f"Created podcast generation task with ID: {task_id}")
        else:
            logger.info(f"Continuing background task with ID: {task_id}")
        
        # Update status to preprocessing
        status_manager.update_status(
            task_id,
            "preprocessing_sources",
            "Validating request and preparing sources",
            5.0
        )
        
        # In async_mode, spawn a background task and return immediately
        if async_mode:
            logger.info(f"Async mode enabled for task {task_id}, spawning background task")
            task_runner = get_task_runner()
            
            # Check if we can accept a new task
            if not task_runner.can_accept_new_task():
                logger.warning(f"Task runner at capacity, cannot accept task {task_id}")
                status_manager.set_error(
                    task_id,
                    "System at capacity",
                    f"Maximum concurrent podcast generations ({task_runner.max_workers}) reached. Please try again later."
                )
                error_episode = PodcastEpisode(
                    title="Error", 
                    summary="System at capacity", 
                    transcript="", 
                    audio_filepath="",
                    source_attributions=[], 
                    warnings=["Maximum concurrent podcast generations reached."]
                )
                return task_id, error_episode
            
            # Submit the task to run in the background
            try:
                # Note: We need to pass the task_id to the async wrapper
                await task_runner.submit_task(
                    task_id,
                    self._run_podcast_generation_sync_wrapper,
                    task_id,
                    request_data
                )
                logger.info(f"Task {task_id} submitted for background processing")
                
                # Return immediately with an empty episode placeholder
                # The actual episode will be available via the status API
                placeholder_episode = PodcastEpisode(
                    title="Processing",
                    summary="Podcast generation in progress",
                    transcript="",
                    audio_filepath="",
                    source_attributions=[],
                    warnings=[]
                )
                return task_id, placeholder_episode
                
            except Exception as e:
                logger.error(f"Failed to submit task {task_id} for background processing: {str(e)}")
                status_manager.set_error(
                    task_id,
                    "Failed to start background processing",
                    str(e)
                )
                error_episode = PodcastEpisode(
                    title="Error", 
                    summary="Failed to start background processing", 
                    transcript="", 
                    audio_filepath="",
                    source_attributions=[], 
                    warnings=[f"Background processing error: {str(e)}"]
                )
                return task_id, error_episode
        
        # Continue with synchronous generation (existing code)
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
            return task_id, error_episode

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
                error_msg = "No content could be extracted from any sources."
                
                # Update status to failed before returning
                status_manager.set_error(task_id, error_msg)
                
                return task_id, PodcastEpisode(
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
            if background_task_id:
                self._check_cancellation(background_task_id)
            
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
            
            # Update status after source analysis
            if source_analysis_obj:
                status_manager.update_status(
                    task_id,
                    "researching_personas",
                    "Source analysis complete, researching personas",
                    30.0
                )
                status_manager.update_artifacts(
                    task_id,
                    source_analysis_complete=True
                )
            
            # Check for cancellation after source analysis
            if background_task_id:
                self._check_cancellation(background_task_id)
            
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

            # Update status after persona research
            status_manager.update_status(
                task_id,
                "generating_outline",
                f"Researched {len(persona_research_docs_content)} personas, generating outline",
                45.0
            )
            status_manager.update_artifacts(
                task_id,
                persona_research_complete=True
            )

            # Check for cancellation after persona research
            if background_task_id:
                self._check_cancellation(background_task_id)
            
            # 4.5. Assign Invented Names and Genders to Personas (mirroring podcast_workflow.py)
            logger.info("STEP: Assigning invented names and genders to personas...")
            # Create a map of PersonaResearch objects for easy lookup by person_id - PRIMARY APPROACH
            persona_research_map: dict[str, PersonaResearch] = {}
            
            # DEPRECATED: persona_details_map is being phased out in favor of PersonaResearch objects
            # This structure is only maintained temporarily for backward compatibility with dependent services
            # TODO: Remove this completely once all dependencies have been updated
            persona_details_map: dict[str, dict[str, str]] = {}
            
            # We'll create the Host persona after processing all guests to avoid voice duplication
            # Capture the host details for later use
            host_name = request_data.host_invented_name or "Brigette"
            host_gender = request_data.host_gender or "Female"
            
            # Track assigned voice IDs to avoid duplicates
            assigned_voice_ids = set()
            
            # We will add the host to persona_research_docs_content after processing all guests

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
                    
                    # Use gender from PersonaResearch if available, otherwise assign based on name analysis or randomize
                    # In a real implementation, you might use a name gender classifier library
                    if persona_research_obj_temp.gender:
                        assigned_gender = persona_research_obj_temp.gender
                    else:
                        # For testing, we'll alternate between genders to ensure variety
                        # In production, consider a more sophisticated approach
                        genders = ["Male", "Female", "Neutral"]
                        assigned_gender = genders[idx % len(genders)]
                    
                    invented_name = "Unknown Person"
                    if assigned_gender == "Male":
                        available_names = [name for name in MALE_INVENTED_NAMES if name not in used_male_names]
                        if not available_names: available_names = MALE_INVENTED_NAMES # fallback if all used
                        invented_name = available_names[idx % len(available_names)]
                        used_male_names.add(invented_name)
                    elif assigned_gender == "Female":
                        available_names = [name for name in FEMALE_INVENTED_NAMES if name not in used_female_names]
                        if not available_names: available_names = FEMALE_INVENTED_NAMES
                        invented_name = available_names[idx % len(available_names)]
                        used_female_names.add(invented_name)
                    else: # Neutral or unknown
                        available_names = [name for name in NEUTRAL_INVENTED_NAMES if name not in used_neutral_names]
                        if not available_names: available_names = NEUTRAL_INVENTED_NAMES
                        invented_name = available_names[idx % len(available_names)]
                        used_neutral_names.add(invented_name)

                    # Update the PersonaResearch object with voice information
                    updated_pr_data = pr_data.copy()
                    updated_pr_data["invented_name"] = invented_name
                    updated_pr_data["gender"] = assigned_gender
                    
                    # Set creation_date as ISO format string if it doesn't exist
                    if "creation_date" not in updated_pr_data or updated_pr_data["creation_date"] is None:
                        updated_pr_data["creation_date"] = datetime.now().isoformat()
                    elif isinstance(updated_pr_data["creation_date"], datetime):
                        # Convert datetime to string if it's a datetime object
                        updated_pr_data["creation_date"] = updated_pr_data["creation_date"].isoformat()
                    
                    # Now we'll also set a specific voice ID based on gender
                    # This would ideally come from a voice selection service
                    if assigned_gender == "Male":
                        updated_pr_data["tts_voice_id"] = "en-US-Neural2-D"  # Example male voice
                    elif assigned_gender == "Female":
                        updated_pr_data["tts_voice_id"] = "en-US-Neural2-F"  # Example female voice
                    else:
                        updated_pr_data["tts_voice_id"] = "en-US-Neural2-A"  # Example neutral voice
                    
                    # Create a new PersonaResearch object with all the updated fields
                    updated_persona = PersonaResearch(**updated_pr_data)
                    
                    # Add to persona_research_map for efficient lookups by ID
                    persona_research_map[updated_persona.person_id] = updated_persona
                    
                    # Replace the original JSON string with the updated one - use model_dump_json for proper serialization
                    persona_research_docs_content[idx] = updated_persona.model_dump_json()
                    
                    # Also maintain the persona_details_map for backward compatibility
                    # This will be deprecated in future versions
                    persona_details_map[person_id] = {
                        "invented_name": invented_name,
                        "gender": assigned_gender,
                        "real_name": real_name,
                        "tts_voice_id": updated_pr_data["tts_voice_id"]
                    }
                    logger.info(f"Assigned to {person_id} ({real_name}): Invented Name='{invented_name}', Gender='{assigned_gender}'")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse PersonaResearch JSON for name/gender assignment: {e}. Content: {pr_json_str[:100]}")
                except Exception as e:
                    logger.error(f"Error processing persona for name/gender assignment: {e}. Persona data: {pr_json_str[:100]}")
            # Now create the Host persona with a voice that doesn't conflict with guests
            # Expanded voice options to provide more variety and avoid duplicates
            male_voices = ["en-US-Neural2-D", "en-US-Neural2-J", "en-GB-Neural2-B", "en-GB-Neural2-D"]
            female_voices = ["en-US-Neural2-F", "en-US-Neural2-G", "en-GB-Neural2-A", "en-GB-Neural2-C"]
            neutral_voices = ["en-US-Neural2-A", "en-US-Neural2-C"]
            
            # Find all currently assigned voices
            used_voice_ids = set()
            for details in persona_details_map.values():
                if "tts_voice_id" in details:
                    used_voice_ids.add(details["tts_voice_id"])
            
            # Select a unique voice for the Host based on gender
            host_voice_id = None
            if host_gender == "Male":
                available_voices = [v for v in male_voices if v not in used_voice_ids]
                # Fallback to all male voices if all are already used
                host_voice_id = random.choice(available_voices if available_voices else male_voices)
            elif host_gender == "Female":
                available_voices = [v for v in female_voices if v not in used_voice_ids]
                # Fallback to all female voices if all are already used
                host_voice_id = random.choice(available_voices if available_voices else female_voices)
            else:  # Neutral
                available_voices = [v for v in neutral_voices if v not in used_voice_ids]
                # Fallback to all neutral voices if all are already used
                host_voice_id = random.choice(available_voices if available_voices else neutral_voices)
            
            # Create the Host persona and add to maps
            host_persona = PersonaResearch(
                person_id="Host",
                name="Host",
                detailed_profile="The podcast host is an engaging personality who is intellectually inquisitive and interested in fostering debate and viewpoint diversity",
                invented_name=host_name,
                gender=host_gender,
                tts_voice_id=host_voice_id,
                creation_date=datetime.now().isoformat()
            )
            
            # Add Host to maps
            persona_research_map["Host"] = host_persona
            persona_details_map["Host"] = {
                "invented_name": host_name,
                "gender": host_gender,
                "real_name": "Host",
                "tts_voice_id": host_voice_id
            }
            
            # Add Host to persona research documents
            persona_research_docs_content.append(host_persona.model_dump_json())
            logger.info(f"Assigned to Host (Host): Invented Name='{host_name}', Gender='{host_gender}', Voice ID='{host_voice_id}'")
            
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

                    # TEMPORARY: Still passing persona_details_map while service methods require it
                    # This will be removed once all methods are updated to use PersonaResearch exclusively
                    podcast_outline_obj = await self.llm_service.generate_podcast_outline_async(
                        source_analyses=source_analyses_content, 
                        persona_research_docs=persona_research_docs_content,
                        desired_podcast_length_str=desired_length_str or "5-7 minutes",
                        num_prominent_persons=num_persons,
                        names_prominent_persons_list=request_data.prominent_persons,
                        persona_details_map=persona_details_map,  # TEMPORARY: Will be removed in future refactoring
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
            if background_task_id:
                self._check_cancellation(background_task_id)
            
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
                            gender_for_tts = "Neutral" # Default
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

                    # TEMPORARY: Still passing persona_details_map while service methods require it
                    # This will be removed once all methods are updated to use PersonaResearch exclusively
                    dialogue_turns_list = await self.llm_service.generate_dialogue_async(
                        podcast_outline=podcast_outline_obj,
                        source_analyses=source_analysis_objects, 
                        persona_research_docs=persona_research_objects_for_dialogue,
                        persona_details_map=persona_details_map,  # TEMPORARY: Will be removed in future refactoring
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
            if background_task_id:
                self._check_cancellation(background_task_id)
            
            # 7. TTS Generation for Dialogue Turns
            logger.info("STEP: Starting TTS generation for dialogue turns...")
            if dialogue_turns_list and self.tts_service:
                audio_segments_dir = os.path.join(tmpdir_path, "audio_segments")
                os.makedirs(audio_segments_dir, exist_ok=True)
                logger.info(f"Created directory for audio segments: {audio_segments_dir}")

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
                            speaker_gender=speaker_gender,
                            voice_name=voice_name,
                            voice_params=voice_params
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
                
                # Update status after TTS generation completes
                status_manager.update_status(
                    task_id,
                    "stitching_audio",
                    "Audio segments complete, stitching final podcast",
                    90.0
                )
                status_manager.update_artifacts(
                    task_id,
                    individual_audio_segments_complete=True
                )
            else:
                logger.warning("No dialogue turns available for TTS processing or TTS service missing.")
                warnings_list.append("TTS skipped: No dialogue turns or TTS service missing.")
                logger.info("STEP: Skipping TTS generation as no dialogue turns are available or tts_service is missing.")
            
            # Check for cancellation after TTS generation
            if background_task_id:
                self._check_cancellation(background_task_id)
            
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
            
            # Update the result in the status
            status_manager.set_episode(task_id, podcast_episode)
            
            return task_id, podcast_episode

        except Exception as main_e:
            logger.critical(f"STEP_CRITICAL_FAILURE: Unhandled exception in generate_podcast_from_source: {main_e}", exc_info=True)
            warnings_list.append(f"CRITICAL FAILURE: {main_e}")
            
            # Update status to failed
            status_manager.set_error(task_id, str(main_e))
            
            # Return a minimal error episode with safe defaults
            return task_id, PodcastEpisode(
                title="Critical Generation Error",
                summary=f"A critical error occurred: {main_e}",
                transcript="",
                audio_filepath="placeholder_error.mp3",  # Safe default
                source_attributions=source_attributions if 'source_attributions' in locals() else [],
                warnings=warnings_list
            )
        finally:
            if 'tmpdir_path' in locals():
                logger.info(f"STEP_FINALLY: Temporary directory (NOT cleaned up): {tmpdir_path}")
            # Note: We're NOT removing tmpdir_path for debugging purposes

# Example usage (for development testing purposes)
async def main_workflow_test():
    """A development testing function to validate the podcast generation workflow."""
    logger.info("Initializing PodcastGeneratorService for test run...")
    generator = PodcastGeneratorService()
    
    logger.info("Defining sample request data...")
    sample_request = PodcastRequest(
        source_urls=[
            "https://www.whitehouse.gov/articles/2025/05/fact-one-big-beautiful-bill-cuts-spending-fuels-growth/",
            "https://thehill.com/opinion/finance/5320248-the-bond-market-is-missing-the-real-big-beautiful-story/"
            "https://www.ronjohnson.senate.gov/2025/5/the-ugly-truth-about-the-big-beautiful-bill"
        ],
        prominent_persons=["Jason Calacanis","David O. Sacks","Chemath Palihapitiya""David Friedberg"],
        desired_podcast_length_str="15 minutes"
    )
    
    try:
        episode = await generator.generate_podcast_from_source(sample_request)
        logger.info(f"Test generation complete.")
        logger.info(f"Title: {episode.title}, Audio: {episode.audio_filepath}")
        return episode
    except Exception as e:
        logger.error(f"Test workflow error: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # This module is not meant to be run directly in production
    # This code is only for development testing purposes
    logger.info("Running podcast workflow in development test mode")
    asyncio.run(main_workflow_test())
    logger.info("Test complete")
