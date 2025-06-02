#!/usr/bin/env python3
"""
Comprehensive test for the new jobs://{task_id}/status MCP resource.

Tests:
1. Job status resource for completed tasks
2. Job status resource for non-existent tasks 
3. Job status resource during active generation (if possible)
4. Proper error handling and data structure validation
"""

import asyncio
import subprocess
import sys
import os
import time
import json
from typing import Optional

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from tests.mcp.client import SimpleMCPTestClient


async def test_job_status_completed_task():
    """Test job status resource for a completed task."""
    print("\n🧪 Testing job status resource for completed task...")
    
    async with SimpleMCPTestClient() as client:
        # Generate a podcast first
        print("📝 Generating podcast for testing...")
        
        generate_result = await client.call_tool("generate_podcast_async_pydantic", {
            "request": {
                "prominent_persons": ["Alan Turing", "Ada Lovelace"],
                "source_urls": ["https://en.wikipedia.org/wiki/Battle_of_Jutland"],
                "podcast_duration_minutes": 3,
                "language": "en"
            }
        })
        
        if not generate_result.get("success"):
            print(f"❌ Failed to generate podcast: {generate_result}")
            return False
            
        task_id = generate_result["task_id"]
        print(f"📋 Generated task ID: {task_id}")
        
        # Wait for completion with progress monitoring
        print("⏳ Waiting for podcast generation to complete...")
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # Check status via tool first
            status_result = await client.call_tool("get_task_status", {"task_id": task_id})
            if status_result.get("success"):
                status = status_result["status"]
                progress = status_result["progress_percentage"]
                print(f"   Status: {status}, Progress: {progress}%")
                
                if status == "completed":
                    print("✅ Podcast generation completed!")
                    break
                elif status == "failed":
                    print(f"❌ Podcast generation failed: {status_result}")
                    return False
                    
            await asyncio.sleep(10)
        else:
            print("❌ Timeout waiting for podcast completion")
            return False
        
        # Now test the job status resource
        print("🔍 Testing jobs://{task_id}/status resource...")
        
        try:
            job_status = await client.read_resource(f"jobs://{task_id}/status")
            print("✅ Successfully accessed job status resource")
            
            # Validate structure
            assert "task_id" in job_status, "Missing task_id"
            assert "status" in job_status, "Missing status"
            assert "progress_percentage" in job_status, "Missing progress_percentage"
            assert "stage" in job_status, "Missing stage"
            assert "timestamps" in job_status, "Missing timestamps"
            assert "request_summary" in job_status, "Missing request_summary"
            assert "completion" in job_status, "Missing completion info for completed task"
            
            # Validate data types and values
            assert job_status["task_id"] == task_id, f"Task ID mismatch"
            assert job_status["status"] == "completed", f"Status should be completed"
            assert 0 <= job_status["progress_percentage"] <= 100, f"Invalid progress"
            assert isinstance(job_status["timestamps"], dict), "Timestamps should be dict"
            assert isinstance(job_status["request_summary"], dict), "Request summary should be dict"
            assert isinstance(job_status["completion"], dict), "Completion should be dict"
            
            # Validate completion data
            completion = job_status["completion"]
            assert "title" in completion, "Missing title in completion"
            assert "duration_seconds" in completion, "Missing duration in completion"
            assert "artifacts_available" in completion, "Missing artifacts info"
            
            artifacts = completion["artifacts_available"]
            assert "transcript" in artifacts, "Missing transcript availability"
            assert "audio" in artifacts, "Missing audio availability"
            assert "outline" in artifacts, "Missing outline availability"
            assert "metadata" in artifacts, "Missing metadata availability"
            
            print(f"📊 Job Status Data:")
            print(f"   Task ID: {job_status['task_id']}")
            print(f"   Status: {job_status['status']}")
            print(f"   Progress: {job_status['progress_percentage']}%")
            print(f"   Stage: {job_status['stage']}")
            print(f"   Title: {completion['title']}")
            print(f"   Duration: {completion['duration_seconds']}s")
            print(f"   Warnings: {completion['warnings_count']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error accessing job status resource: {e}")
            return False


async def test_job_status_missing_task():
    """Test job status resource for non-existent task."""
    print("\n🧪 Testing job status resource for missing task...")
    
    async with SimpleMCPTestClient() as client:
        fake_task_id = "nonexistent-task-12345"
        
        try:
            job_status = await client.read_resource(f"jobs://{fake_task_id}/status")
            print(f"❌ Should have failed for missing task but got: {job_status}")
            return False
            
        except Exception as e:
            expected_errors = ["Task not found", "not found"]
            if any(err in str(e) for err in expected_errors):
                print(f"✅ Correctly handled missing task: {e}")
                return True
            else:
                print(f"❌ Unexpected error for missing task: {e}")
                return False


async def test_job_status_vs_tool_consistency():
    """Test consistency between jobs resource and get_task_status tool."""
    print("\n🧪 Testing consistency between job status resource and tool...")
    
    async with SimpleMCPTestClient() as client:
        # Generate a quick test podcast
        generate_result = await client.call_tool("generate_podcast_async_pydantic", {
            "request": {
                "prominent_persons": ["Isaac Newton"],
                "source_urls": ["https://en.wikipedia.org/wiki/Battle_of_Jutland"],
                "podcast_duration_minutes": 2,
                "language": "en"
            }
        })
        
        if not generate_result.get("success"):
            print(f"❌ Failed to generate test podcast: {generate_result}")
            return False
            
        task_id = generate_result["task_id"]
        print(f"📋 Generated test task ID: {task_id}")
        
        # Wait a bit for some progress
        await asyncio.sleep(15)
        
        try:
            # Get status via tool
            tool_result = await client.call_tool("get_task_status", {"task_id": task_id})
            if not tool_result.get("success"):
                print(f"❌ Tool call failed: {tool_result}")
                return False
                
            tool_status = tool_result  # Access fields directly, not through "result" key
            
            # Get status via resource
            resource_status = await client.read_resource(f"jobs://{task_id}/status")
            
            # Compare key fields
            assert tool_status["task_id"] == resource_status["task_id"], "Task ID mismatch"
            assert tool_status["status"] == resource_status["status"], "Status mismatch"
            assert tool_status["progress_percentage"] == resource_status["progress_percentage"], "Progress mismatch"
            
            print(f"✅ Tool and resource data consistent:")
            print(f"   Status: {tool_status['status']} (both)")
            print(f"   Progress: {tool_status['progress_percentage']}% (both)")
            
            # Resource should have more detailed information
            assert "request_summary" in resource_status, "Resource missing request summary"
            assert "timestamps" in resource_status, "Resource missing timestamps"
            
            print(f"✅ Resource provides additional detail beyond tool")
            return True
            
        except Exception as e:
            print(f"❌ Error comparing tool vs resource: {e}")
            return False


async def run_all_tests():
    """Run all job status resource tests."""
    print("🚀 Starting Job Status Resource Tests")
    print("=" * 50)
    
    tests = [
        ("Job Status for Completed Task", test_job_status_completed_task),
        ("Job Status for Missing Task", test_job_status_missing_task),
        ("Tool vs Resource Consistency", test_job_status_vs_tool_consistency),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func()
            if result:
                print(f"✅ PASSED: {test_name}")
                passed += 1
            else:
                print(f"❌ FAILED: {test_name}")
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    print("🎉 All tests completed!" if passed == total else "⚠️ Some tests failed")
    
    return passed == total


def run_test_in_subprocess(test_name):
    """Run a test function in a separate subprocess to avoid executor issues."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_script = f'''
import asyncio
import sys
import os
sys.path.insert(0, r'{current_dir}')
from test_job_status_resource import {test_name}

async def main():
    result = await {test_name}()
    return result

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
'''
    
    try:
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            cwd=current_dir,
            capture_output=True,
            text=True,
            timeout=400  # 6+ minutes for longer tests
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"❌ Test {test_name} timed out")
        return False
    except Exception as e:
        print(f"❌ Failed to run test {test_name}: {e}")
        return False


if __name__ == "__main__":
    # For development testing, run directly
    if len(sys.argv) > 1 and sys.argv[1] == "--direct":
        asyncio.run(run_all_tests())
    else:
        # Run in subprocess for better isolation
        print("🚀 Running Job Status Resource Tests in Subprocess")
        success = run_test_in_subprocess("run_all_tests")
        sys.exit(0 if success else 1)
