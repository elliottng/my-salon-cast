#!/usr/bin/env python3
"""
YouTube Integration Test for MySalonCast

Tests the complete YouTube URL processing pipeline:
1. YouTube URL validation
2. Transcript extraction 
3. Podcast generation workflow with YouTube sources
"""

import asyncio
import sys
import os
import logging
import time
from typing import List

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest
from app.content_extractor import extract_transcript_from_youtube, ExtractionError
from app.validations import is_valid_youtube_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test YouTube URLs - using well-known videos with transcripts
TEST_YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=9bZkp7q19f0",  # TED Talk - confirmed working
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - confirmed working
]

async def test_youtube_url_validation():
    """Test YouTube URL validation function."""
    logger.info("🔍 Testing YouTube URL validation...")
    
    test_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", True),
        ("https://www.youtube.com/shorts/abcdefghijk", True),
        ("https://www.google.com", False),
        ("not a url", False),
        ("https://www.youtube.com/playlist?list=PLtest", False),
    ]
    
    all_passed = True
    for url, expected in test_cases:
        result = is_valid_youtube_url(url)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        logger.info(f"  {status} '{url}' -> {result} (expected {expected})")
        if result != expected:
            all_passed = False
    
    return all_passed

async def test_youtube_transcript_extraction():
    """Test YouTube transcript extraction directly."""
    logger.info("📝 Testing YouTube transcript extraction...")
    
    # Try multiple URLs to find one with transcripts
    test_urls = [
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # TED Talk - confirmed working
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll - confirmed working
    ]
    
    for test_url in test_urls:
        try:
            logger.info(f"Trying URL: {test_url}")
            transcript = await extract_transcript_from_youtube(test_url)
            if transcript and len(transcript) > 0:
                logger.info(f"✅ Successfully extracted transcript ({len(transcript)} chars)")
                logger.info(f"   Preview: {transcript[:200]}...")
                return True
        except ExtractionError as e:
            logger.warning(f"⚠️ Transcript extraction failed for {test_url}: {e}")
            continue
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error for {test_url}: {e}")
            continue
    
    logger.error("❌ No transcripts could be extracted from any test URLs")
    return False

async def test_youtube_workflow_integration():
    """Test YouTube URL processing in the full podcast workflow."""
    logger.info("🎧 Testing YouTube URL in podcast generation workflow...")
    
    # Use the video that we confirmed works
    test_urls = [
        "https://www.youtube.com/watch?v=9bZkp7q19f0",  # TED Talk - confirmed working
    ]
    
    for youtube_url in test_urls:
        try:
            generator = PodcastGeneratorService()
            
            # Create a simple test request with YouTube URL
            test_request = PodcastRequest(
                source_urls=[youtube_url],
                personas=["Tech Expert", "AI Researcher"],
                desired_podcast_length_str="5 minutes",
                host_invented_name="Bridgette",
                host_gender="Female"
            )
            
            logger.info(f"Starting podcast generation with YouTube URL: {youtube_url}")
            start_time = time.time()
            
            # Generate podcast (this will test the full pipeline)
            episode = await generator.generate_podcast_from_source(test_request)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Check if episode was created successfully (episode object doesn't have status attribute)
            if episode and hasattr(episode, 'title') and episode.title:
                logger.info(f"✅ Podcast generation completed successfully in {duration:.1f}s")
                logger.info(f"   Title: {episode.title}")
                if hasattr(episode, 'audio_filepath'):
                    logger.info(f"   Audio: {episode.audio_filepath}")
                if hasattr(episode, 'llm_transcript_path'):
                    logger.info(f"   Transcript: {episode.llm_transcript_path}")
                return True
            else:
                logger.warning(f"⚠️ Podcast generation failed for {youtube_url}. Episode: {episode}")
                if hasattr(episode, 'warnings') and episode.warnings:
                    logger.warning(f"   Warnings: {episode.warnings}")
                continue
                
        except Exception as e:
            logger.warning(f"⚠️ Workflow test failed for {youtube_url}: {e}")
            continue
    
    logger.error("❌ Workflow integration failed for all test URLs")
    return False

async def main():
    """Run all YouTube integration tests."""
    logger.info("🚀 Starting YouTube Integration Tests for MySalonCast")
    logger.info("=" * 60)
    
    test_results = []
    
    # Test 1: URL Validation
    try:
        result = await test_youtube_url_validation()
        test_results.append(("URL Validation", result))
    except Exception as e:
        logger.error(f"URL validation test crashed: {e}")
        test_results.append(("URL Validation", False))
    
    logger.info("")
    
    # Test 2: Transcript Extraction
    try:
        result = await test_youtube_transcript_extraction()
        test_results.append(("Transcript Extraction", result))
    except Exception as e:
        logger.error(f"Transcript extraction test crashed: {e}")
        test_results.append(("Transcript Extraction", False))
    
    logger.info("")
    
    # Test 3: Full Workflow Integration
    try:
        result = await test_youtube_workflow_integration()
        test_results.append(("Workflow Integration", result))
    except Exception as e:
        logger.error(f"Workflow integration test crashed: {e}")
        test_results.append(("Workflow Integration", False))
    
    # Summary
    logger.info("")
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status} {test_name}")
        if not passed:
            all_passed = False
    
    logger.info("")
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED! YouTube integration is working correctly.")
    else:
        logger.info("⚠️ Some tests failed. Check the logs above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
