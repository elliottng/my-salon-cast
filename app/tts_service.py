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
            
    def _load_or_refresh_voice_cache(self) -> Dict[str, List[Dict]]:
        """Load voice cache from file or refresh it if expired or missing."""
        try:
            # Check if cache file exists and is not expired
            if os.path.exists(self.VOICE_CACHE_FILE):
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
                            logger.info(f"Loaded voice cache from {last_updated} with {sum(len(voices) for voices in voices.values())} voices")
                            return voices
                        else:
                            # Old format (direct dictionary of voices)
                            logger.info(f"Loaded voice cache with {sum(len(voices) for voices in cache_data.values())} voices")
                            return cache_data
            
            # Cache doesn't exist or is expired, refresh it
            logger.info("Voice cache missing or expired, fetching fresh voice list from Google Cloud TTS")
            return self._refresh_voice_cache()
            
        except Exception as e:
            logger.error(f"Error loading voice cache: {str(e)}. Will use empty cache.")
            # Return empty cache structure in case of error
            return {'Male': [], 'Female': [], 'Neutral': []}
    
    def _refresh_voice_cache(self) -> Dict[str, List[Dict]]:
        """Fetch all available voices from Google Cloud TTS API and cache them."""
        try:
            request = texttospeech.ListVoicesRequest()
            response = self.client.list_voices(request=request)
            
            # Filter by max voices per gender and language
            # For each gender, aim for 7 en-US and 3 en-GB voices
            voices_by_gender = {
                'Male': {'en-US': [], 'en-GB': []},
                'Female': {'en-US': [], 'en-GB': []},
                'Neutral': {'en-US': [], 'en-GB': []}
            }
            
            # Process and filter voices
            for voice in response.voices:
                # Convert language_codes from protobuf Repeated to Python list
                language_codes = list(voice.language_codes)
                # Only include en-US and en-GB voices
                if not any(lang.startswith('en-US') or lang.startswith('en-GB') for lang in language_codes):
                    continue
                    
                # Determine gender category
                if voice.ssml_gender == texttospeech.SsmlVoiceGender.MALE:
                    gender = 'Male'
                elif voice.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE:
                    gender = 'Female'
                elif voice.ssml_gender == texttospeech.SsmlVoiceGender.NEUTRAL:
                    gender = 'Neutral'
                else:
                    continue  # Skip voices with unspecified gender
                
                # Add voice with additional parameters
                voice_entry = {
                    'voice_id': voice.name,
                    'language_codes': language_codes,  # Use our converted list instead of the protobuf object
                    # Add reasonable default voice parameters
                    'speaking_rate': 1.0,
                    'pitch': 0.0
                }
                
                # Determine language category for this voice
                lang_category = 'en-US' if any(lang.startswith('en-US') for lang in language_codes) else 'en-GB'
                
                # Vary parameters slightly based on voice index to create natural diversity
                total_voices = len(voices_by_gender[gender]['en-US']) + len(voices_by_gender[gender]['en-GB'])
                if total_voices > 0:
                    idx = total_voices
                    voice_entry['speaking_rate'] = round(0.95 + (idx % 5) * 0.02, 2)  # Values between 0.95 and 1.03
                    voice_entry['pitch'] = round(-1.0 + (idx % 5) * 0.5, 1)  # Values between -1.0 and 1.0
                
                # Add to the appropriate language category
                voices_by_gender[gender][lang_category].append(voice_entry)
            
            # Prepare the final selected voices (up to 10 per gender: 7 en-US, 3 en-GB)
            final_voices_by_gender = {'Male': [], 'Female': [], 'Neutral': []}
            
            for gender in ['Male', 'Female']:  # Only process Male and Female from API responses
                # Take up to 7 en-US voices
                final_voices_by_gender[gender].extend(voices_by_gender[gender]['en-US'][:7])
                # Take up to 3 en-GB voices
                final_voices_by_gender[gender].extend(voices_by_gender[gender]['en-GB'][:3])
                
            # Create Neutral voices by using a subset of Male and Female voices
            # with modified parameters to make them sound more neutral
            if final_voices_by_gender['Male'] and final_voices_by_gender['Female']:
                # Take 5 voices from each gender if possible
                neutral_candidates = []
                neutral_candidates.extend(final_voices_by_gender['Male'][:5])
                neutral_candidates.extend(final_voices_by_gender['Female'][:5])
                
                # Modify the voice parameters to sound more neutral
                for voice in neutral_candidates:
                    # Create a copy of the voice profile to avoid modifying the originals
                    neutral_voice = voice.copy()
                    # Adjust parameters towards more neutral values
                    neutral_voice['speaking_rate'] = 1.0  # Reset to default
                    neutral_voice['pitch'] = 0.0  # Neutral pitch
                    # Add to neutral voices
                    final_voices_by_gender['Neutral'].append(neutral_voice)
            
            # Tally up the number of voices we have
            voice_count = sum(len(voices) for voices in final_voices_by_gender.values())
            logger.info(f"Cached {voice_count} voices: Male={len(final_voices_by_gender['Male'])}, Female={len(final_voices_by_gender['Female'])}, Neutral={len(final_voices_by_gender['Neutral'])}")
            
            # Save the cache to disk
            with open(self.VOICE_CACHE_FILE, 'w') as f:
                cache_data = {
                    'voices': final_voices_by_gender,
                    'last_updated': datetime.now().isoformat()
                }
                json.dump(cache_data, f, indent=2)
            
            return final_voices_by_gender
            
        except Exception as e:
            logger.error(f"Error refreshing voice cache: {str(e)}")
            # Return empty structure in case of error
            return {'Male': [], 'Female': [], 'Neutral': []}
    
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
        language_code: str = "en-US",
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

            # If voice_name is provided, use it (overrides gender)
            if voice_name:
                voice_selection_params.name = voice_name
                logger.info(f"Using specific voice: {voice_name}")
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
            response = await asyncio.to_thread(
                self.client.synthesize_speech,
                request={
                    "input": synthesis_input,
                    "voice": voice_selection_params,
                    "audio_config": audio_config,
                }
            )
            
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
