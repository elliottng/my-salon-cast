#!/usr/bin/env python3
"""
Debug the get_task_status tool response format.
"""

import asyncio
import sys
import os

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from tests.mcp.client import SimpleMCPTestClient


async def debug_tool_format():
    """Debug the format of get_task_status tool."""
    print("🔍 Debugging get_task_status tool format...")
    
    async with SimpleMCPTestClient() as client:
        try:
            # Generate a task first
            generate_result = await client.call_tool(
                "generate_podcast_async",
                {
                    "source_urls": ["https://en.wikipedia.org/wiki/Battle_of_Jutland"],
                    "prominent_persons": ["Test Person"],
                    "podcast_length": "1 minute",
                    "output_language": "en",
                },
            )
            
            print(f"Generate result: {generate_result}")
            
            if generate_result.get("success"):
                task_id = generate_result["task_id"]
                print(f"📋 Task ID: {task_id}")
                
                # Test get_task_status tool
                status_result = await client.call_tool("get_task_status", {"task_id": task_id})
                print(f"Status result type: {type(status_result)}")
                print(f"Status result: {status_result}")
                
                return True
            else:
                print(f"❌ Failed to generate: {generate_result}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    result = asyncio.run(debug_tool_format())
    sys.exit(0 if result else 1)
