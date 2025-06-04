#!/usr/bin/env python3
"""Test SSE endpoint behavior"""
import requests
import time

def test_sse_endpoint():
    """Test what FastMCP's SSE endpoint sends"""
    # Connect to SSE endpoint without auth to see the response
    headers = {
        "Accept": "text/event-stream"
    }
    
    print("Connecting to SSE endpoint without auth...")
    response = requests.get(
        "http://localhost:8000/sse", 
        headers=headers, 
        stream=True,
        timeout=5
    )
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        # Read the error response
        print(f"\nError response: {response.text}")
    else:
        print("\nSSE stream content (first 5 seconds):")
        start_time = time.time()
        
        for line in response.iter_lines():
            if line:
                print(f"  {line.decode('utf-8')}")
            
            # Timeout after 5 seconds
            if time.time() - start_time > 5:
                print("\nTimeout after 5 seconds")
                break

if __name__ == "__main__":
    test_sse_endpoint()
