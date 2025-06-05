#!/usr/bin/env python3
"""
Test script for the async API endpoints using direct HTTP requests
"""
import asyncio
import aiohttp
import json
import logging
import sys
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Server URL
BASE_URL = "http://localhost:8080"

async def test_queue_status_endpoint():
    """Test the /queue/status endpoint"""
    logger.info("Testing /queue/status endpoint")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/queue/status") as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"Queue status: {json.dumps(result, indent=2)}")
                return result
            else:
                logger.error(f"Failed to get queue status: {response.status}")
                return None

async def test_task_cancellation(task_id):
    """Test the /status/{task_id}/cancel endpoint"""
    logger.info(f"Testing cancellation for task {task_id}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/status/{task_id}/cancel") as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"Cancellation result: {json.dumps(result, indent=2)}")
                return result
            else:
                logger.error(f"Failed to cancel task: {response.status}")
                return None

async def check_task_status(task_id):
    """Check the status of a task"""
    logger.info(f"Checking status for task {task_id}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/status/{task_id}") as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"Task status: {json.dumps(result, indent=2)}")
                return result
            else:
                logger.error(f"Failed to get task status: {response.status}")
                return None

async def submit_podcast_task():
    """Submit a new podcast generation task"""
    logger.info("Submitting new podcast generation task")
    
    request_data = {
        "source_urls": ["https://en.wikipedia.org/wiki/Python_(programming_language)"],
        "desired_podcast_length_str": "3-5 minutes",
        "webhook_url": "https://webhook.site/your-test-webhook-id"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BASE_URL}/generate/podcast_async/", 
            json=request_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                task_id = result.get("task_id")
                logger.info(f"Task submitted: {task_id}")
                return task_id
            else:
                logger.error(f"Failed to submit task: {response.status}")
                return None

async def main():
    """Run all API endpoint tests"""
    logger.info("Starting API endpoint tests")
    
    try:
        # 1. Check initial queue status
        await test_queue_status_endpoint()
        
        # 2. Submit a podcast generation task
        task_id = await submit_podcast_task()
        if not task_id:
            logger.error("Failed to get task ID, aborting test")
            return
        
        # 3. Check task status after a short delay
        await asyncio.sleep(2)
        await check_task_status(task_id)
        
        # 4. Check updated queue status
        await test_queue_status_endpoint()
        
        # 5. Cancel the task
        await test_task_cancellation(task_id)
        
        # 6. Check final task status
        await asyncio.sleep(2)
        await check_task_status(task_id)
        
        # 7. Check final queue status
        await test_queue_status_endpoint()
        
        logger.info("API endpoint tests completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
