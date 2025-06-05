#!/usr/bin/env python3
"""
Verbose test of the podcast generation workflow with detailed console output
"""
import asyncio
import logging
import os
import sys
import json
import time
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest

# Set up detailed logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Also log at module level for direct print statements
print_log = lambda msg: print(f"{time.strftime('%H:%M:%S')} - TEST - {msg}")

async def main():
    """Test the podcast workflow with detailed console output"""
    print_log("=== STARTING VERBOSE TEST ===")
    print_log("Initializing PodcastGeneratorService...")
    
    # Initialize the service
    service = PodcastGeneratorService()
    
    print_log("Creating test request...")
    # Create a simple test request
    request = PodcastRequest(
        source_url="https://www.google.com/about/philosophy/",
        prominent_persons=["Host"],
        desired_podcast_length_str="1 minute"
    )
    
    try:
        print_log(f"Testing podcast generation with {request.source_url}")
        print_log("Calling generate_podcast_from_source...")
        result = await service.generate_podcast_from_source(request)
        
        print_log("Call to generate_podcast_from_source returned!")
        print_log(f"Result type: {type(result)}")
        
        print_log("\n=== GENERATED PODCAST DETAILS ===")
        print_log(f"Title: {result.title}")
        print_log(f"Summary: {result.summary}")
        print_log(f"Audio file path: {result.audio_filepath}")
        print_log(f"Number of warnings: {len(result.warnings)}")
        
        if result.warnings:
            print_log("\nWarnings:")
            for i, warning in enumerate(result.warnings, 1):
                print_log(f"{i}. {warning}")
                
        # Check for specific warning patterns related to timeouts
        timeout_warnings = [w for w in result.warnings if "timeout" in w.lower() or "api" in w.lower()]
        if timeout_warnings:
            print_log("\nTimeout-related warnings detected:")
            for warning in timeout_warnings:
                print_log(f"- {warning}")
        
        return result
    except Exception as e:
        print_log(f"ERROR during test: {e}")
        import traceback
        print_log(traceback.format_exc())
        return None
    finally:
        print_log("=== TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(main())
