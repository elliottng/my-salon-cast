#!/usr/bin/env python3
"""
Test script for podcast generation workflow using a local text file
"""
import asyncio
import logging
import os
import sys

# Add the project root to sys.path to fix import issues
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('podcast_workflow_test.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_podcast_generation():
    """Run a test of the podcast generation workflow with a local text file"""
    logger.info("Starting podcast generation test with local article")
    
    # Initialize the service
    service = PodcastGeneratorService()
    
    # Read the test article content
    article_path = os.path.join(os.path.dirname(__file__), "test_article.txt")
    with open(article_path, 'r') as file:
        article_content = file.read()
    
    logger.info(f"Read test article: {len(article_content)} characters")
    
    # Create a simple request with a valid HTTP URL
    # We'll override the content extraction to return our test article
    request = PodcastRequest(
        source_url="https://example.com/test-article",  # Valid HTTP URL (required by validation)
        prominent_persons=["Host", "Medical Expert"],  # Two personas for more interesting dialogue
        desired_podcast_length_str="3 minutes"  # Keep it short for testing
    )
    
    # Import the content_extraction module
    try:
        from app.content_extraction import extract_content_from_url
        original_extract = extract_content_from_url
        
        # Create our mock extraction function
        async def mock_extract(*args, **kwargs):
            logger.info("Using mock content extraction to return test article")
            return article_content
        
        # Apply the patch
        import app.content_extraction
        app.content_extraction.extract_content_from_url = mock_extract
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"Error importing content_extraction module: {e}")
        sys.exit(1)
    
    try:
        logger.info("Calling generate_podcast_from_source")
        episode = await service.generate_podcast_from_source(request)
        
        logger.info(f"Generation complete. Title: {episode.title}")
        logger.info(f"Summary: {episode.summary}")
        logger.info(f"Transcript length: {len(episode.transcript)} characters")
        logger.info(f"Audio file: {episode.audio_filepath}")
        logger.info(f"Warnings count: {len(episode.warnings)}")
        
        # Print a summary of the episode
        print("\n--- Generated Episode ---")
        print(f"Title: {episode.title}")
        print(f"Summary: {episode.summary}")
        print(f"Audio file: {episode.audio_filepath}")
        print(f"Warnings count: {len(episode.warnings)}")
        
        if episode.warnings:
            print("\nWarnings:")
            for i, warning in enumerate(episode.warnings, 1):
                print(f"  {i}. {warning}")
        
        # Print the transcript
        print("\nTranscript Preview (first 500 chars):")
        if episode.transcript:
            print(episode.transcript[:500] + "...")
        else:
            print("No transcript generated")
        
        return episode
        
    except Exception as e:
        logger.error(f"Error in workflow: {e}", exc_info=True)
        print(f"\nError: {e}")
        return None
        
    finally:
        # Restore the original function
        app.content_extraction.extract_content_from_url = original_extract
        logger.info("Test completed, original extraction function restored")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_podcast_generation())
