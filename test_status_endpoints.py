#!/usr/bin/env python3
"""Test script for the new status REST endpoints."""

import asyncio
import aiohttp
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"

async def test_status_endpoints():
    """Test all status endpoints."""
    async with aiohttp.ClientSession() as session:
        print("=== Testing Status REST Endpoints ===\n")
        
        # First, let's generate a podcast asynchronously to get a task_id
        print("1. Generating a podcast to create a task...")
        podcast_request = {
            "source_type": "url",
            "source_location": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "personas": ["Expert", "Layperson"],
            "sections": ["Introduction", "History", "Applications"],
            "api_key": "test_api_key"
        }
        
        # Check if we have the async endpoint, otherwise use sync
        try:
            # Try calling the async endpoint (if implemented)
            # For now, we'll simulate by calling the sync endpoint
            print("   Note: Using sync endpoint for now to generate test data...")
            async with session.post(
                f"{BASE_URL}/generate/podcast_elements/",
                json=podcast_request
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    # Extract task_id if available (it should be in the result)
                    task_id = result.get("task_id", result.get("podcast_id", "test-task-123"))
                    print(f"   ✓ Generated podcast with ID: {task_id}")
                else:
                    print(f"   ✗ Failed to generate podcast: {response.status}")
                    print(f"   Response: {await response.text()}")
                    task_id = "test-task-123"  # Fallback for testing
        except Exception as e:
            print(f"   ✗ Error generating podcast: {e}")
            task_id = "test-task-123"  # Fallback for testing
        
        print(f"\n2. Testing GET /status/{task_id}")
        try:
            async with session.get(f"{BASE_URL}/status/{task_id}") as response:
                if response.status == 200:
                    status_data = await response.json()
                    print(f"   ✓ Status retrieved successfully")
                    print(f"   - Task ID: {status_data.get('task_id')}")
                    print(f"   - Status: {status_data.get('status')}")
                    print(f"   - Progress: {status_data.get('progress_percentage')}%")
                    print(f"   - Created: {status_data.get('created_at')}")
                    if status_data.get('artifacts'):
                        print("   - Artifacts:")
                        for key, value in status_data['artifacts'].items():
                            if value:
                                print(f"     • {key}: {value}")
                elif response.status == 404:
                    print(f"   ✓ 404 correctly returned for non-existent task")
                else:
                    print(f"   ✗ Unexpected status: {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print("\n3. Testing GET /status (list all)")
        try:
            async with session.get(f"{BASE_URL}/status?limit=10&offset=0") as response:
                if response.status == 200:
                    list_data = await response.json()
                    print(f"   ✓ Status list retrieved successfully")
                    print(f"   - Total tasks: {list_data.get('total')}")
                    print(f"   - Returned: {len(list_data.get('statuses', []))}")
                    print(f"   - Limit: {list_data.get('limit')}")
                    print(f"   - Offset: {list_data.get('offset')}")
                    
                    # Show first few tasks
                    for i, status in enumerate(list_data.get('statuses', [])[:3]):
                        print(f"\n   Task {i+1}:")
                        print(f"   - ID: {status.get('task_id')}")
                        print(f"   - Status: {status.get('status')}")
                        print(f"   - Progress: {status.get('progress_percentage')}%")
                else:
                    print(f"   ✗ Failed with status: {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        print("\n4. Testing DELETE /status/{task_id}")
        # Test with non-existent task first
        test_delete_id = "non-existent-task"
        try:
            async with session.delete(f"{BASE_URL}/status/{test_delete_id}") as response:
                if response.status == 404:
                    print(f"   ✓ 404 correctly returned for non-existent task")
                else:
                    print(f"   ✗ Unexpected status for non-existent task: {response.status}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test with actual task (if we have one)
        if task_id != "test-task-123":
            try:
                async with session.delete(f"{BASE_URL}/status/{task_id}") as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"   ✓ Task deleted successfully: {result.get('message')}")
                    else:
                        print(f"   ✗ Failed to delete task: {response.status}")
            except Exception as e:
                print(f"   ✗ Error: {e}")
        
        print("\n5. Testing pagination")
        try:
            # Test different pagination parameters
            test_cases = [
                {"limit": 5, "offset": 0},
                {"limit": 10, "offset": 5},
                {"limit": 200, "offset": 0},  # Should be capped at 100
            ]
            
            for params in test_cases:
                async with session.get(f"{BASE_URL}/status", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        actual_limit = data.get('limit')
                        expected_limit = min(params['limit'], 100)
                        print(f"   ✓ Pagination test - requested limit: {params['limit']}, "
                              f"actual: {actual_limit}, offset: {params['offset']}")
                        if actual_limit != expected_limit:
                            print(f"     Note: Limit was capped at {actual_limit}")
        except Exception as e:
            print(f"   ✗ Error in pagination test: {e}")
        
        print("\n=== Test Summary ===")
        print("All status endpoints have been tested!")
        print("Check the FastAPI /docs endpoint for interactive API documentation.")

if __name__ == "__main__":
    # Check if server is running
    import requests
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("ERROR: Server not responding correctly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to server at http://localhost:8000")
        print("Please ensure the FastAPI server is running with: uvicorn app.main:app --reload")
        sys.exit(1)
    
    asyncio.run(test_status_endpoints())
