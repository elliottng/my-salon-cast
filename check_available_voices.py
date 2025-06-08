#!/usr/bin/env python3
"""Script to check what voices are available from Google Cloud TTS"""

import os
import sys
from collections import defaultdict

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from tts_service import GoogleCloudTtsService
from google.cloud import texttospeech

def check_available_voices():
    """Check what voices are available and their naming patterns"""
    print("🔍 Checking available voices from Google Cloud TTS...")
    
    try:
        tts_service = GoogleCloudTtsService()
        
        # Get all available voices
        response = tts_service.client.list_voices()
        
        # Filter for English voices
        english_voices = []
        for voice in response.voices:
            if any(lang_code.startswith('en-') for lang_code in voice.language_codes):
                english_voices.append(voice)
        
        print(f"\n📊 Found {len(english_voices)} English voices")
        
        # Categorize by voice type
        voice_categories = defaultdict(list)
        for voice in english_voices:
            if 'Chirp3-HD' in voice.name:
                voice_categories['Chirp3-HD'].append(voice)
            elif 'Chirp-HD' in voice.name:
                voice_categories['Chirp-HD'].append(voice)
            elif 'Neural' in voice.name:
                voice_categories['Neural'].append(voice)
            elif 'Standard' in voice.name:
                voice_categories['Standard'].append(voice)
            elif 'WaveNet' in voice.name:
                voice_categories['WaveNet'].append(voice)
            else:
                voice_categories['Other'].append(voice)
        
        print("\n🗂️ Voice categories:")
        for category, voices in voice_categories.items():
            print(f"  {category}: {len(voices)} voices")
            
            # Show gender breakdown
            male_count = sum(1 for v in voices if v.ssml_gender == texttospeech.SsmlVoiceGender.MALE)
            female_count = sum(1 for v in voices if v.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE)
            
            print(f"    - Male: {male_count}, Female: {female_count}")
            
            # Show language breakdown
            lang_breakdown = defaultdict(int)
            for voice in voices:
                for lang_code in voice.language_codes:
                    if lang_code.startswith('en-'):
                        lang_breakdown[lang_code] += 1
            
            print(f"    - Languages: {dict(lang_breakdown)}")
            
            # Show a few examples
            examples = [v.name for v in voices[:3]]
            print(f"    - Examples: {examples}")
        
        # Check specifically Chirp3-HD availability by language and gender
        print("\n🎯 Chirp3-HD voice availability:")
        chirp3_voices = voice_categories['Chirp3-HD']
        
        for lang in ['en-US', 'en-GB', 'en-AU']:
            male_chirp3 = [v for v in chirp3_voices 
                          if lang in v.language_codes and v.ssml_gender == texttospeech.SsmlVoiceGender.MALE]
            female_chirp3 = [v for v in chirp3_voices 
                            if lang in v.language_codes and v.ssml_gender == texttospeech.SsmlVoiceGender.FEMALE]
            
            print(f"  {lang}:")
            print(f"    - Male Chirp3-HD: {len(male_chirp3)} ({[v.name for v in male_chirp3[:3]]})")
            print(f"    - Female Chirp3-HD: {len(female_chirp3)} ({[v.name for v in female_chirp3[:3]]})")
        
    except Exception as e:
        print(f"❌ Error checking voices: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_available_voices()
