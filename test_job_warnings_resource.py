#!/usr/bin/env python3
"""
Test to validate the jobs://{task_id}/warnings MCP resource implementation.
"""

import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.status_manager import get_status_manager
from app.podcast_models import PodcastEpisode
from fastmcp.exceptions import ToolError

async def test_job_warnings_resource():
    """Test the job warnings resource implementation."""
    print("=== Testing Job Warnings Resource Implementation ===")
    
    try:
        # Import the actual resource function
        from app.mcp_server import get_job_warnings_resource
        
        # Step 1: Test with a non-existent task (should raise ToolError)
        print("1. Testing with non-existent task...")
        fake_task_id = str(uuid.uuid4())
        
        try:
            result = await get_job_warnings_resource(fake_task_id)
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
            result = await get_job_warnings_resource("")
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
            result = await get_job_warnings_resource("short")
            print("❌ Should have raised ToolError for short task_id")
            return False
        except ToolError as e:
            if "Invalid task_id format" in str(e):
                print(f"✅ Correctly validates short task_id: {e}")
            else:
                print(f"❌ Wrong error for short task_id: {e}")
                return False
        
        # Step 3: Test with real task that has warnings
        print("3. Testing with real task that has warnings...")
        status_manager = get_status_manager()
        
        # Create a test task with warnings
        test_task_id = str(uuid.uuid4())
        
        # Create status
        status_manager.create_status(test_task_id, request_data=None)
        
        # Create a test episode with warnings
        test_warnings = [
            "Failed to extract content from URL https://example.com: Connection timeout",
            "TTS failed for turn 3: Text too long",
            "LLM source analysis returned no data."
        ]
        
        test_episode = PodcastEpisode(
            title="Test Podcast Episode",
            summary="A test episode with multiple warnings",
            transcript="Host: Welcome to our test podcast. Guest: Thanks for having me!",
            audio_filepath="/tmp/test_audio.mp3",
            source_attributions=["https://example.com"],
            warnings=test_warnings
        )
        
        # Store the episode with warnings
        status_manager.set_episode(test_task_id, test_episode)
        
        # Now test the resource
        result = await get_job_warnings_resource(test_task_id)
        
        print(f"✅ Resource returned data for task with warnings: {test_task_id}")
        
        # Validate the response structure
        expected_fields = ["task_id", "warnings", "warning_count", "has_errors", "error_message", "last_updated", "resource_type"]
        
        for field in expected_fields:
            if field not in result:
                print(f"❌ Missing field in response: {field}")
                return False
        
        print("✅ All expected fields present in response")
        
        # Validate specific values
        if result["task_id"] != test_task_id:
            print(f"❌ Wrong task_id in response: {result['task_id']}")
            return False
        
        if result["warnings"] != test_warnings:
            print(f"❌ Wrong warnings in response. Expected: {test_warnings}, Got: {result['warnings']}")
            return False
        
        if result["warning_count"] != len(test_warnings):
            print(f"❌ Wrong warning count. Expected: {len(test_warnings)}, Got: {result['warning_count']}")
            return False
        
        if result["resource_type"] != "job_warnings":
            print(f"❌ Wrong resource_type: {result['resource_type']}")
            return False
        
        if result["has_errors"] != False:  # Task status should not be "failed"
            print(f"❌ Wrong has_errors value: {result['has_errors']}")
            return False
        
        print("✅ All field values are correct")
        print(f"  - task_id: {result['task_id']}")
        print(f"  - warning_count: {result['warning_count']}")
        print(f"  - warnings: {result['warnings']}")
        print(f"  - has_errors: {result['has_errors']}")
        print(f"  - last_updated: {result['last_updated']}")
        
        # Step 4: Test with task that has no warnings
        print("4. Testing with task that has no warnings...")
        
        test_task_id_no_warnings = str(uuid.uuid4())
        status_manager.create_status(test_task_id_no_warnings, request_data=None)
        
        # Create episode without warnings
        episode_no_warnings = PodcastEpisode(
            title="Clean Episode",
            summary="An episode with no warnings",
            transcript="Perfect generation with no issues",
            audio_filepath="/tmp/clean_audio.mp3",
            source_attributions=["https://perfect-source.com"],
            warnings=[]  # No warnings
        )
        
        status_manager.set_episode(test_task_id_no_warnings, episode_no_warnings)
        
        result_no_warnings = await get_job_warnings_resource(test_task_id_no_warnings)
        
        if result_no_warnings["warning_count"] != 0:
            print(f"❌ Expected 0 warnings, got: {result_no_warnings['warning_count']}")
            return False
        
        if result_no_warnings["warnings"] != []:
            print(f"❌ Expected empty warnings list, got: {result_no_warnings['warnings']}")
            return False
        
        print("✅ Correctly handles task with no warnings")
        
        # Clean up test data
        print("5. Cleaning up test data...")
        # Note: In production, this would clean up database entries
        # For testing, we'll let them remain as they don't interfere
        
        print("\n✅ Job Warnings Resource Implementation is correct!")
        print("✅ Properly accesses status_info.result_episode.warnings")
        print("✅ Handles tasks with and without warnings")
        print("✅ Input validation works properly")
        print("✅ Field mapping is correct (last_updated_at)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test."""
    print("Testing Job Warnings Resource Implementation...")
    success = await test_job_warnings_resource()
    
    if success:
        print("\n🎉 JOB WARNINGS RESOURCE VALIDATION COMPLETE!")
        print("\nThe jobs://{task_id}/warnings resource is properly implemented and will:")
        print("- ✅ Retrieve warnings from StatusManager via result_episode")
        print("- ✅ Return structured warning data with count and metadata")
        print("- ✅ Handle validation errors and missing tasks properly")
        print("- ✅ Map PodcastEpisode.warnings field to response warnings")
        print("- ✅ Include error status and timestamp information")
        print("- ✅ Correctly handle tasks with no warnings (empty list)")
        return 0
    else:
        print("\n❌ Job Warnings Resource Test FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
