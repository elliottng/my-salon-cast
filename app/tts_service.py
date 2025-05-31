# app/tts_service.py

import asyncio
import logging
import os
from google.cloud import texttospeech
from dotenv import load_dotenv

# Load environment variables from env file
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class GoogleCloudTtsService:
    def __init__(self):
        """
        Initializes the Google Cloud Text-to-Speech client.
        Assumes GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
        """
        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("GoogleCloudTtsService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize TextToSpeechClient: {e}", exc_info=True)
            logger.error("Ensure GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly and the account has 'roles/cloudtts.serviceAgent' or equivalent permissions.")
            raise

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
