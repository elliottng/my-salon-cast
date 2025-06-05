#!/usr/bin/env python3
"""
Test the LLM service with a short timeout to verify error handling
"""
import asyncio
import logging
import json
import os
from app.llm_service import GeminiService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_timeout():
    """Test the LLM service with a deliberately short timeout"""
    logger.info("Starting LLM timeout test")
    
    # Initialize the LLM service
    llm_service = GeminiService()
    
    # Test source text (robots.txt format that was causing issues)
    test_text = """
    User-agent: *
    Disallow: /search
    Allow: /search/about
    Allow: /search/static
    Disallow: /sdch
    Disallow: /groups
    Disallow: /index.html?
    Disallow: /?
    Allow: /?hl=
    """
    
    # Try with a very short timeout that should trigger the timeout handling
    try:
        logger.info("Calling analyze_source_text_async with custom timeout")
        # Override the generate_text_async method with a custom implementation with short timeout
        original_method = llm_service.generate_text_async
        
        # Define our custom wrapper method with a short timeout
        async def generate_text_with_short_timeout(prompt, **kwargs):
            logger.info("Using custom wrapper with 5-second timeout")
            return await original_method(prompt, timeout_seconds=5)
            
        # Replace the method temporarily
        llm_service.generate_text_async = generate_text_with_short_timeout
        
        # Call the analyze method
        result = await llm_service.analyze_source_text_async(test_text)
        
        # Restore the original method
        llm_service.generate_text_async = original_method
        
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result length: {len(result) if result else 0}")
        logger.info(f"Result preview: {result[:200]}..." if result and len(result) > 200 else f"Result: {result}")
        
        # Check if the result is JSON and contains an error
        try:
            parsed = json.loads(result)
            if "error" in parsed:
                logger.info(f"Error found in response: {parsed['error']}")
                if "details" in parsed:
                    logger.info(f"Error details: {parsed['details']}")
            else:
                logger.info("Response contains valid JSON but no error field")
        except json.JSONDecodeError:
            logger.info("Response is not valid JSON format")
        
    except Exception as e:
        logger.error(f"Exception during test: {e}", exc_info=True)
    
    logger.info("Timeout test completed")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_timeout())
