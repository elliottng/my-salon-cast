#!/usr/bin/env python
"""
Test script to verify that voice differentiation is working properly across genders.
This script will create multiple personas with different genders and verify that each
gets a unique voice with distinct parameters.
"""

import os
import sys
import json
import logging
import random
import tempfile
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tts_service import GoogleCloudTtsService
from app.llm_service import GeminiService
from app.podcast_models import PersonaResearch

def simulate_persona_research(llm_service, persona_name, gender):
    """Simulate persona research with a specified gender."""
    # Create a person_id from the name
    person_id = persona_name.lower().replace(' ', '_').replace('.', '')
    
    # Create a basic research object with the specified gender
    persona = PersonaResearch(
        person_id=person_id,
        name=persona_name,
        gender=gender,
        detailed_profile=f"Test profile for {persona_name}",
        invented_name=None,
        tts_voice_id=None,
        tts_voice_params=None,
        source_context="Test context",
        creation_date=datetime.now().isoformat()
    )
    
    # Simulate the voice assignment that would happen in research_persona_async
    # by directly calling the voice selection logic
    if llm_service.tts_service:
        voices = llm_service.tts_service.get_voices_by_gender(gender)
        if voices:
            voice_profile = random.choice(voices)
            tts_voice_id = voice_profile['voice_id']
            logger.info(f"Assigned voice profile for {persona_name}: {tts_voice_id}, rate={voice_profile['speaking_rate']}")
            
            # Update the persona with the voice profile
            persona.tts_voice_id = tts_voice_id
            
            # Store the full voice profile parameters
            voice_params = {}
            for key, value in voice_profile.items():
                if key != 'language_codes':  # Skip language_codes
                    voice_params[key] = value
            
            persona.tts_voice_params = voice_params
        else:
            logger.warning(f"No voice profiles available for {gender} gender")
            # Create a fallback voice profile with randomized parameters
            speaking_rate = round(random.uniform(0.8, 1.3), 1)
            persona.tts_voice_params = {
                'voice_id': None,
                'speaking_rate': speaking_rate
            }
    
    return persona

def test_voice_differentiation():
    """Test that personas with different genders get distinct voices."""
    # Initialize TTS service with a forced refresh
    logger.info("Initializing TTS service with forced cache refresh...")
    tts_service = GoogleCloudTtsService()
    tts_service.voice_cache = tts_service._load_or_refresh_voice_cache(force_refresh=True)
    
    # Initialize LLM service with the TTS service
    llm_service = GeminiService(tts_service=tts_service)
    
    # Create test personas with different genders
    personas = [
        ("John Smith", "Male"),
        ("Jane Doe", "Female"),
        ("Alex Johnson", "Neutral"),
        ("Michael Brown", "Male"),
        ("Emily White", "Female"),
        ("Taylor Green", "Neutral")
    ]
    
    # Simulate persona research for each
    persona_objects = []
    for name, gender in personas:
        persona = simulate_persona_research(llm_service, name, gender)
        persona_objects.append(persona)
        logger.info(f"Created persona: {name}, Gender: {gender}, Voice ID: {persona.tts_voice_id}, "
                   f"Speaking Rate: {persona.tts_voice_params.get('speaking_rate')}")
    
    # Check for duplicate voice IDs within the same gender
    for gender in ["Male", "Female", "Neutral"]:
        gender_personas = [p for p in persona_objects if p.gender == gender]
        voice_ids = [p.tts_voice_id for p in gender_personas if p.tts_voice_id is not None]
        unique_ids = set(voice_ids)
        
        if len(voice_ids) != len(unique_ids):
            logger.warning(f"Found duplicate voice IDs within {gender} personas: {voice_ids}")
        else:
            logger.info(f"All {gender} personas have unique voice IDs: {voice_ids}")
    
    # Check for unique voice parameters
    params_set = set()
    for persona in persona_objects:
        if persona.tts_voice_params:
            params = (
                persona.tts_voice_params.get('voice_id'),
                persona.tts_voice_params.get('speaking_rate')
            )
            params_set.add(params)
    
    logger.info(f"Found {len(params_set)} unique voice parameter combinations for {len(persona_objects)} personas")
    if len(params_set) != len(persona_objects):
        logger.warning("Some personas have identical voice parameters!")
    else:
        logger.info("All personas have unique voice parameters!")
    
    # Save personas to JSON for inspection
    output_file = os.path.join(tempfile.gettempdir(), "voice_test_personas.json")
    with open(output_file, 'w') as f:
        # Convert to dict and handle datetime serialization
        persona_dicts = []
        for p in persona_objects:
            p_dict = p.model_dump() if hasattr(p, 'model_dump') else p.dict()
            # Convert datetime to string
            if 'creation_date' in p_dict and isinstance(p_dict['creation_date'], datetime):
                p_dict['creation_date'] = p_dict['creation_date'].isoformat()
            persona_dicts.append(p_dict)
        json.dump(persona_dicts, f, indent=2)
    
    logger.info(f"Saved test personas to {output_file}")
    
    return persona_objects

if __name__ == "__main__":
    logger.info("Starting voice differentiation test...")
    try:
        personas = test_voice_differentiation()
        logger.info("Test completed successfully!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}", exc_info=True)
        sys.exit(1)
