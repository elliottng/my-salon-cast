#!/usr/bin/env python3
"""
Minimal test to verify async task runner functionality.
This test focuses on the task runner mechanics without requiring full podcast generation.
"""

import asyncio
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.task_runner import get_task_runner


async def mock_long_running_task(task_id: str, duration: int) -> str:
    """Mock task that simulates work by sleeping."""
    print(f"Task {task_id}: Starting work (will take {duration} seconds)")
    await asyncio.sleep(duration)
    print(f"Task {task_id}: Work completed!")
    return f"Result from task {task_id}"


def sync_wrapper(task_id: str, duration: int) -> str:
    """Synchronous wrapper for the async task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(mock_long_running_task(task_id, duration))
    finally:
        loop.close()


async def test_task_runner():
    """Test the TaskRunner functionality."""
    print("=== Testing TaskRunner ===")
    
    task_runner = get_task_runner()
    
    # Test 1: Submit a single task
    print("\nTest 1: Single task submission")
    task_id_1 = "test-task-1"
    
    start_time = time.time()
    await task_runner.submit_task(task_id_1, sync_wrapper, task_id_1, 3)
    submit_time = time.time() - start_time
    
    print(f"Task submitted in {submit_time:.3f} seconds (should be nearly instant)")
    assert submit_time < 0.5, "Task submission should be nearly instant"
    
    # Check if task is running
    is_running = task_runner.is_task_running(task_id_1)
    print(f"Task {task_id_1} is running: {is_running}")
    assert is_running, "Task should be running"
    
    # Test 2: Try to submit duplicate task
    print("\nTest 2: Duplicate task rejection")
    try:
        await task_runner.submit_task(task_id_1, sync_wrapper, task_id_1, 3)
        print("ERROR: Duplicate task was accepted!")
        assert False, "Should not accept duplicate task"
    except ValueError as e:
        print(f"Good: Duplicate task rejected with error: {e}")
    
    # Test 3: Check concurrent task limit
    print("\nTest 3: Concurrent task limits")
    print(f"Max workers: {task_runner.max_workers}")
    print(f"Running tasks: {task_runner.get_running_task_count()}")
    print(f"Can accept new task: {task_runner.can_accept_new_task()}")
    
    # Submit tasks up to the limit
    task_ids = []
    for i in range(2, task_runner.max_workers + 1):
        if task_runner.can_accept_new_task():
            task_id = f"test-task-{i}"
            await task_runner.submit_task(task_id, sync_wrapper, task_id, 5)
            task_ids.append(task_id)
            print(f"Submitted {task_id}, running tasks: {task_runner.get_running_task_count()}")
    
    # Try to submit one more (should be at capacity)
    print("\nTest 4: Capacity check")
    print(f"Can accept new task: {task_runner.can_accept_new_task()}")
    assert not task_runner.can_accept_new_task(), "Should be at capacity"
    
    # Wait a bit for first task to complete
    print("\nWaiting for first task to complete...")
    await asyncio.sleep(4)
    
    # Check if we can accept new tasks now
    print(f"After waiting, can accept new task: {task_runner.can_accept_new_task()}")
    
    # Test 5: Task cancellation
    print("\nTest 5: Task cancellation")
    if task_ids:
        cancel_task_id = task_ids[0]
        cancelled = await task_runner.cancel_task(cancel_task_id)
        print(f"Attempted to cancel {cancel_task_id}: {cancelled}")
    
    # Clean up - wait for remaining tasks
    print("\nWaiting for all tasks to complete...")
    await asyncio.sleep(6)
    
    print(f"\nFinal running task count: {task_runner.get_running_task_count()}")
    print("All tests completed!")


async def main():
    """Run the test."""
    try:
        await test_task_runner()
        print("\n✅ All tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
