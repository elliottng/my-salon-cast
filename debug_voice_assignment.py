#!/usr/bin/env python3
"""Debug script to check voice assignment behavior"""

import os
import sys
import asyncio
import logging

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from llm_service import GeminiService
from tts_service import GoogleCloudTtsService
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_voice_assignments():
    """Debug voice assignment for different personas"""
    
    # Initialize services
    config = Config()
    tts_service = GoogleCloudTtsService()
    llm_service = GeminiService(config, tts_service)
    
    # Check TTS service voice cache
    print("\n=== TTS Service Voice Cache Status ===")
    print(f"Voice cache available: {hasattr(tts_service, 'voice_cache')}")
    if hasattr(tts_service, 'voice_cache'):
        for gender in ['Male', 'Female', 'Neutral']:
            voices = tts_service.get_voices_by_gender(gender)
            print(f"{gender}: {len(voices)} voices")
            if voices:
                print(f"  First voice: {voices[0]['voice_id']}")
    
    # Test persona research for different personas
    test_personas = [
        ("Albert Einstein", "Male"),
        ("Marie Curie", "Female"), 
        ("Alan Turing", "Male"),
        ("Ada Lovelace", "Female")
    ]
    
    sample_source_text = "This is a test source text about scientific discoveries and innovations."
    
    print("\n=== Testing Persona Voice Assignment ===")
    for persona_name, expected_gender in test_personas:
        try:
            print(f"\n--- Testing {persona_name} (expected: {expected_gender}) ---")
            
            # Mock LLM response to avoid actual API calls
            mock_response = {
                "person_id": persona_name.lower().replace(' ', '_'),
                "name": persona_name,
                "gender": expected_gender.lower(),
                "detailed_profile": f"Mock profile for {persona_name}",
                "speaking_style": "formal and academic",
                "key_topics": ["science", "research"],
                "invented_name": f"Mock{persona_name.replace(' ', '')}"
            }
            
            # Manually test the voice assignment logic from research_persona_async
            raw_gender = mock_response.get('gender', '').lower()
            
            # Normalize gender
            if not raw_gender or raw_gender not in ['male', 'female', 'neutral']:
                gender = 'Neutral'
            elif raw_gender == 'male':
                gender = 'Male'
            elif raw_gender == 'female':
                gender = 'Female'
            else:
                gender = 'Neutral'
                
            print(f"  Normalized gender: {raw_gender} -> {gender}")
            
            # Test voice assignment
            if tts_service:
                voices = tts_service.get_voices_by_gender(gender)
                if voices:
                    import random
                    voice_profile = random.choice(voices)
                    tts_voice_id = voice_profile['voice_id']
                    print(f"  Voice assigned: {tts_voice_id}")
                    print(f"  Speaking rate: {voice_profile.get('speaking_rate', 1.0)}")
                else:
                    print(f"  ❌ No voices available for {gender} gender")
            else:
                print(f"  ❌ TTS service not available")
                
        except Exception as e:
            print(f"  ❌ Error testing {persona_name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_voice_assignments())
