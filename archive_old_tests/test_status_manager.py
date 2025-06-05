"""
Test script for StatusManager functionality.
Tests basic operations: create, update, get status.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.status_manager import get_status_manager
from app.podcast_models import PodcastStatus
import uuid


def test_status_manager():
    """Test basic StatusManager operations."""
    print("Testing StatusManager...")
    
    # Get the manager instance
    manager = get_status_manager()
    
    # Test 1: Create a new status
    print("\n1. Testing status creation...")
    task_id = str(uuid.uuid4())
    request_data = {
        "source_urls": ["https://example.com/article"],
        "prominent_persons": ["Einstein", "Feynman"],
        "desired_podcast_length_str": "5 minutes"
    }
    
    status = manager.create_status(task_id, request_data)
    print(f"✓ Created status with task_id: {task_id}")
    print(f"  Initial status: {status.status}")
    print(f"  Description: {status.status_description}")
    
    # Test 2: Retrieve the status
    print("\n2. Testing status retrieval...")
    retrieved = manager.get_status(task_id)
    assert retrieved is not None
    assert retrieved.task_id == task_id
    assert retrieved.status == "queued"
    print("✓ Successfully retrieved status")
    
    # Test 3: Update status with progress
    print("\n3. Testing status updates...")
    updated = manager.update_status(
        task_id, 
        "analyzing_sources",
        description="Extracting content from URLs",
        progress=15.0
    )
    assert updated.status == "analyzing_sources"
    assert updated.progress_percentage == 15.0
    print(f"✓ Updated to: {updated.status} ({updated.progress_percentage}%)")
    
    # Test 4: Update artifacts
    print("\n4. Testing artifact updates...")
    updated = manager.update_artifacts(
        task_id,
        source_content_extracted=True,
        source_analysis_complete=True
    )
    assert updated.artifacts.source_content_extracted == True
    assert updated.artifacts.source_analysis_complete == True
    print("✓ Artifacts updated successfully")
    
    # Test 5: Multiple status updates (simulate workflow)
    print("\n5. Testing workflow simulation...")
    steps = [
        ("researching_personas", "Creating persona profiles", 30.0),
        ("generating_outline", "Building podcast structure", 45.0),
        ("generating_dialogue", "Writing conversation script", 60.0),
        ("generating_audio_segments", "Converting to speech", 75.0),
        ("stitching_audio", "Creating final audio", 90.0),
        ("completed", "Podcast generation complete!", 100.0)
    ]
    
    for status_val, desc, progress in steps:
        manager.update_status(task_id, status_val, desc, progress)
        print(f"  → {status_val}: {progress}%")
    
    final_status = manager.get_status(task_id)
    print(f"✓ Final status: {final_status.status} ({final_status.progress_percentage}%)")
    
    # Test 6: Error handling
    print("\n6. Testing error handling...")
    error_task_id = str(uuid.uuid4())
    error_status = manager.create_status(error_task_id)
    manager.set_error(
        error_task_id,
        "Failed to extract content from URL",
        "ConnectionError: Unable to reach https://example.com"
    )
    
    error_retrieved = manager.get_status(error_task_id)
    assert error_retrieved.status == "failed"
    assert error_retrieved.error_message is not None
    print(f"✓ Error status set correctly: {error_retrieved.error_message}")
    
    # Test 7: List all statuses
    print("\n7. Testing list all statuses...")
    all_statuses = manager.list_all_statuses()
    print(f"✓ Total statuses in memory: {len(all_statuses)}")
    
    # Test 8: Cleanup
    print("\n8. Testing cleanup...")
    deleted = manager.delete_status(task_id)
    assert deleted == True
    assert manager.get_status(task_id) is None
    print("✓ Status deleted successfully")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_status_manager()
