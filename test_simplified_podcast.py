#!/usr/bin/env python
"""
Test script to verify the simplified podcast generation process.
This tests the single-segment approach for both outline and dialogue generation.
"""

import asyncio
import logging
import os
import json
from dotenv import load_dotenv

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add the app directory to the path so we can import our modules
from app.podcast_models import PodcastEpisode, PodcastOutline, OutlineSegment
from app.podcast_workflow import PodcastRequest
from app.llm_service import GeminiService
from app.podcast_workflow import PodcastGeneratorService

async def main():
    """
    Test the simplified podcast generation workflow.
    """
    logger.info("Testing simplified podcast generation...")
    
    # Initialize services
    llm_service = GeminiService()
    
    # Test data for source content
    test_article = "This is a test article about artificial intelligence. " \
                  "AI has made significant progress in recent years, with models like " \
                  "GPT and Gemini pushing the boundaries of what's possible. " \
                  "These models can now generate text, images, and even code. " \
                  "However, there are also concerns about AI safety and ethics."
    
    # Test podcast outline generation
    logger.info("Generating simplified podcast outline...")
    source_analyses = ["This article provides an overview of recent AI advances and concerns."]
    persona_research = []
    
    # Generate podcast outline with single segment
    podcast_outline = await llm_service.generate_podcast_outline_async(
        source_analyses=source_analyses,
        persona_research_docs=persona_research,
        desired_podcast_length_str="5 minutes",
        num_prominent_persons=0,
        names_prominent_persons_list=[]
    )
    
    logger.info(f"Generated podcast outline: {podcast_outline.title_suggestion}")
    logger.info(f"Number of segments: {len(podcast_outline.segments)}")
    for segment in podcast_outline.segments:
        logger.info(f"Segment ID: {segment.segment_id}, Title: {segment.segment_title}")
        logger.info(f"Duration: {segment.estimated_duration_seconds} seconds")
    
    # Verify we have a single segment
    if len(podcast_outline.segments) != 1:
        logger.warning(f"Expected 1 segment, but got {len(podcast_outline.segments)}")
    else:
        logger.info("PASS: Single segment outline generated successfully")
    
    # Test dialogue generation with the single segment outline
    logger.info("Generating dialogue for single segment outline...")
    dialogue_turns = await llm_service.generate_dialogue_async(
        podcast_outline=podcast_outline,
        source_analyses=[{"source_text": test_article, "analysis": source_analyses[0]}],
        persona_research_docs=persona_research,
        desired_podcast_length_str="5 minutes",
        num_prominent_persons=0,
        prominent_persons_details=[]
    )
    
    logger.info(f"Generated {len(dialogue_turns)} dialogue turns")
    for i, turn in enumerate(dialogue_turns[:3]):  # Show first 3 turns
        logger.info(f"Turn {i+1}: {turn.speaker_id} - {turn.text[:50]}...")
    
    logger.info("Simplified podcast generation test completed")

if __name__ == "__main__":
    asyncio.run(main())
