#!/usr/bin/env python3
"""Debug the health response format."""

import asyncio
import sys
sys.path.insert(0, '/home/elliottng/CascadeProjects/mysaloncast')

from tests.mcp.client import SimpleMCPTestClient

async def debug_health_response():
    server_url = "http://localhost:8000/mcp"
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "debug-test"}
            })
            
            print(f"Result type: {type(result)}")
            print(f"Result content: {result}")
            
            if isinstance(result, list) and result:
                print(f"First item: {result[0]}")
                print(f"First item type: {type(result[0])}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_health_response())
