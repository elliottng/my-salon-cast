"""
Test script to verify status tracking in podcast workflow.
This tests both sync and async podcast generation methods.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest
from app.status_manager import get_status_manager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_sync_workflow():
    """Test the synchronous workflow (backwards compatible)."""
    print("\nTesting Synchronous Workflow (Backwards Compatible)...")
    
    # Initialize service
    generator = PodcastGeneratorService()
    
    # Create a simple request
    request = PodcastRequest(
        source_urls=["https://en.wikipedia.org/wiki/Artificial_intelligence"],
        prominent_persons=["Alan Turing"],
        desired_podcast_length_str="3 minutes"
    )
    
    print("\n1. Starting podcast generation (sync mode)...")
    
    # Call sync method - returns PodcastEpisode directly
    episode = await generator.generate_podcast_from_source(request)
    
    print(f"\n✓ Got episode directly (no task_id in sync mode)")
    print(f"  - Title: {episode.title}")
    print(f"  - Summary: {episode.summary[:100]}...")
    if episode.warnings:
        print(f"  - Warnings: {episode.warnings}")
    
    print("\n✅ Sync workflow test complete!")


async def test_async_workflow():
    """Test the asynchronous workflow with status tracking."""
    print("\n\nTesting Asynchronous Workflow...")
    
    # Initialize service
    generator = PodcastGeneratorService()
    status_manager = get_status_manager()
    
    # Create a simple request
    request = PodcastRequest(
        source_urls=["https://en.wikipedia.org/wiki/Machine_learning"],
        prominent_persons=["Geoffrey Hinton"],
        desired_podcast_length_str="2 minutes"
    )
    
    print("\n1. Starting podcast generation (async mode)...")
    
    # Call async method - returns task_id immediately
    task_id = await generator.generate_podcast_async(request)
    
    print(f"\n✓ Got task_id immediately: {task_id}")
    
    # Check status
    print("\n2. Checking status...")
    status = status_manager.get_status(task_id)
    
    if status:
        print(f"✓ Status found!")
        print(f"  - Current state: {status.status}")
        print(f"  - Description: {status.status_description}")
        print(f"  - Progress: {status.progress_percentage}%")
        print(f"  - Request data stored: {'Yes' if status.request_data else 'No'}")
        
        # Note: In current implementation, generation is still synchronous
        # In future Phase 4, this would return immediately and we'd poll for completion
        if status.result_episode:
            print(f"\n3. Episode completed:")
            print(f"  - Title: {status.result_episode.title}")
            print(f"  - Summary: {status.result_episode.summary[:100]}...")
    else:
        print("✗ No status found for task_id")
    
    print("\n✅ Async workflow test complete!")


async def test_error_handling_both_modes():
    """Test error handling in both sync and async modes."""
    print("\n\nTesting Error Handling in Both Modes...")
    
    # Create service with broken LLM
    generator = PodcastGeneratorService()
    generator.llm_service = None  # Force error
    status_manager = get_status_manager()
    
    request = PodcastRequest(
        source_urls=["https://example.com"],
        prominent_persons=["Test Person"],
        desired_podcast_length_str="5 minutes"
    )
    
    # Test sync mode error
    print("\n1. Testing sync mode error handling...")
    episode = await generator.generate_podcast_from_source(request)
    print(f"✓ Sync mode returned error episode: {episode.title}")
    
    # Test async mode error
    print("\n2. Testing async mode error handling...")
    task_id = await generator.generate_podcast_async(request)
    status = status_manager.get_status(task_id)
    if status and status.status == "failed":
        print(f"✓ Async mode captured error in status:")
        print(f"  - Error: {status.error_message}")
    
    print("\n✅ Error handling test complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("PODCAST WORKFLOW SYNC/ASYNC TEST")
    print("=" * 60)
    
    asyncio.run(test_sync_workflow())
    asyncio.run(test_async_workflow()) 
    asyncio.run(test_error_handling_both_modes())
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
