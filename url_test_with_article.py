#!/usr/bin/env python3
"""
Test the podcast workflow by mocking the URL extraction to return our test article
"""
import asyncio
import logging
import os
import sys
from unittest.mock import patch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Add the project directory to the path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    """Run a test of the podcast generation workflow with mocked URL extraction"""
    logger.info("Starting podcast generation test with article content")
    
    # Read the test article content
    article_path = os.path.join(os.path.dirname(__file__), "test_article.txt")
    with open(article_path, 'r', encoding='utf-8') as file:
        article_content = file.read()
    
    logger.info(f"Read test article: {len(article_content)} characters")
    
    # Create an async mock function for extract_content_from_url
    async def mock_extract_url(*args, **kwargs):
        logger.info("Mock extract_content_from_url called with URL")
        return article_content
    
    # Apply the patch to the module
    with patch('app.content_extractor.extract_content_from_url', mock_extract_url):
        # Import after patching to ensure our patch is applied
        from app.podcast_workflow import PodcastGeneratorService, PodcastRequest
        
        # Initialize the service with the patched extraction function
        service = PodcastGeneratorService()
        
        # Create a request with a URL
        request = PodcastRequest(
            source_url="https://example.com/test-article",
            prominent_persons=["Host", "Medical Expert"],
            desired_podcast_length_str="3 minutes"
        )
        
        try:
            logger.info(f"Testing podcast generation with {request.source_url}")
            result = await service.generate_podcast_from_source(request)
            
            logger.info("Test completed!")
            logger.info(f"Podcast title: {result.title}")
            logger.info(f"Warnings: {len(result.warnings)}")
            
            print("\n=== Generated Podcast ===")
            print(f"Title: {result.title}")
            print(f"Summary: {result.summary}")
            print(f"Audio file: {result.audio_filepath}")
            
            if result.warnings:
                print("\nWarnings:")
                for i, warning in enumerate(result.warnings, 1):
                    print(f"{i}. {warning}")
            
            print("\nTranscript preview:")
            if result.transcript:
                # Show first 300 characters of transcript
                print(result.transcript[:300] + "..." if len(result.transcript) > 300 else result.transcript)
            else:
                print("No transcript generated")
            
            return result
        
        except Exception as e:
            logger.error(f"Error during test: {e}", exc_info=True)
            print(f"Error: {e}")
            return None

if __name__ == "__main__":
    asyncio.run(main())
