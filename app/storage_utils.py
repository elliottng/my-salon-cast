"""Storage utilities for common operations across the application."""

import os
import logging
from typing import Optional, Tuple


def parse_gs_url(gs_url: str) -> Optional[Tuple[str, str]]:
    """
    Parse a Google Cloud Storage URL into bucket and blob path.
    
    Args:
        gs_url: GS URL in format gs://bucket/path/to/file
        
    Returns:
        Tuple of (bucket_name, blob_path) if valid, None otherwise
    """
    if not gs_url.startswith("gs://"):
        return None
        
    try:
        parts = gs_url[5:].split("/", 1)
        if len(parts) != 2:
            return None
        return parts[0], parts[1]
    except Exception:
        return None


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        True if directory exists or was created, False on error
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Failed to create directory {directory_path}: {e}")
        return False


def log_storage_error(action: str, error: Exception, context: str = "") -> None:
    """
    Log storage-related errors with consistent format.
    
    Args:
        action: The action that failed (e.g., "download audio file")
        error: The exception that occurred
        context: Additional context information
    """
    message = f"Failed to {action}"
    if context:
        message += f" ({context})"
    message += f": {error}"
    logging.error(message)


def validate_storage_available(storage_manager, operation: str) -> bool:
    """
    Check if cloud storage is available and log appropriate error if not.
    
    Args:
        storage_manager: Storage manager instance with is_cloud_storage_available property
        operation: Description of the operation being attempted
        
    Returns:
        True if storage is available, False otherwise
    """
    if not storage_manager.is_cloud_storage_available:
        logging.error(f"Cloud Storage not available for {operation}")
        return False
    return True
