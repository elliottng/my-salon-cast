# app/validations.py

import re
from fastapi import UploadFile
from typing import Optional

# Basic URL validation regex (reverted to previous working version)
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'  # http:// or https:// or ftp:// or ftps://
    r'(?:[^:@/\s]+(?::[^@/\s]*)?@)?'  # optional user:pass@
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE
)

# Regex for YouTube URL validation (video URLs only)
# Covers: youtube.com/watch?v=, youtu.be/, youtube.com/embed/, youtube.com/shorts/
# Allows http, https, www, m, or no subdomain.
# Video ID must be 11 characters long.
# Allows optional query parameters or fragments after the video ID.
YOUTUBE_URL_REGEX = re.compile(
    r"^(?:https?://)?(?:(?:www|m)\.)?"  # Scheme and optional www. or m. subdomain
    r"(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)"  # Domain and video paths
    r"([a-zA-Z0-9_-]{11})"  # 11-character video ID
    r"(?:[?&\#].*)?$"  # Optional query parameters or fragment, then end of string
)

PDF_MAGIC_NUMBER = b"%PDF-"

async def is_valid_pdf(file: UploadFile) -> bool:
    """
    Validates if the uploaded file is a PDF.
    Checks file extension and the first few bytes (magic number).
    """
    if not file.filename:
        return False
    if not file.filename.lower().endswith(".pdf"):
        return False
    
    # Read the first few bytes to check for PDF magic number
    try:
        contents = await file.read(len(PDF_MAGIC_NUMBER))
        await file.seek(0)  # Reset file pointer to the beginning for subsequent reads
        if contents == PDF_MAGIC_NUMBER:
            return True
    except Exception:
        # Handle potential errors during file read
        return False
    return False

def is_valid_url(url: str) -> bool:
    """
    Validates if the provided string is a valid URL.
    """
    if not url or not isinstance(url, str):
        return False
    return re.match(URL_REGEX, url) is not None

def is_valid_youtube_url(url: str) -> bool:
    """
    Validates if the provided string is a valid YouTube video URL.
    It also checks if it's a generally valid URL first, prepending https:// if no scheme is present.
    """
    if not url or not isinstance(url, str):
        return False

    normalized_url = url
    if not (url.startswith('http://') or url.startswith('https://')):
        normalized_url = 'https://' + url
    
    # First ensure it's a structurally valid URL (after potential normalization)
    if not is_valid_url(normalized_url):
        return False
    
    # Then check against the specific YouTube regex
    return re.match(YOUTUBE_URL_REGEX, normalized_url) is not None

# Example usage (can be removed or moved to tests later)
if __name__ == "__main__":
    # Test URL validation
    print(f"'http://example.com' is valid: {is_valid_url('http://example.com')}")
    print(f"'https://www.example.co.uk/path?query=param' is valid: {is_valid_url('https://www.example.co.uk/path?query=param')}")
    print(f"'ftp://user:pass@example.com:21/file.txt' is valid: {is_valid_url('ftp://user:pass@example.com:21/file.txt')}")
    print(f"'just a string' is valid: {is_valid_url('just a string')}")
    print(f"'' is valid: {is_valid_url('')}")
    print(f"'http://localhost:8000' is valid: {is_valid_url('http://localhost:8000')}")

    # Test YouTube URL validation
    print("\n--- YouTube URL Tests ---")
    yt_urls_to_test = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("http://youtu.be/dQw4w9WgXcQ", True),
        ("https://youtube.com/embed/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/shorts/abcdefghijk", True),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL...", True), # With extra params
        ("www.youtube.com/watch?v=dQw4w9WgXcQ", True), # No scheme
        ("youtube.com/watch?v=dQw4w9WgXcQ", True), # No scheme, no www
        ("https://www.youtube.com/watch?v=short", False), # Invalid ID length
        ("https://www.youtube.com/playlist?list=PL...", False), # Playlist URL, not video
        ("https://vimeo.com/12345678", False), # Not YouTube
        ("http://example.com", False),
        ("just a string", False),
    ]
    for yt_url, expected in yt_urls_to_test:
        actual = is_valid_youtube_url(yt_url)
        status = "PASS" if actual == expected else "FAIL"
        print(f"'{yt_url}' is valid YouTube URL: {actual} (Expected: {expected}) - {status}")

    # PDF validation would require a mock UploadFile object to test here directly
    # For now, we'll assume it works as intended and test via API endpoints later.
