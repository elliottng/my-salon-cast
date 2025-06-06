"""MCP server utilities for common operations."""

import json
import logging
import os
from typing import Optional, Dict, Any, List
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


async def get_task_status_or_error(
    status_manager,
    task_id: str,
    require_episode: bool = False
):
    """
    Get task status with standard validation and error handling.
    
    Args:
        status_manager: StatusManager instance
        task_id: Task identifier
        require_episode: Whether to require result_episode to be present
        
    Returns:
        PodcastStatus object
        
    Raises:
        ToolError: If task not found or episode not available
    """
    # Validate task ID
    validate_task_id(task_id)
    
    # Get status
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ToolError(f"Task not found: {task_id}")
    
    if require_episode and not status_info.result_episode:
        raise ToolError(f"Podcast episode not available for task: {task_id}")
    
    return status_info


def build_job_status_response(task_id: str, status_info) -> Dict[str, Any]:
    """
    Build a standardized job status response.
    
    Args:
        task_id: Task identifier
        status_info: PodcastStatus object
        
    Returns:
        Standardized job status response
    """
    return {
        "task_id": task_id,
        "status": status_info.status,
        "progress_percentage": status_info.progress_percentage,
        "current_step": status_info.status_description,
        "start_time": status_info.created_at.isoformat() if status_info.created_at else None,
        "end_time": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None,
        "error_message": status_info.error_message,
        "artifact_availability": status_info.artifacts.model_dump() if status_info.artifacts else None,
        "resource_type": "job_status"
    }


def build_job_logs_response(task_id: str, logs: list) -> Dict[str, Any]:
    """
    Build a standardized job logs response.
    
    Args:
        task_id: Task identifier
        logs: List of log entries
        
    Returns:
        Standardized job logs response
    """
    return {
        "task_id": task_id,
        "logs": logs,
        "log_count": len(logs),
        "resource_type": "job_logs"
    }


def build_job_warnings_response(
    task_id: str,
    status_info,
    warnings: Optional[list] = None
) -> Dict[str, Any]:
    """
    Build a standardized job warnings response.
    
    Args:
        task_id: Task identifier
        status_info: PodcastStatus object
        warnings: List of warnings (optional, extracted from episode)
        
    Returns:
        Standardized job warnings response
    """
    if warnings is None:
        warnings = []
        
    return {
        "task_id": task_id,
        "warnings": warnings,
        "warning_count": len(warnings),
        "has_errors": status_info.status == "failed",
        "error_message": status_info.error_message,
        "last_updated": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None,
        "resource_type": "job_warnings"
    }


def handle_resource_error(e: Exception, task_id: str, operation: str):
    """
    Handle common resource errors with consistent error messages.
    
    Args:
        e: The exception that occurred
        task_id: Task identifier
        operation: The operation being performed (e.g., "retrieve job status")
        
    Raises:
        ToolError: With appropriate error message
    """
    error_str = str(e)
    
    if "Task not found" in error_str:
        raise ToolError(f"Task not found: {task_id}")
    elif "not available" in error_str:
        raise ToolError(f"Podcast episode not available for task: {task_id}")
    else:
        raise ToolError(f"Failed to {operation}: {error_str}")


def build_podcast_transcript_response(task_id: str, episode) -> Dict[str, Any]:
    """
    Build a standardized podcast transcript response.
    
    Args:
        task_id: Task identifier
        episode: PodcastEpisode object
        
    Returns:
        Standardized podcast transcript response
    """
    return {
        "task_id": task_id,
        "transcript": episode.transcript or "",
        "title": episode.title or "",
        "summary": episode.summary or "",
        "character_count": len(episode.transcript) if episode.transcript else 0,
        "resource_type": "podcast_transcript"
    }


def build_podcast_audio_response(task_id: str, episode) -> Dict[str, Any]:
    """
    Build a standardized podcast audio response.
    
    Args:
        task_id: Task identifier
        episode: PodcastEpisode object
        
    Returns:
        Standardized podcast audio response
    """
    import os
    
    audio_filepath = getattr(episode, 'audio_filepath', '') or ""
    audio_exists = os.path.exists(audio_filepath) if audio_filepath else False
    
    return {
        "task_id": task_id,
        "audio_filepath": audio_filepath,
        "audio_exists": audio_exists,
        "file_size": os.path.getsize(audio_filepath) if audio_exists else 0,
        "resource_type": "podcast_audio"
    }


def build_podcast_metadata_response(task_id: str, episode) -> Dict[str, Any]:
    """
    Build a standardized podcast metadata response.
    
    Args:
        task_id: Task identifier
        episode: PodcastEpisode object
        
    Returns:
        Standardized podcast metadata response
    """
    return {
        "task_id": task_id,
        "title": episode.title or "",
        "summary": episode.summary or "",
        "duration": getattr(episode, 'duration', None),
        "source_attributions": getattr(episode, 'source_attributions', []) or [],
        "creation_date": episode.created_at.isoformat() if hasattr(episode, 'created_at') and episode.created_at else None,
        "completion_date": None,  # This should come from status_info, not episode
        "resource_type": "podcast_metadata"
    }


def collect_file_info(file_path: str, file_type: str, **extra_attrs) -> Dict[str, Any]:
    """
    Collect information about a file including size and existence.
    
    Args:
        file_path: Path to the file
        file_type: Type of file (e.g., "main_audio", "audio_segment")
        **extra_attrs: Additional attributes to include
        
    Returns:
        Dictionary with file information
    """
    file_info = {
        "type": file_type,
        "path": file_path,
        "exists": False,
        "size": 0
    }
    
    if file_path and os.path.exists(file_path):
        try:
            file_info["size"] = os.path.getsize(file_path)
            file_info["exists"] = True
        except Exception:
            pass
    
    # Add any extra attributes
    file_info.update(extra_attrs)
    
    return file_info


def collect_directory_info(dir_path: str, **extra_attrs) -> Dict[str, Any]:
    """
    Collect information about a directory including total size and file count.
    
    Args:
        dir_path: Path to the directory
        **extra_attrs: Additional attributes to include
        
    Returns:
        Dictionary with directory information
    """
    dir_info = {
        "path": dir_path,
        "exists": False,
        "size": 0,
        "file_count": 0
    }
    
    if dir_path and os.path.isdir(dir_path):
        try:
            total_size = 0
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(dir_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            dir_info.update({
                "size": total_size,
                "exists": True,
                "file_count": file_count
            })
        except Exception:
            pass
    
    dir_info.update(extra_attrs)
    return dir_info


def collect_multiple_files_info(file_paths: List[str], file_type: str, 
                               add_index: bool = False) -> List[Dict[str, Any]]:
    """
    Collect info for multiple files with optional indexing.
    
    Args:
        file_paths: List of file paths to collect info for
        file_type: Type of files (e.g., "audio_segment")
        add_index: Whether to add segment_index to each file info
        
    Returns:
        List of file information dictionaries
    """
    files_info = []
    for i, file_path in enumerate(file_paths or []):
        extra_attrs = {"segment_index": i} if add_index else {}
        file_info = collect_file_info(file_path, file_type, **extra_attrs)
        files_info.append(file_info)
    return files_info


def collect_and_delete_file_info(file_path: str, file_type: str, **extra_attrs) -> Dict[str, Any]:
    """
    Collect file info and then delete the file if it exists.
    
    Args:
        file_path: Path to the file
        file_type: Type of file (e.g., "main_audio", "audio_segment")
        **extra_attrs: Additional attributes to include
        
    Returns:
        Dictionary with file information including deletion status
    """
    file_info = collect_file_info(file_path, file_type, **extra_attrs)
    
    if file_info["exists"]:
        try:
            os.remove(file_path)
            file_info["deleted"] = True
        except Exception as e:
            file_info["deleted"] = False
            file_info["delete_error"] = str(e)
    else:
        file_info["deleted"] = False
    
    return file_info


def collect_llm_files_info(episode) -> List[Dict[str, Any]]:
    """
    Collect information for all LLM output files from an episode.
    
    Args:
        episode: Episode object with LLM file paths
        
    Returns:
        List of file information dictionaries for LLM files
    """
    llm_files = []
    
    # Source analysis files
    if episode.llm_source_analysis_paths:
        for i, path in enumerate(episode.llm_source_analysis_paths):
            llm_files.append(collect_file_info(path, f"llm_source_analysis", analysis_index=i))
    
    # Persona research files  
    if episode.llm_persona_research_paths:
        for i, path in enumerate(episode.llm_persona_research_paths):
            llm_files.append(collect_file_info(path, f"llm_persona_research", research_index=i))
    
    # Single LLM files
    if episode.llm_podcast_outline_path:
        llm_files.append(collect_file_info(episode.llm_podcast_outline_path, "llm_outline"))
    if episode.llm_dialogue_turns_path:
        llm_files.append(collect_file_info(episode.llm_dialogue_turns_path, "llm_dialogue"))
    
    return llm_files


def collect_and_delete_llm_files(episode) -> List[Dict[str, Any]]:
    """
    Collect information and delete all LLM output files from an episode.
    
    Args:
        episode: Episode object with LLM file paths
        
    Returns:
        List of file information dictionaries for deleted LLM files
    """
    llm_files = []
    
    # Source analysis files
    if episode.llm_source_analysis_paths:
        for i, path in enumerate(episode.llm_source_analysis_paths):
            llm_files.append(collect_and_delete_file_info(path, f"llm_source_analysis", analysis_index=i))
    
    # Persona research files
    if episode.llm_persona_research_paths:
        for i, path in enumerate(episode.llm_persona_research_paths):
            llm_files.append(collect_and_delete_file_info(path, f"llm_persona_research", research_index=i))
    
    # Single LLM files
    if episode.llm_podcast_outline_path:
        llm_files.append(collect_and_delete_file_info(episode.llm_podcast_outline_path, "llm_outline"))
    if episode.llm_dialogue_turns_path:
        llm_files.append(collect_and_delete_file_info(episode.llm_dialogue_turns_path, "llm_dialogue"))
    
    return llm_files
