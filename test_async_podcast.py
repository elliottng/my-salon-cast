#!/usr/bin/env python3
"""
Test script for async podcast generation functionality.
Tests both sync and async modes to ensure backwards compatibility.
"""

import asyncio
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest
from app.status_manager import get_status_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sync_mode():
    """Test the synchronous mode (backwards compatibility)."""
    logger.info("=== Testing SYNC mode ===")
    
    generator = PodcastGeneratorService()
    
    request = PodcastRequest(
        source_urls=["https://example.com/test"],
        prominent_persons=["Test Person"],
        desired_podcast_length_str="5 minutes"
    )
    
    start_time = time.time()
    
    try:
        # This should block until completion
        episode = await generator.generate_podcast_from_source(request)
        elapsed = time.time() - start_time
        
        logger.info(f"Sync mode completed in {elapsed:.2f} seconds")
        logger.info(f"Episode title: {episode.title}")
        
        return True
    except Exception as e:
        logger.error(f"Sync mode failed: {e}")
        return False


async def test_async_mode():
    """Test the asynchronous mode with background processing."""
    logger.info("\n=== Testing ASYNC mode ===")
    
    generator = PodcastGeneratorService()
    status_manager = get_status_manager()
    
    request = PodcastRequest(
        source_urls=["https://example.com/test"],
        prominent_persons=["Test Person"],
        desired_podcast_length_str="5 minutes"
    )
    
    start_time = time.time()
    
    try:
        # This should return immediately
        task_id = await generator.generate_podcast_async(request)
        elapsed = time.time() - start_time
        
        logger.info(f"Async mode returned task_id in {elapsed:.2f} seconds")
        logger.info(f"Task ID: {task_id}")
        
        # Check status immediately
        status = status_manager.get_status(task_id)
        if status:
            logger.info(f"Initial status: {status.status} ({status.progress_percentage}%)")
            logger.info(f"Status message: {status.status_message}")
        
        # Poll status a few times
        for i in range(5):
            await asyncio.sleep(2)
            status = status_manager.get_status(task_id)
            if status:
                logger.info(f"Status after {(i+1)*2}s: {status.status} ({status.progress_percentage}%)")
                if status.status == "completed":
                    logger.info("Task completed!")
                    break
                elif status.status == "failed":
                    logger.error(f"Task failed: {status.error_details}")
                    break
        
        return True
    except Exception as e:
        logger.error(f"Async mode failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting async podcast generation tests...")
    
    # Test sync mode
    sync_success = await test_sync_mode()
    
    # Test async mode
    async_success = await test_async_mode()
    
    # Summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Sync mode: {'PASSED' if sync_success else 'FAILED'}")
    logger.info(f"Async mode: {'PASSED' if async_success else 'FAILED'}")
    
    return sync_success and async_success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
