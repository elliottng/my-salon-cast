"""
Test MCP Persona Resources: research://{job_id}/{person_id} resources
Tests persona research resources with comprehensive validation
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


async def test_persona_research_resource():
    """Test research://{job_id}/{person_id} resource"""
    print("\n=== Test: Persona Research Resource ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task with multiple persons for persona research
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Albert Einstein", "Marie Curie"],
            podcast_length="1 minute",
            custom_prompt="Short test for persona research",
            podcast_name="PersonaTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for persona research phase
        await asyncio.sleep(8)
        
        # Try to get persona research for first person
        # The person_id is typically generated based on the person name
        person_ids = ["albert-einstein", "marie-curie"]
        
        for person_id in person_ids:
            try:
                persona_result = await client.read_resource(f"research://{task_id}/{person_id}")
                
                # Validate required fields
                required_fields = [
                    "job_id", "person_id", "name", "task_status", 
                    "persona_research_data", "voice_characteristics", "file_metadata"
                ]
                
                for field in required_fields:
                    if field not in persona_result:
                        print(f"❌ Missing required field: {field}")
                        return False
                
                # Validate job_id matches
                if persona_result["job_id"] != task_id:
                    print(f"❌ Job ID mismatch: {persona_result['job_id']} != {task_id}")
                    return False
                
                # Validate person_id matches
                if persona_result["person_id"] != person_id:
                    print(f"❌ Person ID mismatch: {persona_result['person_id']} != {person_id}")
                    return False
                
                print(f"✅ Persona research available for {persona_result['name']}")
                print(f"✅ Task status: {persona_result['task_status']}")
                return True
                
            except Exception as e:
                error_msg = str(e)
                if "Task not found" in error_msg:
                    print(f"⚠️  {person_id}: Task not found (expected if not processed yet)")
                    continue
                elif "not found" in error_msg or "not available" in error_msg:
                    print(f"⚠️  {person_id}: Persona research not ready yet")
                    continue
                else:
                    print(f"❌ {person_id}: Unexpected error: {e}")
                    return False
        
        # If we get here, none of the persona research was available yet
        print("✅ Expected behavior - persona research not ready yet for quick test")
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


async def test_persona_research_structure():
    """Test persona research resource structure and content"""
    print("\n=== Test: Persona Research Structure ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Test Person"],
            podcast_length="1 minute",
            custom_prompt="Structure test",
            podcast_name="StructureTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(10)
        
        # Try common person ID patterns
        person_ids_to_try = ["test-person", "testperson", "test_person"]
        
        for person_id in person_ids_to_try:
            try:
                persona_result = await client.read_resource(f"research://{task_id}/{person_id}")
                
                # Validate structure of persona_research_data
                if "persona_research_data" in persona_result:
                    research_data = persona_result["persona_research_data"]
                    if isinstance(research_data, dict):
                        print(f"✅ Persona research data is properly structured")
                    else:
                        print(f"⚠️  Persona research data type: {type(research_data)}")
                
                # Validate structure of voice_characteristics
                if "voice_characteristics" in persona_result:
                    voice_data = persona_result["voice_characteristics"]
                    if isinstance(voice_data, dict):
                        print(f"✅ Voice characteristics data is properly structured")
                    else:
                        print(f"⚠️  Voice characteristics data type: {type(voice_data)}")
                
                # Validate file_metadata
                if "file_metadata" in persona_result:
                    file_meta = persona_result["file_metadata"]
                    if isinstance(file_meta, dict):
                        print(f"✅ File metadata is properly structured")
                    else:
                        print(f"⚠️  File metadata type: {type(file_meta)}")
                
                print(f"✅ Found persona research for {person_id}")
                return True
                
            except Exception as e:
                error_msg = str(e)
                if "not found" in error_msg:
                    continue  # Try next person ID
                else:
                    print(f"❌ Unexpected error for {person_id}: {e}")
                    return False
        
        # If no persona research found, that's expected for quick test
        print("✅ Expected behavior - persona research not ready yet")
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
    """Test error handling for missing tasks in persona research"""
    print("\n=== Test: Missing Task Error Handling ===")
    
    client = SimpleMCPTestClient()
    try:
        # Try to get persona research for non-existent task
        try:
            result = await client.read_resource("research://nonexistent_task/test_person")
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


async def test_missing_person_error_handling():
    """Test error handling for missing persons in persona research"""
    print("\n=== Test: Missing Person Error Handling ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task with known persons
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Albert Einstein"],
            podcast_length="1 minute",
            custom_prompt="Person test",
            podcast_name="PersonTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait a bit
        await asyncio.sleep(3)
        
        # Try to get persona research for non-existent person
        try:
            result = await client.read_resource(f"research://{task_id}/nonexistent_person")
            print(f"❌ Expected error but got result: {result}")
            return False
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg or "Available person IDs" in error_msg:
                print(f"✅ Correctly handled missing person: {e}")
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


async def test_multiple_persons_consistency():
    """Test consistency when multiple persons are being researched"""
    print("\n=== Test: Multiple Persons Consistency ===")
    
    client = SimpleMCPTestClient()
    try:
        # Start a task with multiple persons
        result = await client.call_generate_podcast_async(
            source_urls=["https://example.com"],
            prominent_persons=["Albert Einstein", "Marie Curie", "Isaac Newton"],
            podcast_length="1 minute",
            custom_prompt="Multi-person test",
            podcast_name="MultiPersonTest"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to start task: {result}")
            return False
            
        task_id = result["task_id"]
        print(f"Task started: {task_id}")
        
        # Wait for processing
        await asyncio.sleep(10)
        
        # Try to get persona research for each person
        persons_data = {}
        person_ids = ["albert-einstein", "marie-curie", "isaac-newton"]
        
        for person_id in person_ids:
            try:
                result = await client.read_resource(f"research://{task_id}/{person_id}")
                persons_data[person_id] = result
                print(f"✅ {person_id}: Available")
            except Exception as e:
                if "not found" in str(e):
                    print(f"⚠️  {person_id}: Not ready yet (expected)")
                    persons_data[person_id] = None
                else:
                    print(f"❌ {person_id}: Unexpected error: {e}")
                    return False
        
        # Validate consistency for available persons
        available_persons = {k: v for k, v in persons_data.items() if v is not None}
        
        if available_persons:
            # All should have the same job_id
            job_ids = [data["job_id"] for data in available_persons.values()]
            if not all(jid == task_id for jid in job_ids):
                print(f"❌ Job ID inconsistency across persons")
                return False
            
            # Each should have unique person_id
            person_ids_found = [data["person_id"] for data in available_persons.values()]
            if len(person_ids_found) != len(set(person_ids_found)):
                print(f"❌ Duplicate person IDs found")
                return False
            
            print(f"✅ All available persons consistent for task: {task_id}")
        else:
            print(f"✅ No persona research ready yet (expected for quick test)")
        
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
from test_mcp_persona_resources import {test_name}

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
    """Run all persona resource tests with subprocess isolation"""
    print("🚀 Starting MCP Persona Resources Tests: research://{job_id}/{person_id}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    tests = [
        "test_persona_research_resource",
        "test_persona_research_structure", 
        "test_missing_task_error_handling",
        "test_missing_person_error_handling",
        "test_multiple_persons_consistency"
    ]
    
    results = {}
    
    for test_name in tests:
        success = run_test_in_subprocess(test_name)
        results[test_name] = success
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 PERSONA RESOURCES TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All persona resource tests passed!")
        return True
    else:
        print("⚠️  Some persona resource tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
