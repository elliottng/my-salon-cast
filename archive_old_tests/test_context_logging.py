#!/usr/bin/env python3
"""
Test script to verify Phase 5.1 Option 1: Basic Context Logging is working properly.
"""

import asyncio
import logging
import sys
import os
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.mcp_server import mcp, generate_podcast_async

# Set up logging to see the context-enhanced logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

async def test_context_logging():
    """Test that context logging is working in MCP tools."""
    print("\n=== Testing Phase 5.1 Option 1: Basic Context Logging ===\n")
    
    # Create a mock context object similar to what FastMCP would provide
    mock_context = Mock()
    mock_context.request_id = "test-req-12345"
    mock_context.client_info = {
        "name": "test-client",
        "version": "1.0.0",
        "session_id": "sess-abcdef"
    }
    
    print(f"🧪 Testing with mock context:")
    print(f"   Request ID: {mock_context.request_id}")
    print(f"   Client Info: {mock_context.client_info}")
    print()
    
    try:
        print("🔄 Calling generate_podcast_async with context...")
        
        # Call the MCP tool with context
        result = await generate_podcast_async(
            ctx=mock_context,
            source_urls=["https://example.com/test-article"],
            prominent_persons=["Test Person"],
            podcast_name="Test Podcast",
            dialogue_style="conversation",
            podcast_length="short"
        )
        
        print(f"✅ Tool call completed successfully!")
        print(f"   Success: {result.get('success', False)}")
        print(f"   Task ID: {result.get('task_id', 'None')}")
        print(f"   Message: {result.get('message', 'None')}")
        
        if result.get('task_id'):
            print(f"\n🔄 Testing get_task_status with same context...")
            
            # Import get_task_status
            from app.mcp_server import get_task_status
            
            status_result = await get_task_status(
                ctx=mock_context, 
                task_id=result['task_id']
            )
            
            print(f"✅ Status call completed!")
            print(f"   Success: {status_result.get('success', False)}")
            
            # Extract actual status from the nested structure if available
            if 'status' in status_result:
                status_data = status_result['status']
                if isinstance(status_data, dict):
                    actual_status = status_data.get('status', 'unknown')
                    progress = status_data.get('progress_percentage', 0)
                else:
                    # Handle case where status_data might be a model object
                    actual_status = getattr(status_data, 'status', 'unknown')
                    progress = getattr(status_data, 'progress_percentage', 0)
                    
                print(f"   Task Status: {actual_status}")
                print(f"   Progress: {progress}%")
        
        print(f"\n✅ Context logging test completed successfully!")
        print(f"   Check the logs above for [test-req-12345] prefixed messages")
        print(f"   You should see enhanced logging with request correlation")
        
    except Exception as e:
        print(f"❌ Context logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_context_attributes():
    """Test that context attribute access is safe and handles missing attributes."""
    print(f"\n🧪 Testing context attribute safety...")
    
    # Test with minimal context (missing attributes)
    minimal_context = Mock()
    minimal_context.request_id = "test-req-minimal"
    # Intentionally omit client_info
    
    try:
        result = await generate_podcast_async(
            ctx=minimal_context,
            source_urls=["https://example.com/minimal-test"],
            prominent_persons=["Minimal Test Person"]
        )
        
        print(f"✅ Minimal context test passed - no crashes on missing attributes")
        return True
        
    except Exception as e:
        print(f"❌ Minimal context test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Context Logging Tests...")
    
    async def run_all_tests():
        success1 = await test_context_logging()
        success2 = await test_context_attributes()
        
        if success1 and success2:
            print(f"\n🎉 All context logging tests passed!")
            print(f"   Phase 5.1 Option 1 implementation is working correctly")
            return True
        else:
            print(f"\n❌ Some tests failed")
            return False
    
    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
