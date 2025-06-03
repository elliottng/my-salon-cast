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
import json

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

# =============================================================================
# MCP PROMPTS
# =============================================================================

@mcp.prompt()
def create_podcast_from_url(
    url: str, 
    personas: str = "Einstein, Marie Curie", 
    length: Literal["short", "medium", "long"] = "medium",
    language: Literal["en", "es", "fr", "de", "it", "pt", "hi", "ar"] = "en"
) -> str:
    """Generates a prompt template for creating a podcast from a URL with specific personas and length.
    
    Args:
        url: The source URL to create a podcast from
        personas: Comma-separated list of personas/characters for the discussion
        length: Desired podcast length (short=~5min, medium=~10min, long=~15min)
        language: Output language for the podcast
    """
    return f"""I'd like to create a podcast discussion from this URL: {url}

Please generate a conversational podcast featuring these personas: {personas}

Requirements:
- Length: {length} (short=~5min, medium=~10min, long=~15min)
- Language: {language}
- Style: Natural conversation with different perspectives from each persona
- Include interesting insights and contrasting viewpoints

Use the MySalonCast tools to:
1. First, generate the podcast: generate_podcast_async with source_urls=["{url}"], prominent_persons=[{", ".join([f'"{p.strip()}"' for p in personas.split(",")])}], output_language="{language}"
2. Monitor progress with: get_task_status using the returned task_id
3. Access results via the podcast resources when complete

What aspects of this content would you like the personas to focus on?"""

@mcp.prompt()
def discuss_persona_viewpoint(
    task_id: str, 
    person_id: str, 
    topic: str
) -> str:
    """Generates a prompt for exploring a specific persona's viewpoint on a topic from their research.
    
    Args:
        task_id: The podcast generation task ID
        person_id: The specific persona/person ID to research
        topic: The topic or aspect to explore
    """
    return f"""Let's explore {person_id}'s perspective on "{topic}" from the podcast research.

Please use the MySalonCast resources to:
1. Get the persona research: research://{task_id}/{person_id}
2. Review their background, expertise, and viewpoints

Based on their research profile, help me understand:
- How would {person_id} approach this topic "{topic}"?
- What unique insights would they bring?
- What questions would they ask?
- How does their background influence their perspective?

Use the research data to provide specific examples of how {person_id} would discuss "{topic}" in a podcast conversation."""

@mcp.prompt()
def analyze_podcast_content(
    task_id: str,
    analysis_type: Literal["outline", "transcript", "personas", "summary"] = "summary"
) -> str:
    """Generates a prompt for analyzing different aspects of podcast content.
    
    Args:
        task_id: The podcast generation task ID  
        analysis_type: Type of analysis to perform
    """
    resource_map = {
        "outline": f"podcast://{task_id}/outline",
        "transcript": f"podcast://{task_id}/transcript", 
        "personas": f"research://{task_id}/[person_id]",
        "summary": f"podcast://{task_id}/metadata"
    }
    
    if analysis_type == "personas":
        return f"""Let's analyze the persona research for this podcast task: {task_id}

First, get the podcast metadata to see available personas: podcast://{task_id}/metadata

Then for each persona, examine their research:
- research://{task_id}/[person_id] (replace [person_id] with actual IDs)

Help me understand:
- What personas were researched for this podcast?
- What are their key characteristics and expertise areas?
- How do their perspectives complement each other?
- What interesting contrasts or synergies exist between them?"""
    
    return f"""Let's analyze the {analysis_type} for podcast task: {task_id}

Please access the resource: {resource_map[analysis_type]}

Based on the {analysis_type} data, help me understand:
- What are the key themes and topics covered?
- How well structured is the content?
- What are the most interesting insights or discussion points?
- Are there any areas that could be enhanced or expanded?

Provide a thoughtful analysis with specific examples from the content."""

# =============================================================================
# MCP TOOLS  
# =============================================================================

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
    podcast_length: str = "5-7 minutes",  # Accept time strings like "7 minutes", "5-7 minutes", etc.
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
            desired_podcast_length_str=podcast_length,
            custom_prompt_for_outline=custom_prompt if custom_prompt else None
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

# PHASE 4.4: Job Status and Podcast Resources
# =============================================================================

@mcp.resource("jobs://{task_id}/status")
async def get_job_status_resource(task_id: str) -> dict:
    """
    Get job status resource.
    Returns detailed status information for a podcast generation task.
    """
    logger.info(f"Resource 'job status' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        return {
            "task_id": task_id,
            "status": status_info.status,
            "progress_percentage": status_info.progress_percentage,
            "current_step": status_info.status_description,  # Map status_description to current_step
            "start_time": status_info.created_at.isoformat() if status_info.created_at else None,
            "end_time": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None,
            "error_message": status_info.error_message,
            "artifact_availability": status_info.artifacts.model_dump() if status_info.artifacts else None,
            "resource_type": "job_status"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        raise ToolError(f"Failed to retrieve job status: {str(e)}")


@mcp.resource("jobs://{task_id}/logs")
async def get_job_logs_resource(task_id: str) -> dict:
    """
    Get job logs resource.
    Returns structured log information for a podcast generation task.
    """
    logger.info(f"Resource 'job logs' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        # Get logs from the status info
        logs = []
        if hasattr(status_info, 'logs') and status_info.logs:
            logs = status_info.logs
        
        return {
            "task_id": task_id,
            "logs": logs,
            "log_count": len(logs),
            "last_updated": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None,
            "current_step": status_info.status_description,
            "resource_type": "job_logs"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        raise ToolError(f"Failed to retrieve job logs: {str(e)}")


@mcp.resource("jobs://{task_id}/warnings")
async def get_job_warnings_resource(task_id: str) -> dict:
    """
    Get job warnings resource.
    Returns warning and error information for a podcast generation task.
    """
    logger.info(f"Resource 'job warnings' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        # Extract warnings from episode data if available
        warnings = []
        if status_info.result_episode and hasattr(status_info.result_episode, 'warnings'):
            warnings = status_info.result_episode.warnings or []
        
        return {
            "task_id": task_id,
            "warnings": warnings,
            "warning_count": len(warnings),
            "has_errors": status_info.status == "failed",
            "error_message": status_info.error_message,
            "last_updated": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None,
            "resource_type": "job_warnings"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        raise ToolError(f"Failed to retrieve job warnings: {str(e)}")


@mcp.resource("podcast://{task_id}/transcript")
async def get_podcast_transcript_resource(task_id: str) -> dict:
    """
    Get podcast transcript resource.
    Returns transcript content for a completed podcast.
    """
    logger.info(f"Resource 'podcast transcript' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        return {
            "task_id": task_id,
            "transcript": status_info.result_episode.transcript or "",
            "title": status_info.result_episode.title or "",
            "summary": status_info.result_episode.summary or "",
            "character_count": len(status_info.result_episode.transcript) if status_info.result_episode.transcript else 0,
            "resource_type": "podcast_transcript"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        elif "not available" in str(e):
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        raise ToolError(f"Failed to retrieve podcast transcript: {str(e)}")


@mcp.resource("podcast://{task_id}/audio")
async def get_podcast_audio_resource(task_id: str) -> dict:
    """
    Get podcast audio resource.
    Returns audio file information for a completed podcast.
    """
    logger.info(f"Resource 'podcast audio' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        audio_filepath = status_info.result_episode.audio_filepath or ""
        audio_exists = os.path.exists(audio_filepath) if audio_filepath else False
        
        return {
            "task_id": task_id,
            "audio_filepath": audio_filepath,
            "audio_exists": audio_exists,
            "file_size": os.path.getsize(audio_filepath) if audio_exists else 0,
            "resource_type": "podcast_audio"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        elif "not available" in str(e):
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        raise ToolError(f"Failed to retrieve podcast audio: {str(e)}")


@mcp.resource("podcast://{task_id}/metadata")
async def get_podcast_metadata_resource(task_id: str) -> dict:
    """
    Get podcast metadata resource.
    Returns metadata for a completed podcast episode.
    """
    logger.info(f"Resource 'podcast metadata' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        return {
            "task_id": task_id,
            "title": status_info.result_episode.title or "",
            "summary": status_info.result_episode.summary or "",
            "duration": getattr(status_info.result_episode, 'duration', None),
            "source_attributions": status_info.result_episode.source_attributions or [],
            "creation_date": status_info.created_at.isoformat() if status_info.created_at else None,
            "completion_date": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None,
            "resource_type": "podcast_metadata"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        elif "not available" in str(e):
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        raise ToolError(f"Failed to retrieve podcast metadata: {str(e)}")


@mcp.resource("podcast://{task_id}/outline")
async def get_podcast_outline_resource(task_id: str) -> dict:
    """
    Get podcast outline resource.
    Returns outline/structure information for a podcast episode.
    """
    logger.info(f"Resource 'podcast outline' accessed for task_id: {task_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        # Try to get outline from the file path stored in the episode
        outline_data = None
        outline_file_path = status_info.result_episode.llm_podcast_outline_path
        
        if outline_file_path and os.path.exists(outline_file_path):
            try:
                with open(outline_file_path, 'r') as f:
                    outline_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read outline file {outline_file_path}: {e}")
                outline_data = None
        
        return {
            "task_id": task_id,
            "outline": outline_data,
            "has_outline": outline_data is not None,
            "outline_file_path": outline_file_path,
            "resource_type": "podcast_outline"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        elif "not available" in str(e):
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        raise ToolError(f"Failed to retrieve podcast outline: {str(e)}")


@mcp.resource("research://{task_id}/{person_id}")
async def get_persona_research_resource(task_id: str, person_id: str) -> dict:
    """
    Get persona research resource for a specific person in a podcast generation task.
    Returns research data loaded from PersonaResearch JSON file.
    """
    logger.info(f"Resource 'persona research' accessed for task_id: {task_id}, person_id: {person_id}")
    
    # Basic input validation
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    if not person_id or not person_id.strip():
        raise ToolError("person_id is required")
    
    if len(task_id) < 10 or len(task_id) > 100:
        raise ToolError("Invalid task_id format")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        episode = status_info.result_episode
        
        # Check if task has any persona research files
        if not episode.llm_persona_research_paths:
            raise ToolError(f"No persona research available for task: {task_id}")
        
        # Find the research file for the requested person_id
        target_filename = f"persona_research_{person_id}.json"
        research_file_path = None
        
        for file_path in episode.llm_persona_research_paths:
            if os.path.basename(file_path) == target_filename:
                research_file_path = file_path
                break
        
        if not research_file_path:
            # Extract available person_ids from this task's files for error message
            available_persons = []
            for path in episode.llm_persona_research_paths:
                filename = os.path.basename(path)
                if filename.startswith("persona_research_") and filename.endswith(".json"):
                    available_person_id = filename[17:-5]  # Remove "persona_research_" and ".json"
                    available_persons.append(available_person_id)
            
            if available_persons:
                raise ToolError(f"Person '{person_id}' not found in task {task_id}. Available persons: {', '.join(available_persons)}")
            else:
                raise ToolError(f"No persona research files found for task: {task_id}")
        
        # Read and parse the PersonaResearch JSON file
        research_data = None
        file_exists = os.path.exists(research_file_path)
        file_size = 0
        
        if file_exists:
            try:
                file_size = os.path.getsize(research_file_path)
                with open(research_file_path, 'r', encoding='utf-8') as f:
                    research_json = json.load(f)
                    research_data = research_json
                    logger.info(f"Successfully loaded persona research for {person_id} from {research_file_path}")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Failed to parse persona research JSON for {person_id}: {e}")
                research_data = None
            except Exception as e:
                logger.error(f"Error reading persona research file for {person_id}: {e}")
                research_data = None
        
        return {
            "task_id": task_id,
            "person_id": person_id,
            "research_data": research_data,
            "has_research": research_data is not None,
            "file_metadata": {
                "research_file_path": research_file_path,
                "file_exists": file_exists,
                "file_size": file_size
            },
            "resource_type": "persona_research"
        }
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        elif "not available" in str(e) or "not found" in str(e):
            raise  # Re-raise specific errors with original message
        raise ToolError(f"Failed to retrieve persona research: {str(e)}")


# =============================================================================
# Create the HTTP app for uvicorn
# =============================================================================
app = mcp.http_app(transport="streamable-http")

# =============================================================================
if __name__ == "__main__":
    # Run the server using Starlette/Uvicorn
    import uvicorn
    logger.info("Starting MySalonCast MCP server...")
    
    # Run with uvicorn
    # IMPORTANT: The MCP server runs on port 8000
    # All client code should connect to this port using http://localhost:8000
    # The MySalonCastMCPClient class in tests/mcp/client.py implements the correct approach
    uvicorn.run(app, host="0.0.0.0", port=8000)
