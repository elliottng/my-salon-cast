# app/content_extractor.py

import pdfplumber
from fastapi import UploadFile
import io
import httpx # For making async HTTP requests
from bs4 import BeautifulSoup # For parsing HTML
import re # For YouTube video ID extraction
import asyncio # For running blocking calls in a separate thread
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# Regex to extract YouTube video ID from various URL formats
# Captures the 11-character video ID
YOUTUBE_VIDEO_ID_REGEX = re.compile(
    r'(?:https?://)?(?:www\.)?'
    r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)'
    r'([a-zA-Z0-9_-]{11})'
)

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
        with pdfplumber.open(file.file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    all_text.append(page_text)
        return "\n".join(all_text)
    except Exception as e:
        print(f"Error extracting text from PDF {file.filename}: {e}")
        return ""

async def extract_content_from_url(url: str) -> str:
    """
    Fetches and extracts relevant text content from a given URL.
    Attempts to parse HTML and extract text from common elements.
    """
    all_text = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client: # Added timeout
            response = await client.get(url, follow_redirects=True) # Added follow_redirects
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type:
                print(f"Content at {url} is not HTML (type: {content_type}). Returning raw content if text-based.")
                # For non-HTML, decide if we want to return raw text or nothing
                # For now, let's try to decode if it's a text type, otherwise empty
                if "text/" in content_type:
                    return response.text
                return "" # Or handle other content types like plain text specifically

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
                return soup.get_text(separator=' ', strip=True)

    except httpx.HTTPStatusError as e:
        print(f"HTTP error {e.response.status_code} while fetching {url}: {e}")
        return f"Error: Could not fetch content due to HTTP status {e.response.status_code}."
    except httpx.RequestError as e:
        print(f"Request error while fetching {url}: {e}")
        return "Error: Could not fetch content due to a network or request issue."
    except Exception as e:
        print(f"Error extracting content from URL {url}: {e}")
        return "Error: An unexpected error occurred while processing the URL."


async def extract_transcript_from_youtube(url: str) -> str:
    """
    Extracts the transcript from a YouTube video URL.

    Args:
        url: The YouTube video URL.

    Returns:
        A string containing the transcript, or an error message if extraction fails.
    """
    match = YOUTUBE_VIDEO_ID_REGEX.search(url)
    if not match:
        return "Error: Could not extract YouTube video ID from URL."
    video_id = match.group(1)

    def _fetch_and_process_transcript_sync(vid_id: str) -> str:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(vid_id)
            full_transcript = " ".join([item['text'] for item in transcript_list])
            return full_transcript
        except TranscriptsDisabled:
            return f"Error: Transcripts are disabled for video ID {vid_id}."
        except NoTranscriptFound:
            return f"Error: No transcript found for video ID {vid_id} (could be auto-generated only, or none available)."
        except VideoUnavailable:
            return f"Error: Video ID {vid_id} is unavailable."
        except Exception as e:
            # Catch any other exceptions from the library or processing
            print(f"Error fetching transcript for video ID {vid_id}: {e}")
            return f"Error: An unexpected error occurred while fetching transcript for video ID {vid_id}."

    try:
        # Run the synchronous blocking call in a separate thread
        transcript = await asyncio.to_thread(_fetch_and_process_transcript_sync, video_id)
        return transcript
    except Exception as e:
        # Catch potential errors from asyncio.to_thread itself or other unforeseen issues
        print(f"Asyncio error or other issue processing YouTube URL {url} for video ID {video_id}: {e}")
        return "Error: An unexpected error occurred while preparing to fetch the YouTube transcript."
