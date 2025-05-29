#!/usr/bin/env python3
"""
Quick test of the LLM service timeout handling with a very short timeout
"""
import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import the LLM service
from app.llm_service import GeminiService

async def main():
    """Test the LLM service with a very short timeout"""
    logger.info("Starting quick timeout test")
    
    # Initialize the service
    service = GeminiService()
    
    # Create a test prompt
    test_prompt = "Please analyze this text in great detail, providing multiple paragraphs of analysis: Hello world."
    
    try:
        # Set a very short timeout (2 seconds) to force a timeout
        logger.info(f"Calling generate_text_async with 2-second timeout")
        result = await service.generate_text_async(test_prompt, timeout_seconds=2)
        
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result: {result}")
        
        # Try to parse as JSON to check error format
        import json
        try:
            json_result = json.loads(result)
            logger.info(f"Parsed JSON: {json_result}")
            if "error" in json_result:
                logger.info(f"Error detected: {json_result['error']}")
                return json_result
        except json.JSONDecodeError:
            logger.info("Result is not JSON")
        
        return result
    
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    asyncio.run(main())
