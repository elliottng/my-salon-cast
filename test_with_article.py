#!/usr/bin/env python3
"""
Direct test of the podcast workflow using test_article.txt content
This version doesn't rely on patching but creates a direct request object
"""
import asyncio
import logging
import os
import sys
import json

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

# Import after path setup
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest

async def main():
    """Run a direct test of the podcast generation workflow"""
    logger.info("Starting direct test of podcast generation with test article")
    
    # Read the test article content
    article_path = os.path.join(os.path.dirname(__file__), "test_article.txt")
    with open(article_path, 'r', encoding='utf-8') as file:
        article_content = file.read()
    
    logger.info(f"Read test article: {len(article_content)} characters")
    
    # Initialize the service
    service = PodcastGeneratorService()
    
    # Create a PDF request (this will bypass URL extraction)
    # We'll create a temporary file with our test article content
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
        tmp.write(article_content.encode('utf-8'))
        tmp_path = tmp.name
    
    try:
        # Use the text file as a "PDF" for testing purposes
        # The content_extractor can handle text files too
        request = PodcastRequest(
            source_pdf_path=tmp_path,  # Use our temp file
            prominent_persons=["Host", "Medical Expert"],
            desired_podcast_length_str="2 minutes"
        )
        
        logger.info(f"Testing podcast generation with file: {tmp_path}")
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
    
    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
            logger.info(f"Temporary file removed: {tmp_path}")

if __name__ == "__main__":
    import tempfile
    asyncio.run(main())
