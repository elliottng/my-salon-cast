"""
Status Manager for tracking asynchronous podcast generation tasks.
Provides in-memory storage and management of PodcastStatus objects.
"""

import logging
from typing import Dict, Optional
from threading import Lock
from datetime import datetime

from app.podcast_models import PodcastStatus, PodcastProgressStatus

logger = logging.getLogger(__name__)


class StatusManager:
    """
    Manages podcast generation task statuses in memory.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self):
        self._statuses: Dict[str, PodcastStatus] = {}
        self._lock = Lock()
        logger.info("StatusManager initialized with in-memory storage")
    
    def create_status(self, task_id: str, request_data: Optional[dict] = None) -> PodcastStatus:
        """
        Create a new podcast generation status.
        
        Args:
            task_id: Unique identifier for the task
            request_data: Original request data (optional)
            
        Returns:
            Newly created PodcastStatus object
            
        Raises:
            ValueError: If task_id already exists
        """
        with self._lock:
            if task_id in self._statuses:
                raise ValueError(f"Task ID {task_id} already exists")
            
            status = PodcastStatus(
                task_id=task_id,
                status="queued",
                status_description="Podcast generation task queued",
                request_data=request_data
            )
            
            self._statuses[task_id] = status
            logger.info(f"Created new status for task_id: {task_id}")
            return status
    
    def get_status(self, task_id: str) -> Optional[PodcastStatus]:
        """
        Retrieve status for a given task ID.
        
        Args:
            task_id: Task identifier to look up
            
        Returns:
            PodcastStatus if found, None otherwise
        """
        with self._lock:
            status = self._statuses.get(task_id)
            if status:
                logger.debug(f"Retrieved status for task_id: {task_id} - Status: {status.status}")
            else:
                logger.warning(f"No status found for task_id: {task_id}")
            return status
    
    def update_status(
        self, 
        task_id: str, 
        new_status: PodcastProgressStatus,
        description: Optional[str] = None,
        progress: Optional[float] = None
    ) -> Optional[PodcastStatus]:
        """
        Update the status of an existing task.
        
        Args:
            task_id: Task identifier to update
            new_status: New status value
            description: Optional status description
            progress: Optional progress percentage (0-100)
            
        Returns:
            Updated PodcastStatus if found, None otherwise
        """
        with self._lock:
            status = self._statuses.get(task_id)
            if not status:
                logger.error(f"Cannot update status - task_id not found: {task_id}")
                return None
            
            # Use the built-in update method
            status.update_status(new_status, description, progress)
            
            logger.info(f"Updated status for task_id: {task_id} - New status: {new_status}, Progress: {progress}%")
            return status
    
    def update_artifacts(self, task_id: str, **artifact_updates) -> Optional[PodcastStatus]:
        """
        Update artifact availability flags.
        
        Args:
            task_id: Task identifier to update
            **artifact_updates: Keyword arguments for artifact flags
                               (e.g., source_content_extracted=True)
            
        Returns:
            Updated PodcastStatus if found, None otherwise
        """
        with self._lock:
            status = self._statuses.get(task_id)
            if not status:
                logger.error(f"Cannot update artifacts - task_id not found: {task_id}")
                return None
            
            # Update artifact fields
            for field, value in artifact_updates.items():
                if hasattr(status.artifacts, field):
                    setattr(status.artifacts, field, value)
                    logger.debug(f"Updated artifact {field}={value} for task_id: {task_id}")
                else:
                    logger.warning(f"Unknown artifact field: {field}")
            
            status.last_updated_at = datetime.utcnow()
            return status
    
    def set_error(self, task_id: str, error_message: str, error_details: Optional[str] = None) -> Optional[PodcastStatus]:
        """
        Set error status and details for a task.
        
        Args:
            task_id: Task identifier to update
            error_message: User-friendly error message
            error_details: Technical error details (e.g., traceback)
            
        Returns:
            Updated PodcastStatus if found, None otherwise
        """
        with self._lock:
            status = self._statuses.get(task_id)
            if not status:
                logger.error(f"Cannot set error - task_id not found: {task_id}")
                return None
            
            status.status = "failed"
            status.status_description = "Task failed with error"
            status.error_message = error_message
            status.error_details = error_details
            status.last_updated_at = datetime.utcnow()
            status.logs.append(f"{status.last_updated_at.isoformat()}Z - ERROR: {error_message}")
            
            logger.error(f"Set error status for task_id: {task_id} - Error: {error_message}")
            return status
    
    def list_all_statuses(self) -> Dict[str, PodcastStatus]:
        """
        Get all current statuses (for debugging/monitoring).
        
        Returns:
            Dictionary of all task_id -> PodcastStatus mappings
        """
        with self._lock:
            return self._statuses.copy()
    
    def delete_status(self, task_id: str) -> bool:
        """
        Remove a status from storage (cleanup).
        
        Args:
            task_id: Task identifier to remove
            
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if task_id in self._statuses:
                del self._statuses[task_id]
                logger.info(f"Deleted status for task_id: {task_id}")
                return True
            logger.warning(f"Cannot delete - task_id not found: {task_id}")
            return False


# Global singleton instance
_status_manager_instance = None


def get_status_manager() -> StatusManager:
    """
    Get the global StatusManager instance (singleton pattern).
    
    Returns:
        The StatusManager instance
    """
    global _status_manager_instance
    if _status_manager_instance is None:
        _status_manager_instance = StatusManager()
    return _status_manager_instance
