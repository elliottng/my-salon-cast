import logging
from fastmcp import FastMCP
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest, PodcastEpisode
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize services required by MCP tools
podcast_service = PodcastGeneratorService()
status_manager = get_status_manager()
task_runner = get_task_runner()
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
    source_urls: list[str] = [],
    source_pdf_path: str = "",
    prominent_persons: list[str] = [],
    custom_prompt: str = "",
    podcast_name: str = "",
    podcast_tagline: str = "",
    output_language: str = "en",
    dialogue_style: str = "engaging",
    podcast_length: str = "5-7 minutes",
    ending_message: str = ""
) -> dict:
    """
    Start async podcast generation and return immediately with task_id.
    
    Provide either source_urls OR source_pdf_path (not both).
    Use get_task_status with the returned task_id to check progress.
    
    Args:
        source_urls: List of URLs to extract content from (max 3)
        source_pdf_path: Path to PDF file to extract content from
        prominent_persons: List of people to research for the podcast
        custom_prompt: Additional instructions for podcast generation
        podcast_name: Name of the podcast show
        podcast_tagline: Tagline for the podcast
        output_language: Language code (e.g., 'en', 'es', 'fr')
        dialogue_style: Style of dialogue ('engaging', 'formal', 'casual')
        podcast_length: Duration like '5-7 minutes'
        ending_message: Custom message for the end of the podcast
        
    Returns:
        Dict with task_id and initial status
    """
    logger.info("MCP Tool 'generate_podcast_async' called")
    
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
        logger.warning(f"Validation failed in generate_podcast_async: {e}")
        return {
            "success": False,
            "error": "Invalid podcast generation parameters",
            "details": str(e)
        }
    
    # Submit async task
    try:
        task_id = await podcast_service.generate_podcast_async(request)
        logger.info(f"Async podcast generation started with task_id: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Podcast generation started. Use get_task_status to check progress."
        }
    except Exception as e:
        logger.error(f"Failed to start async podcast generation: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Failed to start podcast generation",
            "details": str(e)
        }

# Async podcast generation with Pydantic model
@mcp.tool()
async def generate_podcast_async_pydantic(request: PodcastRequest) -> dict:
    """
    Start async podcast generation using a structured PodcastRequest model.
    
    Accepts a complete PodcastRequest object with all configuration options.
    Use get_task_status with the returned task_id to check progress.
    
    Args:
        request: PodcastRequest model with all generation parameters
        
    Returns:
        Dict with task_id and initial status
    """
    logger.info("MCP Tool 'generate_podcast_async_pydantic' called")
    
    try:
        task_id = await podcast_service.generate_podcast_async(request)
        logger.info(f"Async podcast generation started with task_id: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": "Podcast generation started. Use get_task_status to check progress."
        }
    except Exception as e:
        logger.error(f"Failed to start async podcast generation: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Failed to start podcast generation",
            "details": str(e)
        }

# Get status of async task
@mcp.tool()
async def get_task_status(task_id: str) -> dict:
    """
    Get the status of an async podcast generation task.
    
    Returns current status, progress percentage, and result when complete.
    
    Args:
        task_id: The task ID returned by generate_podcast_async
        
    Returns:
        Dict with status information and episode data when complete
    """
    logger.info(f"MCP Tool 'get_task_status' called for task_id: {task_id}")
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            return {
                "success": False,
                "error": "Task not found",
                "details": f"No task found with ID: {task_id}"
            }
        
        # Build response based on status
        response = {
            "success": True,
            "task_id": task_id,
            "status": status_info["status"],
            "progress": status_info.get("progress", 0),
            "stage": status_info.get("stage", ""),
            "message": status_info.get("message", "")
        }
        
        # Add episode data if completed
        if status_info["status"] == "completed" and "result" in status_info:
            episode = status_info["result"]
            response["episode"] = {
                "title": episode.title,
                "summary": episode.summary,
                "transcript": episode.transcript,
                "audio_filepath": episode.audio_filepath,
                "duration_seconds": episode.duration_seconds,
                "source_attributions": episode.source_attributions,
                "warnings": episode.warnings
            }
        
        # Add error details if failed
        elif status_info["status"] == "failed":
            response["error"] = status_info.get("error", "Unknown error")
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Failed to retrieve task status",
            "details": str(e)
        }

# MCP Resources for accessing podcast content

@mcp.resource("podcast://{task_id}/transcript")
async def get_transcript_resource(task_id: str) -> str:
    """
    Get the transcript of a completed podcast episode.
    
    Returns the full transcript text for the specified task.
    """
    logger.info(f"Resource 'transcript' accessed for task_id: {task_id}")
    
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    if status_info["status"] != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info['status']}")
    
    if "result" not in status_info:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info["result"]
    return episode.transcript

@mcp.resource("podcast://{task_id}/audio")
async def get_audio_resource(task_id: str) -> dict:
    """
    Get the audio file path and metadata for a completed podcast.
    
    Returns information about the audio file including path and duration.
    """
    logger.info(f"Resource 'audio' accessed for task_id: {task_id}")
    
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    if status_info["status"] != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info['status']}")
    
    if "result" not in status_info:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info["result"]
    
    # Check if audio file exists
    import os
    if not os.path.exists(episode.audio_filepath):
        raise ValueError(f"Audio file not found: {episode.audio_filepath}")
    
    return {
        "audio_filepath": episode.audio_filepath,
        "duration_seconds": episode.duration_seconds,
        "format": "wav",
        "exists": True
    }

@mcp.resource("podcast://{task_id}/metadata")
async def get_metadata_resource(task_id: str) -> dict:
    """
    Get complete metadata for a podcast episode.
    
    Returns all episode information including title, summary, and attributions.
    """
    logger.info(f"Resource 'metadata' accessed for task_id: {task_id}")
    
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    if status_info["status"] != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info['status']}")
    
    if "result" not in status_info:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info["result"]
    
    return {
        "title": episode.title,
        "summary": episode.summary,
        "duration_seconds": episode.duration_seconds,
        "source_attributions": episode.source_attributions,
        "warnings": episode.warnings,
        "audio_filepath": episode.audio_filepath,
        "created_at": status_info.get("created_at", ""),
        "completed_at": status_info.get("completed_at", "")
    }

@mcp.resource("config://supported_formats")
async def get_supported_formats() -> dict:
    """
    Get information about supported input and output formats.
    
    Returns configuration details for podcast generation.
    """
    logger.info("Resource 'supported_formats' accessed")
    
    return {
        "input_formats": {
            "urls": {
                "supported": True,
                "max_count": 3,
                "description": "Web URLs for content extraction"
            },
            "pdf": {
                "supported": True,
                "description": "PDF files for content extraction"
            }
        },
        "output_formats": {
            "audio": {
                "format": "wav",
                "sample_rate": 24000,
                "channels": 1
            },
            "transcript": {
                "format": "text",
                "includes_timestamps": False
            }
        },
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "it", "name": "Italian"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "zh", "name": "Chinese"}
        ],
        "dialogue_styles": ["engaging", "formal", "casual"],
        "podcast_lengths": ["3-5 minutes", "5-7 minutes", "7-10 minutes", "10-15 minutes"]
    }

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
    logger.info(f"MCP Tool 'generate_podcast' called")
    try:
        episode = await podcast_service.generate_podcast_from_source(request_data=request_data)
        logger.info(f"MCP Tool 'generate_podcast' completed successfully. Episode title: {episode.title}")
        
        return {
            "success": True,
            "episode": {
                "title": episode.title,
                "summary": episode.summary,
                "transcript": episode.transcript,
                "audio_filepath": episode.audio_filepath,
                "duration_seconds": episode.duration_seconds,
                "source_attributions": episode.source_attributions,
                "warnings": episode.warnings
            }
        }
    except Exception as e:
        logger.error(f"MCP Tool 'generate_podcast' failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Podcast generation failed",
            "details": str(e)
        }

if __name__ == "__main__":
    # Run the server using Starlette/Uvicorn
    import uvicorn
    logger.info("Starting MySalonCast MCP server...")
    
    # Create the HTTP app with SSE transport
    app = mcp.http_app(transport="sse")
    
    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
