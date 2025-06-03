#!/usr/bin/env python3
"""
Test script for research://{task_id}/{person_id} MCP resource validation.

This script validates:
1. Input validation for task_id and person_id parameters
2. Error handling for non-existent tasks and persons
3. PersonaResearch JSON file reading and parsing
4. Available persons list generation from task files
5. File metadata and error handling scenarios
"""

import os
import sys
import json
import tempfile
import asyncio
import time
from datetime import datetime, timezone

# Add the app directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.mcp_server import get_persona_research_resource
from app.status_manager import StatusManager, PodcastStatus
from app.podcast_models import PodcastEpisode, PersonaResearch
from fastmcp.exceptions import ToolError

# Initialize status manager
status_manager = StatusManager()

# Generate unique suffix for this test run
test_run_suffix = str(int(time.time()))

async def test_input_validation():
    """Test input validation for task_id and person_id parameters."""
    print("🧪 Testing input validation...")
    
    # Test empty task_id
    try:
        await get_persona_research_resource("", "albert-einstein")
        print("❌ Should have failed with empty task_id")
        return False
    except ToolError as e:
        if "task_id is required" in str(e):
            print("✅ Empty task_id validation works")
        else:
            print(f"❌ Wrong error for empty task_id: {e}")
            return False
    
    # Test empty person_id
    try:
        await get_persona_research_resource("valid_task_id_1234567890", "")
        print("❌ Should have failed with empty person_id")
        return False
    except ToolError as e:
        if "person_id is required" in str(e):
            print("✅ Empty person_id validation works")
        else:
            print(f"❌ Wrong error for empty person_id: {e}")
            return False
    
    # Test short task_id
    try:
        await get_persona_research_resource("short", "albert-einstein")
        print("❌ Should have failed with short task_id")
        return False
    except ToolError as e:
        if "Invalid task_id format" in str(e):
            print("✅ Short task_id validation works")
        else:
            print(f"❌ Wrong error for short task_id: {e}")
            return False
    
    # Test long task_id (over 100 characters)
    long_task_id = "x" * 101
    try:
        await get_persona_research_resource(long_task_id, "albert-einstein")
        print("❌ Should have failed with long task_id")
        return False
    except ToolError as e:
        if "Invalid task_id format" in str(e):
            print("✅ Long task_id validation works")
        else:
            print(f"❌ Wrong error for long task_id: {e}")
            return False
    
    return True

async def test_nonexistent_task():
    """Test handling of non-existent task."""
    print("\n🧪 Testing non-existent task handling...")
    
    try:
        result = await get_persona_research_resource(f"nonexistent_task_{test_run_suffix}", "albert-einstein")
        print("❌ Should have raised ToolError for non-existent task")
        return False
    except ToolError as e:
        if "Task not found" in str(e):
            print("✅ Non-existent task error handling works")
            return True
        else:
            print(f"❌ Unexpected error message: {e}")
            return False
    except Exception as e:
        print(f"❌ Unexpected exception type: {e}")
        return False

async def test_task_without_episode():
    """Test error handling for tasks without episodes."""
    print("\n🧪 Testing task without episode...")
    
    # Create a task with no result_episode using create_status
    task_id = f"task_no_episode_{test_run_suffix}"
    status_manager.create_status(task_id)
    
    try:
        await get_persona_research_resource(task_id, "albert-einstein")
        print("❌ Should have failed with no episode")
        return False
    except ToolError as e:
        if "Podcast episode not available" in str(e):
            print("✅ No episode error handling works")
            return True
        else:
            print(f"❌ Wrong error for no episode: {e}")
            return False

async def test_task_without_research_paths():
    """Test error handling for tasks with no persona research files."""
    print("\n🧪 Testing task without persona research paths...")
    
    # Create a task with episode but no research paths
    task_id = f"task_no_research_{test_run_suffix}"
    # First create the status
    status_manager.create_status(task_id)
    
    episode = PodcastEpisode(
        title="Test Episode",
        summary="Test Summary",
        transcript="Test transcript",
        audio_filepath="",
        source_attributions=[],
        warnings=[],
        llm_persona_research_paths=None  # No research paths
    )
    
    # Now set the episode
    status_manager.set_episode(task_id, episode)
    
    try:
        await get_persona_research_resource(task_id, "albert-einstein")
        print("❌ Should have failed with no research available")
        return False
    except ToolError as e:
        if "No persona research available" in str(e):
            print("✅ No research available error handling works")
            return True
        else:
            print(f"❌ Wrong error for no research: {e}")
            return False

async def test_person_not_found():
    """Test error handling when requested person is not found, with available persons list."""
    print("\n🧪 Testing person not found with available persons...")
    
    # Create temporary research files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create research files for different persons
        einstein_file = os.path.join(tmpdir, "persona_research_albert-einstein.json")
        curie_file = os.path.join(tmpdir, "persona_research_marie-curie.json")
        
        einstein_data = {
            "person_id": "albert-einstein",
            "name": "Albert Einstein",
            "detailed_profile": "Theoretical physicist known for theory of relativity.",
            "invented_name": "Dr. Alex",
            "gender": "neutral"
        }
        
        curie_data = {
            "person_id": "marie-curie",
            "name": "Marie Curie", 
            "detailed_profile": "Pioneer in radioactivity research.",
            "invented_name": "Dr. Maria",
            "gender": "female"
        }
        
        with open(einstein_file, 'w') as f:
            json.dump(einstein_data, f, indent=2)
        
        with open(curie_file, 'w') as f:
            json.dump(curie_data, f, indent=2)
        
        # Create task with these research files
        task_id = f"task_person_not_found_{test_run_suffix}"
        # First create the status
        status_manager.create_status(task_id)
        
        episode = PodcastEpisode(
            title="Test Episode",
            summary="Test Summary", 
            transcript="Test transcript",
            audio_filepath="",
            source_attributions=[],
            warnings=[],
            llm_persona_research_paths=[einstein_file, curie_file]
        )
        
        # Now set the episode
        status_manager.set_episode(task_id, episode)
        
        # Try to access non-existent person
        try:
            await get_persona_research_resource(task_id, "isaac-newton")
            print("❌ Should have failed with person not found")
            return False
        except ToolError as e:
            error_msg = str(e)
            if ("Person 'isaac-newton' not found" in error_msg and 
                "albert-einstein" in error_msg and 
                "marie-curie" in error_msg):
                print("✅ Person not found error with available persons works")
                return True
            else:
                print(f"❌ Wrong error format for person not found: {e}")
                return False

async def test_valid_research_access():
    """Test successful research data access."""
    print("\n🧪 Testing valid research data access...")
    
    # Create temporary research file
    with tempfile.TemporaryDirectory() as tmpdir:
        research_file = os.path.join(tmpdir, "persona_research_albert-einstein.json")
        
        research_data = {
            "person_id": "albert-einstein",
            "name": "Albert Einstein",
            "detailed_profile": "Theoretical physicist known for developing the theory of relativity.",
            "invented_name": "Dr. Alex",
            "gender": "neutral",
            "tts_voice_id": "en-US-Neural2-J",
            "tts_voice_params": {"speaking_rate": 1.0, "pitch": 0.0},
            "source_context": "Physics research papers",
            "creation_date": "2025-06-02T20:00:00Z"
        }
        
        with open(research_file, 'w') as f:
            json.dump(research_data, f, indent=2)
        
        # Create task with this research file
        task_id = f"task_valid_research_{test_run_suffix}"
        # First create the status
        status_manager.create_status(task_id)
        
        episode = PodcastEpisode(
            title="Physics Discussion",
            summary="Discussion with Albert Einstein",
            transcript="Test transcript",
            audio_filepath="",
            source_attributions=[],
            warnings=[],
            llm_persona_research_paths=[research_file]
        )
        
        # Now set the episode
        status_manager.set_episode(task_id, episode)
        
        try:
            result = await get_persona_research_resource(task_id, "albert-einstein")
            
            # Validate response structure
            expected_fields = {"task_id", "person_id", "research_data", "has_research", "file_metadata", "resource_type"}
            if not expected_fields.issubset(result.keys()):
                print(f"❌ Missing fields in response. Expected: {expected_fields}, Got: {set(result.keys())}")
                return False
            
            # Validate field values
            if result["task_id"] != task_id:
                print(f"❌ Wrong task_id: {result['task_id']}")
                return False
            
            if result["person_id"] != "albert-einstein":
                print(f"❌ Wrong person_id: {result['person_id']}")
                return False
            
            if not result["has_research"]:
                print("❌ has_research should be True")
                return False
            
            if result["resource_type"] != "persona_research":
                print(f"❌ Wrong resource_type: {result['resource_type']}")
                return False
            
            # Validate research data content
            research = result["research_data"]
            if not research:
                print("❌ research_data should not be None")
                return False
            
            if research["name"] != "Albert Einstein":
                print(f"❌ Wrong name in research data: {research['name']}")
                return False
            
            if research["invented_name"] != "Dr. Alex":
                print(f"❌ Wrong invented_name: {research['invented_name']}")
                return False
            
            # Validate file metadata
            file_meta = result["file_metadata"]
            if not file_meta["file_exists"]:
                print("❌ file_exists should be True")
                return False
            
            if file_meta["file_size"] <= 0:
                print(f"❌ file_size should be positive: {file_meta['file_size']}")
                return False
            
            if research_file not in file_meta["research_file_path"]:
                print(f"❌ Wrong file path: {file_meta['research_file_path']}")
                return False
            
            print("✅ Valid research access works correctly")
            print(f"   📄 Research data loaded for: {research['name']}")
            print(f"   🎭 Invented name: {research['invented_name']}")
            print(f"   📁 File size: {file_meta['file_size']} bytes")
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error in valid research access: {e}")
            return False

async def test_missing_research_file():
    """Test handling of missing research file."""
    print("\n🧪 Testing missing research file handling...")
    
    # Create task with correct filename format but non-existent file path
    task_id = f"task_missing_file_{test_run_suffix}"
    missing_file = "/tmp/persona_research_albert-einstein.json"
    
    # First create the status
    status_manager.create_status(task_id)
    
    episode = PodcastEpisode(
        title="Test Episode",
        summary="Test Summary",
        transcript="Test transcript",
        audio_filepath="",
        source_attributions=[],
        warnings=[],
        llm_persona_research_paths=[missing_file]
    )
    
    # Now set the episode
    status_manager.set_episode(task_id, episode)
    
    try:
        result = await get_persona_research_resource(task_id, "albert-einstein")
        
        # Should return successful response but with null research_data
        if result["has_research"]:
            print("❌ has_research should be False for missing file")
            return False
        
        if result["research_data"] is not None:
            print("❌ research_data should be None for missing file")
            return False
        
        if result["file_metadata"]["file_exists"]:
            print("❌ file_exists should be False for missing file")
            return False
        
        if result["file_metadata"]["file_size"] != 0:
            print(f"❌ file_size should be 0 for missing file: {result['file_metadata']['file_size']}")
            return False
        
        print("✅ Missing research file handling works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error with missing file: {e}")
        return False

async def test_corrupted_json_file():
    """Test handling of corrupted JSON research file."""
    print("\n🧪 Testing corrupted JSON file handling...")
    
    # Create temporary corrupted JSON file
    with tempfile.TemporaryDirectory() as tmpdir:
        research_file = os.path.join(tmpdir, "persona_research_albert-einstein.json")
        
        # Write invalid JSON
        with open(research_file, 'w') as f:
            f.write('{"person_id": "albert-einstein", "name": "Albert Einstein", invalid json}')
        
        # Create task with this corrupted file
        task_id = f"task_corrupted_json_{test_run_suffix}"
        # First create the status
        status_manager.create_status(task_id)
        
        episode = PodcastEpisode(
            title="Test Episode",
            summary="Test Summary",
            transcript="Test transcript",
            audio_filepath="",
            source_attributions=[],
            warnings=[],
            llm_persona_research_paths=[research_file]
        )
        
        # Now set the episode
        status_manager.set_episode(task_id, episode)
        
        try:
            result = await get_persona_research_resource(task_id, "albert-einstein")
            
            # Should handle gracefully with null research_data
            if result["has_research"]:
                print("❌ has_research should be False for corrupted file")
                return False
            
            if result["research_data"] is not None:
                print("❌ research_data should be None for corrupted file")
                return False
            
            if not result["file_metadata"]["file_exists"]:
                print("❌ file_exists should be True for corrupted file")
                return False
            
            if result["file_metadata"]["file_size"] <= 0:
                print("❌ file_size should be positive for corrupted file")
                return False
            
            print("✅ Corrupted JSON file handling works correctly")
            return True
            
        except Exception as e:
            print(f"❌ Unexpected error with corrupted JSON: {e}")
            return False

async def run_all_tests():
    """Run all validation tests."""
    print("🚀 Starting persona research resource validation tests...\n")
    
    tests = [
        ("Input Validation", test_input_validation),
        ("Non-existent Task", test_nonexistent_task),
        ("Task Without Episode", test_task_without_episode),
        ("Task Without Research Paths", test_task_without_research_paths),
        ("Person Not Found", test_person_not_found),
        ("Valid Research Access", test_valid_research_access),
        ("Missing Research File", test_missing_research_file),
        ("Corrupted JSON File", test_corrupted_json_file),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            if success:
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All persona research resource tests passed!")
        print("\n✅ The research://{task_id}/{person_id} resource is ready for production use!")
        print("\n📋 Validated Features:")
        print("   • Task-scoped person ID extraction and validation")
        print("   • PersonaResearch JSON file reading and parsing") 
        print("   • Available persons list generation from task files")
        print("   • Comprehensive error handling and file metadata")
        print("   • Graceful handling of missing and corrupted files")
        print("   • Input validation and security checks")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
