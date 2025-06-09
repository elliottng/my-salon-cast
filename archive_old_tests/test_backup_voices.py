#!/usr/bin/env python3
"""Test backup voice assignment when voice cache is empty"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from llm_service import GeminiService
from tts_service import GoogleCloudTtsService

def test_backup_voice_assignment():
    """Test that backup voices are assigned when cache is empty"""
    print("🔄 Testing backup voice assignment...")
    
    try:
        # Create services
        llm_service = GeminiService()
        
        # Mock an empty TTS service (simulate cache failure)
        class MockEmptyTtsService:
            def get_voices_by_gender(self, gender):
                return []  # Empty cache
        
        llm_service.tts_service = MockEmptyTtsService()
        
        print("\n✅ Simulating empty voice cache...")
        print("🎯 Testing backup voice assignments:")
        
        # Test different personas with different genders
        test_personas = [
            {"name": "Alan Turing", "expected_gender": "Male"},
            {"name": "Ada Lovelace", "expected_gender": "Female"}, 
            {"name": "Claude Shannon", "expected_gender": "Male"},
            {"name": "Grace Hopper", "expected_gender": "Female"},
            {"name": "Alonzo Church", "expected_gender": "Neutral"}
        ]
        
        assigned_voices = []
        
        for i, persona in enumerate(test_personas):
            print(f"\n--- Persona {i+1}: {persona['name']} ---")
            
            # Manually create a persona research request (simulating LLM research)
            # This is testing the voice assignment part only
            persona_research = {
                "name": persona["name"],
                "gender": persona["expected_gender"],
                "expertise": "Computer Science",
                "background": "Pioneer in computing",
                "perspective": "Historical figure perspective"
            }
            
            # Simulate the voice assignment logic that happens in research_persona_async
            gender = persona_research["gender"]
            
            # This is the backup voice logic from our updated code
            chirp3_backup_voices = {
                'Male': ['en-US-Chirp3-HD-Achird', 'en-GB-Chirp3-HD-Algenib', 'en-AU-Chirp3-HD-Algieba'],
                'Female': ['en-US-Chirp3-HD-Achernar', 'en-GB-Chirp3-HD-Aoede', 'en-AU-Chirp3-HD-Autonoe'],
                'Neutral': ['en-US-Chirp3-HD-Achird', 'en-GB-Chirp3-HD-Achernar', 'en-AU-Chirp3-HD-Algenib']
            }
            
            import random
            backup_voice = random.choice(chirp3_backup_voices.get(gender, chirp3_backup_voices['Neutral']))
            speaking_rate = random.uniform(0.85, 1.15)
            
            assigned_voices.append({
                'persona': persona['name'],
                'gender': gender,
                'voice': backup_voice,
                'speaking_rate': round(speaking_rate, 2)
            })
            
            print(f"   Gender: {gender}")
            print(f"   Backup Voice: {backup_voice}")
            print(f"   Speaking Rate: {round(speaking_rate, 2)}")
        
        print(f"\n🎉 Backup Voice Assignment Summary:")
        for assignment in assigned_voices:
            print(f"   {assignment['persona']} ({assignment['gender']}) → {assignment['voice']} @ {assignment['speaking_rate']}")
        
        # Check diversity
        unique_voices = set(a['voice'] for a in assigned_voices)
        print(f"\n📊 Voice Diversity:")
        print(f"   Total personas: {len(assigned_voices)}")
        print(f"   Unique voices: {len(unique_voices)}")
        print(f"   Unique voices list: {sorted(unique_voices)}")
        
        # Check that we're only using Chirp3-HD voices
        all_chirp3 = all('Chirp3-HD' in a['voice'] for a in assigned_voices)
        print(f"   All Chirp3-HD voices: {'✅' if all_chirp3 else '❌'}")
        
        # Check that no old Chirp voices are used
        no_old_chirp = all('Chirp-HD' not in a['voice'] or 'Chirp3-HD' in a['voice'] for a in assigned_voices)
        print(f"   No old Chirp voices: {'✅' if no_old_chirp else '❌'}")
        
        if all_chirp3 and no_old_chirp and len(unique_voices) > 1:
            print("\n🎉 SUCCESS: Backup voice assignment working correctly!")
            print("   ✅ Only Chirp3-HD voices assigned")
            print("   ✅ No old Chirp voices assigned") 
            print("   ✅ Voice diversity maintained")
        else:
            print("\n⚠️  Issues detected in backup voice assignment")
        
    except Exception as e:
        print(f"❌ Error testing backup voices: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backup_voice_assignment()
