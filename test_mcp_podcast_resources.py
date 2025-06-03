"""
Test MCP Podcast Resources: podcast://{task_id}/* resources
Tests transcript, audio, metadata, and outline resources with comprehensive validation
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


async def test_podcast_transcript_resource():
    """Test podcast://{task_id}/transcript resource"""
    print("\n=== Test: Podcast Transcript Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task and wait for completion or significant progress
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Short test for transcript",
            podcast_name="TranscriptTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for some processing
        await asyncio.sleep(5)
        
        # Try to get transcript resource
        try:
            transcript_result = await client.read_resource(f"podcast://{task_id}/transcript")
            
            # Validate required fields
            required_fields = ["task_id", "transcript_data", "file_path", "generated_at"]
            
            for field in required_fields:
                if field not in transcript_result:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Validate task_id matches
            if transcript_result["task_id"] != task_id:
                print(f"❌ Task ID mismatch: {transcript_result['task_id']} != {task_id}")
                return False
            
            print(f"✅ Transcript resource available")
            print(f"✅ File path: {transcript_result['file_path']}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg or "Transcript file not found" in error_msg:
                print(f"✅ Expected behavior - transcript not ready yet: {e}")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
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


async def test_podcast_audio_resource():
    """Test podcast://{task_id}/audio resource"""
    print("\n=== Test: Podcast Audio Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Short test for audio",
            podcast_name="AudioTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Try to get audio resource
        try:
            audio_result = await client.read_resource(f"podcast://{task_id}/audio")
            
            # Validate required fields
            required_fields = ["task_id", "audio_file_path", "file_exists", "generated_at"]
            
            for field in required_fields:
                if field not in audio_result:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Validate task_id matches
            if audio_result["task_id"] != task_id:
                print(f"❌ Task ID mismatch: {audio_result['task_id']} != {task_id}")
                return False
            
            print(f"✅ Audio resource available")
            print(f"✅ File exists: {audio_result['file_exists']}")
            print(f"✅ Audio path: {audio_result['audio_file_path']}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg or "Audio file not found" in error_msg:
                print(f"✅ Expected behavior - audio not ready yet: {e}")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
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


async def test_podcast_metadata_resource():
    """Test podcast://{task_id}/metadata resource"""
    print("\n=== Test: Podcast Metadata Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Short test for metadata",
            podcast_name="MetadataTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Try to get metadata resource
        try:
            metadata_result = await client.read_resource(f"podcast://{task_id}/metadata")
            
            # Validate required fields
            required_fields = ["task_id", "title", "summary", "duration_seconds", "generated_at"]
            
            for field in required_fields:
                if field not in metadata_result:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Validate task_id matches
            if metadata_result["task_id"] != task_id:
                print(f"❌ Task ID mismatch: {metadata_result['task_id']} != {task_id}")
                return False
            
            print(f"✅ Metadata resource available")
            print(f"✅ Title: {metadata_result['title']}")
            print(f"✅ Summary: {metadata_result['summary'][:100]}...")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg or "Episode not found" in error_msg:
                print(f"✅ Expected behavior - metadata not ready yet: {e}")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
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


async def test_podcast_outline_resource():
    """Test podcast://{task_id}/outline resource"""
    print("\n=== Test: Podcast Outline Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Short test for outline",
            podcast_name="OutlineTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Try to get outline resource
        try:
            outline_result = await client.read_resource(f"podcast://{task_id}/outline")
            
            # Validate required fields
            required_fields = ["task_id", "outline_data", "file_path", "generated_at"]
            
            for field in required_fields:
                if field not in outline_result:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Validate task_id matches
            if outline_result["task_id"] != task_id:
                print(f"❌ Task ID mismatch: {outline_result['task_id']} != {task_id}")
                return False
            
            print(f"✅ Outline resource available")
            print(f"✅ File path: {outline_result['file_path']}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "not yet available" in error_msg or "Outline file not found" in error_msg:
                print(f"✅ Expected behavior - outline not ready yet: {e}")
                return True
            else:
                print(f"❌ Unexpected error: {e}")
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


async def test_missing_task_error_handling():
    """Test error handling for missing tasks across all podcast resources"""
    print("\n=== Test: Missing Task Error Handling ===")
    
    client = SimpleMCPTestClient()
    resources_to_test = ["transcript", "audio", "metadata", "outline"]
    
    try:
        for resource_type in resources_to_test:
            try:
                result = await client.read_resource(f"podcast://nonexistent_task/{resource_type}")
                print(f"❌ {resource_type}: Expected error but got result: {result}")
                return False
            except Exception as e:
                error_msg = str(e)
                if "Task not found" in error_msg or "Episode not found" in error_msg:
                    print(f"✅ {resource_type}: Correctly handled missing task")
                else:
                    print(f"❌ {resource_type}: Wrong error message: {e}")
                    return False
        
        print("✅ All podcast resources handle missing tasks correctly")
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
    """Test consistency between podcast resources"""
    print("\n=== Test: Podcast Resource Consistency ===")
    
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
        await asyncio.sleep(5)
        
        # Try to get all podcast resources
        resources_data = {}
        resource_types = ["transcript", "audio", "metadata", "outline"]
        
        for resource_type in resource_types:
            try:
                result = await client.read_resource(f"podcast://{task_id}/{resource_type}")
                resources_data[resource_type] = result
                print(f"✅ {resource_type}: Available")
            except Exception as e:
                if "not yet available" in str(e) or "not found" in str(e):
                    print(f"⚠️  {resource_type}: Not ready yet (expected)")
                    resources_data[resource_type] = None
                else:
                    print(f"❌ {resource_type}: Unexpected error: {e}")
                    return False
        
        # Validate task_id consistency for available resources
        available_resources = {k: v for k, v in resources_data.items() if v is not None}
        
        if available_resources:
            task_ids = [data["task_id"] for data in available_resources.values()]
            if not all(tid == task_id for tid in task_ids):
                print(f"❌ Task ID inconsistency across resources")
                return False
            
            print(f"✅ All available resources consistent for task: {task_id}")
        else:
            print(f"✅ No resources ready yet (expected for quick test)")
        
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
from test_mcp_podcast_resources import {test_name}

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
    """Run all podcast resource tests with subprocess isolation"""
    print("🚀 Starting MCP Podcast Resources Tests: podcast://{task_id}/*")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    tests = [
        "test_podcast_transcript_resource",
        "test_podcast_audio_resource", 
        "test_podcast_metadata_resource",
        "test_podcast_outline_resource",
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
    print("📊 PODCAST RESOURCES TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All podcast resource tests passed!")
        return True
    else:
        print("⚠️  Some podcast resource tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
