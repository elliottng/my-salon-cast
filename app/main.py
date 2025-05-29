from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from app.validations import is_valid_pdf, is_valid_url, is_valid_youtube_url
from app.content_extractor import extract_text_from_pdf, extract_content_from_url, extract_transcript_from_youtube, ExtractionError
from app.podcast_workflow import PodcastRequest, PodcastGeneratorService
from app.podcast_models import PodcastEpisode

app = FastAPI(title="MySalonCast API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to MySalonCast API"}

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
