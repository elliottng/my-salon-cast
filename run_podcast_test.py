#!/usr/bin/env python3
"""
Test runner for podcast generation workflow
"""
import os
import sys
import asyncio
import logging
from pydantic import BaseModel
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('podcast_workflow_test.log')
    ]
)

logger = logging.getLogger(__name__)

# Import the required modules from the app package
sys.path.insert(0, os.path.dirname(__file__))
from app.podcast_workflow import PodcastGeneratorService, PodcastRequest

async def main():
    """Run a test of the podcast generation workflow"""
    logger.info("TEST: Starting podcast generation test...")
    
    service = PodcastGeneratorService()
    
    # Use Google's robots.txt as a simple, stable test source
    request = PodcastRequest(
        source_url="https://www.google.com/robots.txt",
        prominent_persons=["Host"],
        desired_podcast_length_str="1 minute"
    )
    
    try:
        logger.info("TEST: Calling generate_podcast_from_source...")
        episode = await service.generate_podcast_from_source(request)
        
        logger.info(f"TEST: Podcast generation completed with title: {episode.title}")
        logger.info(f"TEST: Audio file path: {episode.audio_filepath}")
        logger.info(f"TEST: Number of warnings: {len(episode.warnings)}")
        
        if episode.warnings:
            logger.warning(f"TEST: Warnings from podcast generation: {episode.warnings}")
            
        print("\n----- Generated Episode -----")
        print(f"Title: {episode.title}")
        print(f"Summary: {episode.summary}")
        print(f"Audio: {episode.audio_filepath}")
        print(f"Warnings: {len(episode.warnings)}")
        if episode.warnings:
            print("\nWarnings:")
            for i, warning in enumerate(episode.warnings, 1):
                print(f"  {i}. {warning}")
                
    except Exception as e:
        logger.error(f"TEST: Error during podcast generation: {e}", exc_info=True)
        print(f"Error during podcast generation: {e}")

if __name__ == "__main__":
    asyncio.run(main())
