#!/usr/bin/env python3
"""
Simple test script to directly call the Gemini API without any of the application code.
This helps verify if the API key is valid and the service is responding.
"""
import os
import sys
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_gemini_api():
    """Test direct call to Gemini API"""
    # Load environment variables from .env file
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        logger.error("GOOGLE_API_KEY not found in environment variables or .env file")
        return False
    
    logger.info(f"Using API key: {api_key[:4]}...{api_key[-4:] if len(api_key) > 8 else ''}")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Create a simple model
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        logger.info("Successfully created Gemini model instance")
        
        # Simple test prompt
        test_prompt = "Hello, please respond with a simple greeting."
        logger.info(f"Sending test prompt: '{test_prompt}'")
        
        # Make the API call
        logger.info("Starting API call...")
        start_time = asyncio.get_event_loop().time()
        
        # Make synchronous call for simplicity
        response = model.generate_content(test_prompt)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        logger.info(f"API call completed in {duration:.2f} seconds")
        
        # Check response
        if hasattr(response, 'text'):
            logger.info(f"Received response: '{response.text[:100]}...'")
            return True
        else:
            logger.error("Response doesn't have 'text' attribute")
            logger.error(f"Response object: {response}")
            return False
            
    except Exception as e:
        logger.error(f"Error during Gemini API test: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting Gemini API test")
    
    # Run the test
    result = asyncio.run(test_gemini_api())
    
    if result:
        logger.info("Gemini API test PASSED ✅")
        sys.exit(0)
    else:
        logger.info("Gemini API test FAILED ❌")
        sys.exit(1)
