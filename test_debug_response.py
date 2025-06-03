#!/usr/bin/env python3
"""
Debug response format from MCP tools.
"""

import asyncio
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from tests.mcp.client import SimpleMCPTestClient


async def debug_response_format():
    """Debug the response format from MCP tools."""
    print("🔍 Debugging MCP response format...")
    
    async with SimpleMCPTestClient() as client:
        try:
            # Test tool call
            print("📞 Testing tool call...")
            result = await client.call_tool("generate_podcast_async_pydantic", {
                "request": {
                    "prominent_persons": ["Test Person"],
                    "source_urls": ["https://en.wikipedia.org/wiki/Battle_of_Jutland"],
                    "podcast_duration_minutes": 1,
                    "language": "en"
                }
            })
            
            print(f"Tool result type: {type(result)}")
            print(f"Tool result: {result}")
            
            if isinstance(result, dict) and "task_id" in result:
                task_id = result["task_id"]
                print(f"✅ Found task_id: {task_id}")
                
                # Wait a moment
                await asyncio.sleep(5)
                
                # Test job status resource
                print(f"📊 Testing job status resource...")
                job_status = await client.read_resource(f"jobs://{task_id}/status")
                print(f"Job status type: {type(job_status)}")
                print(f"Job status: {job_status}")
                
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    result = asyncio.run(debug_response_format())
    sys.exit(0 if result else 1)
