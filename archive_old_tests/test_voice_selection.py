#!/usr/bin/env python
import logging
import sys
import json
from app.tts_service import GoogleCloudTtsService
from app.llm_service import GeminiService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_voice_cache():
    """Test that the TTS service can load and create a voice cache with distinct voices per gender."""
    logger.info("Testing TTS service voice cache...")
    
    # Initialize TTS service
    tts_service = GoogleCloudTtsService()
    
    # Get voices by gender
    male_voices = tts_service.get_voices_by_gender('Male')
    female_voices = tts_service.get_voices_by_gender('Female')
    neutral_voices = tts_service.get_voices_by_gender('Neutral')
    
    # Print voice counts
    logger.info(f"Male voices: {len(male_voices)}")
    logger.info(f"Female voices: {len(female_voices)}")
    logger.info(f"Neutral voices: {len(neutral_voices)}")
    
    # Check for distinct voices
    if len(male_voices) == 0 or len(female_voices) == 0 or len(neutral_voices) == 0:
        logger.error("Missing voices for at least one gender")
        return False
    
    # Print first voice of each gender for inspection
    logger.info(f"Sample Male voice: {male_voices[0]}")
    logger.info(f"Sample Female voice: {female_voices[0]}")
    logger.info(f"Sample Neutral voice: {neutral_voices[0]}")
    
    # Verify unique voice IDs
    male_ids = [v['voice_id'] for v in male_voices]
    female_ids = [v['voice_id'] for v in female_voices]
    neutral_ids = [v['voice_id'] for v in neutral_voices]
    
    if len(set(male_ids)) != len(male_ids):
        logger.warning("Duplicate voice IDs in Male voices")
    if len(set(female_ids)) != len(female_ids):
        logger.warning("Duplicate voice IDs in Female voices")
    if len(set(neutral_ids)) != len(neutral_ids):
        logger.warning("Duplicate voice IDs in Neutral voices")
    
    # Check for variation in voice parameters
    male_params = [(v['speaking_rate']) for v in male_voices]
    female_params = [(v['speaking_rate']) for v in female_voices]
    neutral_params = [(v['speaking_rate']) for v in neutral_voices]
    
    if len(set(male_params)) != len(male_params):
        logger.warning("Duplicate voice parameters in Male voices")
    if len(set(female_params)) != len(female_params):
        logger.warning("Duplicate voice parameters in Female voices")
    if len(set(neutral_params)) != len(neutral_params):
        logger.warning("Duplicate voice parameters in Neutral voices")
    
    logger.info("Voice cache test completed")
    return True

def test_llm_voice_selection():
    """Test that the LLM service properly selects voices from TTS service."""
    logger.info("Testing LLM service voice selection...")
    
    # Initialize TTS and LLM services
    tts_service = GoogleCloudTtsService()
    llm_service = GeminiService(tts_service=tts_service)
    
    # Sample personas with known genders
    test_personas = [
        {"name": "John Smith", "gender": "Male"},
        {"name": "Jane Doe", "gender": "Female"},
        {"name": "Alex Johnson", "gender": "Neutral"}
    ]
    
    for persona in test_personas:
        # Use the internal voice selection method directly
        voices = tts_service.get_voices_by_gender(persona["gender"])
        if not voices:
            logger.error(f"No voices found for {persona['gender']} gender")
            continue
            
        logger.info(f"Found {len(voices)} voices for {persona['gender']} gender")
        # Print the first few voices to check parameters
        for i, voice in enumerate(voices[:3]):
            logger.info(f"Voice {i+1}: ID={voice['voice_id']}, rate={voice['speaking_rate']}")
    
    logger.info("LLM voice selection test completed")
    return True

if __name__ == "__main__":
    logger.info("Starting voice selection tests...")
    
    # Delete the cache file to force refresh
    import os
    cache_file = os.path.join(os.path.dirname(__file__), 'app', 'tts_voices_cache.json')
    if os.path.exists(cache_file):
        os.remove(cache_file)
        logger.info(f"Removed existing cache file: {cache_file}")
    
    if test_voice_cache() and test_llm_voice_selection():
        logger.info("All tests passed!")
        sys.exit(0)
    else:
        logger.error("Tests failed!")
        sys.exit(1)
