#!/usr/bin/env python3
"""
Test Phase 2.3b: jobs://{task_id}/logs MCP resource
Tests the logs resource functionality with subprocess isolation
"""

import asyncio
import json
import sys
import os
import traceback
from datetime import datetime, timezone
import subprocess

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from tests.mcp.client import SimpleMCPTestClient


async def test_logs_resource_missing_task():
    """Test logs resource with missing task ID"""
    print("\n=== Test: Logs Resource - Missing Task ===")
    
    client = SimpleMCPTestClient()
    try:
        # Try to get logs for non-existent task
        try:
            result = await client.read_resource("jobs://nonexistent_task/logs")
            print(f"❌ Expected error but got result: {result}")
            return False
        except Exception as e:
            error_msg = str(e)
            if "Task not found" in error_msg:
                print(f"✅ Correctly handled missing task: {e}")
                return True
            else:
                print(f"❌ Wrong error message: {e}")
                return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        try:
            await client.close()
        except:
            pass


async def test_logs_resource_with_task():
    """Test logs resource with actual task"""
    print("\n=== Test: Logs Resource - With Task ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a short async task
        print("Starting async task...")
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Keep it very short for testing",
            podcast_name="TestPodcast"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started with ID: {task_id}")
        
        # Wait a moment for some logs to be generated
        await asyncio.sleep(2)
        
        # Get logs resource
        print("Getting logs resource...")
        logs_result = await client.read_resource(f"jobs://{task_id}/logs")
        
        # Validate logs resource structure
        required_fields = ["task_id", "logs", "parsed_logs", "log_count", "task_status", "last_updated"]
        for field in required_fields:
            if field not in logs_result:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate task_id matches
        if logs_result["task_id"] != task_id:
            print(f"❌ Task ID mismatch: {logs_result['task_id']} != {task_id}")
            return False
            
        # Validate logs structure
        logs = logs_result["logs"]
        parsed_logs = logs_result["parsed_logs"]
        
        if not isinstance(logs, list):
            print(f"❌ Logs should be a list, got: {type(logs)}")
            return False
            
        if not isinstance(parsed_logs, list):
            print(f"❌ Parsed logs should be a list, got: {type(parsed_logs)}")
            return False
            
        if len(logs) != len(parsed_logs):
            print(f"❌ Logs and parsed_logs length mismatch: {len(logs)} != {len(parsed_logs)}")
            return False
            
        if logs_result["log_count"] != len(logs):
            print(f"❌ Log count mismatch: {logs_result['log_count']} != {len(logs)}")
            return False
            
        # Validate that we have some logs (task should have started)
        if len(logs) == 0:
            print("❌ No logs found - task should have generated some logs")
            return False
            
        print(f"✅ Found {len(logs)} log entries")
        
        # Validate parsed log structure
        for i, parsed_log in enumerate(parsed_logs):
            required_log_fields = ["timestamp", "message", "level", "status", "progress", "description"]
            for field in required_log_fields:
                if field not in parsed_log:
                    print(f"❌ Missing field in parsed_log[{i}]: {field}")
                    return False
                    
        # Print some sample logs
        print(f"Sample raw log: {logs[0] if logs else 'None'}")
        print(f"Sample parsed log: {parsed_logs[0] if parsed_logs else 'None'}")
        
        # Validate task status is included
        if not logs_result["task_status"]:
            print("❌ Missing task_status")
            return False
            
        print(f"Task status: {logs_result['task_status']}")
        print(f"Last updated: {logs_result['last_updated']}")
        
        print("✅ Logs resource test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        try:
            await client.close()
        except:
            pass


async def test_logs_resource_consistency():
    """Test consistency between job status and logs resources"""
    print("\n=== Test: Logs Resource - Consistency with Status ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Short test",
            podcast_name="TestPodcast"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for some processing
        await asyncio.sleep(3)
        
        # Get both status and logs resources
        status_result = await client.read_resource(f"jobs://{task_id}/status")
        logs_result = await client.read_resource(f"jobs://{task_id}/logs")
        
        # Validate consistency
        if status_result["task_id"] != logs_result["task_id"]:
            print(f"❌ Task ID mismatch between resources")
            return False
            
        if status_result["status"] != logs_result["task_status"]:
            print(f"❌ Status mismatch: {status_result['status']} != {logs_result['task_status']}")
            return False
            
        # Both should have the same last_updated time (or very close)
        status_updated = status_result.get("last_updated_at")
        logs_updated = logs_result.get("last_updated")
        
        if status_updated and logs_updated:
            if status_updated != logs_updated:
                print(f"⚠️  Last updated times differ slightly (normal): {status_updated} vs {logs_updated}")
            else:
                print(f"✅ Last updated times match: {status_updated}")
        
        print("✅ Status and logs resources are consistent!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        try:
            await client.close()
        except:
            pass


def run_test_in_subprocess(test_name):
    """Run a test in a separate subprocess for isolation"""
    print(f"\n{'='*60}")
    print(f"Running {test_name} in subprocess...")
    print(f"{'='*60}")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_script = f'''
import asyncio
import sys
import os
sys.path.insert(0, r'{current_dir}')
from test_phase2_3b_logs import {test_name}

async def main():
    return await {test_name}()

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
'''
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=current_dir,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


async def main():
    """Run all tests with subprocess isolation"""
    print("🚀 Starting Phase 2.3b: jobs://{task_id}/logs Resource Tests")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    tests = [
        "test_logs_resource_missing_task",
        "test_logs_resource_with_task", 
        "test_logs_resource_consistency"
    ]
    
    results = {}
    
    for test_name in tests:
        success = run_test_in_subprocess(test_name)
        results[test_name] = success
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 2.3b implementation is working correctly.")
        return True
    else:
        print("💥 Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
