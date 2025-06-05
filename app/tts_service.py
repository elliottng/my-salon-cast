# app/tts_service.py

import asyncio
import logging
import os
from google.cloud import texttospeech
from dotenv import load_dotenv
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
import functools
import atexit

# Load environment variables from env file
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TtsMetrics:
    """Track TTS service performance metrics."""
    
    def __init__(self):
        self.jobs_completed = 0
        self.jobs_failed = 0
        self.total_processing_time = 0.0
        self.min_processing_time = float('inf')
        self.max_processing_time = 0.0
        self.last_minute_jobs = []
        self.last_metrics_log = time.time()
    
    def record_job(self, processing_time: float, success: bool):
        """Record a completed TTS job."""
        current_time = time.time()
        
        if success:
            self.jobs_completed += 1
            self.total_processing_time += processing_time
            self.min_processing_time = min(self.min_processing_time, processing_time)
            self.max_processing_time = max(self.max_processing_time, processing_time)
        else:
            self.jobs_failed += 1
        
        # Track jobs in last minute
        self.last_minute_jobs.append(current_time)
        # Remove jobs older than 1 minute
        self.last_minute_jobs = [t for t in self.last_minute_jobs if current_time - t <= 60]
    
    def get_metrics(self, active_workers: int, max_workers: int, queue_size: int) -> dict:
        """Get current metrics snapshot."""
        total_jobs = self.jobs_completed + self.jobs_failed
        avg_time = (self.total_processing_time / self.jobs_completed) if self.jobs_completed > 0 else 0
        
        return {
            "active_workers": active_workers,
            "max_workers": max_workers,
            "queue_size": queue_size,
            "worker_utilization_pct": round((active_workers / max_workers) * 100, 1),
            "jobs_completed": self.jobs_completed,
            "jobs_failed": self.jobs_failed,
            "success_rate_pct": round((self.jobs_completed / total_jobs) * 100, 1) if total_jobs > 0 else 100,
            "avg_processing_time_ms": round(avg_time * 1000, 1),
            "min_processing_time_ms": round(self.min_processing_time * 1000, 1) if self.min_processing_time != float('inf') else 0,
            "max_processing_time_ms": round(self.max_processing_time * 1000, 1),
            "jobs_completed_last_minute": len(self.last_minute_jobs)
        }
    
    def should_log_metrics(self) -> bool:
        """Check if it's time to log metrics (every 30 seconds during activity)."""
        current_time = time.time()
        if current_time - self.last_metrics_log >= 30:
            self.last_metrics_log = current_time
            return True
        return False

    def get_avg_processing_time(self) -> float:
        """Get average processing time."""
        if self.jobs_completed > 0:
            return self.total_processing_time / self.jobs_completed
        return 0.0

    def get_jobs_last_minute(self) -> int:
        """Get number of jobs completed in the last minute."""
        return len(self.last_minute_jobs)
    
    def has_recent_activity(self, minutes: int = 2) -> bool:
        """Check if there has been TTS activity in the last N minutes."""
        if not self.last_minute_jobs:
            return False
        
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)
        
        # Check if any job was completed in the specified time window
        recent_jobs = [t for t in self.last_minute_jobs if t >= cutoff_time]
        return len(recent_jobs) > 0

class GoogleCloudTtsService:
    # Cache file path for storing voice list
    VOICE_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'tts_voices_cache.json')
    # Cache expiration time (24 hours)
    CACHE_EXPIRATION = 24 * 60 * 60  # seconds
    
    # Shared thread pool executor for TTS calls to prevent shutdown issues
    _executor = None
    _shutdown_registered = False
    _metrics = TtsMetrics()
    
    @classmethod
    def _get_executor(cls):
        """Get or create a shared thread pool executor for TTS operations."""
        if cls._executor is None or cls._executor._shutdown:
            cls._executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="tts_worker")
            logger.info("Created shared TTS thread pool executor")
            
            # Register shutdown handler only once
            if not cls._shutdown_registered:
                atexit.register(cls._shutdown_executor)
                cls._shutdown_registered = True
                
        return cls._executor
    
    @classmethod
    def _shutdown_executor(cls):
        """Safely shutdown the shared thread pool executor."""
        if cls._executor and not cls._executor._shutdown:
            try:
                cls._executor.shutdown(wait=True, cancel_futures=False)
                logger.info("TTS thread pool executor shutdown complete")
            except Exception as e:
                logger.warning(f"Error during TTS executor shutdown: {e}")
    
    @classmethod
    def _executor_is_healthy(cls):
        """Check if the executor is available and not shutdown."""
        return cls._executor is not None and not cls._executor._shutdown

    @classmethod
    def get_current_metrics(cls) -> Dict[str, Any]:
        """Get current TTS service metrics and performance statistics."""
        try:
            # Get executor info
            if cls._executor is None:
                return {
                    "executor_status": "not_initialized",
                    "max_workers": 0,
                    "active_workers": 0,
                    "queue_size": 0,
                    "worker_utilization_pct": 0.0,
                    "total_jobs_completed": cls._metrics.jobs_completed if cls._metrics else None,
                    "total_jobs_failed": cls._metrics.jobs_failed if cls._metrics else None,
                    "success_rate_pct": 100.0 if not cls._metrics or cls._metrics.jobs_failed == 0 else 
                                      (cls._metrics.jobs_completed / (cls._metrics.jobs_completed + cls._metrics.jobs_failed)) * 100,
                    "avg_processing_time_sec": cls._metrics.get_avg_processing_time() if cls._metrics else None,
                    "min_processing_time_sec": cls._metrics.min_processing_time if cls._metrics else None,
                    "max_processing_time_sec": cls._metrics.max_processing_time if cls._metrics else None,
                    "jobs_last_minute": cls._metrics.get_jobs_last_minute() if cls._metrics else 0,
                    "last_updated": datetime.now().isoformat()
                }
            
            executor = cls._executor
            max_workers = executor._max_workers
            
            # Calculate active workers more safely
            active_workers = 0
            try:
                # Try different ways to get active thread count
                if hasattr(executor, '_threads'):
                    total_threads = len(executor._threads) if hasattr(executor._threads, '__len__') else executor._threads
                    if hasattr(executor, '_idle_semaphore'):
                        idle_sem = executor._idle_semaphore
                        if hasattr(idle_sem, '_value'):
                            idle_count = idle_sem._value if isinstance(idle_sem._value, int) else len(idle_sem._value)
                            active_workers = max(0, total_threads - idle_count)
                        else:
                            active_workers = total_threads  # Fallback
                    else:
                        active_workers = total_threads  # Fallback
                else:
                    active_workers = 0
            except Exception:
                # Fallback to 0 if we can't determine
                active_workers = 0
            
            # Calculate queue size more safely
            queue_size = 0
            try:
                if hasattr(executor, '_work_queue'):
                    work_queue = executor._work_queue
                    if hasattr(work_queue, 'qsize'):
                        queue_size = work_queue.qsize()
                    elif hasattr(work_queue, '__len__'):
                        queue_size = len(work_queue)
            except Exception:
                queue_size = 0
            
            # Calculate utilization
            utilization_pct = (active_workers / max_workers * 100) if max_workers > 0 else 0.0
            
            # Get metrics data
            total_completed = cls._metrics.jobs_completed if cls._metrics else 0
            total_failed = cls._metrics.jobs_failed if cls._metrics else 0
            success_rate = 100.0 if total_failed == 0 and total_completed > 0 else \
                          (total_completed / (total_completed + total_failed) * 100) if (total_completed + total_failed) > 0 else 100.0
            
            return {
                "executor_status": "healthy" if not executor._shutdown else "shutdown",
                "max_workers": max_workers,
                "active_workers": active_workers,
                "queue_size": queue_size,
                "worker_utilization_pct": utilization_pct,
                "total_jobs_completed": total_completed,
                "total_jobs_failed": total_failed,
                "success_rate_pct": success_rate,
                "avg_processing_time_sec": cls._metrics.get_avg_processing_time() if cls._metrics else None,
                "min_processing_time_sec": cls._metrics.min_processing_time if cls._metrics else None,
                "max_processing_time_sec": cls._metrics.max_processing_time if cls._metrics else None,
                "jobs_last_minute": cls._metrics.get_jobs_last_minute() if cls._metrics else 0,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            # Return minimal safe metrics on any error
            return {
                "executor_status": "error",
                "max_workers": 0,
                "active_workers": 0,
                "queue_size": 0,
                "worker_utilization_pct": 0.0,
                "total_jobs_completed": None,
                "total_jobs_failed": None,
                "success_rate_pct": 0.0,
                "avg_processing_time_sec": None,
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }

    @classmethod 
    def log_metrics_if_needed(cls):
        """Log TTS metrics every 30 seconds during active operations."""
        if cls._metrics is None:
            return
            
        # Only log if we have recent activity (last 2 minutes)
        if not cls._metrics.has_recent_activity(minutes=2):
            return
            
        # Get current metrics
        metrics = cls.get_current_metrics()
        
        # Log comprehensive metrics
        logger.info(
            f"TTS Metrics - Status: {metrics['executor_status']}, "
            f"Workers: {metrics['active_workers']}/{metrics['max_workers']} "
            f"({metrics['worker_utilization_pct']:.1f}%), "
            f"Queue: {metrics['queue_size']}, "
            f"Completed: {metrics['total_jobs_completed']}, "
            f"Failed: {metrics['total_jobs_failed']}, "
            f"Success Rate: {metrics['success_rate_pct']:.1f}%, "
            f"Avg Time: {metrics['avg_processing_time_sec']:.2f}s, "
            f"Last Minute: {metrics['jobs_last_minute']}"
        )

    def __init__(self):
        """
        Initializes the Google Cloud Text-to-Speech client.
        Assumes GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
        """
        try:
            self.client = texttospeech.TextToSpeechClient()
            self.voice_cache = self._load_or_refresh_voice_cache()
            logger.info("GoogleCloudTtsService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize TextToSpeechClient: {e}", exc_info=True)
            logger.error("Ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly and the account has 'roles/cloudtts.serviceAgent' or equivalent permissions.")
            raise
            
    def _load_or_refresh_voice_cache(self, force_refresh=False) -> Dict[str, List[Dict]]:
        """Load voice cache from file or refresh it if expired or missing.
        
        Args:
            force_refresh: If True, refreshes the cache regardless of expiration
            
        Returns:
            Dictionary of voice profiles by gender
        """
        try:
            # Check if cache file exists and is not expired, unless force_refresh is True
            if not force_refresh and os.path.exists(self.VOICE_CACHE_FILE):
                file_modified_time = os.path.getmtime(self.VOICE_CACHE_FILE)
                if time.time() - file_modified_time < self.CACHE_EXPIRATION:
                    # Cache is still valid, load it
                    with open(self.VOICE_CACHE_FILE, 'r') as f:
                        cache_data = json.load(f)
                        # Handle both old and new cache format
                        if isinstance(cache_data, dict) and 'voices' in cache_data:
                            # New format with timestamp
                            voices = cache_data['voices']
                            last_updated = cache_data.get('last_updated', 'unknown')
                            logger.info(f"Loaded voice cache from {last_updated} with {sum(len(voices.get(g, [])) for g in ['Male', 'Female', 'Neutral'])} voices")
                            return voices
                        else:
                            # Old format (direct dictionary of voices)
                            logger.info(f"Loaded voice cache with {sum(len(cache_data.get(g, [])) for g in ['Male', 'Female', 'Neutral'])} voices")
                            return cache_data
            
            # Cache doesn't exist, is expired, or force_refresh is True
            if force_refresh:
                logger.info("Forcing refresh of voice cache as requested")
            else:
                logger.info("Voice cache missing or expired, fetching fresh voice list from Google Cloud TTS")
            return self._refresh_voice_cache()
                
        except Exception as e:
            logger.error(f"Error loading voice cache: {str(e)}. Will use empty cache.")
            # Return empty cache structure in case of error
            return {'Male': [], 'Female': [], 'Neutral': []}
    
    def _refresh_voice_cache(self) -> Dict[str, List[Dict]]:
        """Fetch all available voices from Google Cloud TTS API and cache them."""
        result = {'Male': [], 'Female': [], 'Neutral': []}
        try:
            # List all available voices
            response = self.client.list_voices()
            english_voices = []
            for voice in response.voices:
                if any(lang_code.startswith('en-') for lang_code in voice.language_codes):
                    english_voices.append(voice)

            male_voices = [v for v in english_voices if v.ssml_gender == texttospeech.SsmlVoiceGender.MALE]
            female_voices = [v for v in english_voices if v.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE]

            # Expanded parameter ranges for 60 unique combinations
            speaking_rates = [round(0.85 + i * 0.03, 2) for i in range(11)]
            male_pitches = [round(-0.6 + i * 0.12, 2) for i in range(11)]
            female_pitches = [round(-0.2 + i * 0.12, 2) for i in range(11)]
            neutral_pitches = [round(-0.3 + i * 0.06, 2) for i in range(11)]

            language_distribution = {'en-US': 36, 'en-GB': 12, 'en-AU': 12}
            gender_limits = {
                'Male': {k: v // 3 for k, v in language_distribution.items()},
                'Female': {k: v // 3 for k, v in language_distribution.items()},
                'Neutral': {k: v // 3 for k, v in language_distribution.items()},
            }

            def sort_voices(voices):
                return sorted(
                    voices,
                    key=lambda v: (
                        'Chirp3-HD' not in v.name and 'Chirp-HD' not in v.name,
                        v.name
                    )
                )

            voices_by_gender_lang = {
                'Male': {lc: [] for lc in language_distribution},
                'Female': {lc: [] for lc in language_distribution}
            }

            for v in male_voices:
                for lc in language_distribution:
                    if lc in v.language_codes:
                        voices_by_gender_lang['Male'][lc].append(v)

            for v in female_voices:
                for lc in language_distribution:
                    if lc in v.language_codes:
                        voices_by_gender_lang['Female'][lc].append(v)

            for gender in voices_by_gender_lang:
                for lc in voices_by_gender_lang[gender]:
                    voices_by_gender_lang[gender][lc] = sort_voices(voices_by_gender_lang[gender][lc])

            used_param_combos = set()
            param_index = 0

            def next_params(pitch_list):
                nonlocal param_index
                for _ in range(len(speaking_rates) * len(pitch_list)):
                    rate = speaking_rates[param_index % len(speaking_rates)]
                    pitch = pitch_list[(param_index * 2) % len(pitch_list)]
                    param_index += 1
                    combo = (rate, pitch)
                    if combo not in used_param_combos:
                        used_param_combos.add(combo)
                        return rate, pitch
                return speaking_rates[0], pitch_list[0]

            selected_voice_objs = {g: {lc: [] for lc in language_distribution} for g in ['Male', 'Female']}

            for gender, pitch_list in [('Male', male_pitches), ('Female', female_pitches)]:
                for lc, limit in gender_limits[gender].items():
                    count = 0
                    for voice in voices_by_gender_lang[gender][lc]:
                        if count >= limit:
                            break
                        speaking_rate, pitch = next_params(pitch_list)
                        result[gender].append({
                            'voice_id': voice.name,
                            'language_codes': list(voice.language_codes),
                            'speaking_rate': speaking_rate,
                            'pitch': pitch
                        })
                        selected_voice_objs[gender][lc].append(voice)
                        count += 1

            neutral_limits = gender_limits['Neutral']
            for lc, limit in neutral_limits.items():
                half = limit // 2
                male_pool = selected_voice_objs['Male'][lc][:half]
                female_pool = selected_voice_objs['Female'][lc][:half]
                for voice in male_pool + female_pool:
                    speaking_rate, pitch = next_params(neutral_pitches)
                    result['Neutral'].append({
                        'voice_id': voice.name,
                        'language_codes': list(voice.language_codes),
                        'speaking_rate': speaking_rate,
                        'pitch': pitch
                    })
            
            
            # Save the cache to file with timestamp
            timestamp = datetime.now().isoformat()
            cache_data = {
                'last_updated': timestamp,
                'voices': result
            }
            os.makedirs(os.path.dirname(self.VOICE_CACHE_FILE), exist_ok=True)
            with open(self.VOICE_CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info(f"Cached {sum(len(voices) for voices in result.values())} voices: Male={len(result['Male'])}, Female={len(result['Female'])}, Neutral={len(result['Neutral'])}")
            return result
            
        except Exception as e:
            logger.error(f"Error refreshing voice cache: {str(e)}", exc_info=True)
            return result
    
    def get_voices_by_gender(self, gender: str) -> List[Dict]:
        """Get cached voices for a specific gender.
        
        Args:
            gender: 'Male', 'Female', or 'Neutral'
            
        Returns:
            List of voice profiles for the specified gender
        """
        if gender not in self.voice_cache or not self.voice_cache[gender]:
            logger.warning(f"No voices available for gender '{gender}'. Using empty list.")
            return []
        return self.voice_cache[gender]

    async def text_to_audio_async(
        self,
        text_input: str,
        output_filepath: str,
        language_code: Optional[str] = "en-US",
        speaker_gender: str = None,  # e.g., "Male", "Female", "Neutral", or None for default
        voice_name: str = None,      # e.g., "en-US-Neural2-F", overrides gender if provided
        voice_params: dict = None    # Optional additional voice parameters like speaking_rate and pitch
    ) -> bool:
        """
        Synthesizes speech from text and saves it to an audio file.

        Args:
            text_input: The text to synthesize.
            output_filepath: The path to save the output audio file (e.g., 'output.mp3').
            language_code: The language code (e.g., 'en-US').
            speaker_gender: Optional gender of the speaker ('Male', 'Female', 'Neutral'). 
                            If None, a default voice for the language will be used.
            voice_name: Optional specific voice name (e.g., 'en-US-Neural2-F'). 
                       If provided, this overrides the speaker_gender setting.
            voice_params: Optional dictionary of additional voice parameters such as:
                         - 'speaking_rate': Speed of speech (0.25 to 4.0, default 1.0)
                         - 'pitch': Voice pitch (-20.0 to 20.0, default 0.0)
        
        Returns:
            True if synthesis was successful and file was saved, False otherwise.
        """
        if not text_input or not output_filepath:
            logger.error("Text input and output filepath cannot be empty.")
            return False

        try:
            synthesis_input = texttospeech.SynthesisInput(text=text_input)

            voice_selection_params = texttospeech.VoiceSelectionParams(
                language_code=language_code
            )

            # If a specific voice name is provided, it overrides gender selection
            if voice_name:
                # Example: "en-US-Neural2-F"
                # Extract language code from voice name if possible
                if '-' in voice_name:
                    # Extract language code from voice name (e.g., "en-GB" from "en-GB-Neural2-C")
                    extracted_lang_code = '-'.join(voice_name.split('-')[:2]).lower()
                    # Use extracted language code if available, otherwise use provided language_code
                    voice_language_code = extracted_lang_code
                    logger.info(f"Extracted language code '{voice_language_code}' from voice name '{voice_name}'")
                else:
                    voice_language_code = language_code
                    
                voice_selection_params = texttospeech.VoiceSelectionParams(
                    language_code=voice_language_code,
                    name=voice_name,
                )
            # Otherwise use gender if provided
            elif speaker_gender:
                if speaker_gender.lower() == "male":
                    voice_selection_params.ssml_gender = texttospeech.SsmlVoiceGender.MALE
                elif speaker_gender.lower() == "female":
                    voice_selection_params.ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
                elif speaker_gender.lower() == "neutral":
                    voice_selection_params.ssml_gender = texttospeech.SsmlVoiceGender.NEUTRAL
                else:
                    logger.warning(f"Unsupported speaker_gender '{speaker_gender}'. Using default voice.")
            # If neither voice_name nor speaker_gender is provided, the API will use a default voice for the language.

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            if voice_params:
                if 'speaking_rate' in voice_params:
                    audio_config.speaking_rate = voice_params['speaking_rate']
                if 'pitch' in voice_params:
                    audio_config.pitch = voice_params['pitch']

            # Enhanced logging with all voice parameters
            log_message = f"Requesting speech synthesis for text: '{text_input[:50]}...' with "
            log_message += f"lang='{language_code}'"
            if voice_name:
                log_message += f", voice='{voice_name}'"
            elif speaker_gender:
                log_message += f", gender='{speaker_gender}'"
            else:
                log_message += ", using default voice"
                
            if voice_params:
                params_str = ', '.join([f"{k}={v}" for k, v in voice_params.items()])
                log_message += f", params={{{params_str}}}"
                
            logger.info(log_message)

            # Log metrics periodically during active TTS operations
            self.log_metrics_if_needed()

            # The synthesize_speech method is blocking, so run it in a separate thread
            # Check executor health before attempting to use it
            if not self._executor_is_healthy():
                logger.warning("TTS executor is shutdown, attempting to recreate...")
                # Try to recreate the executor
                self._executor = None
                executor = self._get_executor()
                if not self._executor_is_healthy():
                    logger.error("Unable to create healthy TTS executor, falling back to synchronous execution")
                    # Fall back to synchronous execution as last resort
                    synthesis_func = functools.partial(
                        self.client.synthesize_speech,
                        request={
                            "input": synthesis_input,
                            "voice": voice_selection_params,
                            "audio_config": audio_config,
                        }
                    )
                    try:
                        response = synthesis_func()
                    except Exception as e:
                        logger.error(f"Synchronous TTS fallback failed: {e}")
                        raise RuntimeError(f"TTS synthesis failed with synchronous fallback: {e}")
                else:
                    executor = self._get_executor()
            else:
                executor = self._get_executor()
            
            if self._executor_is_healthy():
                # Create a partial function to avoid event loop issues
                synthesis_func = functools.partial(
                    self.client.synthesize_speech,
                    request={
                        "input": synthesis_input,
                        "voice": voice_selection_params,
                        "audio_config": audio_config,
                    }
                )
                
                # Submit to our dedicated executor and await the result
                try:
                    start_time = time.time()
                    future = executor.submit(synthesis_func)
                    response = await asyncio.wrap_future(future)
                    processing_time = time.time() - start_time
                    self._metrics.record_job(processing_time, True)
                except RuntimeError as e:
                    if "cannot schedule new futures after interpreter shutdown" in str(e):
                        logger.warning("Executor shutdown during TTS call, falling back to synchronous execution")
                        # Fall back to synchronous execution
                        response = synthesis_func()
                        processing_time = time.time() - start_time
                        self._metrics.record_job(processing_time, True)
                    else:
                        raise
            else:
                # If executor is not healthy, use synchronous execution
                synthesis_func = functools.partial(
                    self.client.synthesize_speech,
                    request={
                        "input": synthesis_input,
                        "voice": voice_selection_params,
                        "audio_config": audio_config,
                    }
                )
                response = synthesis_func()
                processing_time = time.time() - start_time
                self._metrics.record_job(processing_time, True)
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_filepath)
            if output_dir:
                 os.makedirs(output_dir, exist_ok=True)

            with open(output_filepath, "wb") as out_file:
                out_file.write(response.audio_content)
            logger.info(f"Audio content written to file: {output_filepath}")
            return True

        except Exception as e:
            logger.error(f"Error during text-to-speech synthesis: {e}", exc_info=True)
            self._metrics.record_job(0, False)
            return False

# Example usage (for testing purposes, can be removed later)
async def main_tts_test():
    print("Testing TTS Service...")
    # GOOGLE_APPLICATION_CREDENTIALS should be loaded by dotenv from the .env file.
    # The Google client library will automatically use it.
    # We can add a check here if we want to be explicit, or let the client initialization fail if not set.
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warning("GOOGLE_APPLICATION_CREDENTIALS not found in environment after dotenv load. TTS client might fail to initialize if not set globally.")
        # Depending on strictness, you might choose to return here or let it proceed to client init.

    # Forcing a re-check to ensure .env is loaded before client instantiation for the test.
    # In a real app, service instantiation might happen elsewhere.
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("Error: GOOGLE_APPLICATION_CREDENTIALS is not set in .env or environment.")
        print("Please ensure it's in your .env file: GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/key.json")
        return

    service = GoogleCloudTtsService()
    sample_text_host = "Hello, and welcome to the podcast! Today we're discussing exciting topics."
    sample_text_female = "I agree, this is a fascinating subject with many layers."
    sample_text_male = "Indeed, the implications are quite profound when you consider the details."

    output_dir = "./tts_outputs"
    os.makedirs(output_dir, exist_ok=True)

    # Test with default voice (Host)
    success_host = await service.text_to_audio_async(
        text_input=sample_text_host,
        output_filepath=os.path.join(output_dir, "host_audio.mp3")
    )
    print(f"Host audio generation successful: {success_host}")

    # Test with female voice
    success_female = await service.text_to_audio_async(
        text_input=sample_text_female,
        output_filepath=os.path.join(output_dir, "female_audio.mp3"),
        speaker_gender="Female"
    )
    print(f"Female audio generation successful: {success_female}")

    # Test with male voice
    success_male = await service.text_to_audio_async(
        text_input=sample_text_male,
        output_filepath=os.path.join(output_dir, "male_audio.mp3"),
        speaker_gender="Male"
    )
    print(f"Male audio generation successful: {success_male}")
    # print("TTS Test stubs created. Implement text_to_audio_async to run full tests.") # Original line removed

if __name__ == "__main__":
    # To run this test: python app/tts_service.py
    # Make sure GOOGLE_APPLICATION_CREDENTIALS is set.
    asyncio.run(main_tts_test())
