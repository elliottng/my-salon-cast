#!/usr/bin/env python3
"""
Direct test of FastMCP client connection.
"""

import asyncio
import sys
import os
from fastmcp import Client

async def test_direct_connection():
    """Test direct FastMCP client connection."""
    print("🧪 Testing direct FastMCP client connection...")
    
    try:
        client = Client("http://localhost:8000")
        print("✅ Client created")
        
        async with client:
            print("✅ Client context manager worked")
            
            # List tools
            tools = await client.list_tools()
            print(f"✅ Tools: {[tool.name for tool in tools]}")
            
            # List resources
            resources = await client.list_resources() 
            print(f"✅ Resources: {[r.uri for r in resources]}")
            
            # Test job status resource with fake task
            try:
                result = await client.read_resource("jobs://fake-task/status")
                print(f"Unexpected success: {result}")
            except Exception as e:
                print(f"✅ Expected error for fake task: {e}")
                
            return True
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_direct_connection())
    sys.exit(0 if result else 1)
