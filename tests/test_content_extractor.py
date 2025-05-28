# tests/test_content_extractor.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import UploadFile
import io
import httpx
import asyncio

from app.content_extractor import extract_text_from_pdf, extract_content_from_url, extract_transcript_from_youtube
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class MockPdfPage:
    def __init__(self, text_content=""):
        self.text_content = text_content

    def extract_text(self):
        return self.text_content

class MockPdfPlumberPdf:
    def __init__(self, pages=None):
        self.pages = pages if pages is not None else []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


async def test_extract_text_from_pdf_success():
    """Test successful text extraction from a mock PDF."""
    mock_file_content = b"dummy pdf content"
    mock_upload_file = MagicMock(spec=UploadFile)
    mock_upload_file.filename = "test.pdf"
    mock_upload_file.file = io.BytesIO(mock_file_content)
    mock_upload_file.seek = AsyncMock() # Mock the async seek method

    mock_page1 = MockPdfPage(text_content="Hello world")
    mock_page2 = MockPdfPage(text_content="This is a test")
    mock_pdf_object = MockPdfPlumberPdf(pages=[mock_page1, mock_page2])

    with patch('app.content_extractor.pdfplumber.open', return_value=mock_pdf_object) as mock_pdf_open:
        extracted_text = await extract_text_from_pdf(mock_upload_file)
        
        mock_upload_file.seek.assert_awaited_once_with(0)
        mock_pdf_open.assert_called_once_with(mock_upload_file.file)
        assert extracted_text == "Hello world\nThis is a test"

async def test_extract_text_from_pdf_no_text():
    """Test PDF with no extractable text (e.g., image-based)."""
    mock_file_content = b"image pdf content"
    mock_upload_file = MagicMock(spec=UploadFile)
    mock_upload_file.filename = "image.pdf"
    mock_upload_file.file = io.BytesIO(mock_file_content)
    mock_upload_file.seek = AsyncMock()

    mock_page1 = MockPdfPage(text_content=None) # Simulate page.extract_text() returning None
    mock_page2 = MockPdfPage(text_content="")      # Simulate page.extract_text() returning empty string
    mock_pdf_object = MockPdfPlumberPdf(pages=[mock_page1, mock_page2])

    with patch('app.content_extractor.pdfplumber.open', return_value=mock_pdf_object):
        extracted_text = await extract_text_from_pdf(mock_upload_file)
        assert extracted_text == "" # Expect empty string if no text or only empty strings from pages

async def test_extract_text_from_pdf_extraction_error():
    """Test handling of an error during pdfplumber.open or text extraction."""
    mock_file_content = b"corrupted pdf content"
    mock_upload_file = MagicMock(spec=UploadFile)
    mock_upload_file.filename = "error.pdf"
    mock_upload_file.file = io.BytesIO(mock_file_content)
    mock_upload_file.seek = AsyncMock()

    with patch('app.content_extractor.pdfplumber.open', side_effect=Exception("PDF processing error")):
        extracted_text = await extract_text_from_pdf(mock_upload_file)
        assert extracted_text == "" # Expect empty string on error

# --- Tests for extract_content_from_url will go here ---

@pytest.fixture
def mock_httpx_client():
    """Fixture to create a mock httpx.AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client # For async context manager
    mock_client.__aexit__.return_value = None
    return mock_client

async def test_extract_content_from_url_success(mock_httpx_client):
    """Test successful content extraction from a URL returning HTML."""
    test_url = "http://example.com/success"
    html_content = "<html><head><title>Test</title></head><body><p>Hello World</p><span>More text</span></body></html>"
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = html_content.encode('utf-8')
    mock_response.text = html_content # For text/plain fallback, though not primary here
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        mock_httpx_client.get.assert_awaited_once_with(test_url, follow_redirects=True)
        mock_response.raise_for_status.assert_called_once()
        assert "Hello World More text" in content # BeautifulSoup adds spaces

async def test_extract_content_from_url_http_404_error(mock_httpx_client):
    """Test URL returning a 404 HTTP error."""
    test_url = "http://example.com/notfound"
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 404
    # Configure raise_for_status to actually raise an error for this test
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found", request=MagicMock(), response=mock_response
    )
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        assert content == "Error: Could not fetch content due to HTTP status 404."

async def test_extract_content_from_url_http_500_error(mock_httpx_client):
    """Test URL returning a 500 HTTP error."""
    test_url = "http://example.com/servererror"
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Server Error", request=MagicMock(), response=mock_response
    )
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        assert content == "Error: Could not fetch content due to HTTP status 500."

async def test_extract_content_from_url_request_error(mock_httpx_client):
    """Test a network request error (e.g., DNS failure)."""
    test_url = "http://example.com/networkissue"
    mock_httpx_client.get.side_effect = httpx.RequestError("Network error", request=MagicMock())

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        assert content == "Error: Could not fetch content due to a network or request issue."

async def test_extract_content_from_url_non_html_content(mock_httpx_client):
    """Test URL returning non-HTML content (e.g., an image)."""
    test_url = "http://example.com/image.png"
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b"dummy image data"
    mock_response.headers = {"content-type": "image/png"}
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        assert content == ""

async def test_extract_content_from_url_text_plain_content(mock_httpx_client):
    """Test URL returning text/plain content."""
    test_url = "http://example.com/file.txt"
    plain_text = "This is some plain text."
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = plain_text.encode('utf-8')
    mock_response.text = plain_text
    mock_response.headers = {"content-type": "text/plain; charset=utf-8"}
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        assert content == plain_text

async def test_extract_content_from_url_html_no_body(mock_httpx_client):
    """Test HTML content that surprisingly has no <body> tag."""
    test_url = "http://example.com/no_body_html"
    html_content = "<html><head><title>Test</title></head>Hello outside body</html>"
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = html_content.encode('utf-8')
    mock_response.headers = {"content-type": "text/html"}
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        # BeautifulSoup's get_text() on the whole document if no body is found
        assert "Hello outside body" in content

async def test_extract_content_from_url_removes_scripts_and_styles(mock_httpx_client):
    """Test that script and style tags are removed."""
    test_url = "http://example.com/with_scripts"
    html_content = (
        "<html><head><title>Test</title>"
        "<style>body { color: red; }</style></head>"
        "<body><p>Visible text</p>"
        "<script>alert('invisible text');</script>"
        "<span>More visible text</span></body></html>"
    )
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = html_content.encode('utf-8')
    mock_response.headers = {"content-type": "text/html"}
    mock_httpx_client.get.return_value = mock_response

    with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
        content = await extract_content_from_url(test_url)
        assert "Visible text More visible text" in content
        assert "alert('invisible text')" not in content
        assert "body { color: red; }" not in content

# --- Tests for extract_transcript_from_youtube ---

VALID_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Video ID: dQw4w9WgXcQ
INVALID_YOUTUBE_URL_NO_ID = "https://www.youtube.com/watch?v="

@patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
async def test_extract_transcript_success(mock_get_transcript):
    """Test successful transcript extraction."""
    mock_transcript_list = [
        {'text': 'Hello world', 'start': 0.0, 'duration': 1.5},
        {'text': 'this is a test', 'start': 1.5, 'duration': 2.0}
    ]
    mock_get_transcript.return_value = mock_transcript_list
    
    result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
    assert result == "Hello world this is a test"
    mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ')

@patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
async def test_extract_transcript_disabled(mock_get_transcript):
    """Test when transcripts are disabled for a video."""
    mock_get_transcript.side_effect = TranscriptsDisabled('dQw4w9WgXcQ')
    
    result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
    assert result == "Error: Transcripts are disabled for video ID dQw4w9WgXcQ."
    mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ')

@patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
async def test_extract_transcript_no_transcript_found(mock_get_transcript):
    """Test when no transcript is found for a video."""
    # Provide dummy arguments for the NoTranscriptFound exception constructor
    mock_get_transcript.side_effect = NoTranscriptFound('dQw4w9WgXcQ', ['en'], {})
    
    result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
    assert result == "Error: No transcript found for video ID dQw4w9WgXcQ (could be auto-generated only, or none available)."
    mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ')

@patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
async def test_extract_transcript_video_unavailable(mock_get_transcript):
    """Test when a video is unavailable."""
    mock_get_transcript.side_effect = VideoUnavailable('dQw4w9WgXcQ')
    
    result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
    assert result == "Error: Video ID dQw4w9WgXcQ is unavailable."
    mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ')

@patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
async def test_extract_transcript_generic_api_error(mock_get_transcript):
    """Test handling of a generic error from the YouTubeTranscriptApi."""
    mock_get_transcript.side_effect = Exception("Some API error")
    
    result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
    assert result == "Error: An unexpected error occurred while fetching transcript for video ID dQw4w9WgXcQ."
    mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ')

async def test_extract_transcript_invalid_url_no_id():
    """Test with a YouTube URL from which video ID cannot be extracted."""
    result = await extract_transcript_from_youtube(INVALID_YOUTUBE_URL_NO_ID)
    assert result == "Error: Could not extract YouTube video ID from URL."

@patch('app.content_extractor.asyncio.to_thread')
async def test_extract_transcript_asyncio_to_thread_error(mock_to_thread):
    """Test an error occurring during the asyncio.to_thread call itself."""
    mock_to_thread.side_effect = RuntimeError("Simulated asyncio.to_thread error")
    
    result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
    # The video_id is extracted before asyncio.to_thread is called in the current implementation
    assert result == "Error: An unexpected error occurred while preparing to fetch the YouTube transcript."
    mock_to_thread.assert_called_once()
