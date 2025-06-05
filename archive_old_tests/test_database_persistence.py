#!/usr/bin/env python3
"""Test script to verify database persistence for StatusManager."""

import time
import json
from app.status_manager import get_status_manager
from app.podcast_models import PodcastRequest

def test_database_persistence():
    """Test that status data persists in the database."""
    print("Testing Database Persistence for StatusManager\n")
    
    # Get the status manager
    sm = get_status_manager()
    
    # Create a test request
    test_request = PodcastRequest(
        source_urls=["https://example.com/article1"],
        prominent_persons=["Test Person"],
        num_sections=3,
        section_length=120
    )
    
    # Test 1: Create a new status
    print("1. Creating new status...")
    task_id = "test_persist_001"
    
    # Clean up any existing status with this ID
    sm.delete_status(task_id)
    
    status = sm.create_status(task_id, test_request.dict())
    print(f"   Created status: {status.task_id}, Status: {status.status}")
    
    # Test 2: Update the status
    print("\n2. Updating status...")
    updated = sm.update_status(
        task_id, 
        "analyzing_sources", 
        "Analyzing content sources", 
        15.0
    )
    print(f"   Updated to: {updated.status}, Progress: {updated.progress_percentage}%")
    
    # Test 3: Update artifacts
    print("\n3. Updating artifacts...")
    updated = sm.update_artifacts(
        task_id,
        source_content_extracted=True,
        source_analysis_complete=True
    )
    print(f"   Artifacts: {json.dumps(updated.artifacts.dict(), indent=2)}")
    
    # Test 4: Simulate getting a new instance (like after restart)
    print("\n4. Simulating server restart - creating new StatusManager instance...")
    # Force new instance by clearing the singleton
    import app.status_manager
    app.status_manager._status_manager_instance = None
    
    # Get new instance
    sm2 = get_status_manager()
    print("   Got new StatusManager instance")
    
    # Test 5: Retrieve the status from the new instance
    print("\n5. Retrieving status from new instance...")
    retrieved = sm2.get_status(task_id)
    if retrieved:
        print(f"   Retrieved status: {retrieved.task_id}")
        print(f"   Status: {retrieved.status}")
        print(f"   Progress: {retrieved.progress_percentage}%")
        print(f"   Artifacts: {json.dumps(retrieved.artifacts.dict(), indent=2)}")
        print("   SUCCESS: Data persisted across instances!")
    else:
        print("   FAILED: Status not found after restart")
    
    # Test 6: List all statuses
    print("\n6. Listing all statuses...")
    all_statuses = sm2.list_all_statuses(limit=10)
    print(f"   Found {len(all_statuses)} status(es)")
    for s in all_statuses:
        print(f"   - {s.task_id}: {s.status} ({s.progress_percentage}%)")
    
    # Test 7: Error handling
    print("\n7. Testing error handling...")
    sm2.set_error(task_id, "Test error message", "Detailed error traceback")
    error_status = sm2.get_status(task_id)
    print(f"   Status: {error_status.status}")
    print(f"   Error: {error_status.error_message}")
    
    # Test 8: Clean up
    print("\n8. Cleaning up...")
    deleted = sm2.delete_status(task_id)
    print(f"   Deleted: {deleted}")
    
    # Verify deletion
    verify = sm2.get_status(task_id)
    if verify is None:
        print("   Successfully deleted")
    else:
        print("   Failed to delete")
    
    print("\nAll database persistence tests completed!")

if __name__ == "__main__":
    test_database_persistence()
