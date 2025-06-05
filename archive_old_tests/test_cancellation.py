#!/usr/bin/env python3
"""
Comprehensive test script for task cancellation feature
Tests cancellation in different states: queued, active, completed/failed
"""
import asyncio
import json
import sys
import os
import uuid
import time
import random
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.podcast_models import PodcastRequest
from app.podcast_workflow import PodcastGeneratorService
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner, TaskRunner
from test_helpers import reset_all_executors

def get_test_request(source_url=None, delay=None):
    """Create a test podcast request"""
    # Add a random number to the title to make it unique
    random_suffix = random.randint(1000, 9999)
    
    if source_url is None:
        # Use a public URL that should be accessible
        source_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    
    request = PodcastRequest(
        source_urls=[source_url],
        desired_podcast_length_str="2-3 minutes",
        title=f"Test Podcast {random_suffix} (Cancellation Test)",
        # If a delay was specified, add it as a custom parameter for our test
        custom_parameters={"test_delay": delay} if delay is not None else None
    )
    return request

async def test_cancel_active_task():
    """Test cancelling a task that is actively processing"""
    print("\n=== Test 1: Cancel Active Task ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    service = PodcastGeneratorService()
    status_manager = get_status_manager()
    task_runner = get_task_runner()
    
    # Create a request with a valid URL
    request = get_test_request()
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait a moment to let the task start processing
    await asyncio.sleep(2)
    status = status_manager.get_status(task_id)
    print(f"Task status before cancellation: {status.status}")
    
    # Cancel the task
    cancelled = await task_runner.cancel_task(task_id)
    print(f"Cancellation requested: {cancelled}")
    
    # Wait and check final status
    await asyncio.sleep(3)
    final_status = status_manager.get_status(task_id)
    print(f"Final task status: {final_status.status}")
    print(f"Status description: {final_status.status_description}")
    
    # Verify the task was actually cancelled
    if final_status.status == "cancelled":
        print("✅ Test PASSED: Task was successfully cancelled")
    else:
        print(f"❌ Test FAILED: Task was not cancelled, status is {final_status.status}")
    
    # Clean up the status
    status_manager.delete_status(task_id)

async def test_cancel_completed_task():
    """Test attempting to cancel a task that has already completed or failed"""
    print("\n=== Test 2: Cancel Completed/Failed Task ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    service = PodcastGeneratorService()
    status_manager = get_status_manager()
    task_runner = get_task_runner()
    
    # Create a request with an invalid URL that will fail quickly
    request = get_test_request("https://nonexistent-url-that-will-fail-quickly.com")
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait for the task to fail (due to invalid URL)
    await asyncio.sleep(5)
    status = status_manager.get_status(task_id)
    print(f"Task status after 5s: {status.status}")
    
    # Try to cancel the task after it's already failed
    cancelled = await task_runner.cancel_task(task_id)
    print(f"Cancellation requested: {cancelled}")
    
    # Verify the task was not cancelled (should remain in failed state)
    if cancelled == False and status.status == "failed":
        print("✅ Test PASSED: System correctly rejected cancellation of already failed task")
    else:
        print(f"❌ Test FAILED: Unexpected behavior when cancelling failed task")
    
    # Clean up the status
    status_manager.delete_status(task_id)

async def test_cancel_queued_task():
    """Test cancelling a task that is queued and waiting"""
    print("\n=== Test 3: Cancel Queued Task ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    service = PodcastGeneratorService()
    status_manager = get_status_manager()
    task_runner = get_task_runner()
    
    # First, reduce max_workers temporarily to ensure queueing
    original_max_workers = task_runner.max_workers
    task_runner.max_workers = 1
    print(f"Temporarily reduced max_workers to 1 (was {original_max_workers})")
    
    try:
        # Submit one task that will occupy the only worker slot
        active_request = get_test_request()
        active_task_id = await service.generate_podcast_async(active_request)
        print(f"Started active task: {active_task_id}")
        
        # Wait to ensure the task is running
        await asyncio.sleep(1)
        
        # Now submit a second task that should be queued
        queued_request = get_test_request()
        queued_task_id = await service.generate_podcast_async(queued_request)
        print(f"Submitted queued task: {queued_task_id}")
        
        # Check queue status to confirm
        queue_status = task_runner.get_queue_status()
        print(f"Queue status: {json.dumps(queue_status, indent=2)}")
        
        # Cancel the queued task
        cancelled = await task_runner.cancel_task(queued_task_id)
        print(f"Cancellation of queued task requested: {cancelled}")
        
        # Check the status of the queued task
        await asyncio.sleep(2)
        queued_status = status_manager.get_status(queued_task_id)
        print(f"Queued task status: {queued_status.status}")
        
        # Verify the queued task was cancelled
        if queued_status.status == "cancelled":
            print("✅ Test PASSED: Queued task was successfully cancelled")
        else:
            print(f"❌ Test FAILED: Queued task was not cancelled, status is {queued_status.status}")
        
        # Clean up
        status_manager.delete_status(queued_task_id)
        
        # Also cancel the active task
        await task_runner.cancel_task(active_task_id)
        status_manager.delete_status(active_task_id)
        
    finally:
        # Restore original max_workers
        task_runner.max_workers = original_max_workers
        print(f"Restored max_workers to {original_max_workers}")

async def main():
    """Run all cancellation tests"""
    print("\n=== Starting Comprehensive Task Cancellation Tests ===\n")
    
    # Test cancelling an active task
    await test_cancel_active_task()
    
    # Test attempting to cancel an already completed/failed task
    await test_cancel_completed_task()
    
    # Test cancelling a queued task
    await test_cancel_queued_task()
    
    print("\n=== All Cancellation Tests Completed ===\n")

if __name__ == "__main__":
    asyncio.run(main())
