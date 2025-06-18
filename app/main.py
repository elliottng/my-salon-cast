from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
from datetime import datetime
from app.validations import is_valid_pdf
from app.content_extractor import extract_text_from_pdf, ExtractionError
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastEpisode, PodcastStatus, PodcastRequest
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner
from app.config import setup_environment, get_config

# Setup configuration and environment
config = setup_environment("REST API")
logger = logging.getLogger(__name__)

# Enhanced FastAPI app with comprehensive OpenAPI metadata
app = FastAPI(
    title="MySalonCast API",
    description="""AI-powered podcast generation platform. Extract text from PDFs, generate engaging podcasts with multiple personas, track progress, and stream audio. Perfect for content creators and educators.""",
    version="1.0.0",
    contact={
        "name": "MySalonCast Support",
        "email": "support@mysaloncast.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    servers=[
        {
            "url": "https://mysaloncast-api-644248751086.us-west1.run.app",
            "description": "Production server"
        }
    ],
    openapi_tags=[
        {
            "name": "content",
            "description": "Content processing endpoints"
        },
        {
            "name": "generation",
            "description": "Podcast generation endpoints"
        },
        {
            "name": "playback",
            "description": "Audio streaming endpoints"
        },
        {
            "name": "status",
            "description": "Status tracking endpoints"
        }
    ]
)

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

@app.post("/process/pdf/", tags=["content"], summary="Extract Text from PDF")
async def process_pdf_endpoint(pdf_file: UploadFile = File(...)):
    """
    Extract text content from a PDF document for podcast generation.

    Upload a PDF file to extract readable text content. Returns filename,
    extraction status, text snippet preview, and total character count.
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


@app.post("/generate/podcast_async/", tags=["generation"], summary="Start Podcast Generation")
async def generate_podcast_async_endpoint(request: PodcastRequest):
    """
    Start asynchronous podcast generation with AI-powered content creation.

    Initiates podcast generation using provided content sources. Returns task ID
    for tracking progress and status URL for monitoring.
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


@app.get("/podcast/{task_id}/audio", tags=["playback"], summary="Stream Podcast Audio")
async def get_podcast_audio(task_id: str):
    """
    Stream or download completed podcast audio with embedded web player.

    Provides access to final generated podcast audio file with playback controls.
    """
    # Get the task status to retrieve the audio file path
    status_manager = get_status_manager()
    status = status_manager.get_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"Podcast generation not completed. Current status: {status.status}")
    
    if not status.result_episode or not status.result_episode.audio_filepath:
        raise HTTPException(status_code=404, detail="Podcast audio not found")
    
    audio_filepath = status.result_episode.audio_filepath
    
    # Check if it's a cloud URL
    if audio_filepath.startswith(('http://', 'https://', 'gs://')):
        # For cloud URLs, redirect to the actual URL or embed it directly
        if audio_filepath.startswith('gs://'):
            # Convert gs:// URL to public HTTPS URL
            # gs://bucket/path -> https://storage.googleapis.com/bucket/path
            gs_path = audio_filepath[5:]  # Remove 'gs://' prefix
            audio_url = f"https://storage.googleapis.com/{gs_path}"
            logger.info(f"Converted gs:// URL to public URL: {audio_url}")
        else:
            # For HTTP/HTTPS URLs, we can embed them directly
            audio_url = audio_filepath
    else:
        # For local files, verify the file exists
        if not os.path.exists(audio_filepath):
            # Try the old path structure as fallback
            fallback_path = f"./outputs/audio/{task_id}/final.mp3"
            if os.path.exists(fallback_path):
                audio_url = f"/audio/{task_id}/final.mp3"
            else:
                raise HTTPException(status_code=404, detail=f"Podcast audio file not found at {audio_filepath}")
        else:
            # Extract the relative path for serving via static files
            # The audio_filepath might be something like ./outputs/audio/<task_id>/final.mp3
            if audio_filepath.startswith("./outputs/audio/"):
                relative_path = audio_filepath.replace("./outputs/audio/", "")
                audio_url = f"/audio/{relative_path}"
            else:
                # If it's a different local path, we can't serve it via static files
                raise HTTPException(
                    status_code=503, 
                    detail=f"Cannot serve audio from path: {audio_filepath}"
                )

    # Return HTML with audio player
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MySalonCast - Podcast Player</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .info {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .player-container {{ margin: 20px 0; }}
            audio {{ width: 100%; }}
            .download-link {{ display: inline-block; margin-top: 10px; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }}
            .download-link:hover {{ background-color: #45a049; }}
            .error {{ color: #d32f2f; background-color: #ffebee; padding: 10px; border-radius: 4px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>MySalonCast Podcast Player</h1>
        <div class="info">
            <strong>Title:</strong> {status.result_episode.title}<br>
            <strong>Task ID:</strong> {task_id}<br>
            <strong>Status:</strong> {status.status}
        </div>
        <div class="player-container">
            <audio controls>
                <source src="{audio_url}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
        </div>
        <a class="download-link" href="{audio_url}" download>Download Audio</a>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@app.get("/privacy-policy", tags=["content"], summary="View Privacy Policy")
async def get_privacy_policy():
    """
    View the MySalonCast privacy policy.

    Returns the full text of the privacy policy.
    """
    try:
        with open("./templates/privacy_policy.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Privacy policy not found")


# Status management endpoints
@app.get("/status/{task_id}", response_model=PodcastStatus, tags=["status"], summary="Get Task Status")
async def get_task_status(task_id: str):
    """
    Get detailed status of podcast generation task with progress updates.

    Provides current phase, progress percentage, and available artifacts.
    """
    status_manager = get_status_manager()
    status = status_manager.get_status(task_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return status


# Health check endpoint
@app.get("/health", tags=["status"], summary="Health Check")
async def health_check():
    """
    Health check endpoint for monitoring and load balancer probes.

    Returns service status and basic system information.
    """
    return {
        "status": "healthy",
        "service": "MySalonCast API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
