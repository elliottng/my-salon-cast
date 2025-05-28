from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from app.validations import is_valid_pdf, is_valid_url, is_valid_youtube_url
from app.content_extractor import extract_text_from_pdf, extract_content_from_url, extract_transcript_from_youtube

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
