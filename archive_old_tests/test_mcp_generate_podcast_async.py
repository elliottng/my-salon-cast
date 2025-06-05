#!/usr/bin/env python3
"""
Test script for MCP generate_podcast_async tool.
Modify the test parameters directly in the code below and run.
"""

import asyncio
import sys
import os
from pathlib import Path
import json
import time

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastmcp import Client
from app.mcp_server import mcp


async def test_generate_podcast_async(ctx=None):
    """Test the generate_podcast_async MCP tool with configurable parameters."""
    
    # =============================================================================
    # MODIFY THESE PARAMETERS FOR TESTING
    # =============================================================================
    
    test_params = {
        "ctx": None,  # MCP context parameter
        "source_urls": [
            "https://en.wikipedia.org/wiki/Battle_of_Jutland",
            # "https://en.wikipedia.org/wiki/Machine_learning",  # Add more URLs as needed
        ],
        "source_pdf_path": None,  # Set to a PDF file path if needed
        "prominent_persons": [
            "Sam Altman",
            "Denis Hassabis",
            "Yuval Noah Harari"
        ],
        "podcast_length": "7 minutes",  # Accept time strings like "7 minutes", "5-7 minutes", etc.
        "custom_prompt": "",  # Optional
        "podcast_name": "",  # Optional
    }
    
    # =============================================================================
    # TEST EXECUTION
    # =============================================================================
    
    print("🚀 Testing MCP generate_podcast_async tool")
    print(f"📝 Test Parameters:")
    for key, value in test_params.items():
        if value is not None:
            print(f"   {key}: {value}")
    print()
    
    try:
        # Use in-memory FastMCP client (no separate server process needed)
        async with Client(mcp) as client:
            print("🔄 Calling generate_podcast_async...")
            
            # Call the MCP tool
            result = await client.call_tool("generate_podcast_async", test_params)
            
            print("✅ Tool call successful!")
            print(f"📋 Result: {result}")
            
            # Extract task_id from result if available
            if result and len(result) > 0:
                result_text = result[0].text if hasattr(result[0], 'text') else str(result[0])
                print(f"📄 Response: {result_text}")
                
                # Try to extract task_id for follow-up testing
                import json
                try:
                    response_data = json.loads(result_text)
                    if 'task_id' in response_data:
                        task_id = response_data['task_id']
                        print(f"🆔 Task ID: {task_id}")
                        
                        # Optional: Test get_task_status with the returned task_id
                        print("\n🔄 Testing get_task_status...")
                        status_result = await client.call_tool("get_task_status", {"ctx": ctx, "task_id": task_id})
                        print(f"📊 Status Result: {status_result}")
                        
                        # Monitor task until completion - can set verbose=True for more detailed logging
                        await monitor_task_completion(client, task_id, ctx, verbose=True)
                        
                except json.JSONDecodeError:
                    print("ℹ️  Response is not JSON format")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        print(f"🔍 Error type: {type(e)}")
        import traceback
        traceback.print_exc()


async def monitor_task_completion(client, task_id, ctx=None, poll_interval=10, max_wait_minutes=15, verbose=False):
    """Poll task status until completion or timeout."""
    print(f"\n🕐 Monitoring task {task_id} until completion...")
    print(f"⏱️  Polling every {poll_interval} seconds (max {max_wait_minutes} minutes)")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    
    while True:
        try:
            # Check current status
            status_result = await client.call_tool("get_task_status", {"ctx": ctx, "task_id": task_id})
            
            if status_result and len(status_result) > 0:
                status_text = status_result[0].text if hasattr(status_result[0], 'text') else str(status_result[0])
                
                try:
                    status_data = json.loads(status_text)
                    current_status = status_data.get('status', 'unknown')
                    progress = status_data.get('progress_percentage', 0)
                    description = status_data.get('status_description', '')
                    
                    elapsed = int(time.time() - start_time)
                    print(f"📊 [{elapsed:3d}s] Status: {current_status} ({progress}%) - {description}\n")
                    
                    # Optional: Show recent logs with line breaks (uncomment for detailed logging)
                    if verbose and 'logs' in status_data and status_data['logs']:
                        recent_logs = status_data['logs'][-3:]  # Show last 3 log entries
                        for log in recent_logs:
                            print(f"    📝 {log}")
                        print()  # Extra line break
                    
                    # Check if completed
                    if current_status in ['completed', 'failed', 'cancelled']:
                        print(f"\n✅ Task {current_status}!")
                        
                        if current_status == 'completed':
                            print("🎉 Podcast generation successful!")
                            # Show final results
                            if 'episode_title' in status_data:
                                print(f"📼 Episode: {status_data['episode_title']}")
                            if 'artifacts' in status_data:
                                print(f"📁 Artifacts: {status_data['artifacts']}")
                        else:
                            print(f"❌ Task ended with status: {current_status}")
                            if 'error_message' in status_data:
                                print(f"🚨 Error: {status_data['error_message']}")
                        
                        break
                    
                except json.JSONDecodeError:
                    print(f"⚠️  Could not parse status response: {status_text}")
            
            # Check timeout
            if time.time() - start_time > max_wait_seconds:
                print(f"\n⏰ Timeout reached ({max_wait_minutes} minutes)")
                print("🛑 Stopping monitoring (task may still be running)")
                break
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            await asyncio.sleep(poll_interval)


async def test_tool_discovery():
    """Test that we can discover available tools."""
    print("\n🔍 Testing tool discovery...")
    
    try:
        async with Client(mcp) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"📚 Available tools: {[tool.name for tool in tools]}")
            
            # Find our specific tool
            podcast_tool = next((tool for tool in tools if tool.name == "generate_podcast_async"), None)
            if podcast_tool:
                print(f"✅ Found generate_podcast_async tool")
                print(f"📝 Description: {podcast_tool.description}")
            else:
                print("❌ generate_podcast_async tool not found")
                
    except Exception as e:
        print(f"❌ Error during tool discovery: {e}")


if __name__ == "__main__":
    async def main():
        print("🧪 MCP Generate Podcast Async Test")
        print("=" * 50)
        
        # Test tool discovery first
        await test_tool_discovery()
        
        # Test the actual tool
        await test_generate_podcast_async()
        
        print("\n✨ Test completed!")
    
    # Run the test
    asyncio.run(main())
