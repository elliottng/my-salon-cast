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

# Enhanced FastAPI app with comprehensive OpenAPI metadata
app = FastAPI(
    title="MySalonCast API",
    description="""
    **MySalonCast** is an AI-powered podcast generation platform that creates engaging podcasts from your content sources.
    
    ## Features
    
    * **PDF Text Extraction** - Extract text content from PDF documents
    * **Async Podcast Generation** - Generate podcasts with multiple personas and custom outlines
    * **Status Tracking** - Real-time tracking of podcast generation progress
    * **Audio Playback** - Stream generated podcasts directly in your browser
    
    ## Workflow
    
    1. **Submit Content** - Provide URLs, PDFs, or custom prompts
    2. **Generate Podcast** - Our AI creates engaging dialogue between personas
    3. **Track Progress** - Monitor generation through detailed status updates
    4. **Listen & Download** - Access your completed podcast via audio endpoint
    
    ## Authentication
    
    This API currently operates without authentication for development purposes.
    
    For production deployments, appropriate authentication should be implemented.
    """,
    version="1.0.0",
    contact={
        "name": "MySalonCast Support",
        "email": "support@mysaloncast.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8002",
            "description": "Development server"
        },
        {
            "url": "https://api.mysaloncast.com",
            "description": "Production server"
        }
    ],
    openapi_tags=[
        {
            "name": "content",
            "description": "Content processing operations"
        },
        {
            "name": "generation",
            "description": "Podcast generation operations"
        },
        {
            "name": "playback",
            "description": "Audio playback and access"
        },
        {
            "name": "status",
            "description": "Task status and monitoring"
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
    **Extract text content from a PDF document**
    
    This endpoint accepts a PDF file upload and extracts all readable text content.
    The extracted text can then be used as source material for podcast generation.
    
    **Parameters:**
    - **pdf_file**: PDF document to process (max file size varies by server configuration)
    
    **Returns:**
    - **filename**: Original filename of the uploaded PDF
    - **message**: Status message indicating success or failure
    - **extracted_text_snippet**: First 500 characters of extracted text (for preview)
    - **total_extracted_characters**: Total number of characters extracted
    
    **Error Responses:**
    - **400 Bad Request**: Invalid PDF file or corrupted document
    - **500 Internal Server Error**: Text extraction failure
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
    **Start asynchronous podcast generation**
    
    Initiates the AI-powered podcast generation process using your provided content sources.
    Returns immediately with a task ID for tracking progress.
    
    **Process Overview:**
    1. **Source Analysis** - AI analyzes your content sources
    2. **Persona Research** - Creates detailed persona profiles for dialogue participants  
    3. **Outline Generation** - Structures the podcast with engaging segments
    4. **Dialogue Creation** - Generates natural conversation between personas
    5. **Audio Synthesis** - Converts dialogue to high-quality speech
    6. **Final Assembly** - Combines all segments into polished podcast
    
    **Request Body:**
    - **source_urls**: List of web URLs to extract content from
    - **source_pdf_path**: Path to PDF file for content extraction
    - **prominent_persons**: List of personas to include in dialogue
    - **desired_podcast_length_str**: Target duration (e.g., "15-20 minutes")
    - **custom_prompt_for_outline**: Optional custom instructions for structure
    - **host_invented_name**: Optional custom name for podcast host
    - **host_gender**: Host gender preference ("male", "female", "neutral")
    - **custom_prompt_for_dialogue**: Optional custom dialogue instructions
    - **webhook_url**: Optional webhook for completion notifications
    
    **Returns:**
    - **task_id**: Unique identifier for tracking this generation task
    - **message**: Confirmation message
    - **status_url**: Endpoint URL for checking progress
    
    **Usage:**
    Use the returned task_id with the `/status/{task_id}` endpoint to monitor progress.
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


@app.get("/podcast/{podcast_id}/audio", tags=["playback"], summary="Stream Podcast Audio")
async def get_podcast_audio(podcast_id: str):
    """
    **Stream or download completed podcast audio**
    
    Provides access to the final generated podcast audio file with an embedded web player.
    The audio file can be streamed directly in the browser or downloaded for offline listening.
    
    **Parameters:**
    - **podcast_id**: Unique identifier of the completed podcast (same as task_id from generation)
    
    **Returns:**
    - **HTML Response**: Web page with embedded audio player and download link
    - **Audio Format**: MP3 format optimized for podcast consumption
    - **Quality**: High-quality speech synthesis with natural intonation
    
    **Features:**
    - **Browser Playback**: Embedded HTML5 audio player with controls
    - **Download Option**: Direct download link for offline access
    - **Responsive Design**: Works on desktop and mobile browsers
    
    **Error Responses:**
    - **404 Not Found**: Podcast audio file not available (generation may still be in progress)
    
    **Usage Tips:**
    - Ensure podcast generation is completed before accessing this endpoint
    - Check task status first using `/status/{task_id}` endpoint
    - Audio files are typically 10-50MB depending on podcast length
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
@app.get("/status/{task_id}", response_model=PodcastStatus, tags=["status"], summary="Get Task Status")
async def get_task_status(task_id: str):
    """
    **Get detailed status of podcast generation task**
    
    Provides comprehensive information about the current state of a podcast generation task,
    including progress percentage, current phase, available artifacts, and any errors.
    
    **Parameters:**
    - **task_id**: Unique identifier returned from the generation endpoint
    
    **Returns:**
    - **task_id**: Echo of the requested task identifier
    - **status**: Current phase (queued, analyzing_sources, generating_dialogue, etc.)
    - **status_description**: Human-readable description of current activity
    - **progress_percentage**: Overall completion percentage (0-100)
    - **created_at**: When the task was initially queued
    - **last_updated_at**: Most recent status update timestamp
    - **request_data**: Original generation request parameters
    - **result_episode**: Complete podcast data (when finished)
    - **error_message**: Summary of any errors encountered
    - **error_details**: Detailed error information for debugging
    - **logs**: Chronological list of key events and milestones
    - **artifacts**: Availability status of intermediate files (outline, transcript, etc.)
    
    **Status Values:**
    - **queued**: Task accepted and waiting to start
    - **preprocessing_sources**: Downloading and validating content sources
    - **analyzing_sources**: AI analysis of source material
    - **researching_personas**: Creating detailed persona profiles
    - **generating_outline**: Structuring podcast segments and flow
    - **generating_dialogue**: Creating natural conversation between personas
    - **generating_audio_segments**: Converting text to speech
    - **stitching_audio**: Combining segments into final audio file
    - **postprocessing_final_episode**: Final quality checks and packaging
    - **completed**: Podcast ready for playback
    - **failed**: Generation encountered unrecoverable error
    - **cancelled**: Task was cancelled by user or system
    
    **Polling Guidance:**
    - Check status every 10-30 seconds during generation
    - Most podcasts complete within 5-15 minutes
    - Monitor `progress_percentage` for completion estimates
    """
    status_manager = get_status_manager()
    status = status_manager.get_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return status
