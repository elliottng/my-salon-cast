"""
Background task runner for async podcast generation.
Handles running podcast generation tasks in the background using asyncio and ThreadPoolExecutor.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Callable, Any, List
import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


class TaskRunner:
    """Manages background task execution for podcast generation."""
    
    def __init__(self, max_workers: int = 3):
        """
        Initialize the task runner.
        
        Args:
            max_workers: Maximum number of concurrent podcast generation tasks
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._task_futures: Dict[str, asyncio.Future] = {}
        logger.info(f"TaskRunner initialized with max_workers={max_workers}")
    
    async def submit_task(
        self, 
        task_id: str, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> None:
        """
        Submit a function to run in the background.
        
        Args:
            task_id: Unique identifier for the task
            func: The function to run (should be the podcast generation function)
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
        """
        if task_id in self._running_tasks:
            raise ValueError(f"Task {task_id} is already running")
        
        # Create an asyncio task that runs the function in a thread pool
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(self._executor, func, *args, **kwargs)
        
        # Wrap the future in an asyncio task for better control
        task = asyncio.create_task(self._monitor_task(task_id, future))
        
        self._running_tasks[task_id] = task
        self._task_futures[task_id] = future
        
        logger.info(f"Task {task_id} submitted for background execution")
    
    async def _monitor_task(self, task_id: str, future: asyncio.Future) -> Any:
        """
        Monitor a running task and clean up when complete.
        
        Args:
            task_id: The task identifier
            future: The future representing the running task
        """
        try:
            result = await future
            logger.info(f"Task {task_id} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Task {task_id} failed with error: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        finally:
            # Clean up task references
            self._running_tasks.pop(task_id, None)
            self._task_futures.pop(task_id, None)
    
    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        return task_id in self._running_tasks
    
    def get_running_task_count(self) -> int:
        """Get the number of currently running tasks."""
        return len(self._running_tasks)
    
    def can_accept_new_task(self) -> bool:
        """Check if the runner can accept a new task."""
        return self.get_running_task_count() < self.max_workers
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Attempt to cancel a running task.
        
        Args:
            task_id: The task to cancel
            
        Returns:
            True if cancellation was initiated, False if task not found
        """
        if task_id not in self._running_tasks:
            return False
        
        task = self._running_tasks.get(task_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancellation requested for task {task_id}")
            return True
        
        return False
    
    def get_queue_status(self) -> dict:
        """
        Get current queue status information.
        
        Returns:
            Dict containing queue status metrics
        """
        active_count = sum(1 for task in self._running_tasks.values() if not task.done())
        
        return {
            "max_workers": self.max_workers,
            "active_tasks": active_count,
            "available_slots": self.max_workers - active_count,
            "total_submitted": len(self._running_tasks),
            "task_ids": list(self._running_tasks.keys())
        }
    
    def get_active_tasks(self) -> List[dict]:
        """
        Get information about currently active tasks.
        
        Returns:
            List of dicts with task information
        """
        active_tasks = []
        for task_id, task in self._running_tasks.items():
            if not task.done():
                active_tasks.append({
                    "task_id": task_id,
                    "running": task.running(),
                    "cancelled": task.cancelled()
                })
        return active_tasks
    
    def shutdown(self) -> None:
        """Shutdown the task runner and cleanup resources."""
        logger.info("Shutting down TaskRunner")
        self._executor.shutdown(wait=True)
        
        # Cancel any remaining tasks
        for task_id, task in self._running_tasks.items():
            if not task.done():
                task.cancel()
                logger.warning(f"Cancelled running task {task_id} during shutdown")


# Global task runner instance
_task_runner: Optional[TaskRunner] = None


def get_task_runner() -> TaskRunner:
    """Get or create the global task runner instance."""
    global _task_runner
    if _task_runner is None:
        _task_runner = TaskRunner()
    return _task_runner
