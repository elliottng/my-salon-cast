#!/usr/bin/env python3
"""
Direct test of just the LLM service with timeout handling
"""
import asyncio
import logging
import sys
import json
from app.llm_service import GeminiService

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_timeout():
    """Test the LLM service timeout directly"""
    print("\n=== TESTING LLM SERVICE TIMEOUT ===")
    
    # Initialize the LLM service
    service = GeminiService()
    print(f"LLM service initialized")
    
    # Create a test prompt similar to a source analysis
    test_prompt = "Please analyze the following text and provide a detailed summary:\n\n"
    # Add a long text to analyze (deliberately making it complex enough to potentially timeout)
    test_prompt += """Google's Ten things we know to be true

    Since the beginning, we've focused on providing the best user experience possible. Whether we're designing a new Internet browser or a new tweak to the look of the homepage, we take great care to ensure that they will ultimately serve you, rather than our own internal goal or bottom line...

    (Content shortened for the example) 
    
    It's best to do one thing really, really well.
    We do search. With one of the world's largest research groups focused exclusively on solving search problems, we know what we do well, and how we could do it better. Through continued iteration on difficult problems, we've been able to solve complex issues and provide continuous improvements to a service that already makes finding information a fast and seamless experience for millions of people. Our dedication to improving search helps us apply what we've learned to new products, like Gmail and Google Maps. Our hope is to bring the power of search to previously unexplored areas, and to help people access and use even more of the ever-expanding information in their lives.

    You can make money without doing evil.
    We firmly believe that in the long term, we will be better served — as shareholders and in all other ways — by a company that does good things for the world even if we forgo some short term gains. This is an important aspect of our culture and is broadly shared within the company...
    """
    
    print(f"Created test prompt of length {len(test_prompt)} characters")
    print("Calling analyze_source_text_async with 10s timeout...")
    
    try:
        # This should timeout after 10 seconds
        start_time = asyncio.get_event_loop().time()
        result = await service.analyze_source_text_async(test_prompt)
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        print(f"Call completed in {duration:.2f} seconds")
        print(f"Result type: {type(result)}")
        print(f"Result length: {len(result)}")
        print(f"Result preview: {result[:200]}...")
        
        # Try to parse the result as JSON
        try:
            parsed = json.loads(result)
            print(f"Parsed JSON result: {json.dumps(parsed, indent=2)}")
            
            # Check if it contains an error
            if "error" in parsed:
                print(f"Error detected: {parsed['error']}")
                if "details" in parsed:
                    print(f"Error details: {parsed['details']}")
                print("✅ Timeout handling worked correctly!")
            else:
                print("No error found in the response.")
        except json.JSONDecodeError:
            print("Result is not valid JSON")
            print("Raw result:", result)
    
    except Exception as e:
        print(f"Exception during test: {e}")
        import traceback
        traceback.print_exc()
    
    print("=== TEST COMPLETED ===")

if __name__ == "__main__":
    asyncio.run(test_timeout())
