#!/usr/bin/env python3
"""
Test script for Phase 2.3c: jobs://{task_id}/warnings MCP resource implementation.

This tests the warnings resource functionality including:
- Missing task error handling
- Warnings resource structure validation 
- Consistency with job status resource
- Error information handling for failed tasks

Uses subprocess isolation to avoid async executor shutdown issues.
"""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_missing_task_warnings():
    """Test warnings resource handling of missing task IDs."""
    print("🔍 Test 1: Missing task warnings resource")
    
    from tests.mcp.client import SimpleMCPTestClient
    
    try:
        async with SimpleMCPTestClient() as client:
            # Test non-existent task ID
            result = await client.read_resource("jobs://fake-task-id/warnings")
            print(f"❌ Expected error for missing task, but got result: {result}")
            return False
            
    except Exception as e:
        error_message = str(e)
        if "Task not found" in error_message and "fake-task-id" in error_message:
            print(f"✅ Correct error handling: {error_message}")
            return True
        else:
            print(f"❌ Unexpected error: {error_message}")
            return False

async def test_warnings_resource_structure():
    """Test warnings resource returns expected structure for actual task."""
    print("\n🔍 Test 2: Warnings resource structure validation")
    
    from tests.mcp.client import SimpleMCPTestClient
    
    try:
        async with SimpleMCPTestClient() as client:
            # Submit a podcast generation request
            print("📤 Submitting podcast generation request...")
            tool_result = await client.call_tool("generate_podcast_async", {
                "source_urls": ["https://example.com/test"],
                "prominent_persons": ["Test Speaker"],
                "podcast_length": "2-3 minutes", 
                "custom_prompt": "Test prompt for warnings resource validation",
                "podcast_name": "Warnings Test Podcast"
            })
            
            if not tool_result.get("success"):
                print(f"❌ Tool call failed: {tool_result}")
                return False
                
            task_id = tool_result.get("task_id")
            print(f"✅ Task submitted successfully: {task_id}")
            
            # Wait a moment for task to start
            await asyncio.sleep(2)
            
            # Test warnings resource
            print(f"📖 Reading warnings resource for task: {task_id}")
            warnings_result = await client.read_resource(f"jobs://{task_id}/warnings")
            
            # Validate structure
            required_fields = [
                "task_id", "warnings", "parsed_warnings", "warning_count", 
                "error_info", "task_status", "has_errors", "last_updated"
            ]
            
            for field in required_fields:
                if field not in warnings_result:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Validate data types
            if not isinstance(warnings_result["warnings"], list):
                print(f"❌ warnings should be list, got: {type(warnings_result['warnings'])}")
                return False
                
            if not isinstance(warnings_result["parsed_warnings"], list):
                print(f"❌ parsed_warnings should be list, got: {type(warnings_result['parsed_warnings'])}")
                return False
                
            if not isinstance(warnings_result["warning_count"], int):
                print(f"❌ warning_count should be int, got: {type(warnings_result['warning_count'])}")
                return False
                
            if not isinstance(warnings_result["has_errors"], bool):
                print(f"❌ has_errors should be bool, got: {type(warnings_result['has_errors'])}")
                return False
            
            # Validate task_id matches
            if warnings_result["task_id"] != task_id:
                print(f"❌ Task ID mismatch: expected {task_id}, got {warnings_result['task_id']}")
                return False
            
            # Validate parsed warnings structure
            for parsed_warning in warnings_result["parsed_warnings"]:
                required_warning_fields = ["message", "type", "severity", "stage"]
                for field in required_warning_fields:
                    if field not in parsed_warning:
                        print(f"❌ Missing warning field: {field}")
                        return False
            
            print("✅ All warnings resource structure validations passed")
            print(f"📊 Warning count: {warnings_result['warning_count']}")
            print(f"📊 Task status: {warnings_result['task_status']}")
            print(f"📊 Has errors: {warnings_result['has_errors']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_status_warnings_consistency():
    """Test consistency between job status and warnings resources."""
    print("\n🔍 Test 3: Status/warnings resource consistency")
    
    from tests.mcp.client import SimpleMCPTestClient
    
    try:
        async with SimpleMCPTestClient() as client:
            # Submit a podcast generation request
            print("📤 Submitting podcast generation request...")
            tool_result = await client.call_tool("generate_podcast_async", {
                "source_urls": ["https://example.com/consistency-test"],
                "prominent_persons": ["Consistency Tester"],
                "podcast_length": "3-4 minutes",
                "custom_prompt": "Test consistency between status and warnings",
                "podcast_name": "Consistency Test Podcast"
            })
            
            if not tool_result.get("success"):
                print(f"❌ Tool call failed: {tool_result}")
                return False
                
            task_id = tool_result.get("task_id")
            print(f"✅ Task submitted successfully: {task_id}")
            
            # Wait a moment for task to progress
            await asyncio.sleep(3)
            
            # Get both status and warnings resources
            print(f"📖 Reading status resource for task: {task_id}")
            status_result = await client.read_resource(f"jobs://{task_id}/status")
            
            print(f"📖 Reading warnings resource for task: {task_id}")
            warnings_result = await client.read_resource(f"jobs://{task_id}/warnings")
            
            # Validate consistency
            if status_result["task_id"] != warnings_result["task_id"]:
                print(f"❌ Task ID mismatch: status={status_result['task_id']}, warnings={warnings_result['task_id']}")
                return False
            
            if status_result["status"] != warnings_result["task_status"]:
                print(f"❌ Status mismatch: status={status_result['status']}, warnings={warnings_result['task_status']}")
                return False
            
            # Check timestamp consistency (should be very close)
            status_time = status_result["timestamps"]["last_updated_at"]
            warnings_time = warnings_result["last_updated"]
            
            if status_time != warnings_time:
                print(f"⚠️  Minor timestamp difference: status={status_time}, warnings={warnings_time}")
                # This is not necessarily an error, just noting the difference
            
            print("✅ Status and warnings resources are consistent")
            print(f"📊 Task status: {status_result['status']}")
            print(f"📊 Warnings count: {warnings_result['warning_count']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all warnings resource tests using subprocess isolation."""
    print("🚀 Starting Phase 2.3c Warnings Resource Tests")
    print("=" * 60)
    
    # Test functions to run in isolation
    test_functions = [
        test_missing_task_warnings,
        test_warnings_resource_structure, 
        test_status_warnings_consistency
    ]
    
    results = []
    
    for test_func in test_functions:
        print(f"\n⚡ Running {test_func.__name__} in subprocess...")
        
        # Run each test in isolated subprocess to avoid async issues
        cmd = [
            sys.executable, "-c", 
            f"""
import asyncio
import sys
from pathlib import Path

# Add project root to path  
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

# Import and run the test
from test_phase2_3c_warnings import {test_func.__name__}
result = asyncio.run({test_func.__name__}())
sys.exit(0 if result else 1)
"""
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=project_root,
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            success = result.returncode == 0
            results.append(success)
            
            if success:
                print(f"✅ {test_func.__name__} PASSED")
            else:
                print(f"❌ {test_func.__name__} FAILED")
                if result.stderr:
                    print(f"STDERR: {result.stderr}")
                    
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_func.__name__} TIMED OUT")
            results.append(False)
        except Exception as e:
            print(f"💥 {test_func.__name__} ERROR: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 PHASE 2.3C WARNINGS RESOURCE TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_func, result) in enumerate(zip(test_functions, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test_func.__name__}: {status}")
    
    print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL WARNINGS RESOURCE TESTS PASSED!")
        print("✅ Phase 2.3c implementation is working correctly")
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        print("❌ Phase 2.3c needs fixes before completion")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
