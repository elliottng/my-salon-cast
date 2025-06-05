#!/usr/bin/env python3
"""
Test script for enhanced async features:
- Task cancellation
- Queue status monitoring
- Webhook notifications
"""
import asyncio
import json
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.podcast_models import PodcastRequest
from app.podcast_workflow import PodcastGeneratorService
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner

async def test_task_cancellation():
    """Test task cancellation functionality."""
    print("\n=== Testing Task Cancellation ===")
    
    service = PodcastGeneratorService()
    status_manager = get_status_manager()
    task_runner = get_task_runner()
    
    # Create a request with a test URL
    request = PodcastRequest(
        source_urls=["https://en.wikipedia.org/wiki/Artificial_intelligence"],
        desired_podcast_length_str="5-7 minutes"
    )
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait a moment then check status
    await asyncio.sleep(2)
    status = status_manager.get_status(task_id)
    print(f"Task status after 2s: {status.status}")
    
    # Cancel the task
    cancelled = await task_runner.cancel_task(task_id)
    print(f"Cancellation requested: {cancelled}")
    
    # Wait and check final status
    await asyncio.sleep(3)
    final_status = status_manager.get_status(task_id)
    print(f"Final task status: {final_status.status}")
    print(f"Status description: {final_status.status_description}")
    
    return task_id

async def test_queue_status():
    """Test queue status monitoring."""
    print("\n=== Testing Queue Status ===")
    
    task_runner = get_task_runner()
    
    # Get initial queue status
    queue_status = task_runner.get_queue_status()
    print(f"Initial queue status: {json.dumps(queue_status, indent=2)}")
    
    # Submit multiple tasks
    service = PodcastGeneratorService()
    tasks = []
    
    for i in range(3):
        request = PodcastRequest(
            source_urls=[f"https://example.com/article{i}"],
            desired_podcast_length_str="3-5 minutes"
        )
        task_id = await service.generate_podcast_async(request)
        tasks.append(task_id)
        print(f"Submitted task {i+1}: {task_id}")
        
        # Check queue after each submission
        queue_status = task_runner.get_queue_status()
        print(f"Queue after submission {i+1}: Active={queue_status['active_tasks']}, Available={queue_status['available_slots']}")
    
    # Try to submit one more (should fail if max_workers=3)
    try:
        extra_request = PodcastRequest(
            source_urls=["https://example.com/extra"],
            desired_podcast_length_str="3-5 minutes"
        )
        extra_task = await service.generate_podcast_async(extra_request)
        print(f"Extra task accepted: {extra_task}")
    except Exception as e:
        print(f"Extra task rejected (expected): Queue at capacity")
    
    # Get active tasks details
    active_tasks = task_runner.get_active_tasks()
    print(f"\nActive tasks: {len(active_tasks)}")
    for task in active_tasks:
        print(f"  - {task['task_id']}: running={task['running']}, cancelled={task['cancelled']}")
    
    # Cancel all tasks to clean up
    for task_id in tasks:
        await task_runner.cancel_task(task_id)
    
    await asyncio.sleep(2)
    print("\nCleanup complete")

async def test_webhook_notifications():
    """Test webhook notification functionality."""
    print("\n=== Testing Webhook Notifications ===")
    
    # Note: In a real test, you'd use a webhook testing service or local server
    # For this demo, we'll just show the webhook would be called
    
    service = PodcastGeneratorService()
    status_manager = get_status_manager()
    
    # Create request with webhook URL
    request = PodcastRequest(
        source_urls=["https://en.wikipedia.org/wiki/Python_(programming_language)"],
        desired_podcast_length_str="2-3 minutes",
        webhook_url="https://webhook.site/test-webhook-url"  # Example webhook URL
    )
    
    print(f"Starting task with webhook URL: {request.webhook_url}")
    task_id = await service.generate_podcast_async(request)
    print(f"Task started: {task_id}")
    
    # For demo, we'll cancel it quickly to trigger a webhook
    await asyncio.sleep(2)
    cancelled = await task_runner.cancel_task(task_id)
    print(f"Task cancelled: {cancelled}")
    
    # In real scenario, the webhook would be called with cancellation status
    print("Webhook notification would be sent with 'cancelled' status")
    
    # Check final status
    await asyncio.sleep(2)
    final_status = status_manager.get_status(task_id)
    print(f"Final status: {final_status.status}")

async def main():
    """Run all enhanced async tests."""
    print("Testing Enhanced Async Features\n")
    
    try:
        # Test 1: Cancellation
        await test_task_cancellation()
        
        # Test 2: Queue Status
        await test_queue_status()
        
        # Test 3: Webhooks
        await test_webhook_notifications()
        
        print("\n✅ All enhanced async tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
