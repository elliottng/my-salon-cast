#!/usr/bin/env python3
"""
Debug content extraction issues
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.content_extractor import extract_content_from_url

async def test_content_extraction():
    """Test content extraction with various URLs"""
    
    test_urls = [
        "http://localhost:9999/test_content.html",  # Our local content
        "https://httpbin.org/html",  # Simple test HTML
        "https://httpbin.org/json",  # JSON response
        "https://example.com",  # Basic HTML
    ]
    
    for url in test_urls:
        print(f"\n🧪 Testing: {url}")
        try:
            print(f"   ⏳ Starting extraction...")
            content = await extract_content_from_url(url)
            print(f"   ✅ Success: {len(content)} characters")
            print(f"   📝 Preview: {content[:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_content_extraction())
