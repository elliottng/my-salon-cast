"""
Test script for MySalonCast REST API interface

This script tests the ability to interact with the MySalonCast REST API endpoints.
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path

# Add the project root to the path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from tests.mcp.client import SimpleMCPTestClient
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server URL for tests
SERVER_URL = "http://localhost:8000/mcp"

async def test_list_tools_and_resources():
    """Test MCP tools and resources listing"""
    try:
        client = SimpleMCPTestClient(SERVER_URL)
        
        # List available MCP tools
        print("Listing available MCP tools...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} MCP tools:")
        for tool in tools:
            # Tool objects have .name attribute, not subscriptable
            print(f"   - {tool.name}: {getattr(tool, 'description', 'No description')}")
        
        # List available MCP resources  
        print("\nListing available MCP resources...")
        resources = await client.list_resources()
        print(f"✅ Found {len(resources)} MCP resources:")
        for resource in resources:
            # Resource objects have .uri attribute, not subscriptable
            print(f"   - {resource.uri}: {getattr(resource, 'name', 'No name')}")
            
        print("✅ PASSED: List Tools and Resources")
        await client.close()
        return True
        
    except Exception as e:
        logger.error(f"MCP tools and resources check failed: {e}")
        print(f"❌ MCP tools and resources check failed: {e}")
        print("❌ FAILED: List Tools and Resources")
        return False

async def test_hello_tool():
    """Test the hello MCP tool"""
    client = SimpleMCPTestClient(SERVER_URL)
    
    try:
        print("Calling hello MCP tool...")
        result = await client.call_tool("hello", {"name": "MCP Tester"})
        
        # Hello tool returns a simple string, not JSON
        if isinstance(result, dict) and "text" in result:
            response_text = result["text"]
            print(f"✅ Successfully called hello tool")
            print(f"   Response: {response_text}")
            if "Hello, MCP Tester!" in response_text:
                print("✅ PASSED: Hello Tool")
                return True
            else:
                print(f"❌ Unexpected response text: {response_text}")
                return False
        else:
            print(f"❌ Unexpected response format: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Hello tool test failed: {e}")
        print(f"❌ Hello tool test failed: {e}")
        print("❌ FAILED: Hello Tool")
        return False
    finally:
        await client.close()

async def test_supported_formats_resource():
    """Test reading the supported formats resource"""
    client = SimpleMCPTestClient(SERVER_URL)
    
    try:
        print("Reading supported formats resource...")
        formats_data = await client.read_resource("config://supported_formats")
        
        if formats_data and isinstance(formats_data, dict):
            print("✅ Successfully read supported formats resource")
            print(f"   Input formats: {list(formats_data.get('input_formats', {}).keys())}")
            print(f"   Output formats: {list(formats_data.get('output_formats', {}).keys())}")
            print(f"   Languages: {len(formats_data.get('languages', []))}")
            print("✅ PASSED: Supported Formats Resource")
            return True
        else:
            print(f"❌ Resource content format unexpected: {formats_data}")
            return False
            
    except Exception as e:
        logger.error(f"Supported formats test failed: {e}")
        print(f"❌ Supported formats test failed: {e}")
        print("❌ FAILED: Supported Formats Resource")
        return False
    finally:
        await client.close()

async def test_generate_podcast_async():
    """Test the async podcast generation tool"""
    try:
        client = SimpleMCPTestClient(SERVER_URL)
        
        # Create a podcast generation request
        print("Creating async podcast generation request...")
        payload = {
            "source_urls": ["https://www.example.com/sample", "https://www.example.org/test"],
            "podcast_name": "Test Podcast",
            "podcast_length": "3-5 minutes",
            "output_language": "en",  
            "dialogue_style": "conversational"
        }
        
        # Submit the request using the updated client
        print("Submitting async podcast generation request...")
        result = await client.call_generate_podcast_async(**payload)
        
        # Check if the response contains a task_id
        if not result.get("task_id"):
            print(f"❌ No task_id in response: {result}")
            await client.close()
            return False
        
        task_id = result["task_id"]
        print(f"✅ Task submitted successfully! Task ID: {task_id}")
        
        # Get initial status
        print("\nChecking initial task status...")
        status = await client.get_task_status(task_id)
        print(f"Initial status: {status}")
        
        # Wait a short time to let the task start processing
        print("Waiting 2 seconds for task to start processing...")
        await asyncio.sleep(2)
        
        # We'll only wait briefly since full generation takes a long time
        # and we're just testing the interface, not completion
        
        # Get updated status
        print("Checking updated task status...")
        status = await client.get_task_status(task_id)
        print(f"Updated status: {status}")
        
        # Verify the status has expected fields
        for field in ["status", "progress_percentage"]:
            if field not in status:
                print(f"❌ Status missing {field} field: {status}")
                return False
                
        print(f"✅ Status contains expected fields")
        
        await client.close()
        return True
    except Exception as e:
        logging.error(f"Generate podcast async test failed: {e}")
        print(f"❌ Generate podcast async test failed: {e}")
        return False
                
async def test_non_existent_task():
    """Test error handling for non-existent task IDs"""
    try:
        client = SimpleMCPTestClient(SERVER_URL)
        
        # Generate a random UUID that definitely doesn't exist
        task_id = str(uuid.uuid4())
        print(f"Testing with non-existent task ID: {task_id}")
        
        # Try to get status for the non-existent task
        try:
            status = await client.get_task_status(task_id)
            
            # If we got a successful response, check if it indicates an error
            if status.get("error") or status.get("status") == "not_found":
                print(f"✅ Successfully detected non-existent task ID (got error response)")
                print(f"   Response: {status}")
                await client.close()
                return True
                
            # If we didn't get an error, something unexpected happened
            print(f"❌ Expected error response but got: {status}")
            return False
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                print(f"✅ Successfully detected non-existent task ID (got exception: {e})")
                await client.close()
                return True
            raise  # Re-raise if it's not the expected exception
    except Exception as e:
        logging.error(f"Non-existent task test failed: {e}")
        print(f"❌ Non-existent task test failed: {e}")
        return False

async def test_validation_error():
    """Test validation error handling for invalid requests"""
    client = SimpleMCPTestClient(SERVER_URL)
    
    try:
        print("Testing with empty request (should succeed with defaults)")
        # Empty payload should work since all parameters have defaults
        result = await client.call_generate_podcast_async()
        
        # Handle various response formats
        if isinstance(result, dict):
            if result.get("success"):
                print("✅ Empty request handled correctly with defaults")
                print("✅ PASSED: Validation Error")
                return True
            else:
                print(f"❌ Expected success but got error: {result}")
                return False
        elif result == 0:  # Some edge case where result is 0
            print("❌ Received unexpected result: 0 (likely an issue)")
            return False
        else:
            print(f"❌ Unexpected result format: {result} (type: {type(result)})")
            return False
            
    except Exception as e:
        logger.error(f"Validation error test failed: {e}")
        print(f"❌ Validation error test failed: {e}")
        print("❌ FAILED: Validation Error") 
        return False
    finally:
        await client.close()

async def run_all_tests():
    """Run all MCP client tests"""
    tests = [
        ("List Tools and Resources", test_list_tools_and_resources),
        ("Hello Tool", test_hello_tool),
        ("Supported Formats Resource", test_supported_formats_resource),
        ("Non-existent Task", test_non_existent_task),
        ("Validation Error", test_validation_error),
        ("Generate Podcast Async", test_generate_podcast_async),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Test: {name}")
        print(f"{'='*60}")
        
        try:
            result = await test_func()
            if result:
                print(f"✅ PASSED: {name}")
                passed += 1
            else:
                print(f"❌ FAILED: {name}")
                failed += 1
        except Exception as e:
            print(f"❌ FAILED: {name} - {type(e).__name__}: {str(e)}")
            logger.exception(f"Error in test {name}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    # Check if MCP server is running
    print("Starting MCP client tests - make sure the MySalonCast server is running on port 8000")
    print("=" * 60)
    
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
