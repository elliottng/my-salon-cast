#!/usr/bin/env python3
"""Simple test for status endpoints using the async workflow."""

import requests
import json
import time
import asyncio

BASE_URL = "http://localhost:8080"

# First, let's check if we have the async endpoint by looking at the available endpoints
print("1. Creating a test task using the workflow...")

# Import and use the async workflow directly
import sys
sys.path.insert(0, '/home/elliottng/CascadeProjects/mysaloncast')

from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest

async def create_test_task():
    # Create a test request
    request = PodcastRequest(
        source_urls=["https://en.wikipedia.org/wiki/Python_(programming_language)"],
        prominent_persons=["Guido van Rossum"],
        desired_podcast_length_str="short"
    )

    # Create service instance
    service = PodcastGeneratorService()
    
    # Generate async to get task_id
    print("   Calling generate_podcast_async()...")
    task_id = await service.generate_podcast_async(request)
    print(f"   ✓ Got task_id: {task_id}")
    return task_id

# Run async function
task_id = asyncio.run(create_test_task())

# Add a small delay to ensure async processing completes
print("\n   Waiting a moment for async processing...")
time.sleep(2)

# Check if status exists immediately
print("\n1.5. Checking if status exists immediately after creation...")
response = requests.get(f"{BASE_URL}/status/{task_id}")
if response.status_code == 200:
    status = response.json()
    print(f"   ✓ Status exists!")
    print(f"   - Status: {status.get('status')}")
    print(f"   - Error: {status.get('error_message', 'None')}")
else:
    print(f"   ✗ Status not found immediately: {response.status_code}")

# Now test the endpoints
print("\n2. Testing GET /status/{task_id}")
response = requests.get(f"{BASE_URL}/status/{task_id}")
if response.status_code == 200:
    status = response.json()
    print(f"   ✓ Status retrieved successfully")
    print(f"   - Status: {status['status']}")
    print(f"   - Progress: {status['progress_percentage']}%")
    print(f"   - Description: {status.get('status_description', 'N/A')}")
else:
    print(f"   ✗ Failed: {response.status_code} - {response.text}")

print("\n3. Testing GET /status")
response = requests.get(f"{BASE_URL}/status")
if response.status_code == 200:
    data = response.json()
    print(f"   ✓ Status list retrieved")
    print(f"   - Total tasks: {data['total']}")
    print(f"   - Tasks in response: {len(data['statuses'])}")
    if data['statuses']:
        print(f"   - First task ID: {data['statuses'][0]['task_id']}")
        print(f"   - First task status: {data['statuses'][0]['status']}")
else:
    print(f"   ✗ Failed: {response.status_code}")

print("\n4. Testing DELETE /status/{task_id}")
response = requests.delete(f"{BASE_URL}/status/{task_id}")
if response.status_code == 200:
    print(f"   ✓ Task deleted: {response.json()['message']}")
else:
    print(f"   ✗ Failed: {response.status_code}")

# Verify deletion
response = requests.get(f"{BASE_URL}/status/{task_id}")
if response.status_code == 404:
    print(f"   ✓ Confirmed: Task no longer exists (404)")
else:
    print(f"   ✗ Task still exists? Status: {response.status_code}")

print("\n✅ All tests completed!")
print("\nYou can also check the interactive API docs at: http://localhost:8080/docs")
