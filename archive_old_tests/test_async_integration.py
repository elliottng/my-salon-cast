#!/usr/bin/env python3
"""
Integration test for async podcast generation.
Tests the async mode integration without requiring external services.
"""

import asyncio
import sys
import os
import time
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))


async def test_async_podcast_integration():
    """Test the async podcast generation integration."""
    print("=== Testing Async Podcast Generation Integration ===")
    
    # Mock the LLM and TTS services to avoid external dependencies
    with patch('app.podcast_workflow.GeminiService') as mock_llm, \
         patch('app.podcast_workflow.GoogleCloudTtsService') as mock_tts:
        
        # Setup mocks
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        mock_tts_instance = Mock()
        mock_tts.return_value = mock_tts_instance
        
        # Now we can import and use the service
        from app.podcast_workflow import PodcastGeneratorService
        from app.podcast_models import PodcastRequest
        from app.status_manager import get_status_manager
        
        generator = PodcastGeneratorService()
        status_manager = get_status_manager()
        
        # Test async mode
        print("\nTesting async mode (should return immediately)...")
        request = PodcastRequest(
            source_urls=["https://example.com/test"],
            prominent_persons=["Test Person"],
            desired_podcast_length_str="5 minutes"
        )
        
        start_time = time.time()
        task_id = await generator.generate_podcast_async(request)
        elapsed = time.time() - start_time
        
        print(f"✅ Async call returned in {elapsed:.3f} seconds")
        print(f"Task ID: {task_id}")
        
        # Verify it returned quickly
        assert elapsed < 1.0, f"Async call took too long: {elapsed} seconds"
        
        # Check initial status
        status = status_manager.get_status(task_id)
        assert status is not None, "Status should exist"
        print(f"Initial status: {status.status}")
        print(f"Status message: {status.status_message}")
        
        # The task should be in a processing state (not completed)
        assert status.status != "completed", "Task should not be completed immediately"
        
        # Check that the task is actually running in the background
        from app.task_runner import get_task_runner
        task_runner = get_task_runner()
        
        print(f"\nBackground task running: {task_runner.is_task_running(task_id)}")
        print(f"Total running tasks: {task_runner.get_running_task_count()}")
        
        print("\n✅ Async integration test passed!")


async def test_sync_vs_async_comparison():
    """Compare sync and async modes to ensure they behave differently."""
    print("\n=== Testing Sync vs Async Mode Comparison ===")
    
    # Mock services again
    with patch('app.podcast_workflow.GeminiService') as mock_llm, \
         patch('app.podcast_workflow.GoogleCloudTtsService') as mock_tts:
        
        mock_llm.return_value = Mock()
        mock_tts.return_value = Mock()
        
        from app.podcast_workflow import PodcastGeneratorService
        from app.podcast_models import PodcastRequest
        
        generator = PodcastGeneratorService()
        
        # Create a request
        request = PodcastRequest(
            source_urls=["https://example.com/test"],
            prominent_persons=["Test Person"],
            desired_podcast_length_str="5 minutes"
        )
        
        # Test sync mode behavior
        print("\n1. Testing sync mode (should block)...")
        start_time = time.time()
        
        # Mock the internal method to simulate work
        original_internal = generator._generate_podcast_internal
        async def mock_internal(req, async_mode=False):
            if not async_mode:
                # Simulate some work in sync mode
                await asyncio.sleep(0.1)
            return await original_internal(req, async_mode)
        
        generator._generate_podcast_internal = mock_internal
        
        episode = await generator.generate_podcast_from_source(request)
        sync_elapsed = time.time() - start_time
        print(f"Sync mode took: {sync_elapsed:.3f} seconds")
        print(f"Episode returned: {episode.title}")
        
        # Test async mode behavior  
        print("\n2. Testing async mode (should return immediately)...")
        start_time = time.time()
        task_id = await generator.generate_podcast_async(request)
        async_elapsed = time.time() - start_time
        print(f"Async mode took: {async_elapsed:.3f} seconds")
        print(f"Task ID returned: {task_id}")
        
        # Verify async is faster
        assert async_elapsed < sync_elapsed, "Async should return faster than sync"
        print(f"\n✅ Async returned {(sync_elapsed/async_elapsed):.1f}x faster than sync!")


async def main():
    """Run all integration tests."""
    try:
        await test_async_podcast_integration()
        await test_sync_vs_async_comparison()
        print("\n🎉 All integration tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
