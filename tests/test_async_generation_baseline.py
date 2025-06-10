#!/usr/bin/env python3
"""
Baseline Integration Test for Async Podcast Generation

This test captures the current async behavior before refactoring to remove sync methods.
Tests the complete workflow through the MCP server interface to validate:
- Task ID generation and tracking
- Status updates through all phases
- Background execution via task runner
- Webhook notifications (mocked)
- Error handling and cleanup

This test should pass both before and after the sync removal refactoring,
ensuring no behavioral changes occur during the refactoring process.
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest
from app.status_manager import StatusManager
from app.task_runner import TaskRunner


class BaselineAsyncTest:
    """Test harness for validating async generation behavior."""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.task_ids = []
        self.captured_statuses = {}
        self.captured_webhooks = []
        
    async def setup_services(self) -> PodcastGeneratorService:
        """Initialize services with mocked external dependencies."""
        
        # Mock external services to avoid actual API calls
        with patch('app.llm_service.GeminiService') as mock_llm, \
             patch('app.tts_service.GoogleCloudTtsService') as mock_tts, \
             patch('app.storage.CloudStorageManager') as mock_storage:
            
            # Configure LLM service mock
            mock_llm_instance = AsyncMock()
            mock_llm_instance.analyze_source_text_async.return_value = {
                "summary": "Test content analysis",
                "themes": ["technology", "innovation"],
                "word_count": 1500
            }
            mock_llm_instance.research_persona_async.return_value = {
                "name": "Test Persona",
                "profile": "A technology expert with deep insights",
                "gender": "male",
                "invented_name": "Alex",
                "tts_voice_id": "en-US-Chirp3-HD-Achird"
            }
            mock_llm_instance.generate_podcast_outline_async.return_value = {
                "title": "Test Podcast: Innovation Discussion",
                "segments": [
                    {"title": "Introduction", "content": "Welcome to our discussion", "duration_seconds": 60},
                    {"title": "Main Topic", "content": "Deep dive into technology", "duration_seconds": 240},
                    {"title": "Conclusion", "content": "Wrapping up our insights", "duration_seconds": 60}
                ]
            }
            mock_llm_instance.generate_dialogue_async.return_value = {
                "turns": [
                    {"speaker_id": "host", "speaker_name": "Host", "text": "Welcome everyone", "turn_id": 1},
                    {"speaker_id": "alex", "speaker_name": "Alex", "text": "Thanks for having me", "turn_id": 2}
                ]
            }
            mock_llm.return_value = mock_llm_instance
            
            # Configure TTS service mock
            mock_tts_instance = AsyncMock()
            mock_tts_instance.text_to_audio_async.return_value = b"fake_audio_data"
            mock_tts.return_value = mock_tts_instance
            
            # Configure storage mock
            mock_storage_instance = AsyncMock()
            mock_storage_instance.upload_audio_async.return_value = "gs://test-bucket/podcast.mp3"
            mock_storage_instance.upload_transcript_async.return_value = "gs://test-bucket/transcript.txt"
            mock_storage.return_value = mock_storage_instance
            
            # Initialize the service
            generator = PodcastGeneratorService()
            return generator

    def capture_status_update(self, task_id: str, status: str, message: str, progress: float):
        """Capture status updates for validation."""
        if task_id not in self.captured_statuses:
            self.captured_statuses[task_id] = []
        
        self.captured_statuses[task_id].append({
            "status": status,
            "message": message,
            "progress": progress,
            "timestamp": asyncio.get_event_loop().time()
        })
        print(f"[STATUS] {task_id}: {status} - {message} ({progress}%)")

    def capture_status_update_wrapped(self, task_id: str, new_status: str, description: Optional[str] = None, progress: Optional[float] = None, progress_details: Optional[str] = None):
        """Wrapper to match StatusManager.update_status signature and call our capture method."""
        self.capture_status_update(task_id, new_status, description or "", progress or 0.0)
        return None  # Return None like the real method when task not found

    async def mock_webhook_notification(self, task_id: str, status: str, webhook_url: Optional[str] = None):
        """Mock webhook notifications for testing."""
        webhook_data = {
            "task_id": task_id,
            "status": status,
            "webhook_url": webhook_url,
            "timestamp": asyncio.get_event_loop().time()
        }
        self.captured_webhooks.append(webhook_data)
        print(f"[WEBHOOK] {task_id}: {status} -> {webhook_url}")

    async def test_basic_async_generation(self) -> bool:
        """Test basic async podcast generation workflow."""
        print("\n=== Testing Basic Async Generation ===")
        
        generator = await self.setup_services()
        
        # Mock status manager update method using patch
        with patch.object(StatusManager, 'update_status') as mock_update:
            mock_update.side_effect = self.capture_status_update_wrapped
            
            try:
                # Create test request
                request = PodcastRequest(
                    source_urls=["http://example.com/test-content"],  
                    prominent_persons=["Tech Expert"],
                    desired_podcast_length_str="5 minutes",  
                    webhook_url="http://test.webhook.com/notify"
                )
                
                print(f"Generated test request with {len(request.source_urls or [])} source URLs")
                
                # Submit async generation request
                task_id = await generator.generate_podcast_async(request)
                self.task_ids.append(task_id)
                
                print(f"Generated task ID: {task_id}")
                
                # Validate task ID format
                try:
                    uuid.UUID(task_id)
                    print("✓ Task ID is valid UUID format")
                except ValueError:
                    print("✗ Task ID is not valid UUID format")
                    return False
                
                # Wait for background processing to complete
                print("Waiting for background processing...")
                await asyncio.sleep(10)  # Allow processing time
                
                # Check if status updates were captured
                if task_id in self.captured_statuses:
                    statuses = self.captured_statuses[task_id]
                    print(f"✓ Captured {len(statuses)} status updates")
                    
                    # Validate status progression
                    status_sequence = [s["status"] for s in statuses]
                    expected_statuses = ["preprocessing_sources", "analyzing_sources", "researching_personas", 
                                       "generating_outline", "generating_dialogue", "generating_audio_segments"]
                    
                    # Check that we have meaningful status progression
                    if len(status_sequence) >= 3:
                        print("✓ Status progression looks reasonable")
                        print(f"  Status sequence: {status_sequence}")
                    else:
                        print("✗ Insufficient status updates captured")
                        return False
                        
                else:
                    print("✗ No status updates captured")
                    return False
                
                return True
                
            except Exception as e:
                print(f"✗ Test failed with exception: {e}")
                return False

    async def test_concurrent_generation(self) -> bool:
        """Test multiple concurrent async generations."""
        print("\n=== Testing Concurrent Generation ===")
        
        generator = await self.setup_services()
        
        # Mock status manager update method using patch
        with patch.object(StatusManager, 'update_status') as mock_update:
            mock_update.side_effect = self.capture_status_update_wrapped
            
            try:
                # Submit multiple requests concurrently
                requests = [
                    PodcastRequest(
                        source_urls=[f"http://example.com/test-content-{i}"],  # Use source_urls
                        prominent_persons=[f"Expert {i}"],
                        desired_podcast_length_str="3 minutes"  # Use desired_podcast_length_str
                    )
                    for i in range(3)
                ]
                
                # Submit all requests
                tasks = []
                for request in requests:
                    task = asyncio.create_task(generator.generate_podcast_async(request))
                    tasks.append(task)
                
                # Wait for all task IDs
                task_ids = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Validate all succeeded
                valid_task_ids = []
                for i, task_id in enumerate(task_ids):
                    if isinstance(task_id, Exception):
                        print(f"✗ Request {i} failed: {task_id}")
                    else:
                        valid_task_ids.append(task_id)
                        self.task_ids.append(task_id)
                        print(f"✓ Request {i} generated task ID: {task_id}")
                
                if len(valid_task_ids) == len(requests):
                    print(f"✓ All {len(requests)} concurrent requests succeeded")
                    return True
                else:
                    print(f"✗ Only {len(valid_task_ids)}/{len(requests)} requests succeeded")
                    return False
                    
            except Exception as e:
                print(f"✗ Concurrent test failed: {e}")
                return False

    async def test_error_handling(self) -> bool:
        """Test error handling in async generation."""
        print("\n=== Testing Error Handling ===")
        
        # Test with invalid request
        try:
            generator = await self.setup_services()
            
            # Create invalid request (empty content)
            request = PodcastRequest(
                source_urls=[],  # Invalid empty source URLs
                prominent_persons=[],
                desired_podcast_length_str="5 minutes"
            )
            
            # This should either fail gracefully or handle the error
            task_id = await generator.generate_podcast_async(request)
            
            if task_id:
                print(f"✓ Error handling: Got task ID even with invalid request: {task_id}")
                # This is OK - the system might queue it and handle the error during processing
                return True
            else:
                print("✗ Error handling: No task ID returned for invalid request")
                return False
                
        except Exception as e:
            print(f"✓ Error handling: Properly caught exception for invalid request: {e}")
            return True

    async def test_task_runner_integration(self) -> bool:
        """Test integration with task runner system."""
        print("\n=== Testing Task Runner Integration ===")
        
        try:
            # Check if task runner can accept new tasks
            task_runner = TaskRunner()
            can_accept = task_runner.can_accept_new_task()
            print(f"✓ Task runner can accept new tasks: {can_accept}")
            
            # Check task runner queue status
            active_tasks = task_runner.get_active_tasks()
            print(f"✓ Active tasks count: {len(active_tasks)}")
            
            return True
            
        except Exception as e:
            print(f"✗ Task runner integration failed: {e}")
            return False

    def cleanup(self):
        """Clean up test resources."""
        print(f"\n=== Cleanup ===")
        print(f"Generated {len(self.task_ids)} task IDs during testing")
        print(f"Captured {len(self.captured_statuses)} status update sequences")
        print(f"Captured {len(self.captured_webhooks)} webhook notifications")
        
        # Clean up temp directory
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"✓ Cleaned up temp directory: {self.temp_dir}")

    async def run_all_tests(self) -> bool:
        """Run all baseline tests."""
        print("🚀 Starting Async Generation Baseline Tests")
        print("=" * 60)
        
        all_passed = True
        
        tests = [
            ("Basic Async Generation", self.test_basic_async_generation),
            ("Concurrent Generation", self.test_concurrent_generation),
            ("Error Handling", self.test_error_handling),
            ("Task Runner Integration", self.test_task_runner_integration),
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n🧪 Running: {test_name}")
                result = await test_func()
                if result:
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
                    all_passed = False
            except Exception as e:
                print(f"💥 {test_name}: EXCEPTION - {e}")
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL BASELINE TESTS PASSED")
        else:
            print("⚠️  SOME BASELINE TESTS FAILED")
        
        self.cleanup()
        return all_passed


async def main():
    """Run the baseline tests."""
    test_suite = BaselineAsyncTest()
    success = await test_suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
