"""
Helper functions for testing async functionality.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.task_runner import TaskRunner, _task_runner, get_task_runner

def reset_task_runner():
    """
    Reset the global task runner instance with a fresh executor.
    This allows test functions to run sequentially without the "cannot schedule new futures after shutdown" error.
    Only meant to be used in test scripts.
    """
    global _task_runner
    
    # Create a new TaskRunner with fresh executor
    new_runner = TaskRunner(max_workers=4)
    
    # Update the global instance
    import app.task_runner
    app.task_runner._task_runner = new_runner
    
    return new_runner

async def reset_asyncio_executor():
    """Reset the asyncio event loop's default ThreadPoolExecutor to avoid shutdown errors in asyncio.to_thread calls"""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    # Get the current event loop
    loop = asyncio.get_running_loop()
    
    # Create a new default executor
    # The default executor is used by asyncio.to_thread
    new_executor = ThreadPoolExecutor()
    loop.set_default_executor(new_executor)
    
    print("Asyncio default executor reset")

async def reset_all_executors():
    """Reset both TaskRunner and asyncio executors - convenience function for tests"""
    reset_task_runner()
    await reset_asyncio_executor()
