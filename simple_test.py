#!/usr/bin/env python3
"""
Simple direct test of the podcast generation workflow using the test article
"""
import asyncio
import logging
import os
from unittest.mock import patch, AsyncMock
from app.podcast_workflow import PodcastGeneratorService, PodcastRequest

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Test the podcast workflow with the test article"""
    logger.info("Starting simple test of podcast generation workflow")
    
    # Read the test article content directly from the file
    article_path = os.path.join(os.path.dirname(__file__), "test_article.txt")
    with open(article_path, 'r', encoding='utf-8') as file:
        article_content = file.read()
    
    logger.info(f"Read test article: {len(article_content)} characters")
    
    # We'll modify the PodcastGeneratorService._extract_content method instead of 
    # trying to patch the content_extractor module, which is more reliable
    
    # Create a request with a dummy URL
    request = PodcastRequest(
        source_url="https://example.com/test-article",  # Just a placeholder
        prominent_persons=["Host", "Medical Expert"],  # Appropriate for the AI healthcare article
        desired_podcast_length_str="2 minutes"
    )
    
    # Initialize the service before monkey patching
    service = PodcastGeneratorService()
    
    # Save the original _extract_content method
    original_extract_content = service._extract_content
    
    # Create a replacement method that returns our test article
    async def mock_extract_content(self, request):
        logger.info("Using mock content extraction to return test article")
        return article_content
    
    # Apply the monkey patch directly to the instance method
    import types
    service._extract_content = types.MethodType(mock_extract_content, service)
    
    try:
        logger.info(f"Testing podcast generation with {request.source_url}")
        result = await service.generate_podcast_from_source(request)
        
        logger.info("Test completed successfully!")
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
        
        return result
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        print(f"Error: {e}")
        return None
    finally:
        # Restore the original method
        service._extract_content = original_extract_content
        logger.info("Original extract_content method restored")

if __name__ == "__main__":
    # Simple asyncio run without the patch complexity
    asyncio.run(main())
