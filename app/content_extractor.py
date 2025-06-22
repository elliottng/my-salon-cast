# app/content_extractor.py

import pdfplumber
from fastapi import UploadFile
import io
import httpx # For making async HTTP requests
from bs4 import BeautifulSoup # For parsing HTML
import re # For YouTube video ID extraction
import asyncio # For running blocking calls in a separate thread
import os
from .common_exceptions import ExtractionError
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Graceful Firecrawl import
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False

logger = logging.getLogger(__name__)

# Regex to extract YouTube video ID from various URL formats
# Captures the 11-character video ID
YOUTUBE_VIDEO_ID_REGEX = re.compile(
    r'(?:https?://)?(?:www\.)?'
    r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)'
    r'([a-zA-Z0-9_-]{11})'
)

def _is_firecrawl_enabled() -> bool:
    """
    Check if Firecrawl is available and configured for use.
    
    Returns:
        True if Firecrawl SDK is available, FIRECRAWL_ENABLED is set to true,
        and FIRECRAWL_API_KEY exists in environment variables.
    """
    if not FIRECRAWL_AVAILABLE:
        return False
    
    # Check if explicitly enabled
    enabled = os.environ.get('FIRECRAWL_ENABLED', '').lower() == 'true'
    if not enabled:
        return False
    
    # Check if API key exists
    api_key = os.environ.get('FIRECRAWL_API_KEY', '')
    if not api_key:
        logger.warning("FIRECRAWL_ENABLED is true but FIRECRAWL_API_KEY is not set")
        return False
    
    return True

async def extract_text_from_pdf(file: UploadFile) -> str:
    """
    Extracts all text content from an uploaded PDF file.

    Args:
        file: The UploadFile object, assumed to be a validated PDF.

    Returns:
        A string containing all extracted text from the PDF.
        Returns an empty string if no text could be extracted or if an error occurs.
    """
    all_text = []
    try:
        await file.seek(0)
        # Read file content and create BytesIO object for pdfplumber
        content = await file.read()
        pdf_file = io.BytesIO(content)
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
        return "\n".join(all_text)
    except Exception as e:
        err_msg = f"Error extracting text from PDF {file.filename}: {e}"
        raise ExtractionError(err_msg)

async def extract_text_from_pdf_path(pdf_path: str) -> str:
    """
    Extracts all text content from a PDF file specified by its path.

    Args:
        pdf_path: The absolute or relative path to the PDF file.

    Returns:
        A string containing all extracted text from the PDF.
        Raises ExtractionError if the file doesn't exist, is not a PDF, or text extraction fails.
    """
    all_text = []
    if not os.path.exists(pdf_path):
        raise ExtractionError(f"PDF file not found at path: {pdf_path}")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages: # Check if PDF has pages (basic validation)
                raise ExtractionError(f"No pages found in PDF: {pdf_path}. It might be empty or corrupted.")
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
        if not all_text:
            # If all_text is empty after processing, it could be an image-based PDF or truly empty.
            # pdfplumber's extract_text() returns None for pages with no text, or empty string.
            # Consider if this should be an ExtractionError or just return empty string.
            # For now, let's be consistent: if no text, it's an issue for podcast generation.
            raise ExtractionError(f"No text could be extracted from PDF: {pdf_path}. It might be image-based or empty.")
        return "\n".join(all_text)
    except Exception as e:
        # Catch other potential errors from pdfplumber or file operations
        err_msg = f"Error extracting text from PDF at path {pdf_path}: {e}"
        raise ExtractionError(err_msg)


# Global client to prevent 'cannot schedule new futures after shutdown' errors
_http_client = None

async def get_http_client():
    """
    Returns a singleton httpx.AsyncClient instance to prevent 
    'cannot schedule new futures after shutdown' errors when 
    processing multiple URLs in sequence.
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=10.0)
    return _http_client

async def _extract_with_beautifulsoup(url: str) -> str:
    """
    Extract content from URL using Beautiful Soup (original method).
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Extracted text content
        
    Raises:
        ExtractionError: If extraction fails
    """
    client = await get_http_client()
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

    content_type = response.headers.get("content-type", "").lower()
    if "html" not in content_type:
        print(f"Content at {url} is not HTML (type: {content_type}). Returning raw content if text-based.")
        # For non-HTML, decide if we want to return raw text or nothing
        # For now, let's try to decode if it's a text type, otherwise empty
        if "text/" in content_type:
            return response.text
        raise ExtractionError(f"Content at {url} is not HTML and not a recognized text type (type: {content_type}).")

    soup = BeautifulSoup(response.content, 'html.parser')

    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()

    # Get text from the body, or specific tags. This is a basic approach.
    # More sophisticated extraction might target <article>, <main>, or specific class/id attributes.
    body = soup.find('body')
    if body:
        # Get text from all elements, join with space, then strip extra whitespace
        text_content = body.get_text(separator=' ', strip=True)
        return text_content
    else:
        # Fallback if no body tag (unlikely for valid HTML)
        text_content = soup.get_text(separator=' ', strip=True)
        if not text_content:
            raise ExtractionError(f"No text content found in body or fallback for URL: {url}")
        return text_content

async def _extract_with_firecrawl(url: str) -> str:
    """
    Extract content from URL using Firecrawl (fallback method).
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Extracted text content
        
    Raises:
        ExtractionError: If extraction fails or Firecrawl is not configured
    """
    api_key = os.environ.get('FIRECRAWL_API_KEY', '')
    if not api_key:
        raise ExtractionError("Firecrawl API key not configured")
    
    try:
        # Use asyncio.to_thread to run the synchronous Firecrawl API call
        def scrape_url():
            if not FIRECRAWL_AVAILABLE:
                raise ExtractionError("Firecrawl is not installed")
            app = FirecrawlApp(api_key=api_key)
            result = app.scrape_url(
                url,
                formats=['markdown'],
                only_main_content=True
            )
            return result
        
        result = await asyncio.to_thread(scrape_url)
        
        # Extract content from result
        content = ''
        if result and hasattr(result, 'markdown'):
            # Try to access markdown content directly
            content = result.markdown
        elif result and isinstance(result, dict):
            # Fallback to dict access
            if 'markdown' in result:
                content = result['markdown']
            elif 'content' in result:
                content = result['content']
            elif 'text' in result:
                content = result['text']
        
        if not content:
            raise ExtractionError(f"No content extracted by Firecrawl from URL: {url}")
        
        return content.strip()
        
    except Exception as e:
        raise ExtractionError(f"Firecrawl extraction failed for URL {url}: {e}")

async def extract_content_from_url(url: str) -> str:
    """
    Fetches and extracts relevant text content from a given URL.
    Attempts to parse HTML and extract text from common elements.
    """
    try:
        # Try Beautiful Soup first
        return await _extract_with_beautifulsoup(url)

    except Exception as e:
        # If Beautiful Soup fails (including HTTP errors), try Firecrawl if enabled
        beautifulsoup_error = e
        
        if _is_firecrawl_enabled():
            logger.warning(f"Beautiful Soup extraction failed for {url}: {e}. Trying Firecrawl fallback...")
            try:
                content = await _extract_with_firecrawl(url)
                logger.info(f"Successfully extracted content from {url} using Firecrawl fallback")
                return content
            except Exception as firecrawl_error:
                logger.error(f"Firecrawl extraction also failed for {url}: {firecrawl_error}")
        
        # If we get here, either Firecrawl is not enabled or both methods failed
        # Raise the original Beautiful Soup error to maintain backward compatibility
        if isinstance(beautifulsoup_error, httpx.HTTPStatusError):
            err_msg = f"HTTP error {beautifulsoup_error.response.status_code} while fetching {url}: {beautifulsoup_error}"
            print(err_msg)
            raise ExtractionError(err_msg)
        elif isinstance(beautifulsoup_error, httpx.RequestError):
            err_msg = f"Request error while fetching {url}: {beautifulsoup_error}"
            print(err_msg)
            raise ExtractionError(err_msg)
        else:
            err_msg = f"Error extracting content from URL {url}: {beautifulsoup_error}"
            print(err_msg)
            raise ExtractionError(err_msg)

async def _extract_with_assemblyai(url: str) -> str:
    """Extract YouTube transcript using AssemblyAI async API (direct fetch via audio_url)."""
    if os.environ.get("ASSEMBLYAI_ENABLED", "true").lower() != "true":
        raise ExtractionError("AssemblyAI disabled")
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise ExtractionError("ASSEMBLYAI_API_KEY not set")
    headers = {"authorization": api_key, "content-type": "application/json"}
        # Resolve YouTube URL to a direct audio stream via yt_dlp
    # Step 1: resolve YouTube link to a direct audio stream URL
    try:
        import yt_dlp
        ydl_opts = {"format": "bestaudio/best", "quiet": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_src = info["url"]
    except Exception as e:
        raise ExtractionError(f"Failed to extract audio stream from YouTube link: {e}")

    async with httpx.AsyncClient(timeout=180) as client:
        # Step 2: download the audio data into memory (works for typical <50 MB videos)
        audio_resp = await client.get(audio_src)
        audio_resp.raise_for_status()

        # Step 3: upload to AssemblyAI
        upload_resp = await client.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": api_key},
            content=audio_resp.content,
        )
        upload_resp.raise_for_status()
        upload_url = upload_resp.json()["upload_url"]

        # Step 4: create transcription job
        create_resp = await client.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=headers,
            json={"audio_url": upload_url},
        )
        create_resp.raise_for_status()
        tid = create_resp.json()["id"]
        poll_seconds = int(os.environ.get("ASSEMBLYAI_POLL_SECONDS", 5))
        while True:
            await asyncio.sleep(poll_seconds)
            status_resp = await client.get(
                f"https://api.assemblyai.com/v2/transcript/{tid}", headers=headers
            )
            status_resp.raise_for_status()
            data = status_resp.json()
            if data["status"] == "completed":
                return data["text"]
            if data["status"] in {"error", "failed"}:
                raise ExtractionError(f"AssemblyAI error: {data.get('error', 'unknown')}")

async def extract_transcript_from_youtube(url: str) -> str:
    """Extract transcript from a YouTube video using AssemblyAI only."""
    return await _extract_with_assemblyai(url)
