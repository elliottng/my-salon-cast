#!/usr/bin/env python3
"""
Quick test to validate the jobs://{task_id}/status resource with real data.
"""

import asyncio
import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.mcp.client import SimpleMCPTestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVER_URL = "http://localhost:8000"

async def test_job_status_resource():
    """Test the job status resource with a real task."""
    client = SimpleMCPTestClient(SERVER_URL)
    
    try:
        print("=== Testing Job Status Resource ===")
        
        # Step 1: Create a real task
        print("1. Creating a podcast generation task...")
        task_result = await client.call_generate_podcast_async(
            source_urls=["https://en.wikipedia.org/wiki/Artificial_intelligence"],
            prominent_persons=["Alan Turing", "Geoffrey Hinton"],
            podcast_length="5-7 minutes",
            custom_prompt="Focus on AI history"
        )
        
        if not task_result.get("success"):
            print(f"❌ Failed to create task: {task_result}")
            return False
            
        task_id = task_result["task_id"]
        print(f"✅ Created task: {task_id}")
        
        # Step 2: Test the job status resource
        print("2. Testing job status resource...")
        status_result = await client.read_resource(f"jobs://{task_id}/status")
        
        print(f"✅ Got status resource: {status_result}")
        
        # Step 3: Validate the response structure
        required_fields = ["task_id", "status", "progress_percentage", "current_step", 
                          "start_time", "resource_type"]
        
        for field in required_fields:
            if field not in status_result:
                print(f"❌ Missing required field: {field}")
                return False
            print(f"✅ Found field '{field}': {status_result[field]}")
        
        # Step 4: Validate data types
        if status_result["task_id"] != task_id:
            print(f"❌ Task ID mismatch: expected {task_id}, got {status_result['task_id']}")
            return False
            
        if not isinstance(status_result["progress_percentage"], (int, float)):
            print(f"❌ Progress should be numeric, got: {type(status_result['progress_percentage'])}")
            return False
        
        if status_result["resource_type"] != "job_status":
            print(f"❌ Wrong resource type: {status_result['resource_type']}")
            return False
            
        print("✅ All validation checks passed!")
        print(f"📊 Task Status: {status_result['status']}")
        print(f"📈 Progress: {status_result['progress_percentage']}%")
        print(f"🔄 Current Step: {status_result['current_step']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error(f"Job status test failed: {e}", exc_info=True)
        return False
        
    finally:
        await client.close()

async def main():
    """Run the test."""
    print("Testing Job Status Resource...")
    success = await test_job_status_resource()
    
    if success:
        print("\n🎉 Job Status Resource Test PASSED!")
        return 0
    else:
        print("\n❌ Job Status Resource Test FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
