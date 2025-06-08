#!/usr/bin/env python3
"""
Debug YouTube transcript extraction
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

def test_youtube_api_directly():
    """Test the YouTube transcript API directly without our wrapper."""
    print("🔍 Testing YouTube Transcript API directly...")
    
    # Test with a well-known video that should have transcripts
    test_videos = [
        "dQw4w9WgXcQ",  # Rick Roll
        "9bZkp7q19f0",  # TED Talk
        "kJQP7kiw5Fk",  # Another TED talk
    ]
    
    for video_id in test_videos:
        print(f"\n📹 Testing video ID: {video_id}")
        try:
            # Try to get available transcript languages first
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            print(f"   Available transcripts:")
            
            # Try each available transcript
            for transcript in transcript_list:
                print(f"     - {transcript.language} ({transcript.language_code}) - Generated: {transcript.is_generated}")
                
                try:
                    # Try to fetch this specific transcript
                    transcript_data = transcript.fetch()
                    if transcript_data:
                        full_text = " ".join([item['text'] for item in transcript_data])
                        print(f"       ✅ Success! Transcript length: {len(full_text)} chars")
                        print(f"       Preview: {full_text[:200]}...")
                        return True
                except Exception as e:
                    print(f"       ❌ Failed to fetch: {e}")
                    continue
            
            # Also try the default get_transcript method with language codes
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                if transcript:
                    full_text = " ".join([item['text'] for item in transcript])
                    print(f"   ✅ Default method success! Transcript length: {len(full_text)} chars")
                    print(f"   Preview: {full_text[:200]}...")
                    return True
            except Exception as e:
                print(f"   ❌ Default method error: {e}")
                
        except TranscriptsDisabled:
            print(f"   ⚠️ Transcripts are disabled for this video")
        except NoTranscriptFound:
            print(f"   ⚠️ No transcript found for this video")
        except VideoUnavailable:
            print(f"   ⚠️ Video is unavailable")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    success = test_youtube_api_directly()
    print(f"\n🎯 Result: {'SUCCESS' if success else 'FAILED'}")
