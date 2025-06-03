#!/usr/bin/env python3
"""
Test to validate the podcast://{task_id}/transcript MCP resource implementation.
"""

import asyncio
import sys
import os
import uuid

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.status_manager import get_status_manager
from app.podcast_models import PodcastEpisode
from fastmcp.exceptions import ToolError

async def test_podcast_transcript_resource():
    """Test the podcast transcript resource implementation."""
    print("=== Testing Podcast Transcript Resource Implementation ===")
    
    try:
        # Import the actual resource function
        from app.mcp_server import get_podcast_transcript_resource
        
        # Step 1: Test with a non-existent task (should raise ToolError)
        print("1. Testing with non-existent task...")
        fake_task_id = str(uuid.uuid4())
        
        try:
            result = await get_podcast_transcript_resource(fake_task_id)
            print("❌ Should have raised ToolError for non-existent task")
            return False
        except ToolError as e:
            if "Task not found" in str(e):
                print(f"✅ Correctly raised ToolError: {e}")
            else:
                print(f"❌ Wrong error message: {e}")
                return False
        
        # Step 2: Test input validation
        print("2. Testing input validation...")
        
        # Test empty task_id
        try:
            result = await get_podcast_transcript_resource("")
            print("❌ Should have raised ToolError for empty task_id")
            return False
        except ToolError as e:
            if "task_id is required" in str(e):
                print(f"✅ Correctly validates empty task_id: {e}")
            else:
                print(f"❌ Wrong error for empty task_id: {e}")
                return False
        
        # Test short task_id
        try:
            result = await get_podcast_transcript_resource("short")
            print("❌ Should have raised ToolError for short task_id")
            return False
        except ToolError as e:
            if "Invalid task_id format" in str(e):
                print(f"✅ Correctly validates short task_id: {e}")
            else:
                print(f"❌ Wrong error for short task_id: {e}")
                return False
        
        # Step 3: Test with task that has no episode (should raise ToolError)
        print("3. Testing with task that has no episode...")
        status_manager = get_status_manager()
        
        # Create a test task without an episode
        test_task_no_episode = str(uuid.uuid4())
        status_manager.create_status(test_task_no_episode, request_data=None)
        
        try:
            result = await get_podcast_transcript_resource(test_task_no_episode)
            print("❌ Should have raised ToolError for task without episode")
            return False
        except ToolError as e:
            if "not available" in str(e):
                print(f"✅ Correctly raised ToolError for missing episode: {e}")
            else:
                print(f"❌ Wrong error for missing episode: {e}")
                return False
        
        # Step 4: Test with real task that has transcript
        print("4. Testing with real task that has transcript...")
        
        test_task_id = str(uuid.uuid4())
        status_manager.create_status(test_task_id, request_data=None)
        
        # Create a test episode with transcript
        test_transcript = """Host: Welcome to MySalonCast! Today we're discussing the future of technology.

Guest: Thanks for having me on. I'm excited to share my thoughts on AI and automation.

Host: Let's start with artificial intelligence. What do you think are the biggest opportunities?

Guest: I believe AI will revolutionize how we work, especially in creative fields. The key is human-AI collaboration.

Host: That's fascinating. Can you give us a specific example?

Guest: Certainly! Take podcast production - AI can help with research, script writing, and even audio editing, but the human touch is still essential for authenticity and creativity.

Host: Great point! What about the challenges and concerns?

Guest: The main concerns are job displacement and the need for proper regulation. We need to ensure AI benefits everyone, not just a few.

Host: Absolutely. Any final thoughts for our listeners?

Guest: Stay curious, keep learning, and don't fear technology - embrace it as a tool to enhance your capabilities.

Host: Wonderful advice! Thanks for joining us today. That's all for this episode of MySalonCast!"""
        
        test_episode = PodcastEpisode(
            title="The Future of AI and Automation",
            summary="A deep dive into artificial intelligence, automation, and their impact on the future of work with industry expert Dr. Sarah Chen.",
            transcript=test_transcript,
            audio_filepath="/tmp/ai_future_podcast.mp3",
            source_attributions=["https://techreview.com/ai-trends", "https://futureofwork.org/automation"],
            warnings=[]
        )
        
        # Store the episode
        status_manager.set_episode(test_task_id, test_episode)
        
        # Now test the resource
        result = await get_podcast_transcript_resource(test_task_id)
        
        print(f"✅ Resource returned data for task with transcript: {test_task_id}")
        
        # Validate the response structure
        expected_fields = ["task_id", "transcript", "title", "summary", "character_count", "resource_type"]
        
        for field in expected_fields:
            if field not in result:
                print(f"❌ Missing field in response: {field}")
                return False
        
        print("✅ All expected fields present in response")
        
        # Validate specific values
        if result["task_id"] != test_task_id:
            print(f"❌ Wrong task_id in response: {result['task_id']}")
            return False
        
        if result["transcript"] != test_transcript:
            print(f"❌ Wrong transcript in response")
            return False
        
        if result["title"] != test_episode.title:
            print(f"❌ Wrong title in response: {result['title']}")
            return False
        
        if result["summary"] != test_episode.summary:
            print(f"❌ Wrong summary in response")
            return False
        
        expected_char_count = len(test_transcript)
        if result["character_count"] != expected_char_count:
            print(f"❌ Wrong character count. Expected: {expected_char_count}, Got: {result['character_count']}")
            return False
        
        if result["resource_type"] != "podcast_transcript":
            print(f"❌ Wrong resource_type: {result['resource_type']}")
            return False
        
        print("✅ All field values are correct")
        print(f"  - task_id: {result['task_id']}")
        print(f"  - title: {result['title']}")
        print(f"  - character_count: {result['character_count']}")
        print(f"  - transcript preview: {result['transcript'][:100]}...")
        
        # Step 5: Test with task that has empty transcript
        print("5. Testing with task that has empty transcript...")
        
        test_task_empty = str(uuid.uuid4())
        status_manager.create_status(test_task_empty, request_data=None)
        
        # Create episode with empty transcript
        episode_empty = PodcastEpisode(
            title="Empty Transcript Episode",
            summary="An episode with no transcript content",
            transcript="",  # Empty transcript
            audio_filepath="/tmp/empty_podcast.mp3",
            source_attributions=[],
            warnings=[]
        )
        
        status_manager.set_episode(test_task_empty, episode_empty)
        
        result_empty = await get_podcast_transcript_resource(test_task_empty)
        
        if result_empty["transcript"] != "":
            print(f"❌ Expected empty transcript, got: {result_empty['transcript']}")
            return False
        
        if result_empty["character_count"] != 0:
            print(f"❌ Expected 0 character count, got: {result_empty['character_count']}")
            return False
        
        print("✅ Correctly handles task with empty transcript")
        
        # Step 6: Clean up test data
        print("6. Cleaning up test data...")
        
        print("\n✅ Podcast Transcript Resource Implementation is correct!")
        print("✅ Properly accesses status_info.result_episode.transcript")
        print("✅ Handles various transcript scenarios (content, empty)")
        print("✅ Input validation works properly")
        print("✅ Field mapping is correct")
        print("✅ Character count calculation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test."""
    print("Testing Podcast Transcript Resource Implementation...")
    success = await test_podcast_transcript_resource()
    
    if success:
        print("\n🎉 PODCAST TRANSCRIPT RESOURCE VALIDATION COMPLETE!")
        print("\nThe podcast://{task_id}/transcript resource is properly implemented and will:")
        print("- ✅ Retrieve transcript from StatusManager via result_episode")
        print("- ✅ Return structured transcript data with metadata")
        print("- ✅ Handle validation errors and missing tasks/episodes properly")
        print("- ✅ Map PodcastEpisode.transcript field to response transcript")
        print("- ✅ Calculate character count correctly")
        print("- ✅ Handle empty transcripts gracefully")
        return 0
    else:
        print("\n❌ Podcast Transcript Resource Test FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
