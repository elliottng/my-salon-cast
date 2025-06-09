from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
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
