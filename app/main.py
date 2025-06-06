from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
from app.validations import is_valid_pdf, is_valid_url, is_valid_youtube_url
from app.content_extractor import extract_text_from_pdf, extract_content_from_url, extract_transcript_from_youtube, ExtractionError
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastEpisode, PodcastStatus, PodcastRequest
from pydantic import BaseModel
from typing import List, Optional
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner
from datetime import datetime
from app.config import setup_environment, get_config

# Setup environment and get configuration
config = setup_environment()
logger = logging.getLogger(__name__)

app = FastAPI(title="MySalonCast API")

# Configure CORS with environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for serving audio files
# Create the outputs directory if it doesn't exist based on environment
if config.is_local_environment:
    audio_dir = "./outputs/audio"
    os.makedirs(audio_dir, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=audio_dir), name="audio")
    logger.info(f"Mounted local audio directory: {audio_dir}")
else:
    # In cloud environment, audio files are served from Cloud Storage
    logger.info("Cloud environment detected - audio files served from Cloud Storage")

@app.get("/")
async def root():
    return {
        "message": "Welcome to MySalonCast API",
        "environment": config.environment,
        "version": "1.0.0",
        "features": {
            "secret_manager": config.is_cloud_environment,
            "cloud_storage": config.is_cloud_environment,
            "local_files": config.is_local_environment
        }
    }

@app.post("/process/pdf/")
async def process_pdf_endpoint(pdf_file: UploadFile = File(...)):
    """
    Receives a PDF file, validates it, and extracts its text content.
    """
    if not await is_valid_pdf(pdf_file):
        raise HTTPException(status_code=400, detail="Invalid PDF file. Please upload a valid PDF document.")
    
    extracted_text = await extract_text_from_pdf(pdf_file)
    
    if not extracted_text:
        return {"filename": pdf_file.filename, "message": "PDF validated, but no text could be extracted or an error occurred during extraction.", "extracted_text_snippet": ""}

    snippet_length = 500
    text_snippet = extracted_text[:snippet_length] + ("..." if len(extracted_text) > snippet_length else "")
    
    return {
        "filename": pdf_file.filename, 
        "message": "PDF received, validated, and text extracted successfully.",
        "extracted_text_snippet": text_snippet,
        "total_extracted_characters": len(extracted_text)
    }

@app.post("/process/url/")
async def process_url_endpoint(url: str = Form(...)):
    """
    Receives a URL, validates it, and extracts its text content.
    """
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="Invalid URL provided. Please enter a valid HTTP/HTTPS/FTP URL.")
    
    extracted_content = await extract_content_from_url(url)

    if not extracted_content or extracted_content.startswith("Error:"):
        return {"url": url, "message": "URL validated, but content could not be extracted or an error occurred.", "extracted_content_snippet": extracted_content}

    snippet_length = 500
    content_snippet = extracted_content[:snippet_length] + ("..." if len(extracted_content) > snippet_length else "")

    return {
        "url": url, 
        "message": "URL received, validated, and content extracted successfully.",
        "extracted_content_snippet": content_snippet,
        "total_extracted_characters": len(extracted_content)
    }

@app.post("/process/youtube/")
async def process_youtube_endpoint(url: str = Form(...)):
    """
    Receives a YouTube URL, validates it, and extracts its transcript.
    """
    if not is_valid_youtube_url(url):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL provided. Please enter a valid YouTube video URL.")
    
    transcript = await extract_transcript_from_youtube(url)

    if not transcript or transcript.startswith("Error:"):
        return {"url": url, "message": "YouTube URL validated, but transcript could not be extracted or an error occurred.", "transcript_snippet": transcript}

    snippet_length = 500
    transcript_snippet = transcript[:snippet_length] + ("..." if len(transcript) > snippet_length else "")

    return {
        "url": url, 
        "message": "YouTube URL received, validated, and transcript extracted successfully.",
        "transcript_snippet": transcript_snippet,
        "total_transcript_characters": len(transcript)
    }


@app.post("/generate/podcast_elements/", response_model=PodcastEpisode)
async def generate_podcast_elements_endpoint(request: PodcastRequest):
    """
    Receives a podcast request, performs content extraction, persona research,
    and generates a podcast outline.
    Returns the structured podcast episode data.
    """
    try:
        print(f"Received podcast generation request: {request}")
        generator_service = PodcastGeneratorService()
        print("Created PodcastGeneratorService instance")
        # The service handles the creation of output directories and saving files.
        podcast_episode = await generator_service.generate_podcast_from_source(request)
        print("Successfully generated podcast episode")
        return podcast_episode
    except ExtractionError as e:
        error_msg = f"Content extraction failed: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except ValueError as e: # Catches Pydantic validation errors and other ValueErrors
        error_msg = f"Validation error: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except AttributeError as e:
        error_msg = f"Attribute error: {str(e)}. This might be due to a missing attribute or method in the service or models."
        print(error_msg)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred during podcast generation: {type(e).__name__} - {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {type(e).__name__}")


@app.post("/generate/podcast_async/")
async def generate_podcast_async_endpoint(request: PodcastRequest):
    """
    Start async podcast generation and return task_id immediately.
    Use the /status/{task_id} endpoint to track progress.
    """
    try:
        generator_service = PodcastGeneratorService()
        task_id = await generator_service.generate_podcast_async(request)
        
        return {
            "task_id": task_id,
            "message": "Podcast generation started",
            "status_url": f"/status/{task_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start podcast generation: {str(e)}")


@app.get("/podcast/{podcast_id}/audio")
@app.get("/listen/{podcast_id}")
async def get_podcast_audio(podcast_id: str):
    """
    Endpoint to get the complete podcast audio file.
    This URL can be used in a browser to listen to the generated podcast.
    
    Args:
        podcast_id: The unique identifier for the podcast
    
    Returns:
        HTML page with an audio player to listen to the podcast
    """
    audio_path = f"./outputs/audio/{podcast_id}/final.mp3"
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Podcast audio not found")
    
    # Return HTML with audio player
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MySalonCast - Podcast Player</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .player-container {{ margin: 20px 0; }}
            audio {{ width: 100%; }}
            .download-link {{ display: inline-block; margin-top: 10px; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }}
            .download-link:hover {{ background-color: #45a049; }}
        </style>
    </head>
    <body>
        <h1>MySalonCast Podcast Player</h1>
        <div class="player-container">
            <audio controls>
                <source src="/audio/{podcast_id}/final.mp3" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </div>
        <a class="download-link" href="/audio/{podcast_id}/final.mp3" download>Download Audio</a>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/podcast/{podcast_id}/segments/{segment_id}")
@app.get("/listen/{podcast_id}/segment/{segment_id}")
async def get_segment_audio(podcast_id: str, segment_id: int):
    """
    Endpoint to get an individual segment audio file.
    
    Args:
        podcast_id: The unique identifier for the podcast
        segment_id: The ID of the segment
    
    Returns:
        HTML page with an audio player to listen to the segment
    """
    audio_path = f"./outputs/audio/{podcast_id}/segments/turn_{segment_id:03d}.mp3"
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Segment audio not found")
    
    # Return HTML with audio player
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MySalonCast - Segment Player</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .player-container {{ margin: 20px 0; }}
            audio {{ width: 100%; }}
            .download-link {{ display: inline-block; margin-top: 10px; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }}
            .download-link:hover {{ background-color: #45a049; }}
            .back-link {{ display: inline-block; margin-top: 10px; padding: 8px 16px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; }}
            .back-link:hover {{ background-color: #0b7dda; }}
        </style>
    </head>
    <body>
        <h1>MySalonCast Segment Player</h1>
        <div class="player-container">
            <p>Segment ID: {segment_id}</p>
            <audio controls>
                <source src="/audio/{podcast_id}/segments/turn_{segment_id:03d}.mp3" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </div>
        <a class="back-link" href="/podcast/{podcast_id}/audio">Back to Full Podcast</a>
        <a class="download-link" href="/audio/{podcast_id}/segments/turn_{segment_id:03d}.mp3" download>Download Segment</a>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


# Status management endpoints
@app.get("/status/{task_id}", response_model=PodcastStatus)
async def get_task_status(task_id: str):
    """
    Get the status of a specific podcast generation task.
    
    Args:
        task_id: The unique identifier for the task
        
    Returns:
        PodcastStatus: The current status of the task including progress, artifacts, and result
        
    Raises:
        HTTPException: 404 if task_id not found
    """
    status_manager = get_status_manager()
    status = status_manager.get_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return status


class StatusListResponse(BaseModel):
    statuses: List[PodcastStatus]
    total: int
    limit: int
    offset: int


@app.get("/status", response_model=StatusListResponse)
async def list_task_statuses(limit: int = 50, offset: int = 0):
    """
    List all podcast generation task statuses with pagination.
    
    Args:
        limit: Maximum number of statuses to return (default: 50, max: 100)
        offset: Number of statuses to skip (default: 0)
        
    Returns:
        StatusListResponse: List of statuses with pagination metadata
    """
    # Enforce maximum limit
    limit = min(limit, 100)
    
    status_manager = get_status_manager()
    statuses = status_manager.list_all_statuses(limit=limit, offset=offset)
    
    # Get total count (we'll get all statuses with a large limit for now)
    # In production, we'd want a separate count query
    total_statuses = len(status_manager.list_all_statuses(limit=1000, offset=0))
    
    return StatusListResponse(
        statuses=statuses,
        total=total_statuses,
        limit=limit,
        offset=offset
    )


@app.delete("/status/{task_id}")
async def delete_task_status(task_id: str):
    """
    Delete a specific task status from the status manager.
    
    Args:
        task_id: The unique identifier for the task to delete
        
    Returns:
        dict: Confirmation message
        
    Raises:
        HTTPException: 404 if task_id not found
    """
    status_manager = get_status_manager()
    deleted = status_manager.delete_status(task_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return {"message": f"Task {task_id} deleted successfully"}


@app.post("/status/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Cancel a running podcast generation task.
    
    Args:
        task_id: The ID of the task to cancel
        
    Returns:
        Dict with success status and message
        
    Raises:
        404: If task_id is not found
        400: If task is not in a cancellable state
    """
    try:
        logger.info(f"Handling POST /status/{task_id}/cancel request")
        
        # Get status from status manager
        try:
            status_manager = get_status_manager()
            status = status_manager.get_status(task_id)
            
            if not status:
                logger.warning(f"Task {task_id} not found in status manager")
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
                
            logger.info(f"Found task {task_id} with status '{status.status}'")
        except Exception as e:
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Error retrieving task status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving task status: {str(e)}")
        
        # Check if task is in a cancellable state
        if status.status in ["completed", "failed", "cancelled"]:
            logger.warning(f"Task {task_id} is already {status.status} and cannot be cancelled")
            raise HTTPException(
                status_code=400, 
                detail=f"Task {task_id} is already {status.status} and cannot be cancelled"
            )
        
        # Get task runner and attempt cancellation
        try:
            task_runner = get_task_runner()
            cancelled = await task_runner.cancel_task(task_id)
            logger.info(f"Cancellation attempt result for task {task_id}: {cancelled}")
        except Exception as e:
            logger.error(f"Error during task cancellation: {str(e)}")
            # Mark as not cancelled due to error, but don't fail the request
            return {
                "task_id": task_id,
                "cancelled": False,
                "message": f"Error attempting to cancel task: {str(e)}"
            }
        
        if cancelled:
            try:
                # Update status to reflect cancellation is pending
                status_manager.update_status(
                    task_id,
                    "cancelled",
                    "Cancellation requested - task is being terminated",
                    progress_percentage=status.progress_percentage
                )
                logger.info(f"Task {task_id} marked as cancelled in status manager")
            except Exception as e:
                logger.error(f"Error updating status after cancellation: {str(e)}")
                # Continue despite status update failure
            
            return {
                "task_id": task_id,
                "cancelled": True,
                "message": "Task cancellation initiated successfully"
            }
        else:
            # Task not found in runner (might have already completed)
            logger.info(f"Task {task_id} not found in active tasks list")
            return {
                "task_id": task_id,
                "cancelled": False,
                "message": "Task not found in active tasks (may have already completed)"
            }
    except HTTPException:
        # Re-raise HTTPExceptions for proper status code handling
        raise
    except Exception as e:
        logger.error(f"Unhandled error in cancel_task endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@app.get("/queue/status")
async def get_queue_status():
    """
    Get the current status of the task queue.
    
    Returns:
        Dict containing queue metrics and active task information
    """
    try:
        logger.info("Handling GET /queue/status request")
        task_runner = get_task_runner()
        
        # Get queue status
        try:
            queue_status = task_runner.get_queue_status()
            logger.debug(f"Queue status: {queue_status}")
        except Exception as e:
            logger.error(f"Error getting queue status: {str(e)}")
            queue_status = {
                "max_workers": task_runner.max_workers,
                "active_tasks": 0,
                "available_slots": task_runner.max_workers,
                "total_submitted": 0,
                "task_ids": []
            }
        
        # Get active tasks
        try:
            active_tasks = task_runner.get_active_tasks()
            logger.debug(f"Active tasks count: {len(active_tasks)}")
        except Exception as e:
            logger.error(f"Error getting active tasks: {str(e)}")
            active_tasks = []
        
        # Get status information for active tasks
        status_manager = get_status_manager()
        active_task_details = []
        
        for task in active_tasks:
            try:
                task_id = task["task_id"]
                status = status_manager.get_status(task_id)
                if status:
                    # Ensure all datetime fields are properly serialized
                    created_at_str = None
                    if status.created_at:
                        try:
                            created_at_str = status.created_at.isoformat()
                        except Exception as e:
                            logger.error(f"Error serializing created_at: {str(e)}")
                    
                    active_task_details.append({
                        "task_id": task_id,
                        "status": status.status,
                        "progress": status.progress_percentage,
                        "description": status.status_description,
                        "started_at": created_at_str,
                        "running": task["running"],
                        "cancelled": task["cancelled"]
                    })
            except Exception as e:
                logger.error(f"Error processing task {task.get('task_id', 'unknown')}: {str(e)}")
        
        # Construct and return response
        response = {
            "queue": queue_status,
            "active_tasks": active_task_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return response
    except Exception as e:
        logger.error(f"Unhandled error in get_queue_status endpoint: {str(e)}")
        # Return a minimalist response rather than failing
        return {
            "queue": {"max_workers": 3, "active_tasks": 0, "available_slots": 3, "total_submitted": 0, "task_ids": []},
            "active_tasks": [],
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Internal error fetching queue status"
        }


@app.get("/health")
async def get_health():
    return {"status": "healthy"}
