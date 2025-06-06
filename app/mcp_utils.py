"""MCP server utilities for common operations."""

import json
import logging
from typing import Optional, Dict, Any
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)


def validate_task_id(task_id: str) -> None:
    """
    Validate task ID format.
    
    Args:
        task_id: Task identifier to validate
        
    Raises:
        ToolError: If task_id is invalid
    """
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError(f"Invalid task_id format: {task_id}")


def validate_person_id(person_id: str) -> None:
    """
    Validate person ID format.
    
    Args:
        person_id: Person identifier to validate
        
    Raises:
        ToolError: If person_id is invalid
    """
    if not person_id or not person_id.strip():
        raise ToolError("person_id is required")
        

async def download_and_parse_json(
    storage_manager,
    file_path: str,
    resource_type: str
) -> Optional[Dict[str, Any]]:
    """
    Download and parse JSON content from storage.
    
    Args:
        storage_manager: CloudStorageManager instance
        file_path: Path to the JSON file
        resource_type: Type of resource for logging (e.g., "outline", "persona research")
        
    Returns:
        Parsed JSON data if successful, None otherwise
    """
    try:
        content = await storage_manager.download_text_file_async(file_path)
        
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {resource_type} JSON: {e}")
                return None
        else:
            logger.warning(f"Failed to download {resource_type} from: {file_path}")
            return None
            
    except Exception as e:
        logger.error(f"Error reading {resource_type} file: {e}")
        return None


def build_resource_response(
    task_id: str,
    data: Optional[Dict[str, Any]],
    resource_type: str,
    additional_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build a standardized resource response.
    
    Args:
        task_id: Task identifier
        data: Resource data (can be None)
        resource_type: Type of resource (e.g., "outline", "persona_research")
        additional_fields: Additional fields to include in response
        
    Returns:
        Standardized resource response dictionary
    """
    response = {
        "task_id": task_id,
        resource_type: data
    }
    
    if additional_fields:
        response.update(additional_fields)
        
    return response
