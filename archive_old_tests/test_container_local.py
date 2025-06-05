#!/usr/bin/env python3
"""
Local Container Test Script for MySalonCast MCP Server
Tests the health endpoint and basic MCP functionality locally.
"""

import asyncio
import httpx
import time
import os
import sys

async def test_health_endpoint(base_url: str = "http://localhost:8000"):
    """Test the health endpoint."""
    print(f"🏥 Testing health endpoint at {base_url}/health...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Health check passed!")
                print(f"   Status: {health_data.get('status')}")
                print(f"   Service: {health_data.get('service')}")
                print(f"   Timestamp: {health_data.get('timestamp')}")
                return True
            else:
                print(f"❌ Health check failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Health check failed with error: {e}")
        return False

async def test_mcp_endpoint(base_url: str = "http://localhost:8000"):
    """Test basic MCP functionality."""
    print(f"🔧 Testing MCP endpoint at {base_url}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test the hello tool
            mcp_request = {
                "method": "tools/call",
                "params": {
                    "name": "hello",
                    "arguments": {"name": "Container Test"}
                }
            }
            
            response = await client.post(
                f"{base_url}/mcp/v1/",
                json=mcp_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ MCP test passed!")
                print(f"   Response: {result}")
                return True
            else:
                print(f"❌ MCP test failed with status {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ MCP test failed with error: {e}")
        return False

async def wait_for_server(base_url: str = "http://localhost:8000", max_attempts: int = 30):
    """Wait for server to be ready."""
    print(f"⏳ Waiting for server at {base_url} to be ready...")
    
    for attempt in range(max_attempts):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    print(f"✅ Server is ready after {attempt + 1} attempts!")
                    return True
        except:
            pass
        
        print(f"   Attempt {attempt + 1}/{max_attempts} - Server not ready yet...")
        await asyncio.sleep(2)
    
    print(f"❌ Server failed to start after {max_attempts} attempts")
    return False

async def main():
    """Main test function."""
    print("🚀 MySalonCast MCP Server Container Test")
    print("=" * 50)
    
    # Check if we should wait for server startup
    if len(sys.argv) > 1 and sys.argv[1] == "--wait":
        if not await wait_for_server():
            sys.exit(1)
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Health endpoint
    if await test_health_endpoint():
        tests_passed += 1
    
    # Test 2: MCP functionality
    if await test_mcp_endpoint():
        tests_passed += 1
    
    # Results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Container is working correctly.")
        sys.exit(0)
    else:
        print("💥 Some tests failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
