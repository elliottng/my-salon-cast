import logging
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest, PodcastEpisode
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner
from app.cleanup_config import cleanup_manager, get_cleanup_manager, CleanupPolicy
from fastmcp.prompts.prompt import Message
from pydantic import Field
from typing import Literal, Optional, List
import os
import tempfile
import base64
import mimetypes
from pathlib import Path
import logging
import glob
import shutil

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize services required by MCP tools
podcast_service = PodcastGeneratorService()
status_manager = get_status_manager()
task_runner = get_task_runner()
cleanup_manager = get_cleanup_manager()
logger.info("Services initialized for MCP.")

# Initialize the FastMCP server with correct API
mcp = FastMCP("MySalonCast Podcast Generator")

# Simple test tool
@mcp.tool()
async def hello(name: str = "world") -> str:
    """Returns a simple greeting."""
    logger.info(f"Tool 'hello' called with name: {name}")
    return f"Hello, {name}!"

# Async podcast generation with individual parameters
@mcp.tool()
async def generate_podcast_async(
    ctx,  # MCP context for request correlation
    source_urls: Optional[List[str]] = None,
    source_pdf_path: Optional[str] = None,
    prominent_persons: Optional[List[str]] = None,
    custom_prompt: Optional[str] = None,
    podcast_name: Optional[str] = None,
    podcast_tagline: Optional[str] = None,
    output_language: Literal["en", "es", "fr", "de", "it", "pt", "hi", "ar"] = "en",
    dialogue_style: Literal["interview", "conversation", "debate", "educational"] = "conversation",
    podcast_length: Literal["short", "medium", "long"] = "medium",
    ending_message: Optional[str] = None
) -> dict:
    """
    Generate a podcast asynchronously using provided sources.
    Returns immediately with a task ID for status tracking.
    """
    # Enhanced logging with MCP context
    request_id = getattr(ctx, 'request_id', 'unknown')
    client_info = getattr(ctx, 'client_info', {})
    
    logger.info(f"[{request_id}] MCP Tool 'generate_podcast_async' called")
    logger.info(f"[{request_id}] Client info: {client_info}")
    logger.info(f"[{request_id}] Request params: sources={len(source_urls or [])}, persons={len(prominent_persons or [])}, style={dialogue_style}, length={podcast_length}")
    
    # Basic input validation
    if not source_urls and not source_pdf_path:
        raise ToolError("At least one source (URL or PDF) must be provided")
    
    if source_urls:
        if len(source_urls) > 10:
            raise ToolError("Maximum 10 source URLs allowed")
        for url in source_urls:
            if not url.strip() or not (url.startswith('http://') or url.startswith('https://')):
                raise ToolError(f"Invalid URL format: {url}")
    
    if source_pdf_path and not source_pdf_path.endswith('.pdf'):
        raise ToolError("PDF file must have .pdf extension")
    
    if prominent_persons and len(prominent_persons) > 5:
        raise ToolError("Maximum 5 prominent persons allowed")
    
    # Validate and convert to PodcastRequest
    try:
        request = PodcastRequest(
            source_urls=source_urls if source_urls else None,
            source_pdf_path=source_pdf_path if source_pdf_path else None,
            prominent_persons=prominent_persons if prominent_persons else None,
            custom_prompt=custom_prompt if custom_prompt else None,
            podcast_name=podcast_name if podcast_name else None,
            podcast_tagline=podcast_tagline if podcast_tagline else None,
            output_language=output_language,
            dialogue_style=dialogue_style,
            podcast_length=podcast_length,
            ending_message=ending_message if ending_message else None
        )
    except Exception as e:
        raise ToolError("Invalid podcast generation parameters", str(e))
    
    # Submit async task
    try:
        task_id = await podcast_service.generate_podcast_async(request)
        logger.info(f"[{request_id}] Async podcast generation started with task_id: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Podcast generation started. Use get_task_status to check progress."
        }
    except Exception as e:
        raise ToolError("Failed to start podcast generation", str(e))

# Async podcast generation with Pydantic model
@mcp.tool()
async def generate_podcast_async_pydantic(ctx, request: PodcastRequest) -> dict:
    """
    Start async podcast generation using a structured PodcastRequest model.
    
    Accepts a complete PodcastRequest object with all configuration options.
    Use get_task_status with the returned task_id to check progress.
    
    Args:
        request: PodcastRequest model with all generation parameters
        
    Returns:
        Dict with task_id and initial status
    """
    # Enhanced logging with MCP context
    request_id = getattr(ctx, 'request_id', 'unknown')
    logger.info(f"[{request_id}] MCP Tool 'generate_podcast_async_pydantic' called")
    logger.info(f"[{request_id}] Request model: {request.model_dump(exclude_none=True)}")
    
    try:
        task_id = await podcast_service.generate_podcast_async(request)
        logger.info(f"[{request_id}] Async podcast generation started with task_id: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Podcast generation started. Use get_task_status to check progress."
        }
    except Exception as e:
        raise ToolError("Failed to start podcast generation", str(e))

# Get status of async task
@mcp.tool()
async def get_task_status(ctx, task_id: str) -> dict:
    """
    Get the status of an async podcast generation task.
    
    Returns current status, progress percentage, and result when complete.
    
    Args:
        task_id: The task ID returned by generate_podcast_async
        
    Returns:
        Dict with status information and episode data when complete
    """
    # Enhanced logging with MCP context
    request_id = getattr(ctx, 'request_id', 'unknown')
    client_info = getattr(ctx, 'client_info', {})
    logger.info(f"[{request_id}] MCP Tool 'get_task_status' called for task: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if status_info:
            logger.info(f"[{request_id}] Retrieved status for task {task_id}: {status_info.status}")
            return {
                "success": True,
                "task_id": task_id,
                "status": status_info.model_dump()
            }
        else:
            raise ToolError(f"Task {task_id} not found")
    except Exception as e:
        raise ToolError("Failed to retrieve task status", str(e))

# Phase 4.3b: File Cleanup Management Tool

@mcp.tool()
async def cleanup_task_files(
    ctx,  # MCP context for request correlation
    task_id: str = Field(..., description="Task ID to clean up files for"),
    force_cleanup: bool = Field(False, description="Force cleanup even if task is not completed"),
    policy_override: Optional[Literal["manual", "auto_on_complete", "auto_after_hours", "auto_after_days", "retain_audio_only", "retain_all"]] = Field(None, description="Override default cleanup policy for this operation")
) -> dict:
    """
    Clean up files associated with a podcast generation task.
    
    Removes temporary files, audio segments, and LLM output files for the specified task
    based on the configured cleanup policy or optional override.
    Use with caution as this action cannot be undone.
    
    Args:
        task_id: The task ID to clean up files for
        force_cleanup: If True, proceed with cleanup even if task is not completed
        policy_override: Optional policy override ('manual', 'retain_audio_only', 'retain_all', etc.)
        
    Returns:
        Dict with cleanup status and details about removed files
    """
    # Enhanced logging with MCP context  
    request_id = getattr(ctx, 'request_id', 'unknown')
    logger.info(f"[{request_id}] MCP Tool 'cleanup_task_files' called for task_id: {task_id}")
    logger.info(f"[{request_id}] Cleanup params: force={force_cleanup}, policy_override={policy_override}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        # Validate task and ownership
        status_info = _validate_task_ownership(task_id)
        
        # Safety check - don't clean up running tasks unless forced
        if status_info.status in ["queued", "preprocessing_sources", "analyzing_sources", "researching_personas", 
                                 "generating_outline", "generating_dialogue", "generating_audio_segments", 
                                 "postprocessing_final_episode"] and not force_cleanup:
            raise ToolError("Task is still running", "Task " + task_id + " has status '" + status_info.status + "'. Use force_cleanup=True to cleanup anyway.")
        
        # Get cleanup rules based on policy
        if policy_override:
            try:
                override_policy = CleanupPolicy(policy_override)
                # Temporarily set the policy for this task
                original_policy = cleanup_manager.config.default_policy  
                cleanup_manager.config.default_policy = override_policy
                cleanup_rules = cleanup_manager.get_cleanup_rules(task_id)
                cleanup_manager.config.default_policy = original_policy
            except ValueError:
                raise ToolError("Invalid policy override: " + policy_override, "Valid policies: " + str([p.value for p in CleanupPolicy]))
        else:
            cleanup_rules = cleanup_manager.get_cleanup_rules(task_id)
        
        # Add retain_audio field for test compatibility
        cleanup_rules['retain_audio'] = not cleanup_rules.get('audio_files', False)
        
        # Log the cleanup action
        logger.info(f"Using cleanup rules for task {task_id}: {cleanup_rules}")
        
        cleaned_files = []
        failed_cleanups = []
        total_size_freed = 0
        
        if status_info.result_episode:
            episode = status_info.result_episode
            
            # Clean up main audio file (only if policy allows)
            if cleanup_rules.get("audio_files", False) and episode.audio_filepath and _validate_file_access(episode.audio_filepath):
                try:
                    file_size = os.path.getsize(episode.audio_filepath)
                    os.remove(episode.audio_filepath)
                    cleaned_files.append({
                        "type": "main_audio",
                        "path": episode.audio_filepath,
                        "size": file_size
                    })
                    total_size_freed += file_size
                    logger.info(f"Removed main audio file: {episode.audio_filepath}")
                except Exception as e:
                    failed_cleanups.append({
                        "type": "main_audio", 
                        "path": episode.audio_filepath,
                        "error": str(e)
                    })
                    logger.warning(f"Failed to remove audio file {episode.audio_filepath}: {e}")
            elif episode.audio_filepath and not cleanup_rules.get("audio_files", False):
                logger.info(f"Skipping main audio file removal due to policy: {episode.audio_filepath}")
            
            # Clean up audio segments (only if policy allows)
            if cleanup_rules.get("audio_segments", False) and episode.dialogue_turn_audio_paths:
                for i, segment_path in enumerate(episode.dialogue_turn_audio_paths):
                    if _validate_file_access(segment_path):
                        try:
                            file_size = os.path.getsize(segment_path)
                            os.remove(segment_path)
                            cleaned_files.append({
                                "type": "audio_segment",
                                "path": segment_path,
                                "size": file_size,
                                "segment_index": i
                            })
                            total_size_freed += file_size
                            logger.info(f"Removed audio segment: {segment_path}")
                        except Exception as e:
                            failed_cleanups.append({
                                "type": "audio_segment",
                                "path": segment_path,
                                "segment_index": i,
                                "error": str(e)
                            })
                            logger.warning(f"Failed to remove segment {segment_path}: {e}")
            elif episode.dialogue_turn_audio_paths and not cleanup_rules.get("audio_segments", False):
                logger.info(f"Skipping {len(episode.dialogue_turn_audio_paths)} audio segments due to policy")
            
            # Clean up LLM output files (only if policy allows)
            if cleanup_rules.get("llm_outputs", False):
                llm_files = []
                
                # Handle source analysis paths (list)
                if episode.llm_source_analysis_paths:
                    for i, path in enumerate(episode.llm_source_analysis_paths):
                        llm_files.append((f"source_analysis_{i}", path))
                
                # Handle persona research paths (list)
                if episode.llm_persona_research_paths:
                    for i, path in enumerate(episode.llm_persona_research_paths):
                        llm_files.append((f"persona_research_{i}", path))
                
                # Handle single paths
                if episode.llm_podcast_outline_path:
                    llm_files.append(("outline", episode.llm_podcast_outline_path))
                if episode.llm_dialogue_turns_path:
                    llm_files.append(("dialogue", episode.llm_dialogue_turns_path))
                
                for file_type, file_path in llm_files:
                    if file_path and _validate_file_access(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_files.append({
                                "type": f"llm_{file_type}",
                                "path": file_path,
                                "size": file_size,
                                "removed": True
                            })
                            logger.info(f"Removed LLM file: {file_path}")
                        except Exception as e:
                            failed_cleanups.append({
                                "type": f"llm_{file_type}",
                                "path": file_path,
                                "error": str(e)
                            })
                            logger.warning(f"Failed to remove LLM file {file_path}: {e}")
            else:
                llm_file_count = 0
                # Count list-type paths
                if episode.llm_source_analysis_paths:
                    llm_file_count += len(episode.llm_source_analysis_paths)
                if episode.llm_persona_research_paths:
                    llm_file_count += len(episode.llm_persona_research_paths)
                # Count single paths  
                if episode.llm_podcast_outline_path:
                    llm_file_count += 1
                if episode.llm_dialogue_turns_path:
                    llm_file_count += 1
                    
                if llm_file_count > 0:
                    logger.info(f"Skipping {llm_file_count} LLM output files due to policy")
            
            # Try to remove the temporary directory if it appears to be empty (only if policy allows)
            if cleanup_rules.get("temp_directories", False):
                try:
                    if episode.audio_filepath:
                        temp_dir = os.path.dirname(episode.audio_filepath)
                        if os.path.isdir(temp_dir) and not os.listdir(temp_dir):
                            os.rmdir(temp_dir)
                            logger.info(f"Removed empty temporary directory: {temp_dir}")
                            cleaned_files.append({
                                "type": "temp_directory",
                                "path": temp_dir,
                                "size": 0
                            })
                except Exception as e:
                    logger.warning(f"Could not remove temporary directory: {e}")
            
        # Also look for any remaining temporary directories for this task (only if policy allows)
        if cleanup_rules.get("temp_directories", False):
            import glob
            temp_dirs_pattern = os.path.join(tempfile.gettempdir(), f"podcast_job_*")
            for temp_dir in glob.glob(temp_dirs_pattern):
                if task_id[:8] in temp_dir:
                    try:
                        import shutil
                        dir_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                       for dirpath, dirnames, filenames in os.walk(temp_dir)
                                       for filename in filenames)
                        shutil.rmtree(temp_dir)
                        cleaned_files.append({
                            "type": "temp_directory_full",
                            "path": temp_dir,
                            "size": dir_size
                        })
                        total_size_freed += dir_size
                        logger.info(f"Removed temporary directory: {temp_dir}")
                    except Exception as e:
                        failed_cleanups.append({
                            "type": "temp_directory_full",
                            "path": temp_dir,
                            "error": str(e)
                        })
                        logger.warning(f"Failed to remove temp directory {temp_dir}: {e}")
        
        success = len(cleaned_files) > 0 or not any(cleanup_rules.values())
        
        # Get applied policy information
        applied_policy = cleanup_manager.get_policy_for_task(task_id)
        if policy_override:
            applied_policy = CleanupPolicy(policy_override)
        
        return {
            "success": success,
            "task_id": task_id,
            "cleaned_files": cleaned_files,
            "failed_files": failed_cleanups,
            "files_cleaned": len(cleaned_files),
            "files_failed": len(failed_cleanups),
            "total_size_freed": total_size_freed,
            "applied_policy": applied_policy.value,
            "cleanup_rules": cleanup_rules,
            "message": f"Cleanup completed. {len(cleaned_files)} files cleaned, {len(failed_cleanups)} failures.",
            "cleanup_options": {
                "force_cleanup": force_cleanup,
                "policy_override": policy_override
            }
        }
        
    except ValueError as e:
        # Handle validation errors (e.g., task not found)
        raise ToolError(str(e), "Task validation failed")
    except Exception as e:
        logger.error(f"Failed to cleanup task files: {e}", exc_info=True)
        raise ToolError("Cleanup operation failed", str(e))

@mcp.resource("files://{task_id}/cleanup")
async def get_cleanup_status_resource(task_id: str) -> dict:
    """
    Get cleanup status and options for task files.
    Provides information about temporary files and cleanup policies.
    """
    logger.info(f"Resource 'cleanup status' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    # Validate task and ownership
    status_info = _validate_task_ownership(task_id)
    
    # Check for temporary directories (these exist regardless of episode status)
    temp_dirs = []
    import glob
    for temp_dir in glob.glob(os.path.join(tempfile.gettempdir(), "podcast_job_*")):
        if task_id[:8] in temp_dir and os.path.isdir(temp_dir):
            temp_dirs.append(temp_dir)
    
    if not status_info.result_episode:
        # For tasks without episodes, we can still show temp directory info
        return {
            "task_id": task_id,
            "status": status_info.status,
            "cleanup_available": len(temp_dirs) > 0,
            "temp_directories": temp_dirs,
            "cleanup_policy": cleanup_manager.get_policy_for_task(task_id),
            "files_available": False,
            "estimated_size": 0
        }
    
    episode = status_info.result_episode
    
    # Collect file information
    files_info = []
    total_size = 0
    
    # Main audio file
    if episode.audio_filepath and _validate_file_access(episode.audio_filepath):
        try:
            size = os.path.getsize(episode.audio_filepath)
            files_info.append({
                "type": "main_audio",
                "path": episode.audio_filepath,
                "size": size,
                "exists": True
            })
            total_size += size
        except:
            files_info.append({
                "type": "main_audio", 
                "path": episode.audio_filepath,
                "size": 0,
                "exists": False
            })
    
    # Audio segments
    if episode.dialogue_turn_audio_paths:
        for i, segment_path in enumerate(episode.dialogue_turn_audio_paths):
            if _validate_file_access(segment_path):
                try:
                    size = os.path.getsize(segment_path)
                    files_info.append({
                        "type": "audio_segment",
                        "path": segment_path,
                        "size": size,
                        "segment_index": i,
                        "exists": True
                    })
                    total_size += size
                except:
                    files_info.append({
                        "type": "audio_segment",
                        "path": segment_path,
                        "size": 0,
                        "segment_index": i,
                        "exists": False
                    })
    
    # LLM output files
    llm_files = []
    
    # Handle source analysis paths (list)
    if episode.llm_source_analysis_paths:
        for i, path in enumerate(episode.llm_source_analysis_paths):
            llm_files.append((f"source_analysis_{i}", path))
    
    # Handle persona research paths (list)
    if episode.llm_persona_research_paths:
        for i, path in enumerate(episode.llm_persona_research_paths):
            llm_files.append((f"persona_research_{i}", path))
    
    # Handle single paths
    if episode.llm_podcast_outline_path:
        llm_files.append(("outline", episode.llm_podcast_outline_path))
    if episode.llm_dialogue_turns_path:
        llm_files.append(("dialogue", episode.llm_dialogue_turns_path))
    
    for file_type, file_path in llm_files:
        if file_path and _validate_file_access(file_path):
            try:
                size = os.path.getsize(file_path)
                files_info.append({
                    "type": f"llm_{file_type}",
                    "path": file_path,
                    "size": size,
                    "exists": True
                })
                total_size += size
            except:
                files_info.append({
                    "type": f"llm_{file_type}",
                    "path": file_path,
                    "size": 0,
                    "exists": False
                })
    
    return {
        "task_id": task_id,
        "status": status_info.status,
        "cleanup_available": len(files_info) > 0,
        "files": files_info,
        "file_count": len(files_info),
        "total_size": total_size,
        "cleanup_policy": cleanup_manager.get_policy_for_task(task_id),
        "files_exist": {
            "audio_file": any(f["type"] == "main_audio" and f.get("exists", False) for f in files_info),
            "audio_segments": any(f["type"] == "audio_segment" and f.get("exists", False) for f in files_info),
            "temp_directory": len(temp_dirs) > 0,
            "llm_outputs": any(f["type"].startswith("llm_") and f.get("exists", False) for f in files_info)
        },
        "created_at": status_info.created_at.isoformat() if status_info.created_at else "",
        "last_updated": status_info.last_updated_at.isoformat() if status_info.last_updated_at else ""
    }

# Phase 4.3c: Cleanup Configuration Management Tool

@mcp.tool()
async def configure_cleanup_policy(
    ctx,  # MCP context for request correlation
    default_policy: str = None,
    auto_cleanup_hours: int = None,
    auto_cleanup_days: int = None,
    retain_audio_files: bool = None,
    retain_transcripts: bool = None,
    retain_llm_outputs: bool = None,
    retain_audio_segments: bool = None,
    max_temp_size_mb: int = None,
    enable_background_cleanup: bool = None
) -> dict:
    """
    Configure cleanup policies for MySalonCast file management.
    
    Updates the global cleanup configuration settings that control how and when
    temporary files are cleaned up after podcast generation.
    
    Args:
        default_policy: Default cleanup policy ('manual', 'auto_on_complete', 'auto_after_hours', etc.)
        auto_cleanup_hours: Hours after completion before auto cleanup (for AUTO_AFTER_HOURS policy)  
        auto_cleanup_days: Days after completion before auto cleanup (for AUTO_AFTER_DAYS policy)
        retain_audio_files: Whether to retain final audio files during cleanup
        retain_transcripts: Whether to retain transcript files during cleanup
        retain_llm_outputs: Whether to retain LLM intermediate output files
        retain_audio_segments: Whether to retain individual audio segment files
        max_temp_size_mb: Maximum total size of temp files per task in MB
        enable_background_cleanup: Whether to enable background cleanup scheduler
        
    Returns:
        Dict with updated configuration and status
    """
    # Enhanced logging with MCP context
    request_id = getattr(ctx, 'request_id', 'unknown')
    logger.info(f"[{request_id}] MCP Tool 'configure_cleanup_policy' called with updates")
    
    try:
        # Build update dictionary with only provided values
        updates = {}
        if default_policy is not None:
            # Validate policy value
            try:
                CleanupPolicy(default_policy)
                updates["default_policy"] = default_policy
            except ValueError:
                raise ToolError("Invalid cleanup policy: " + default_policy, "Valid policies: " + str([p.value for p in CleanupPolicy]))
        
        if auto_cleanup_hours is not None:
            if auto_cleanup_hours < 1 or auto_cleanup_hours > 8760:  # 1 year max
                raise ToolError("auto_cleanup_hours must be between 1 and 8760")
            updates["auto_cleanup_hours"] = auto_cleanup_hours
            
        if auto_cleanup_days is not None:
            if auto_cleanup_days < 1 or auto_cleanup_days > 365:
                raise ToolError("auto_cleanup_days must be between 1 and 365")
            updates["auto_cleanup_days"] = auto_cleanup_days
            
        if retain_audio_files is not None:
            updates["retain_audio_files"] = retain_audio_files
            
        if retain_transcripts is not None:
            updates["retain_transcripts"] = retain_transcripts
            
        if retain_llm_outputs is not None:
            updates["retain_llm_outputs"] = retain_llm_outputs
            
        if retain_audio_segments is not None:
            updates["retain_audio_segments"] = retain_audio_segments
            
        if max_temp_size_mb is not None:
            if max_temp_size_mb < 1 or max_temp_size_mb > 10000:  # 10GB max
                raise ToolError("max_temp_size_mb must be between 1 and 10000")
            updates["max_temp_size_mb"] = max_temp_size_mb
            
        if enable_background_cleanup is not None:
            updates["enable_background_cleanup"] = enable_background_cleanup
        
        if not updates:
            raise ToolError("No configuration updates provided", "Current config: " + cleanup_manager.config.model_dump())
        
        # Apply updates
        updated_config = cleanup_manager.update_config(**updates)
        
        logger.info(f"Updated cleanup configuration: {updates}")
        
        return {
            "success": True,
            "message": f"Updated {len(updates)} cleanup configuration setting(s)",
            "updated_fields": list(updates.keys()),
            "current_config": updated_config.model_dump(),
            "config_file": cleanup_manager.config_path
        }
        
    except Exception as e:
        logger.error(f"Error updating cleanup configuration: {e}")
        raise ToolError(str(e), "Failed to update cleanup configuration")

# Phase 4.3d: Cleanup Configuration Resource

@mcp.resource("config://cleanup")
async def get_cleanup_config_resource() -> dict:
    """
    Get current cleanup configuration and policy settings.
    
    Returns the current cleanup policy configuration including default policies,
    retention settings, size limits, and background cleanup options.
    """
    logger.info("Resource 'cleanup configuration' accessed")
    
    config = cleanup_manager.config
    
    return {
        "cleanup_policies": {
            "current_default": config.default_policy,
            "available_policies": [p.value for p in CleanupPolicy],
            "policy_descriptions": {
                "manual": "No automatic cleanup, require explicit cleanup_task_files calls",
                "auto_on_complete": "Cleanup immediately when task completes",
                "auto_after_hours": "Cleanup after specified hours since completion",
                "auto_after_days": "Cleanup after specified days since completion", 
                "retain_audio_only": "Keep only final audio, remove temp files",
                "retain_all": "Never cleanup (for development/testing)"
            }
        },
        "timing_settings": {
            "auto_cleanup_hours": config.auto_cleanup_hours,
            "auto_cleanup_days": config.auto_cleanup_days
        },
        "retention_settings": {
            "retain_audio_files": config.retain_audio_files,
            "retain_transcripts": config.retain_transcripts,
            "retain_llm_outputs": config.retain_llm_outputs,
            "retain_audio_segments": config.retain_audio_segments
        },
        "size_limits": {
            "max_temp_size_mb": config.max_temp_size_mb,
            "max_total_storage_gb": config.max_total_storage_gb
        },
        "background_cleanup": {
            "enabled": config.enable_background_cleanup,
            "cleanup_on_startup": config.cleanup_on_startup,
            "interval_minutes": config.background_cleanup_interval_minutes
        },
        "configuration": {
            "config_file": cleanup_manager.config_path,
            "last_modified": os.path.getmtime(cleanup_manager.config_path) if os.path.exists(cleanup_manager.config_path) else None
        }
    }

# Security and file management helpers
def _validate_task_ownership(task_id: str) -> dict:
    """Validate task exists and return status info."""
    status_info = status_manager.get_status(task_id)
    if not status_info:
        raise ValueError("Task not found: " + task_id)
    return status_info

def _validate_file_access(filepath: str, task_id: str = None) -> bool:
    """Validate file path for security (prevent directory traversal)."""
    if not filepath:
        return False
    
    # Convert to absolute path and resolve any .. or . components
    abs_path = os.path.abspath(filepath)
    
    # Check if file exists
    if not os.path.exists(abs_path):
        return False
    
    # Ensure file is within temp directory or outputs directory
    temp_dir = tempfile.gettempdir()
    outputs_dir = os.path.abspath("./outputs")
    
    # File must be within temp directory (for active tasks) or outputs directory
    is_in_temp = abs_path.startswith(temp_dir)
    is_in_outputs = abs_path.startswith(outputs_dir)
    
    if not (is_in_temp or is_in_outputs):
        logger.warning("File access denied - path outside allowed directories: " + abs_path)
        return False
    
    return True

def _get_file_content_safe(filepath: str, max_size_mb: int = 50) -> bytes:
    """Safely read file content with size limits."""
    if not _validate_file_access(filepath):
        raise ValueError("File access denied: " + filepath)
    
    # Check file size
    file_size = os.path.getsize(filepath)
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        raise ValueError("File too large: " + str(file_size) + " bytes > " + str(max_size_bytes) + " bytes limit")
    
    try:
        with open(filepath, 'rb') as f:
            return f.read()
    except Exception as e:
        raise ValueError("Error reading file: " + str(e))

def _list_directory_safe(directory: str, task_id: str = None) -> list:
    """Safely list directory contents with security validation."""
    if not _validate_file_access(directory, task_id):
        raise ValueError("Directory access denied: " + directory)
    
    if not os.path.isdir(directory):
        raise ValueError("Path is not a directory: " + directory)
    
    try:
        files = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                file_size = os.path.getsize(item_path)
                mime_type, _ = mimetypes.guess_type(item_path)
                files.append({
                    "name": item,
                    "path": item_path,
                    "size": file_size,
                    "mime_type": mime_type or "application/octet-stream",
                    "is_audio": mime_type and mime_type.startswith("audio/") if mime_type else False
                })
        return files
    except Exception as e:
        raise ValueError("Error listing directory: " + str(e))

# Temporary sync tool for testing (will be moved to generate_podcast_sync later)
@mcp.tool()
async def generate_podcast(request_data: PodcastRequest) -> dict:
    """
    [TEMPORARY - Will be renamed to generate_podcast_sync_pydantic]
    Generates a podcast episode synchronously.

    This tool orchestrates the entire podcast generation workflow.
    
    Args:
        request_data: A PodcastRequest object containing source URLs,
                      PDF path, desired length, custom prompts, etc.

    Returns:
        Dict with success status and episode data or error details.
    """
    logger.info("MCP Tool 'generate_podcast' called")
    try:
        episode = await podcast_service.generate_podcast_from_source(request_data=request_data)
        logger.info("MCP Tool 'generate_podcast' completed successfully. Episode title: " + episode.title)
        
        return {
            "success": True,
            "episode": {
                "title": episode.title,
                "summary": episode.summary,
                "transcript": episode.transcript,
                "audio_filepath": episode.audio_filepath,
                "source_attributions": episode.source_attributions,
                "warnings": episode.warnings
            }
        }
    except Exception as e:
        logger.error("MCP Tool 'generate_podcast' failed: " + str(e), exc_info=True)
        raise ToolError("Podcast generation failed", str(e))

# =============================================================================
# Phase 3.1: Core Prompt Templates
# =============================================================================

@mcp.prompt()
def podcast_generation_request(
    topic: str = Field(description="The main topic or subject for the podcast episode"),
    sources: str = Field(description="URLs or content sources (comma-separated if multiple)"),
    persons: Optional[str] = Field(default="", description="Prominent people to research and feature (comma-separated)"),
    style: Literal["engaging", "educational", "conversational", "formal"] = "engaging",
    length: Literal["3-5 minutes", "5-7 minutes", "7-10 minutes", "10-15 minutes"] = "5-7 minutes",
    language: Literal["en", "es", "fr", "de"] = "en",
    custom_focus: Optional[str] = Field(default="", description="Additional focus or angle for the podcast")
) -> str:
    """
    Generates a structured prompt for podcast creation requests.
    
    This template helps format podcast generation requests with all necessary
    parameters for the MySalonCast system.
    """
    
    prompt = f"Create a {length} podcast episode about '{topic}' in {language}.\n\n"
    prompt += f"**Content Sources:**\n{sources}\n\n"
    
    if persons:
        prompt += f"**Featured Personas:**\nResearch and include perspectives from: {persons}\n\n"
    
    prompt += f"**Style Requirements:**\n"
    prompt += f"- Dialogue style: {style}\n"
    prompt += f"- Episode length: {length}\n"
    prompt += f"- Language: {language}\n\n"
    
    if custom_focus:
        prompt += f"**Special Focus:**\n{custom_focus}\n\n"
    
    prompt += "**Output Requirements:**\n"
    prompt += "- Generate engaging dialogue between well-researched personas\n"
    prompt += "- Include proper source attribution\n"
    prompt += "- Create natural conversation flow\n"
    prompt += "- Ensure factual accuracy from provided sources"
    
    return prompt

@mcp.prompt()
def persona_research_prompt(
    person_name: str = Field(description="Name of the person to research"),
    research_focus: Literal["voice_characteristics", "speaking_style", "expertise", "full_profile"] = "full_profile",
    context_topic: Optional[str] = Field(default="", description="Specific topic or domain context for the research"),
    detail_level: Literal["basic", "detailed", "comprehensive"] = "detailed",
    time_period: Optional[str] = Field(default="", description="Specific time period or era to focus on (e.g., '1920s', 'early career')")
) -> str:
    """
    Generates a structured prompt for persona research requests.
    
    This template helps create focused research prompts for developing
    realistic personas for podcast dialogue generation.
    """
    
    prompt = f"Research {person_name} for podcast persona development.\n\n"
    
    prompt += f"**Research Focus:** {research_focus}\n"
    prompt += f"**Detail Level:** {detail_level}\n\n"
    
    if context_topic:
        prompt += f"**Context Topic:** {context_topic}\n\n"
        
    if time_period:
        prompt += f"**Time Period Focus:** {time_period}\n\n"
    
    prompt += "**Required Research Areas:**\n"
    
    if research_focus in ["voice_characteristics", "full_profile"]:
        prompt += "- Speech patterns and communication style\n"
        prompt += "- Vocabulary preferences and linguistic habits\n"
        prompt += "- Tone and emotional expression patterns\n"
    
    if research_focus in ["speaking_style", "full_profile"]:
        prompt += "- Argumentation and reasoning style\n"
        prompt += "- How they explain complex concepts\n" 
        prompt += "- Characteristic phrases or expressions\n"
        
    if research_focus in ["expertise", "full_profile"]:
        prompt += "- Core areas of knowledge and expertise\n"
        prompt += "- Key contributions and achievements\n"
        prompt += "- Historical context and background\n"
        
    if research_focus == "full_profile":
        prompt += "- Personality traits and characteristics\n"
        prompt += "- Notable quotes and documented statements\n"
        prompt += "- Relationships with other historical figures\n"
    
    prompt += "\n**Output Format:**\n"
    prompt += "Provide structured research that can be used to:\n"
    prompt += "1. Generate authentic dialogue in their voice\n"
    prompt += "2. Ensure historically accurate representation\n"
    prompt += "3. Create engaging conversational interactions\n"
    
    if context_topic:
        prompt += f"4. Focus expertise on {context_topic} specifically"
    
    return prompt

# =============================================================================
if __name__ == "__main__":
    # Run the server using Starlette/Uvicorn
    import uvicorn
    logger.info("Starting MySalonCast MCP server...")
    
    # Create the HTTP app with streamable-http transport (recommended for FastMCP 2.0+)
    # This provides efficient bidirectional communication over HTTP
    # Clients should connect to the base URL (no /sse endpoint needed)
    app = mcp.http_app(transport="streamable-http")
    
    # Run with uvicorn
    # IMPORTANT: The MCP server runs on port 8000
    # All client code should connect to this port using http://localhost:8000
    # The MySalonCastMCPClient class in tests/mcp/client.py implements the correct approach
    uvicorn.run(app, host="0.0.0.0", port=8000)
