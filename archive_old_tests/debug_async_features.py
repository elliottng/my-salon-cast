import requests
import time
import json

BASE_URL = "http://localhost:8080"  # Assuming your server runs on port 8000

def submit_podcast_request(source_url, title, num_speakers=2, language="en", webhook_url=None):
    """Submits an asynchronous podcast generation request."""
    payload = {
        "source_url": source_url,
        "title": title,
        "num_speakers": num_speakers,
        "language": language,
        "user_id": "test_user_queue_debug",
        "generation_options": {
            "target_audience": "general",
            "desired_length_minutes": 1, # Keep it short for testing
            "style_and_tone": "informative",
            "custom_instructions": "Keep this very brief for testing purposes."
        }
    }
    if webhook_url:
        payload["webhook_url"] = webhook_url
    
    try:
        response = requests.post(f"{BASE_URL}/generate/podcast_async/", json=payload)
        response.raise_for_status()
        task_info = response.json()
        print(f"Submitted task: {task_info.get('task_id')} for '{title}'")
        return task_info
    except requests.exceptions.RequestException as e:
        print(f"Error submitting task for '{title}': {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Response content: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"Response content: {e.response.text}")
        return None

def get_queue_status():
    """Gets the current queue status."""
    try:
        response = requests.get(f"{BASE_URL}/queue/status")
        response.raise_for_status()
        status = response.json()
        print("\n--- Queue Status ---")
        print(json.dumps(status, indent=2))
        print("--------------------")
        return status
    except requests.exceptions.RequestException as e:
        print(f"Error getting queue status: {e}")
        return None

if __name__ == "__main__":
    print("Starting Task Runner and Queue Management Test...")

    # Ensure server is ready - wait a few seconds
    print("Waiting for server to be ready (5s)...")
    time.sleep(5) # Give server time to start

    # Submit 5 tasks
    task_ids = []
    for i in range(5):
        # Using a dummy URL as content extraction might take time or fail if URL is invalid
        # The goal here is to test queueing, not successful generation
        task_info = submit_podcast_request(
            source_url=f"http://example.com/source{i+1}",
            title=f"Test Podcast {i+1} (Queue Test)"
        )
        if task_info and task_info.get("task_id"):
            task_ids.append(task_info["task_id"])
    
    if not task_ids:
        print("No tasks were submitted successfully. Aborting test.")
    else:
        print(f"\nSubmitted {len(task_ids)} tasks. Waiting for tasks to process/queue (10s)...")
        # Wait for a bit to allow tasks to be processed or queued
        time.sleep(10)

        # Get queue status
        queue_status = get_queue_status()

        if queue_status:
            active_tasks = queue_status.get("active_tasks_count", 0)
            queued_tasks_count = queue_status.get("queued_tasks_count", 0)
            
            print("\n--- Test Summary ---")
            # Assuming MAX_CONCURRENT_TASKS is 3 (default)
            # We submitted 5 tasks.
            # Expected: 3 active, 2 queued (or fewer if some completed very quickly)
            # Or, if tasks are super short, some might have completed.
            # A more robust check would be that active_tasks <= 3
            # and active_tasks + queued_tasks_count <= 5

            if active_tasks <= 3:
                print(f"PASS: Active tasks ({active_tasks}) is within the limit of 3.")
            else:
                print(f"FAIL: Active tasks ({active_tasks}) exceeds the limit of 3.")

            if active_tasks + queued_tasks_count <= len(task_ids):
                 print(f"PASS: Total tasks in system ({active_tasks + queued_tasks_count}) is consistent with submitted tasks ({len(task_ids)})." )
            else:
                 print(f"FAIL: Total tasks in system ({active_tasks + queued_tasks_count}) is more than submitted tasks ({len(task_ids)})." )

            print(f"Active tasks: {active_tasks}")
            print(f"Queued tasks: {queued_tasks_count}")
            print(f"Available slots: {queue_status.get('available_slots')}")
            
            # Further checks could involve inspecting the details of active_tasks_details
            # and queued_tasks_details to see if our submitted task_ids are present.
        else:
            print("FAIL: Could not retrieve queue status.")

    print("\nTest finished.")
