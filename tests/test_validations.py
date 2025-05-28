# tests/test_validations.py

import pytest
import io
from fastapi import UploadFile
from app.validations import is_valid_url, is_valid_pdf, PDF_MAGIC_NUMBER, is_valid_youtube_url

# --- Tests for is_valid_url ---

@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://example.com", True),
        ("https://www.example.co.uk/path?query=param#fragment", True),
        ("ftp://user:pass@example.com:21/file.txt", True),
        ("http://localhost", True),
        ("http://localhost:8000", True),
        ("https://127.0.0.1/test", True),
        ("https://1.2.3.4:1234/a/b/c", True),
        ("http://example.com/path_with_underscore", True),
        ("http://example.com/path-with-hyphen", True),
        ("just a string", False),
        ("", False),
        (None, False),
        ("htp://malformed.com", False),
        ("http//malformed.com", False),
        ("http:/malformed.com", False),
        ("http:malformed.com", False),
        ("example.com", False), # Missing scheme
        ("www.example.com", False), # Missing scheme
        ("//example.com", False), # Scheme-relative URL, our regex might not support, depends on strictness
    ],
)
def test_is_valid_url(url: str, expected: bool):
    assert is_valid_url(url) == expected

# --- Tests for is_valid_pdf ---

class MockUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self.file = io.BytesIO(content)

    async def read(self, size: int = -1) -> bytes:
        return self.file.read(size)

    async def seek(self, offset: int) -> int:
        return self.file.seek(offset)

    def __getattr__(self, name):
        # Forward other attribute access to the underlying BytesIO object if needed
        # For UploadFile, 'filename' and 'file' (or read/seek methods) are key.
        return getattr(self.file, name)

@pytest.mark.asyncio
async def test_is_valid_pdf_valid():
    """Test with a valid PDF (correct extension and magic number)."""
    content = PDF_MAGIC_NUMBER + b" rest of pdf content"
    mock_file = MockUploadFile(filename="test.pdf", content=content)
    assert await is_valid_pdf(mock_file) == True

@pytest.mark.asyncio
async def test_is_valid_pdf_invalid_extension():
    """Test with an invalid file extension."""
    content = PDF_MAGIC_NUMBER + b" rest of pdf content"
    mock_file = MockUploadFile(filename="test.txt", content=content)
    assert await is_valid_pdf(mock_file) == False

@pytest.mark.asyncio
async def test_is_valid_pdf_invalid_magic_number():
    """Test with correct extension but invalid magic number."""
    content = b"NOT PDF" + b" rest of content"
    mock_file = MockUploadFile(filename="test.pdf", content=content)
    assert await is_valid_pdf(mock_file) == False

@pytest.mark.asyncio
async def test_is_valid_pdf_empty_content():
    """Test with an empty file content."""
    mock_file = MockUploadFile(filename="empty.pdf", content=b"")
    assert await is_valid_pdf(mock_file) == False

@pytest.mark.asyncio
async def test_is_valid_pdf_no_filename():
    """Test with no filename provided for UploadFile."""
    # FastAPI's UploadFile might not allow filename to be None directly,
    # but our validation checks for it.
    # We can simulate this by setting filename to None or empty string if the mock allows.
    class MockUploadFileNoName(MockUploadFile):
        def __init__(self, content: bytes):
            super().__init__(filename=None, content=content) # type: ignore
    
    mock_file = MockUploadFileNoName(content=PDF_MAGIC_NUMBER)
    # Our current is_valid_pdf checks file.filename first, so this should be False
    # if file.filename is None or empty.
    # Let's adjust the mock or test based on UploadFile's actual behavior if needed.
    # For now, assuming our validation's `if not file.filename:` catches this.
    assert await is_valid_pdf(mock_file) == False

    mock_file_empty_name = MockUploadFile(filename="", content=PDF_MAGIC_NUMBER)
    assert await is_valid_pdf(mock_file_empty_name) == False

@pytest.mark.asyncio
async def test_is_valid_pdf_content_shorter_than_magic_number():
    """Test with content shorter than the PDF magic number."""
    content = b"%P"
    mock_file = MockUploadFile(filename="short.pdf", content=content)
    assert await is_valid_pdf(mock_file) == False

@pytest.mark.asyncio
async def test_is_valid_pdf_file_read_exception():
    """Test scenario where file.read() might raise an exception."""
    class MockUploadFileReadError(MockUploadFile):
        async def read(self, size: int = -1) -> bytes:
            raise IOError("Simulated read error")

    mock_file = MockUploadFileReadError(filename="error.pdf", content=b"")
    assert await is_valid_pdf(mock_file) == False

# --- Tests for is_valid_youtube_url ---

@pytest.mark.parametrize(
    "url, expected",
    [
        # Valid YouTube URLs
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("http://youtu.be/dQw4w9WgXcQ", True),
        ("https://youtube.com/embed/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/shorts/abcdefghijk", True),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLt0000000000000000", True), # With list param
        ("www.youtube.com/watch?v=dQw4w9WgXcQ", True), # No scheme, should be normalized
        ("youtube.com/watch?v=dQw4w9WgXcQ", True), # No scheme or www, should be normalized
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", True), # Mobile URL

        # Invalid YouTube URLs or non-YouTube URLs
        ("https://www.youtube.com/watch?v=short", False), # Video ID too short (5 chars)
        ("https://www.youtube.com/watch?v=too_long_video_id_123", False), # Video ID too long (20 chars)
        ("https://www.youtube.com/playlist?list=PLt0000000000000000", False), # Playlist URL, not a video URL
        ("https://www.youtube.com/watch?v=", False), # Missing video ID
        ("https://www.youtube.com/watch", False), # Missing ?v=
        ("https://vimeo.com/12345678", False), # Non-YouTube domain
        ("http://example.com", False), # Non-YouTube domain
        ("just a string", False), # Not a URL
        ("", False), # Empty string
        (None, False), # None input
        ("https://www.youtube.com/user/channelname", False), # Channel URL
        ("https://www.youtube.com/c/channelname", False), # Channel URL (custom)
        ("https://www.youtube.com/", False), # Base YouTube URL
        ("https://youtube.com", False), # Base YouTube URL (no www)
    ],
)
def test_is_valid_youtube_url(url: str, expected: bool):
    assert is_valid_youtube_url(url) == expected
