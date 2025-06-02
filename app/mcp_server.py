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
        
        # Build response based on status - status_info is a PodcastStatus model, not a dict
        response = {
            "success": True,
            "task_id": task_id,
            "status": status_info.status,
            "progress_percentage": status_info.progress_percentage,
            "stage": status_info.status_description or "",
            "message": status_info.status_description or ""
        }
        
        # Add episode data if completed
        if status_info.status == "completed" and status_info.result_episode:
            episode = status_info.result_episode
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
        elif status_info.status == "failed":
            response["error"] = status_info.error_message or "Unknown error"
            response["error_details"] = status_info.error_details
        
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
    
    if status_info.status != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info.status}")
    
    if not status_info.result_episode:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info.result_episode
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
    
    if status_info.status != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info.status}")
    
    if not status_info.result_episode:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info.result_episode
    
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
    
    if status_info.status != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info.status}")
    
    if not status_info.result_episode:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info.result_episode
    
    return {
        "title": episode.title,
        "summary": episode.summary,
        "source_attributions": episode.source_attributions,
        "warnings": episode.warnings,
        "audio_filepath": episode.audio_filepath,
        "created_at": status_info.created_at.isoformat() if status_info.created_at else "",
        "completed_at": status_info.last_updated_at.isoformat() if status_info.last_updated_at else ""
    }

@mcp.resource("podcast://{task_id}/outline")
async def get_outline_resource(task_id: str) -> dict:
    """
    Get the podcast outline for a completed podcast episode.
    
    Returns the structured outline including segments, timing, and content cues.
    """
    logger.info(f"Resource 'outline' accessed for task_id: {task_id}")
    
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    if status_info.status != "completed":
        raise ValueError(f"Task {task_id} is not completed. Status: {status_info.status}")
    
    if not status_info.result_episode:
        raise ValueError(f"No result found for task {task_id}")
    
    episode = status_info.result_episode
    
    if not episode.llm_podcast_outline_path:
        raise ValueError(f"No outline data available for task {task_id}")
    
    # Check if outline file exists
    import os
    import json
    if not os.path.exists(episode.llm_podcast_outline_path):
        raise ValueError(f"Outline file not found: {episode.llm_podcast_outline_path}")
    
    try:
        # Read and return the outline JSON content
        with open(episode.llm_podcast_outline_path, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        
        return {
            "outline": outline_data,
            "outline_filepath": episode.llm_podcast_outline_path,
            "task_id": task_id,
            "generated_at": status_info.created_at.isoformat() if status_info.created_at else ""
        }
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in outline file {episode.llm_podcast_outline_path}: {e}")
    except Exception as e:
        raise ValueError(f"Error reading outline file: {e}")

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

@mcp.resource("config://app")
async def get_app_config() -> dict:
    """
    Get MySalonCast application configuration and settings.
    
    Returns app-level configuration including limits, features, and system info.
    """
    logger.info("Resource 'config://app' accessed")
    
    return {
        "app_name": "MySalonCast",
        "version": "1.0.0",
        "description": "AI-powered podcast generation service",
        "server_info": {
            "mcp_port": 8000,
            "transport": "streamable-http",
            "framework": "FastMCP 2.0"
        },
        "limits": {
            "max_source_urls": 3,
            "max_concurrent_tasks": 3,
            "max_podcast_length_minutes": 15,
            "supported_file_size_mb": 50
        },
        "features": {
            "async_generation": True,
            "sync_generation": True,
            "multiple_languages": True,
            "custom_prompts": True,
            "tts_voices": True,
            "pdf_extraction": True,
            "url_extraction": True
        },
        "ai_services": {
            "llm_provider": "Google Gemini",
            "tts_provider": "Google Cloud TTS",
            "voice_count": 30
        }
    }

@mcp.resource("docs://api")
async def get_api_docs() -> dict:
    """
    Get comprehensive API documentation for MySalonCast MCP tools and resources.
    
    Returns detailed documentation for all available MCP endpoints.
    """
    logger.info("Resource 'docs://api' accessed")
    
    return {
        "tools": {
            "hello": {
                "description": "Simple greeting tool for testing connectivity",
                "parameters": [],
                "returns": "String greeting message",
                "example": "Hello, MCP Tester!"
            },
            "generate_podcast_async": {
                "description": "Start async podcast generation with individual parameters",
                "parameters": {
                    "source_urls": "List[str] - URLs to extract content from (max 3)",
                    "source_pdf_path": "str - Path to PDF file",
                    "prominent_persons": "List[str] - People to research",
                    "custom_prompt": "str - Additional instructions",
                    "podcast_name": "str - Name of the podcast show",
                    "podcast_tagline": "str - Tagline for the podcast",
                    "output_language": "str - Language code (e.g., 'en', 'es')",
                    "dialogue_style": "str - Style ('engaging', 'formal', 'casual')",
                    "podcast_length": "str - Duration like '5-7 minutes'",
                    "ending_message": "str - Custom ending message"
                },
                "returns": "Dict with task_id and initial status",
                "workflow": "Returns immediately with task_id, use get_task_status to monitor"
            },
            "generate_podcast_async_pydantic": {
                "description": "Start async podcast generation with structured PodcastRequest",
                "parameters": {
                    "request": "PodcastRequest - Complete request model"
                },
                "returns": "Dict with task_id and initial status",
                "workflow": "Same as generate_podcast_async but with structured input"
            },
            "get_task_status": {
                "description": "Get status and progress of async podcast generation",
                "parameters": {
                    "task_id": "str - Task ID from generate_podcast_async"
                },
                "returns": "Dict with status, progress_percentage, stage, message",
                "status_values": ["queued", "preprocessing_sources", "generating_outline", "generating_transcript", "generating_audio", "completed", "failed"]
            }
        },
        "resources": {
            "config://supported_formats": "Supported input/output formats and configuration",
            "config://app": "Application configuration and limits",
            "docs://api": "This API documentation",
            "examples://requests": "Example podcast generation requests",
            "podcast://{task_id}/transcript": "Episode transcript for completed podcast",
            "podcast://{task_id}/audio": "Audio file info for completed podcast",
            "podcast://{task_id}/metadata": "Episode metadata for completed podcast",
            "podcast://{task_id}/outline": "Episode outline for completed podcast",
            "jobs://{task_id}/status": "Comprehensive job status and progress information",
            "jobs://{task_id}/logs": "Detailed log entries with timestamps and progress updates",
            "jobs://{task_id}/warnings": "Warnings and error information from generation process"
        },
        "authentication": "None required for MCP protocol",
        "rate_limits": "3 concurrent tasks maximum",
        "error_handling": "All tools return success:false with error details on failure"
    }

@mcp.resource("examples://requests")
async def get_example_requests() -> dict:
    """
    Get example podcast generation requests to guide users.
    
    Returns sample requests for different use cases and scenarios.
    """
    logger.info("Resource 'examples://requests' accessed")
    
    return {
        "basic_url_example": {
            "description": "Simple podcast from web articles",
            "tool": "generate_podcast_async",
            "request": {
                "source_urls": [
                    "https://example.com/tech-news-article",
                    "https://example.com/industry-trends"
                ],
                "podcast_name": "Tech Weekly",
                "podcast_tagline": "Your weekly dose of technology news",
                "output_language": "en",
                "dialogue_style": "engaging",
                "podcast_length": "5-7 minutes"
            }
        },
        "research_podcast_example": {
            "description": "Research-focused podcast with prominent persons",
            "tool": "generate_podcast_async",
            "request": {
                "source_urls": ["https://example.com/ai-research-paper"],
                "prominent_persons": ["Geoffrey Hinton", "Yann LeCun"],
                "custom_prompt": "Focus on the implications for neural network architecture",
                "podcast_name": "AI Research Roundup",
                "dialogue_style": "formal",
                "podcast_length": "10-15 minutes",
                "ending_message": "Thanks for listening to AI Research Roundup"
            }
        },
        "pdf_example": {
            "description": "Podcast from PDF document",
            "tool": "generate_podcast_async",
            "request": {
                "source_pdf_path": "/path/to/research-paper.pdf",
                "podcast_name": "Paper Review",
                "dialogue_style": "casual",
                "podcast_length": "7-10 minutes",
                "custom_prompt": "Explain this in simple terms for a general audience"
            }
        },
        "multilingual_example": {
            "description": "Spanish language podcast",
            "tool": "generate_podcast_async",
            "request": {
                "source_urls": ["https://example.com/spanish-news"],
                "output_language": "es",
                "podcast_name": "Noticias Tech",
                "dialogue_style": "engaging",
                "podcast_length": "5-7 minutes"
            }
        },
        "pydantic_model_example": {
            "description": "Using structured PodcastRequest model",
            "tool": "generate_podcast_async_pydantic",
            "request": {
                "request": {
                    "source_urls": ["https://example.com/startup-news"],
                    "podcast_name": "Startup Stories",
                    "podcast_tagline": "Inspiring entrepreneur journeys",
                    "output_language": "en",
                    "dialogue_style": "engaging",
                    "podcast_length": "5-7 minutes",
                    "custom_prompt": "Focus on lessons learned and actionable insights"
                }
            }
        },
        "workflow_example": {
            "description": "Complete async workflow example",
            "steps": [
                {
                    "step": 1,
                    "action": "Submit generation request",
                    "tool": "generate_podcast_async",
                    "expected_response": {"success": True, "task_id": "uuid-here", "status": "queued"}
                },
                {
                    "step": 2,
                    "action": "Check initial status",
                    "tool": "get_task_status",
                    "parameters": {"task_id": "uuid-from-step-1"},
                    "expected_response": {"success": True, "status": "preprocessing_sources", "progress_percentage": 5.0}
                },
                {
                    "step": 3,
                    "action": "Monitor progress",
                    "tool": "get_task_status",
                    "note": "Repeat every 10-30 seconds until status is 'completed' or 'failed'"
                },
                {
                    "step": 4,
                    "action": "Access completed podcast",
                    "resources": [
                        "podcast://{task_id}/transcript",
                        "podcast://{task_id}/audio",
                        "podcast://{task_id}/metadata",
                        "podcast://{task_id}/outline"
                    ]
                }
            ]
        }
    }

@mcp.resource("jobs://{task_id}/status")
async def get_job_status_resource(task_id: str) -> dict:
    """
    Get comprehensive job status and progress information.
    
    Returns real-time status, progress, stage details, and timing for any task.
    Works for active, completed, and failed tasks.
    """
    logger.info(f"Resource 'jobs://{task_id}/status' accessed for task_id: {task_id}")
    
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    # Build comprehensive status response
    response = {
        "task_id": task_id,
        "status": status_info.status,
        "progress_percentage": status_info.progress_percentage,
        "stage": status_info.status_description or "No description available",
        "timestamps": {
            "created_at": status_info.created_at.isoformat() if status_info.created_at else "",
            "last_updated_at": status_info.last_updated_at.isoformat() if status_info.last_updated_at else ""
        }
    }
    
    # Add request summary for context
    if status_info.request_data:
        response["request_summary"] = {
            "prominent_persons": status_info.request_data.prominent_persons,
            "source_urls": status_info.request_data.source_urls,
            "desired_podcast_length": status_info.request_data.desired_podcast_length_str or "5 minutes",
            "source_pdf_path": status_info.request_data.source_pdf_path,
            "host_invented_name": status_info.request_data.host_invented_name,
            "webhook_url": status_info.request_data.webhook_url
        }
    
    # Add error details if task failed
    if status_info.status == "failed":
        response["error"] = {
            "message": status_info.error_message or "Unknown error",
            "details": status_info.error_details
        }
    
    # Add completion details if task succeeded
    if status_info.status == "completed" and status_info.result_episode:
        episode = status_info.result_episode
        response["completion"] = {
            "title": episode.title,
            "duration_seconds": episode.duration_seconds,
            "warnings_count": len(episode.warnings) if episode.warnings else 0,
            "artifacts_available": {
                "transcript": bool(episode.transcript),
                "audio": bool(episode.audio_filepath),
                "outline": bool(episode.llm_podcast_outline_path),
                "metadata": True
            }
        }
    
    # Add artifacts availability for any status
    if status_info.artifacts:
        response["artifacts"] = status_info.artifacts
    
    return response

@mcp.resource("jobs://{task_id}/logs")
async def get_job_logs_resource(task_id: str) -> dict:
    """
    Get detailed log entries for a podcast generation task.
    
    Returns comprehensive log information including timestamps, status changes,
    and progress updates for any task (active, completed, failed, or cancelled).
    
    Args:
        task_id: The task ID to get logs for
        
    Returns:
        Dict with task ID, logs list, and log metadata
    """
    logger.info(f"Resource 'jobs://{task_id}/logs' requested")
    
    # Get status info from StatusManager
    status_info = status_manager.get_status(task_id)
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    # Extract logs from status info
    logs = status_info.logs if status_info.logs else []
    
    # Parse log entries to provide structured information
    parsed_logs = []
    for log_entry in logs:
        # Try to parse structured log entries (format: timestamp - Status: ..., Progress: ..., Description: ...)
        if " - Status: " in log_entry:
            parts = log_entry.split(" - ", 1)
            timestamp = parts[0]
            message = parts[1] if len(parts) > 1 else log_entry
            
            # Try to extract status, progress, and description
            status_match = None
            progress_match = None
            description_match = None
            
            if ", Progress: " in message and ", Description: " in message:
                # Format: Status: {status}, Progress: {progress}%, Description: {description}
                status_part = message.split(", Progress: ")[0].replace("Status: ", "")
                progress_part = message.split(", Progress: ")[1].split(", Description: ")[0].replace("%", "")
                description_part = message.split(", Description: ")[1]
                
                status_match = status_part
                try:
                    progress_match = float(progress_part)
                except ValueError:
                    progress_match = None
                description_match = description_part if description_part != "N/A" else None
            
            parsed_logs.append({
                "timestamp": timestamp,
                "message": message,
                "level": "info",  # Default level
                "status": status_match,
                "progress": progress_match,
                "description": description_match
            })
        else:
            # Unstructured log entry
            parsed_logs.append({
                "timestamp": None,
                "message": log_entry,
                "level": "info",
                "status": None,
                "progress": None,
                "description": None
            })
    
    return {
        "task_id": task_id,
        "logs": logs,  # Raw log entries
        "parsed_logs": parsed_logs,  # Structured log data
        "log_count": len(logs),
        "task_status": status_info.status,
        "last_updated": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None
    }

@mcp.resource("jobs://{task_id}/warnings")
async def get_job_warnings_resource(task_id: str) -> dict:
    """
    Get detailed warnings and error information for a podcast generation task.
    
    Returns warnings from both the generation process and final episode,
    along with error details if the task failed.
    """
    logger.info(f"Resource 'jobs://{task_id}/warnings' accessed for task_id: {task_id}")
    
    status_info = status_manager.get_status(task_id)
    
    if not status_info:
        raise ValueError(f"Task not found: {task_id}")
    
    warnings = []
    error_info = None
    
    # Get warnings from completed episode
    if status_info.result_episode and status_info.result_episode.warnings:
        warnings = status_info.result_episode.warnings
    
    # Get error information if task failed
    if status_info.status == "failed":
        error_info = {
            "error_message": status_info.error_message,
            "error_details": status_info.error_details,
            "occurred_at": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None
        }
        # Include error message as a warning entry for consistency
        if status_info.error_message:
            warnings.append(f"ERROR: {status_info.error_message}")
    
    # Parse warnings to extract structured data
    parsed_warnings = []
    for warning in warnings:
        # Basic parsing of warning format
        warning_entry = {
            "message": warning,
            "type": "error" if warning.startswith("ERROR:") or warning.startswith("CRITICAL") else 
                    "warning" if warning.startswith("WARNING:") else "info",
            "severity": "high" if any(keyword in warning.upper() for keyword in ["ERROR", "CRITICAL", "FAILED", "FAILURE"]) else
                       "medium" if any(keyword in warning.upper() for keyword in ["WARNING", "WARN"]) else "low"
        }
        
        # Extract stage information if available
        if "analysis" in warning.lower():
            warning_entry["stage"] = "source_analysis"
        elif "persona" in warning.lower() or "research" in warning.lower():
            warning_entry["stage"] = "persona_research"
        elif "outline" in warning.lower():
            warning_entry["stage"] = "outline_generation"
        elif "dialogue" in warning.lower():
            warning_entry["stage"] = "dialogue_generation"
        elif "tts" in warning.lower() or "audio" in warning.lower():
            warning_entry["stage"] = "audio_generation"
        elif "stitch" in warning.lower():
            warning_entry["stage"] = "audio_stitching"
        else:
            warning_entry["stage"] = "general"
        
        parsed_warnings.append(warning_entry)
    
    return {
        "task_id": task_id,
        "warnings": warnings,  # Raw warning messages
        "parsed_warnings": parsed_warnings,  # Structured warning data
        "warning_count": len(warnings),
        "error_info": error_info,  # Detailed error info if failed
        "task_status": status_info.status,
        "has_errors": status_info.status == "failed",
        "last_updated": status_info.last_updated_at.isoformat() if status_info.last_updated_at else None
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
    
    # Create the HTTP app with streamable-http transport (recommended for FastMCP 2.0+)
    # This provides efficient bidirectional communication over HTTP
    # Clients should connect to the base URL (no /sse endpoint needed)
    app = mcp.http_app(transport="streamable-http")
    
    # Run with uvicorn
    # IMPORTANT: The MCP server runs on port 8000
    # All client code should connect to this port using http://localhost:8000
    # The MySalonCastMCPClient class in tests/mcp/client.py implements the correct approach
    uvicorn.run(app, host="0.0.0.0", port=8000)
