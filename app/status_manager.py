"""
Status Manager for tracking asynchronous podcast generation tasks.
Provides database-backed storage and management of PodcastStatus objects.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime
import json

from sqlmodel import Session, select
from app.podcast_models import PodcastStatus, PodcastProgressStatus, PodcastEpisode, ArtifactAvailability, PodcastRequest
from app.database import (
    PodcastStatusDB, 
    get_session, 
    serialize_to_json, 
    deserialize_from_json,
    init_db
)

logger = logging.getLogger(__name__)


class StatusManager:
    """
    Manages podcast generation task statuses with database persistence.
    Uses SQLModel for database operations.
    """
    
    def __init__(self):
        # Initialize database tables on startup
        init_db()
        logger.info("StatusManager initialized with database storage")
    
    def _db_to_model(self, db_status: PodcastStatusDB) -> PodcastStatus:
        """Convert database model to Pydantic model."""
        # Deserialize JSON fields
        request_data = deserialize_from_json(db_status.request_data)
        result_episode = deserialize_from_json(db_status.result_episode) if db_status.result_episode else None
        artifacts = deserialize_from_json(db_status.artifacts)
        logs = deserialize_from_json(db_status.logs)
        
        # Create PodcastRequest object if request_data exists
        podcast_request = PodcastRequest(**request_data) if request_data else None
        
        # Create PodcastEpisode object if result_episode exists
        podcast_episode = PodcastEpisode(**result_episode) if result_episode else None
        
        # Create ArtifactAvailability object
        artifact_availability = ArtifactAvailability(**artifacts) if artifacts else ArtifactAvailability()
        
        return PodcastStatus(
            task_id=db_status.task_id,
            status=db_status.status,
            progress_percentage=db_status.progress,
            status_description=db_status.status_description,
            created_at=db_status.created_at,
            last_updated_at=db_status.last_updated_at,
            request_data=podcast_request,
            result_episode=podcast_episode,
            error_message=db_status.error_message,
            error_details=db_status.error_details,
            artifacts=artifact_availability,
            logs=logs if isinstance(logs, list) else []
        )
    
    def _model_to_db(self, status: PodcastStatus) -> dict:
        """Convert Pydantic model to database fields."""
        return {
            "task_id": status.task_id,
            "status": status.status,
            "progress": status.progress_percentage,
            "status_description": status.status_description,
            "created_at": status.created_at,
            "last_updated_at": status.last_updated_at,
            "request_data": serialize_to_json(status.request_data),
            "result_episode": serialize_to_json(status.result_episode) if status.result_episode else None,
            "error_message": status.error_message,
            "error_details": status.error_details,
            "artifacts": serialize_to_json(status.artifacts),
            "logs": serialize_to_json(status.logs)
        }
    
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
        with get_session() as session:
            # Check if task_id already exists
            existing = session.get(PodcastStatusDB, task_id)
            if existing:
                raise ValueError(f"Task ID {task_id} already exists")
            
            # Create new status
            status = PodcastStatus(
                task_id=task_id,
                status="queued",
                status_description="Podcast generation task queued",
                request_data=request_data
            )
            
            # Convert to database model
            db_status = PodcastStatusDB(**self._model_to_db(status))
            
            # Save to database
            session.add(db_status)
            session.commit()
            
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
        with get_session() as session:
            db_status = session.get(PodcastStatusDB, task_id)
            if db_status:
                logger.debug(f"Retrieved status for task_id: {task_id} - Status: {db_status.status}")
                return self._db_to_model(db_status)
            else:
                logger.warning(f"No status found for task_id: {task_id}")
                return None
    
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
        with get_session() as session:
            db_status = session.get(PodcastStatusDB, task_id)
            if not db_status:
                logger.error(f"Cannot update status - task_id not found: {task_id}")
                return None
            
            # Update fields
            db_status.status = new_status
            if description:
                db_status.status_description = description
            if progress is not None:
                db_status.progress = progress
            db_status.last_updated_at = datetime.utcnow()
            
            # Add log entry
            logs = deserialize_from_json(db_status.logs) or []
            logs.append(f"{db_status.last_updated_at.isoformat()}Z - Status: {new_status}")
            db_status.logs = serialize_to_json(logs)
            
            session.add(db_status)
            session.commit()
            session.refresh(db_status)
            
            logger.info(f"Updated status for task_id: {task_id} - New status: {new_status}, Progress: {progress}%")
            return self._db_to_model(db_status)
    
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
        with get_session() as session:
            db_status = session.get(PodcastStatusDB, task_id)
            if not db_status:
                logger.error(f"Cannot update artifacts - task_id not found: {task_id}")
                return None
            
            # Get current artifacts
            artifacts = deserialize_from_json(db_status.artifacts) or {}
            
            # Update artifact fields
            for field, value in artifact_updates.items():
                artifacts[field] = value
                logger.debug(f"Updated artifact {field}={value} for task_id: {task_id}")
            
            db_status.artifacts = serialize_to_json(artifacts)
            db_status.last_updated_at = datetime.utcnow()
            
            session.add(db_status)
            session.commit()
            session.refresh(db_status)
            
            return self._db_to_model(db_status)
    
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
        with get_session() as session:
            db_status = session.get(PodcastStatusDB, task_id)
            if not db_status:
                logger.error(f"Cannot set error - task_id not found: {task_id}")
                return None
            
            db_status.status = "failed"
            db_status.status_description = "Task failed with error"
            db_status.error_message = error_message
            db_status.error_details = error_details
            db_status.last_updated_at = datetime.utcnow()
            
            # Add error to logs
            logs = deserialize_from_json(db_status.logs) or []
            logs.append(f"{db_status.last_updated_at.isoformat()}Z - ERROR: {error_message}")
            db_status.logs = serialize_to_json(logs)
            
            session.add(db_status)
            session.commit()
            session.refresh(db_status)
            
            logger.error(f"Set error status for task_id: {task_id} - Error: {error_message}")
            return self._db_to_model(db_status)
    
    def set_episode(self, task_id: str, episode: PodcastEpisode) -> Optional[PodcastStatus]:
        """
        Set the result episode for a completed task.
        
        Args:
            task_id: Task identifier to update
            episode: The completed PodcastEpisode object
            
        Returns:
            Updated PodcastStatus if found, None otherwise
        """
        with get_session() as session:
            db_status = session.get(PodcastStatusDB, task_id)
            if not db_status:
                logger.error(f"Cannot set episode - task_id not found: {task_id}")
                return None
            
            # Serialize the episode to JSON
            db_status.result_episode = serialize_to_json(episode)
            db_status.last_updated_at = datetime.utcnow()
            
            # Add log entry
            logs = deserialize_from_json(db_status.logs) or []
            logs.append(f"{db_status.last_updated_at.isoformat()}Z - Episode set: {episode.title}")
            db_status.logs = serialize_to_json(logs)
            
            session.add(db_status)
            session.commit()
            session.refresh(db_status)
            
            logger.info(f"Set episode for task_id: {task_id} - Title: {episode.title}")
            return self._db_to_model(db_status)
    
    def list_all_statuses(self, limit: int = 100, offset: int = 0) -> List[PodcastStatus]:
        """
        Get all current statuses with pagination.
        
        Args:
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of PodcastStatus objects
        """
        with get_session() as session:
            statement = select(PodcastStatusDB).offset(offset).limit(limit).order_by(PodcastStatusDB.created_at.desc())
            results = session.exec(statement).all()
            return [self._db_to_model(db_status) for db_status in results]
    
    def delete_status(self, task_id: str) -> bool:
        """
        Remove a status from storage (cleanup).
        
        Args:
            task_id: Task identifier to remove
            
        Returns:
            True if deleted, False if not found
        """
        with get_session() as session:
            db_status = session.get(PodcastStatusDB, task_id)
            if db_status:
                session.delete(db_status)
                session.commit()
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
