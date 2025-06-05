"""
Test MCP Job Resources: jobs://{task_id}/* resources
Tests status, logs, and warnings resources with comprehensive validation
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


async def test_job_status_resource():
    """Test jobs://{task_id}/status resource"""
    print("\n=== Test: Job Status Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a short async task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Keep it very short for testing",
            podcast_name="StatusTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started with ID: {task_id}")
        
        # Wait for some processing
        await asyncio.sleep(2)
        
        # Get status resource
        status_result = await client.read_resource(f"jobs://{task_id}/status")
        
        # Validate required fields
        required_fields = [
            "task_id", "status", "progress_percentage", "created_at", 
            "last_updated_at", "request_summary", "error_details", 
            "completion_details", "artifacts"
        ]
        
        for field in required_fields:
            if field not in status_result:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate task_id matches
        if status_result["task_id"] != task_id:
            print(f"❌ Task ID mismatch: {status_result['task_id']} != {task_id}")
            return False
            
        # Validate status values
        valid_statuses = ["queued", "analyzing_sources", "researching_personas", "generating_outline", 
                         "generating_dialogue", "generating_audio_segments", "postprocessing_final_episode", 
                         "completed", "failed", "cancelled"]
        
        if status_result["status"] not in valid_statuses:
            print(f"❌ Invalid status: {status_result['status']}")
            return False
            
        print(f"✅ Status: {status_result['status']} ({status_result['progress_percentage']}%)")
        print(f"✅ Task created: {status_result['created_at']}")
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


async def test_job_logs_resource():
    """Test jobs://{task_id}/logs resource"""
    print("\n=== Test: Job Logs Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Short test for logs",
            podcast_name="LogsTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for some logs to be generated
        await asyncio.sleep(3)
        
        # Get logs resource
        logs_result = await client.read_resource(f"jobs://{task_id}/logs")
        
        # Validate required fields
        required_fields = ["task_id", "logs", "parsed_logs", "log_count", "task_status", "last_updated"]
        
        for field in required_fields:
            if field not in logs_result:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate logs structure
        if not isinstance(logs_result["logs"], list):
            print(f"❌ Logs should be a list, got: {type(logs_result['logs'])}")
            return False
            
        if not isinstance(logs_result["parsed_logs"], list):
            print(f"❌ Parsed logs should be a list, got: {type(logs_result['parsed_logs'])}")
            return False
            
        print(f"✅ Found {logs_result['log_count']} log entries")
        print(f"✅ Task status: {logs_result['task_status']}")
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


async def test_job_warnings_resource():
    """Test jobs://{task_id}/warnings resource"""
    print("\n=== Test: Job Warnings Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Test warnings",
            podcast_name="WarningsTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Get warnings resource
        warnings_result = await client.read_resource(f"jobs://{task_id}/warnings")
        
        # Validate required fields
        required_fields = [
            "task_id", "warnings", "parsed_warnings", "warning_count", 
            "error_info", "task_status", "has_errors", "last_updated"
        ]
        
        for field in required_fields:
            if field not in warnings_result:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Validate warnings structure
        if not isinstance(warnings_result["warnings"], list):
            print(f"❌ Warnings should be a list, got: {type(warnings_result['warnings'])}")
            return False
            
        if not isinstance(warnings_result["parsed_warnings"], list):
            print(f"❌ Parsed warnings should be a list, got: {type(warnings_result['parsed_warnings'])}")
            return False
            
        print(f"✅ Found {warnings_result['warning_count']} warnings")
        print(f"✅ Has errors: {warnings_result['has_errors']}")
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


async def test_missing_task_error_handling():
    """Test error handling for missing tasks across all job resources"""
    print("\n=== Test: Missing Task Error Handling ===")
    
    client = SimpleMCPTestClient()
    resources_to_test = ["status", "logs", "warnings"]
    
    try:
        for resource_type in resources_to_test:
            try:
                result = await client.read_resource(f"jobs://nonexistent_task/{resource_type}")
                print(f"❌ {resource_type}: Expected error but got result: {result}")
                return False
            except Exception as e:
                error_msg = str(e)
                if "Task not found" in error_msg:
                    print(f"✅ {resource_type}: Correctly handled missing task")
                else:
                    print(f"❌ {resource_type}: Wrong error message: {e}")
                    return False
        
        print("✅ All job resources handle missing tasks correctly")
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


async def test_resource_consistency():
    """Test consistency between job resources"""
    print("\n=== Test: Job Resource Consistency ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Consistency test",
            podcast_name="ConsistencyTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(3)
        
        # Get all job resources
        status_result = await client.read_resource(f"jobs://{task_id}/status")
        logs_result = await client.read_resource(f"jobs://{task_id}/logs")
        warnings_result = await client.read_resource(f"jobs://{task_id}/warnings")
        
        # Validate task_id consistency
        if not (status_result["task_id"] == logs_result["task_id"] == warnings_result["task_id"] == task_id):
            print("❌ Task ID inconsistency across resources")
            return False
            
        # Validate status consistency
        status_fields = ["status", "task_status", "task_status"]
        statuses = [status_result["status"], logs_result["task_status"], warnings_result["task_status"]]
        
        if not all(s == statuses[0] for s in statuses):
            print(f"❌ Status inconsistency: {statuses}")
            return False
            
        print("✅ All job resources are consistent")
        print(f"✅ Task ID: {task_id}")
        print(f"✅ Status: {statuses[0]}")
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
from test_mcp_job_resources import {test_name}

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
    """Run all job resource tests with subprocess isolation"""
    print("🚀 Starting MCP Job Resources Tests: jobs://{task_id}/*")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    tests = [
        "test_job_status_resource",
        "test_job_logs_resource", 
        "test_job_warnings_resource",
        "test_missing_task_error_handling",
        "test_resource_consistency"
    ]
    
    results = {}
    
    for test_name in tests:
        success = run_test_in_subprocess(test_name)
        results[test_name] = success
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 JOB RESOURCES TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All job resource tests passed!")
        return True
    else:
        print("⚠️  Some job resource tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
