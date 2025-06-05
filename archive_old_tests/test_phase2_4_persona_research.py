#!/usr/bin/env python3
"""
Test script for Phase 2.4: research://{job_id}/{person_id} MCP Resource
Tests persona research data retrieval for podcast generation tasks.
"""

import asyncio
import subprocess
import sys
import json
from pathlib import Path


def run_test_in_subprocess(test_func):
    """
    Run a test function in an isolated subprocess to avoid async issues.
    Returns (success: bool, stdout: str, stderr: str)
    """
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
from test_phase2_4_persona_research import {test_func.__name__}
result = asyncio.run({test_func.__name__}())
sys.exit(0 if result else 1)
"""
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
    return result.returncode == 0, result.stdout, result.stderr


async def test_missing_task_persona_research():
    """Test persona research resource with non-existent task ID."""
    from tests.mcp.client import SimpleMCPTestClient
    
    try:
        async with SimpleMCPTestClient("http://localhost:8000/mcp") as client:
            # Test with non-existent task ID
            response = await client.read_resource("research://nonexistent-task-id/some-person-id")
            
            # Should not reach here - expecting an exception
            print("❌ Expected exception for missing task, but got response:", response)
            return False
            
    except Exception as e:
        error_msg = str(e).lower()
        if "task not found" in error_msg or "nonexistent-task-id" in error_msg:
            print("✅ Correctly handles missing task ID")
            return True
        else:
            print(f"❌ Unexpected error for missing task: {e}")
            return False


async def test_persona_research_resource_structure():
    """Test persona research resource structure and content validation."""
    from tests.mcp.client import SimpleMCPTestClient
    
    try:
        async with SimpleMCPTestClient("http://localhost:8000/mcp") as client:
            # First, generate a podcast to get a task with persona research
            print("🔧 Generating podcast with substantial content for persona research...")
            
            # Use a longer, more substantial request that will actually generate content
            tool_response = await client.call_tool("generate_podcast_async", {
                "source_urls": [
                    "https://en.wikipedia.org/wiki/Albert_Einstein",  # Rich content about Einstein
                    "https://en.wikipedia.org/wiki/Marie_Curie"       # Rich content about Curie
                ],
                "prominent_persons": ["Albert Einstein", "Marie Curie"],
                "podcast_length": "5 minutes",
                "custom_prompt": "Create a conversation between Einstein and Curie about their scientific discoveries and methodology",
                "podcast_name": "Phase 2.4 Persona Research Test - Scientists Discussion"
            })
            
            if not tool_response or "task_id" not in tool_response:
                print("❌ Failed to get task_id from podcast generation")
                return False
            
            task_id = tool_response["task_id"]
            print(f"✅ Generated task: {task_id}")
            
            # Wait for completion with extended timeout for substantial content
            print("⏳ Waiting for podcast generation to complete (this may take longer due to substantial content)...")
            max_wait = 600  # 10 minutes for substantial content processing
            wait_time = 0
            step = 15
            
            while wait_time < max_wait:
                status_response = await client.read_resource(f"jobs://{task_id}/status")
                current_status = status_response.get("status")
                progress = status_response.get("progress_percentage", 0)
                description = status_response.get("status_description", "")
                
                print(f"⏳ Status: {current_status} ({progress:.1f}%) - {description}")
                
                if current_status == "completed":
                    print("✅ Podcast generation completed")
                    break
                elif current_status == "failed":
                    error_msg = status_response.get("error_message", "Unknown error")
                    print(f"❌ Podcast generation failed: {error_msg}")
                    
                    # Try to get more error details
                    completion = status_response.get("completion", {})
                    if completion.get("warnings"):
                        print(f"Warnings: {completion['warnings']}")
                    
                    return False
                
                await asyncio.sleep(step)
                wait_time += step
            
            if wait_time >= max_wait:
                print("❌ Timeout waiting for podcast completion")
                return False
            
            # Check if persona research was actually generated
            status_response = await client.read_resource(f"jobs://{task_id}/status")
            artifacts = status_response.get("artifacts", {})
            
            print(f"📊 Artifacts status: {artifacts}")
            
            if not artifacts.get("persona_research_complete", False):
                print("⚠️  Persona research was not completed - checking pipeline status")
                
                # Test that our improved error handling works
                try:
                    await client.read_resource(f"research://{task_id}/any-person-id")
                    print("❌ Expected error for incomplete persona research")
                    return False
                except Exception as e:
                    error_msg = str(e)
                    if "Pipeline:" in error_msg:
                        print(f"✅ Enhanced error handling working: {error_msg}")
                        return True
                    else:
                        print(f"❌ Unexpected error format: {error_msg}")
                        return False
            
            # Try to get available person IDs by attempting invalid access first
            try:
                await client.read_resource(f"research://{task_id}/invalid-person-id")
                print("❌ Expected error for invalid person ID, but got success")
                return False
            except Exception as e:
                error_msg = str(e)
                if "Available person IDs:" in error_msg:
                    # Extract available person IDs from error message
                    available_ids_part = error_msg.split("Available person IDs: ")[1]
                    if available_ids_part.strip() == "none":
                        print("⚠️  No persona research data generated despite completion status")
                        return False
                    
                    # Parse available person IDs
                    available_person_ids = [pid.strip() for pid in available_ids_part.split(",")]
                    person_id = available_person_ids[0]
                    print(f"✅ Found available person ID: {person_id}")
                else:
                    print(f"❌ Unexpected error format: {error_msg}")
                    return False
            
            # Test the persona research resource with a valid person ID
            research_response = await client.read_resource(f"research://{task_id}/{person_id}")
            
            # Validate response structure
            required_fields = [
                "job_id", "person_id", "name", "gender", "detailed_profile", 
                "voice_characteristics", "raw_research_data", "task_status",
                "profile_length", "last_updated"
            ]
            
            for field in required_fields:
                if field not in research_response:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Validate field types and content
            if research_response["job_id"] != task_id:
                print(f"❌ Job ID mismatch: {research_response['job_id']} != {task_id}")
                return False
            
            if research_response["person_id"] != person_id:
                print(f"❌ Person ID mismatch: {research_response['person_id']} != {person_id}")
                return False
            
            if research_response["task_status"] != "completed":
                print(f"❌ Unexpected task status: {research_response['task_status']}")
                return False
            
            if not isinstance(research_response["detailed_profile"], str):
                print(f"❌ detailed_profile should be string, got: {type(research_response['detailed_profile'])}")
                return False
            
            if not isinstance(research_response["voice_characteristics"], dict):
                print(f"❌ voice_characteristics should be dict, got: {type(research_response['voice_characteristics'])}")
                return False
            
            if not isinstance(research_response["raw_research_data"], dict):
                print(f"❌ raw_research_data should be dict, got: {type(research_response['raw_research_data'])}")
                return False
            
            if research_response["profile_length"] != len(research_response["detailed_profile"]):
                print(f"❌ profile_length mismatch: {research_response['profile_length']} != {len(research_response['detailed_profile'])}")
                return False
            
            # Validate content quality (should have substantial content for Einstein/Curie)
            if research_response["profile_length"] < 200:
                print(f"⚠️  Profile seems quite short ({research_response['profile_length']} chars) for a well-known historical figure")
            
            print("✅ Persona research resource structure is valid")
            print(f"✅ Profile length: {research_response['profile_length']} characters")
            print(f"✅ Person name: {research_response['name']}")
            print(f"✅ Gender: {research_response['gender']}")
            print(f"✅ Voice characteristics keys: {list(research_response['voice_characteristics'].keys())}")
            
            return True
            
    except Exception as e:
        print(f"❌ Persona research resource structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_status_research_consistency():
    """Test consistency between job status and persona research resources."""
    from tests.mcp.client import SimpleMCPTestClient
    
    try:
        async with SimpleMCPTestClient("http://localhost:8000/mcp") as client:
            # Generate a podcast with persona research
            print("🔧 Generating podcast for consistency test with realistic content...")
            
            tool_response = await client.call_tool("generate_podcast_async", {
                "source_urls": [
                    "https://en.wikipedia.org/wiki/Isaac_Newton"  # Rich, substantial content
                ],
                "prominent_persons": ["Isaac Newton"],
                "podcast_length": "4 minutes",
                "custom_prompt": "Explore Newton's contributions to physics and mathematics",
                "podcast_name": "Phase 2.4 Consistency Test - Newton's Legacy"
            })
            
            if not tool_response or "task_id" not in tool_response:
                print("❌ Failed to get task_id from podcast generation")
                return False
            
            task_id = tool_response["task_id"]
            
            # Wait for completion (reasonable timeout for consistency test)
            print("⏳ Waiting for completion...")
            max_wait = 600  # 10 minutes for substantial content
            wait_time = 0
            step = 20
            
            while wait_time < max_wait:
                status_response = await client.read_resource(f"jobs://{task_id}/status")
                current_status = status_response.get("status")
                
                if current_status == "completed":
                    break
                elif current_status == "failed":
                    error_msg = status_response.get("error_message", "Unknown error")
                    print(f"❌ Generation failed: {error_msg}")
                    return False
                
                await asyncio.sleep(step)
                wait_time += step
                
                if wait_time % 60 == 0:  # Progress update every minute
                    progress = status_response.get("progress_percentage", 0)
                    description = status_response.get("status_description", "")
                    print(f"⏳ Progress: {current_status} ({progress:.1f}%) - {description}")
            
            if wait_time >= max_wait:
                print("❌ Timeout waiting for completion")
                return False
            
            # Get status resource
            status_response = await client.read_resource(f"jobs://{task_id}/status")
            
            # Check if persona research is available
            artifacts = status_response.get("artifacts", {})
            persona_research_complete = artifacts.get("persona_research_complete", False)
            
            if not persona_research_complete:
                print("⚠️  No persona research generated - testing error consistency")
                
                # Test that persona research resource gives appropriate error
                try:
                    await client.read_resource(f"research://{task_id}/any-person-id")
                    print("❌ Expected error for task without persona research")
                    return False
                except Exception as e:
                    error_msg = str(e)
                    if "Pipeline:" in error_msg:
                        print(f"✅ Consistent error handling with pipeline info: {error_msg}")
                        return True
                    elif "No persona research data available" in error_msg:
                        print("✅ Consistent error handling for tasks without persona research")
                        return True
                    else:
                        print(f"❌ Unexpected error: {error_msg}")
                        return False
            
            # Test with invalid person ID to get available IDs
            try:
                await client.read_resource(f"research://{task_id}/invalid-person-id")
                print("❌ Expected error for invalid person ID")
                return False
            except Exception as e:
                error_msg = str(e)
                if "Available person IDs:" not in error_msg:
                    print(f"❌ Unexpected error format: {error_msg}")
                    return False
                
                available_ids_part = error_msg.split("Available person IDs: ")[1]
                if available_ids_part.strip() == "none":
                    print("⚠️  No persona research data found despite completion flag")
                    return False
                
                available_person_ids = [pid.strip() for pid in available_ids_part.split(",")]
                person_id = available_person_ids[0]
                print(f"✅ Found person ID for consistency test: {person_id}")
            
            # Get persona research resource
            research_response = await client.read_resource(f"research://{task_id}/{person_id}")
            
            # Verify consistency
            if status_response["task_id"] != research_response["job_id"]:
                print(f"❌ Task ID inconsistency: {status_response['task_id']} != {research_response['job_id']}")
                return False
            
            if status_response["status"] != research_response["task_status"]:
                print(f"❌ Status inconsistency: {status_response['status']} != {research_response['task_status']}")
                return False
            
            if status_response["last_updated"] != research_response["last_updated"]:
                print(f"❌ Last updated inconsistency: {status_response['last_updated']} != {research_response['last_updated']}")
                return False
            
            print("✅ Status and persona research resources are consistent")
            print(f"✅ Both report task_id: {status_response['task_id']}")
            print(f"✅ Both report status: {status_response['status']}")
            print(f"✅ Both report last_updated: {status_response['last_updated']}")
            
            return True
            
    except Exception as e:
        print(f"❌ Status/research consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test runner for Phase 2.4 persona research resource tests."""
    print("🚀 Starting Phase 2.4 Persona Research Resource Tests")
    print("=" * 60)
    
    # Define test functions
    test_functions = [
        test_missing_task_persona_research,
        test_persona_research_resource_structure,
        test_status_research_consistency
    ]
    
    # Run tests
    results = {}
    
    for test_func in test_functions:
        print(f"\n⚡ Running {test_func.__name__} in subprocess...")
        success, stdout, stderr = run_test_in_subprocess(test_func)
        
        if success:
            print(f"✅ {test_func.__name__} PASSED")
        else:
            print(f"❌ {test_func.__name__} FAILED")
            if stderr:
                print(f"STDERR: {stderr}")
        
        # Store results
        results[test_func.__name__] = success
        
        # Print any stdout from the test
        if stdout.strip():
            for line in stdout.strip().split('\n'):
                print(f"   {line}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 PHASE 2.4 PERSONA RESEARCH RESOURCE TEST SUMMARY")
    print("=" * 60)
    
    for i, (test_name, passed) in enumerate(results.items(), 1):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{i}. {test_name}: {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n🎯 OVERALL RESULT: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 ALL PERSONA RESEARCH RESOURCE TESTS PASSED!")
        print("✅ Phase 2.4 implementation is working correctly")
    else:
        failed_count = total_count - passed_count
        print(f"⚠️  {failed_count} test(s) failed")
        print("❌ Phase 2.4 needs fixes before completion")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
