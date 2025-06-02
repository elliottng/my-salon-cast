#!/usr/bin/env python3
"""
Test script for webhook notification feature
Tests webhook notifications for task completion, failure, and cancellation
"""
import asyncio
import json
import sys
import os
import uuid
import time
import random
from datetime import datetime
from aiohttp import web
import threading
import requests
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.podcast_models import PodcastRequest
from app.podcast_workflow import PodcastGeneratorService
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner
from test_helpers import reset_all_executors

# Global storage for received webhooks
webhook_received = []
mock_server_port = 8090  # Different from the main app port

async def webhook_handler(request):
    """Handler for incoming webhook requests"""
    global webhook_received
    
    # Parse the webhook payload
    payload = await request.json()
    
    # Store the webhook data with a timestamp
    webhook_received.append({
        "timestamp": datetime.now().isoformat(),
        "payload": payload
    })
    
    print(f"Webhook received: {json.dumps(payload, indent=2)}")
    
    # Return a success response
    return web.json_response({"status": "success", "message": "Webhook received"})

async def setup_webhook_server():
    """Set up a simple webhook receiver server"""
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', mock_server_port)
    await site.start()
    
    print(f"Mock webhook server running at http://localhost:{mock_server_port}/webhook")
    return runner

def get_test_request(webhook_url, source_url=None):
    """Create a test podcast request with webhook URL"""
    # Add a random number to the title to make it unique
    random_suffix = random.randint(1000, 9999)
    
    if source_url is None:
        # Use a public URL that should be accessible
        source_url = "https://en.wikipedia.org/wiki/Artificial_intelligence"
    
    request = PodcastRequest(
        source_urls=[source_url],
        desired_podcast_length_str="2-3 minutes",
        title=f"Test Podcast {random_suffix} (Webhook Test)",
        webhook_url=webhook_url
    )
    return request

async def test_webhook_success():
    """Test webhook notification for successful task completion"""
    print("\n=== Test 1: Webhook for Successful Task ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    # Create a short-lived but successful task
    service = PodcastGeneratorService()
    webhook_url = f"http://localhost:{mock_server_port}/webhook"
    
    # Clear previous webhook data
    global webhook_received
    webhook_received = []
    
    # Create request with a valid URL but a very short podcast length
    # This should complete relatively quickly with success
    request = get_test_request(webhook_url)
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait for the task to complete and webhook to be received
    # Use a timeout to avoid waiting indefinitely
    max_wait = 60  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check if we received the webhook
        for webhook in webhook_received:
            if webhook['payload'].get('task_id') == task_id and webhook['payload'].get('status') == "completed":
                print("✅ Test PASSED: Webhook received for successful task completion")
                return True
        
        # Check if the task failed instead
        status = get_status_manager().get_status(task_id)
        if status.status == "failed":
            print(f"❌ Test FAILED: Task failed unexpectedly: {status.error_details}")
            return False
            
        # Wait a bit before checking again
        await asyncio.sleep(2)
        print(f"Waiting for webhook... ({int(time.time() - start_time)}s elapsed)")
    
    print("❌ Test FAILED: Webhook not received within timeout period")
    return False

async def test_webhook_failure():
    """Test webhook notification for failed task"""
    print("\n=== Test 2: Webhook for Failed Task ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    service = PodcastGeneratorService()
    webhook_url = f"http://localhost:{mock_server_port}/webhook"
    
    # Clear previous webhook data
    global webhook_received
    webhook_received = []
    
    # Create request with an invalid URL that will fail
    request = get_test_request(webhook_url, "https://nonexistent-url-that-will-fail-quickly.com")
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait for the task to fail and webhook to be received
    max_wait = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check if we received the webhook
        for webhook in webhook_received:
            if webhook['payload'].get('task_id') == task_id and webhook['payload'].get('status') == "failed":
                print("✅ Test PASSED: Webhook received for failed task")
                return True
        
        # Check status manually to see if we should keep waiting
        status = get_status_manager().get_status(task_id)
        if status.status == "failed" and time.time() - start_time > 15:
            # If the status is failed but we haven't received webhook after 15s, likely an issue
            print("❌ Test FAILED: Task failed but webhook not received")
            return False
            
        # Wait a bit before checking again
        await asyncio.sleep(2)
        print(f"Waiting for webhook... ({int(time.time() - start_time)}s elapsed)")
    
    print("❌ Test FAILED: Webhook not received within timeout period")
    return False

async def test_webhook_cancellation():
    """Test webhook notification for cancelled task"""
    print("\n=== Test 3: Webhook for Cancelled Task ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    service = PodcastGeneratorService()
    task_runner = get_task_runner()
    webhook_url = f"http://localhost:{mock_server_port}/webhook"
    
    # Clear previous webhook data
    global webhook_received
    webhook_received = []
    
    # Create request with a valid URL
    request = get_test_request(webhook_url)
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait a moment for the task to start, then cancel it
    await asyncio.sleep(3)
    cancelled = await task_runner.cancel_task(task_id)
    print(f"Cancellation requested: {cancelled}")
    
    if not cancelled:
        print("❌ Test FAILED: Could not cancel task")
        return False
    
    # Wait for the webhook notification
    max_wait = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check if we received the webhook
        for webhook in webhook_received:
            if webhook['payload'].get('task_id') == task_id and webhook['payload'].get('status') == "cancelled":
                print("✅ Test PASSED: Webhook received for cancelled task")
                return True
            
        # Wait a bit before checking again
        await asyncio.sleep(2)
        print(f"Waiting for webhook... ({int(time.time() - start_time)}s elapsed)")
    
    print("❌ Test FAILED: Webhook not received within timeout period")
    return False

async def test_webhook_invalid_url():
    """Test handling of invalid webhook URL (should not crash the task)"""
    print("\n=== Test 4: Invalid Webhook URL Handling ===\n")
    
    # Reset both task runner and asyncio executors to ensure fresh state
    await reset_all_executors()
    
    service = PodcastGeneratorService()
    
    # Create request with an invalid webhook URL
    request = get_test_request("http://nonexistent-server:9999/webhook")
    
    # Start async generation
    task_id = await service.generate_podcast_async(request)
    print(f"Started task: {task_id}")
    
    # Wait for the task to complete or fail
    max_wait = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check task status
        status = get_status_manager().get_status(task_id)
        
        # If the task completed or failed but didn't crash, that's success
        if status.status in ["completed", "failed"]:
            print(f"✅ Test PASSED: Task {status.status} despite invalid webhook URL")
            return True
            
        # Wait a bit before checking again
        await asyncio.sleep(2)
        print(f"Waiting for task to complete... ({int(time.time() - start_time)}s elapsed)")
    
    print("❌ Test FAILED: Task did not complete within timeout period")
    return False

async def main():
    """Run all webhook tests"""
    print("\n=== Starting Webhook Notification Tests ===\n")
    
    # Set up a mock webhook server
    runner = await setup_webhook_server()
    
    try:
        # Test webhook for successful task completion
        await test_webhook_success()
        
        # Test webhook for failed task
        await test_webhook_failure()
        
        # Test webhook for cancelled task
        await test_webhook_cancellation()
        
        # Test handling of invalid webhook URL
        await test_webhook_invalid_url()
        
    finally:
        # Clean up the mock server
        await runner.cleanup()
    
    print("\n=== All Webhook Tests Completed ===\n")

if __name__ == "__main__":
    asyncio.run(main())
