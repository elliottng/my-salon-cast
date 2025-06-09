#!/usr/bin/env python3
"""Test the new voice filtering logic"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from tts_service import GoogleCloudTtsService

def test_new_voice_filter():
    """Test the new voice filtering logic"""
    print("🔄 Testing new Chirp3-HD only voice filtering...")
    
    try:
        tts_service = GoogleCloudTtsService()
        
        # Force refresh the voice cache with new logic
        new_cache = tts_service._load_or_refresh_voice_cache(force_refresh=True)
        
        print("\n✅ Voice cache refreshed with new filtering!")
        print(f"📊 Voice count by gender:")
        
        for gender in ['Male', 'Female', 'Neutral']:
            voices = new_cache.get(gender, [])
            print(f"\n{gender}: {len(voices)} voices")
            
            # Categorize voices by type
            chirp3_voices = [v for v in voices if 'Chirp3-HD' in v['voice_id']]
            chirp_voices = [v for v in voices if 'Chirp-HD' in v['voice_id'] and 'Chirp3-HD' not in v['voice_id']]
            neural_voices = [v for v in voices if 'Neural' in v['voice_id']]
            other_voices = [v for v in voices if not any(x in v['voice_id'] for x in ['Chirp3-HD', 'Chirp-HD', 'Neural'])]
            
            print(f"    ✅ Chirp3-HD: {len(chirp3_voices)}")
            print(f"    ❌ Old Chirp-HD: {len(chirp_voices)}")
            print(f"    ❌ Neural: {len(neural_voices)}")
            print(f"    ❓ Other: {len(other_voices)}")
            
            # Show language distribution
            if voices:
                lang_count = {'en-US': 0, 'en-GB': 0, 'en-AU': 0, 'other': 0}
                for voice in voices:
                    voice_langs = voice.get('language_codes', [])
                    if 'en-US' in voice_langs:
                        lang_count['en-US'] += 1
                    elif 'en-GB' in voice_langs:
                        lang_count['en-GB'] += 1
                    elif 'en-AU' in voice_langs:
                        lang_count['en-AU'] += 1
                    else:
                        lang_count['other'] += 1
                
                print(f"    📍 Languages: US={lang_count['en-US']}, GB={lang_count['en-GB']}, AU={lang_count['en-AU']}, Other={lang_count['other']}")
                
                # Show first few examples
                examples = [v['voice_id'] for v in voices[:5]]
                print(f"    🎯 Examples: {examples}")
        
        # Check if we successfully eliminated old Chirp voices
        total_old_chirp = sum(len([v for v in new_cache.get(g, []) if 'Chirp-HD' in v['voice_id'] and 'Chirp3-HD' not in v['voice_id']]) for g in ['Male', 'Female', 'Neutral'])
        total_chirp3 = sum(len([v for v in new_cache.get(g, []) if 'Chirp3-HD' in v['voice_id']]) for g in ['Male', 'Female', 'Neutral'])
        
        print(f"\n🎯 Filtering Summary:")
        print(f"   ✅ Total Chirp3-HD voices: {total_chirp3}")
        print(f"   ❌ Total old Chirp-HD voices: {total_old_chirp}")
        
        if total_old_chirp == 0:
            print("   🎉 SUCCESS: All old Chirp voices eliminated!")
        else:
            print("   ⚠️  WARNING: Some old Chirp voices still present")
        
    except Exception as e:
        print(f"❌ Error testing voice filter: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_new_voice_filter()
