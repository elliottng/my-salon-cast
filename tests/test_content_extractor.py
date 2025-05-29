# tests/test_content_extractor.py

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import UploadFile
import io
import httpx
import asyncio

from app.content_extractor import extract_text_from_pdf, extract_content_from_url, extract_transcript_from_youtube, ExtractionError
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


# Common fixtures for all test classes
@pytest.fixture
def mock_pdf_file():
    """Create a mock PDF file for testing."""
    mock_file_content = b"dummy pdf content"
    mock_upload_file = MagicMock(spec=UploadFile)
    mock_upload_file.filename = "test.pdf"
    mock_upload_file.file = io.BytesIO(mock_file_content)
    mock_upload_file.seek = AsyncMock()  # Mock the async seek method
    return mock_upload_file


@pytest.fixture
def mock_pdf_with_text():
    """Create mock PDF pages with text content."""
    return MockPdfPlumberPdf(pages=[
        MockPdfPage(text_content="Hello world"),
        MockPdfPage(text_content="This is a test")
    ])


@pytest.fixture
def mock_pdf_without_text():
    """Create mock PDF pages without text content."""
    return MockPdfPlumberPdf(pages=[
        MockPdfPage(text_content=None),  # Simulate page.extract_text() returning None
        MockPdfPage(text_content="")    # Simulate page.extract_text() returning empty string
    ])


@pytest.fixture
def mock_httpx_client():
    """Fixture to create a mock httpx.AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client  # For async context manager
    mock_client.__aexit__.return_value = None
    return mock_client


# Define YouTube constants for testing
VALID_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Video ID: dQw4w9WgXcQ
INVALID_YOUTUBE_URL_NO_ID = "https://www.youtube.com/watch?v="


class TestPdfExtraction:
    """Tests for PDF text extraction functionality."""
    
    async def test_extract_text_from_pdf_success(self, mock_pdf_file, mock_pdf_with_text):
        """Test successful text extraction from a mock PDF."""
        with patch('app.content_extractor.pdfplumber.open', return_value=mock_pdf_with_text) as mock_pdf_open:
            extracted_text = await extract_text_from_pdf(mock_pdf_file)
            
            mock_pdf_file.seek.assert_awaited_once_with(0)
            mock_pdf_open.assert_called_once_with(mock_pdf_file.file)
            assert extracted_text == "Hello world\nThis is a test"

    async def test_extract_text_from_pdf_no_text(self, mock_pdf_file, mock_pdf_without_text):
        """Test PDF with no extractable text (e.g., image-based)."""
        # Override filename for this test
        mock_pdf_file.filename = "image.pdf"
        
        with patch('app.content_extractor.pdfplumber.open', return_value=mock_pdf_without_text):
            extracted_text = await extract_text_from_pdf(mock_pdf_file)
            assert extracted_text == ""  # Expect empty string if no text or only empty strings from pages

    async def test_extract_text_from_pdf_extraction_error(self, mock_pdf_file):
        """Test handling of an error during pdfplumber.open or text extraction."""
        # Override filename for this test
        mock_pdf_file.filename = "error.pdf"
        error_message = "PDF processing error"
        
        with patch('app.content_extractor.pdfplumber.open', side_effect=Exception(error_message)):
            with pytest.raises(ExtractionError) as excinfo:
                await extract_text_from_pdf(mock_pdf_file)
                
            # Verify error message contains relevant information
            error_str = str(excinfo.value)
            assert "Error extracting text from PDF" in error_str
            assert "error.pdf" in error_str  # filename from test setup
            assert error_message in error_str

class TestUrlContentExtraction:
    """Tests for URL content extraction functionality."""
    
    def setup_mock_response(self, mock_httpx_client, url, status_code, content, content_type, text=None):
        """Set up a mock HTTP response with the given parameters."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.status_code = status_code
        
        if isinstance(content, str):
            mock_response.content = content.encode('utf-8')
        else:
            mock_response.content = content
            
        mock_response.text = text if text is not None else (
            content if isinstance(content, str) else content.decode('utf-8', errors='ignore')
        )
        
        mock_response.headers = {"content-type": content_type}
        mock_httpx_client.get.return_value = mock_response
        return mock_response, url
    
    def verify_extraction_error(self, error_context, *expected_strings):
        """Verify that an ExtractionError contains the expected strings."""
        error_str = str(error_context.value)
        for expected in expected_strings:
            assert expected in error_str
    
    async def test_extract_content_from_url_success(self, mock_httpx_client):
        """Test successful content extraction from a URL returning HTML."""
        html_content = "<html><head><title>Test</title></head><body><p>Hello World</p><span>More text</span></body></html>"
        mock_response, test_url = self.setup_mock_response(
            mock_httpx_client, 
            "http://example.com/success", 
            200, 
            html_content, 
            "text/html; charset=utf-8"
        )

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            content = await extract_content_from_url(test_url)
            mock_httpx_client.get.assert_awaited_once_with(test_url, follow_redirects=True)
            mock_response.raise_for_status.assert_called_once()
            assert "Hello World More text" in content  # BeautifulSoup adds spaces

    @pytest.mark.parametrize("status_code, error_message, path", [
        (404, "Not Found", "notfound"),
        (500, "Server Error", "servererror"),
    ])
    async def test_extract_content_from_url_http_errors(self, mock_httpx_client, status_code, error_message, path):
        """Test URL returning various HTTP errors."""
        test_url = f"http://example.com/{path}"
        mock_response, _ = self.setup_mock_response(
            mock_httpx_client, 
            test_url, 
            status_code, 
            "", 
            "text/html"
        )
        
        # Configure raise_for_status to raise an error with the specified message
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=error_message, request=MagicMock(), response=mock_response
        )

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            with pytest.raises(ExtractionError) as excinfo:
                await extract_content_from_url(test_url)
            
            self.verify_extraction_error(
                excinfo, 
                f"HTTP error {status_code} while fetching {test_url}"
            )
            
            # For 404 errors, we also check for the specific error message
            if status_code == 404:
                assert error_message in str(excinfo.value)

    async def test_extract_content_from_url_request_error(self, mock_httpx_client):
        """Test a network request error (e.g., DNS failure)."""
        test_url = "http://example.com/networkissue"
        error_message = "Network issue"
        mock_httpx_client.get.side_effect = httpx.RequestError(error_message, request=MagicMock())

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            with pytest.raises(ExtractionError) as excinfo:
                await extract_content_from_url(test_url)
            
            self.verify_extraction_error(
                excinfo, 
                f"Request error while fetching {test_url}",
                error_message
            )

    async def test_extract_content_from_url_non_html_content(self, mock_httpx_client):
        """Test URL returning non-HTML content (e.g., an image)."""
        test_url = "http://example.com/image.png"
        mock_response, _ = self.setup_mock_response(
            mock_httpx_client, 
            test_url, 
            200, 
            b"dummy image data", 
            "image/png"
        )

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            with pytest.raises(ExtractionError) as excinfo:
                await extract_content_from_url(test_url)
            
            self.verify_extraction_error(
                excinfo, 
                f"Content at {test_url} is not HTML and not a recognized text type (type: image/png)"
            )

    async def test_extract_content_from_url_text_plain_content(self, mock_httpx_client):
        """Test URL returning text/plain content."""
        test_url = "http://example.com/file.txt"
        plain_text = "This is some plain text."
        self.setup_mock_response(
            mock_httpx_client, 
            test_url, 
            200, 
            plain_text, 
            "text/plain; charset=utf-8"
        )

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            content = await extract_content_from_url(test_url)
            assert content == plain_text

    async def test_extract_content_from_url_html_no_body(self, mock_httpx_client):
        """Test HTML content that surprisingly has no <body> tag."""
        test_url = "http://example.com/no_body_html"
        html_content = "<html><head><title>Test</title></head>Hello outside body</html>"
        self.setup_mock_response(
            mock_httpx_client, 
            test_url, 
            200, 
            html_content, 
            "text/html"
        )

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            content = await extract_content_from_url(test_url)
            # BeautifulSoup's get_text() on the whole document if no body is found
            assert "Hello outside body" in content

    async def test_extract_content_from_url_removes_scripts_and_styles(self, mock_httpx_client):
        """Test that script and style tags are removed."""
        test_url = "http://example.com/with_scripts"
        html_content = (
            "<html><head><title>Test</title>"
            "<style>body { color: red; }</style></head>"
            "<body><p>Visible text</p>"
            "<script>alert('invisible text');</script>"
            "<span>More visible text</span></body></html>"
        )
        self.setup_mock_response(
            mock_httpx_client, 
            test_url, 
            200, 
            html_content, 
            "text/html"
        )

        with patch('app.content_extractor.httpx.AsyncClient', return_value=mock_httpx_client):
            content = await extract_content_from_url(test_url)
            assert "Visible text More visible text" in content
            assert "alert('invisible text')" not in content
            assert "body { color: red; }" not in content

class TestYouTubeTranscriptExtraction:
    """Tests for YouTube transcript extraction functionality."""

    def verify_extraction_error(self, error_context, *expected_strings):
        """Verify that an ExtractionError contains the expected strings."""
        error_str = str(error_context.value)
        for expected in expected_strings:
            assert expected in error_str
    
    @patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
    async def test_extract_transcript_success(self, mock_get_transcript):
        """Test successful transcript extraction."""
        mock_transcript_list = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 1.5},
            {'text': 'this is a test', 'start': 1.5, 'duration': 2.0}
        ]
        mock_get_transcript.return_value = mock_transcript_list
        
        result = await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
        assert result == "Hello world this is a test"
        mock_get_transcript.assert_called_once_with('dQw4w9WgXcQ')
    
    @pytest.mark.parametrize("exception_class, exception_args, expected_message", [
        (TranscriptsDisabled, ['dQw4w9WgXcQ'], "Transcripts are disabled for video ID dQw4w9WgXcQ"),
        (NoTranscriptFound, ['dQw4w9WgXcQ', ['en'], {}], "No transcript found for video ID dQw4w9WgXcQ"),
        (VideoUnavailable, ['dQw4w9WgXcQ'], "Video ID dQw4w9WgXcQ is unavailable"),
        (Exception, ["Some API error"], "Error fetching transcript for video ID dQw4w9WgXcQ: Some API error")
    ])
    @patch('app.content_extractor.YouTubeTranscriptApi.get_transcript')
    async def test_extract_transcript_api_errors(self, mock_get_transcript, exception_class, exception_args, expected_message):
        """Test various error scenarios from the YouTubeTranscriptApi."""
        mock_get_transcript.side_effect = exception_class(*exception_args)
        
        with pytest.raises(ExtractionError) as excinfo:
            await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
        
        self.verify_extraction_error(
            excinfo,
            "Asyncio error or other issue processing YouTube URL",
            expected_message
        )
        
        # Note: Since mock_get_transcript is called inside asyncio.to_thread, we can't directly assert its call count
        # The side effect being triggered is evidence that it was called
    
    async def test_extract_transcript_invalid_url_no_id(self):
        """Test with a YouTube URL from which video ID cannot be extracted."""
        with pytest.raises(ExtractionError) as excinfo:
            await extract_transcript_from_youtube(INVALID_YOUTUBE_URL_NO_ID)
        
        self.verify_extraction_error(
            excinfo,
            "Could not extract YouTube video ID from URL"
        )

    @patch('app.content_extractor.asyncio.to_thread')
    async def test_extract_transcript_asyncio_to_thread_error(self, mock_to_thread):
        """Test an error occurring during the asyncio.to_thread call itself."""
        error_message = "Simulated asyncio.to_thread error"
        mock_to_thread.side_effect = RuntimeError(error_message)
        
        with pytest.raises(ExtractionError) as excinfo:
            await extract_transcript_from_youtube(VALID_YOUTUBE_URL)
        
        self.verify_extraction_error(
            excinfo,
            "Asyncio error or other issue processing YouTube URL",
            error_message
        )
        mock_to_thread.assert_called_once()
