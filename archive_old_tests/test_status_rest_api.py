"""Test status endpoints by creating a podcast through the REST API."""

import requests
import json
import time

BASE_URL = "http://localhost:8080"

print("1. Creating a podcast through the REST API...")

# Create a podcast request through the API
podcast_request = {
    "source_urls": ["https://en.wikipedia.org/wiki/Python_(programming_language)"],
    "prominent_persons": ["Guido van Rossum"],
    "desired_podcast_length_str": "short"
}

# Call the generate endpoint
response = requests.post(f"{BASE_URL}/generate/podcast_async/", json=podcast_request)
if response.status_code != 200:
    print(f"   ✗ Failed to create podcast: {response.status_code} - {response.text}")
    exit(1)

result = response.json()
task_id = result.get("task_id")
if not task_id:
    print("   ✗ No task_id in response")
    exit(1)

print(f"   ✓ Got task_id: {task_id}")

# Now test the status endpoints
print("\n2. Testing GET /status/{task_id}")
response = requests.get(f"{BASE_URL}/status/{task_id}")
if response.status_code == 200:
    status = response.json()
    print("   ✓ Status retrieved successfully")
    print(f"   - Status: {status.get('status')}")
    print(f"   - Progress: {status.get('progress')}%") 
    print(f"   - Description: {status.get('status_description')}")
else:
    print(f"   ✗ Failed: {response.status_code} - {response.text}")

print("\n3. Testing GET /status")
response = requests.get(f"{BASE_URL}/status")
if response.status_code == 200:
    data = response.json()
    print("   ✓ Status list retrieved")
    print(f"   - Total tasks: {data.get('total', 0)}")
    print(f"   - Tasks in response: {len(data.get('statuses', []))}")
    
    # Show first task if any
    if data.get('statuses'):
        first = data['statuses'][0]
        print(f"   - First task: {first.get('task_id')} - {first.get('status')}")
else:
    print(f"   ✗ Failed: {response.status_code}")

print("\n4. Waiting for podcast to complete...")
max_wait = 60  # seconds
start_time = time.time()
while time.time() - start_time < max_wait:
    response = requests.get(f"{BASE_URL}/status/{task_id}")
    if response.status_code == 200:
        status = response.json()
        current_status = status.get('status')
        progress = status.get('progress', 0)
        print(f"   Status: {current_status} ({progress}%)", end='\r')
        
        if current_status in ['completed', 'failed']:
            print(f"\n   ✓ Final status: {current_status}")
            if current_status == 'failed':
                print(f"   - Error: {status.get('error_message')}")
            break
    
    time.sleep(2)
else:
    print("\n   ⚠ Timeout waiting for completion")

print("\n5. Testing DELETE /status/{task_id}")
response = requests.delete(f"{BASE_URL}/status/{task_id}")
if response.status_code == 200:
    print("   ✓ Task deleted successfully")
elif response.status_code == 404:
    print("   ✗ Failed: 404 (already deleted?)")
else:
    print(f"   ✗ Failed: {response.status_code}")

# Verify deletion
response = requests.get(f"{BASE_URL}/status/{task_id}")
if response.status_code == 404:
    print("   ✓ Confirmed: Task no longer exists (404)")
else:
    print("   ✗ Task still exists after deletion")

print("\n✅ All tests completed!")
print("\nNote: Make sure the FastAPI server is running with:")
print("  uvicorn app.main:app --reload")
