# app/tts_service.py

import asyncio
import logging
import os
from google.cloud import texttospeech
from dotenv import load_dotenv
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor
import functools

# Load environment variables from env file
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class GoogleCloudTtsService:
    # Cache file path for storing voice list
    VOICE_CACHE_FILE = os.path.join(os.path.dirname(__file__), 'tts_voices_cache.json')
    # Cache expiration time (24 hours)
    CACHE_EXPIRATION = 24 * 60 * 60  # seconds
    
    # Shared thread pool executor for TTS calls to prevent shutdown issues
    _executor = None
    
    @classmethod
    def _get_executor(cls):
        """Get or create a shared thread pool executor for TTS operations."""
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tts_worker")
            logger.info("Created shared TTS thread pool executor")
        return cls._executor
    
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
            # Count natural and standard voices with good ratings
            english_voices = []
            for voice in response.voices:
                # Only consider English voices
                if any(lang_code.startswith('en-') for lang_code in voice.language_codes):
                    # Include this voice
                    english_voices.append(voice)
            
            # Group voices by gender for natural sounding voices
            # In some regions there are fewer options, so we'll try to get as many as we can
            male_voices = [v for v in english_voices if v.ssml_gender == texttospeech.SsmlVoiceGender.MALE]
            female_voices = [v for v in english_voices if v.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE]
            
            # Ensure we have enough parameter variations to make each voice unique
            # Create a set of unique speaking rates and pitches
            speaking_rates = [round(0.85 + i * 0.05, 2) for i in range(7)]  # 0.85 to 1.15
            male_pitches = [round(-0.6 + i * 0.2, 1) for i in range(7)]     # -0.6 to 0.6
            female_pitches = [round(-0.2 + i * 0.2, 1) for i in range(7)]   # -0.2 to 1.0
            neutral_pitches = [round(-0.3 + i * 0.1, 1) for i in range(7)]  # -0.3 to 0.3
            
            # Process Male voices with unique parameters
            used_male_combos = set()
            for i, voice in enumerate(male_voices):
                if i >= 10:  # Limit to 10 male voices
                    break
                
                # Ensure unique parameter combinations
                rate_idx = i % len(speaking_rates)
                pitch_idx = (i * 2) % len(male_pitches)
                speaking_rate = speaking_rates[rate_idx]
                pitch = male_pitches[pitch_idx]
                
                # Check if this combo is already used
                combo = (voice.name, speaking_rate, pitch)
                attempts = 0
                while combo in used_male_combos and attempts < 10:
                    # Try a different combination
                    rate_idx = (rate_idx + 1) % len(speaking_rates)
                    pitch_idx = (pitch_idx + 1) % len(male_pitches)
                    speaking_rate = speaking_rates[rate_idx]
                    pitch = male_pitches[pitch_idx]
                    combo = (voice.name, speaking_rate, pitch)
                    attempts += 1
                
                used_male_combos.add(combo)
                voice_data = {
                    'voice_id': voice.name,
                    'language_codes': list(voice.language_codes),
                    'speaking_rate': speaking_rate,
                    'pitch': pitch
                }
                result['Male'].append(voice_data)
            
            # Process Female voices with unique parameters
            used_female_combos = set()
            for i, voice in enumerate(female_voices):
                if i >= 10:  # Limit to 10 female voices
                    break
                
                # Ensure unique parameter combinations
                rate_idx = (i + 3) % len(speaking_rates)  # Offset to create different patterns
                pitch_idx = (i * 3) % len(female_pitches)
                speaking_rate = speaking_rates[rate_idx]
                pitch = female_pitches[pitch_idx]
                
                # Check if this combo is already used
                combo = (voice.name, speaking_rate, pitch)
                attempts = 0
                while combo in used_female_combos and attempts < 10:
                    # Try a different combination
                    rate_idx = (rate_idx + 1) % len(speaking_rates)
                    pitch_idx = (pitch_idx + 1) % len(female_pitches)
                    speaking_rate = speaking_rates[rate_idx]
                    pitch = female_pitches[pitch_idx]
                    combo = (voice.name, speaking_rate, pitch)
                    attempts += 1
                
                used_female_combos.add(combo)
                voice_data = {
                    'voice_id': voice.name,
                    'language_codes': list(voice.language_codes),
                    'speaking_rate': speaking_rate,
                    'pitch': pitch
                }
                result['Female'].append(voice_data)
            
            # Create neutral voices with unique parameters
            neutral_source_voices = male_voices[:5] + female_voices[:5]  # Take 5 from each gender
            used_neutral_combos = set()
            
            for i, voice in enumerate(neutral_source_voices):
                if i >= 10:  # Limit to 10 neutral voices
                    break
                
                # Ensure unique parameter combinations
                rate_idx = (i + 1) % len(speaking_rates)
                pitch_idx = i % len(neutral_pitches)
                speaking_rate = speaking_rates[rate_idx]
                pitch = neutral_pitches[pitch_idx]
                
                # Check if this combo is already used
                combo = (voice.name, speaking_rate, pitch)
                attempts = 0
                while combo in used_neutral_combos and attempts < 10:
                    # Try a different combination
                    rate_idx = (rate_idx + 1) % len(speaking_rates)
                    pitch_idx = (pitch_idx + 1) % len(neutral_pitches)
                    speaking_rate = speaking_rates[rate_idx]
                    pitch = neutral_pitches[pitch_idx]
                    combo = (voice.name, speaking_rate, pitch)
                    attempts += 1
                
                used_neutral_combos.add(combo)
                voice_data = {
                    'voice_id': voice.name,
                    'language_codes': list(voice.language_codes),
                    'speaking_rate': speaking_rate,
                    'pitch': pitch
                }
                result['Neutral'].append(voice_data)
            
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

            # The synthesize_speech method is blocking, so run it in a separate thread
            executor = self._get_executor()
            
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
            future = executor.submit(synthesis_func)
            response = await asyncio.wrap_future(future)
            
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
