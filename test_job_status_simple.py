#!/usr/bin/env python3
"""
Simple test for the new jobs://{task_id}/status MCP resource.
"""

import asyncio
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from tests.mcp.client import SimpleMCPTestClient


async def test_simple_job_status():
    """Simple test to debug job status resource."""
    print("🧪 Testing job status resource...")
    
    async with SimpleMCPTestClient() as client:
        try:
            # First, list resources to see what's available
            print("📋 Listing available resources...")
            resources = await client.list_resources()
            print(f"Available resources: {resources}")
            
            # Test with an existing task ID if available
            print("\n🔍 Testing job status resource with fake task...")
            try:
                job_status = await client.read_resource("jobs://fake-task-123/status")
                print(f"Unexpected success: {job_status}")
            except Exception as e:
                print(f"Expected error for fake task: {e}")
                
            # Generate a real task to test with  
            print("\n📝 Generating test podcast...")
            generate_result = await client.call_tool("generate_podcast_async_pydantic", {
                "request": {
                    "prominent_persons": ["Test Person"],
                    "source_urls": ["https://en.wikipedia.org/wiki/Battle_of_Jutland"],
                    "podcast_duration_minutes": 1,
                    "language": "en"
                }
            })
            
            print(f"Generate result: {generate_result}")
            
            if generate_result.get("success"):
                task_id = generate_result["result"]["task_id"]
                print(f"📋 Generated task ID: {task_id}")
                
                # Wait a moment
                await asyncio.sleep(5)
                
                # Test job status resource
                print(f"\n🔍 Testing job status resource for task {task_id}...")
                try:
                    job_status = await client.read_resource(f"jobs://{task_id}/status")
                    print(f"✅ Job status: {job_status}")
                    return True
                except Exception as e:
                    print(f"❌ Error reading job status: {e}")
                    return False
            else:
                print(f"❌ Failed to generate podcast: {generate_result}")
                return False
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_simple_job_status())
    sys.exit(0 if result else 1)
