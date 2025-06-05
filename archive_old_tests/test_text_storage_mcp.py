#!/usr/bin/env python3
"""
Test script for Phase 2.3 text file cloud storage integration using MCP protocol.
Tests both local development mode and cloud storage functionality.
"""

import asyncio
import sys
import time
from datetime import datetime
from tests.mcp.client import SimpleMCPTestClient

# Test configuration
MCP_SERVER_URL = "http://localhost:8000/mcp"
TEST_TOPIC = "Testing text file cloud storage integration for MySalonCast"
TEST_DESCRIPTION = "This is a test to verify that podcast outlines and persona research files are properly uploaded to cloud storage and accessible via MCP resources."

async def test_podcast_generation():
    """Test podcast generation with text file storage."""
    print("🧪 Testing Phase 2.3: Text File Cloud Storage Integration")
    print("=" * 60)
    
    async with SimpleMCPTestClient(MCP_SERVER_URL) as client:
        # Step 1: Generate a podcast episode
        print("\n📝 Step 1: Starting podcast generation...")
        
        try:
            result = await client.call_generate_podcast_async(
                source_urls=["https://en.wikipedia.org/wiki/Cloud_storage"],  # Use a simple URL for testing
                custom_prompt=f"Topic: {TEST_TOPIC}. Description: {TEST_DESCRIPTION}",
                prominent_persons=["Alice", "Bob"],  # Simple test personas
                podcast_length="3-4 minutes"  # Keep it short for testing
            )
            
            task_id = result.get("task_id")
            
            if not task_id:
                print("❌ No task_id returned from podcast generation")
                print(f"Result: {result}")
                return None
            
            print(f"✅ Podcast generation started with task_id: {task_id}")
            return task_id
            
        except Exception as e:
            print(f"❌ Error starting podcast generation: {e}")
            return None

async def monitor_task_progress(task_id):
    """Monitor task progress until completion."""
    print(f"\n⏳ Step 2: Monitoring task progress for {task_id}...")
    
    async with SimpleMCPTestClient(MCP_SERVER_URL) as client:
        max_attempts = 120  # 10 minutes max wait
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_data = await client.get_task_status(task_id)
                
                status = status_data.get("status", "unknown")
                progress = status_data.get("progress", 0)
                
                print(f"📊 Progress: {progress}% - Status: {status}")
                
                if status == "completed":
                    print("✅ Podcast generation completed!")
                    return status_data
                elif status == "failed":
                    print("❌ Podcast generation failed!")
                    print(f"Error: {status_data.get('error', 'Unknown error')}")
                    return None
                
                await asyncio.sleep(5)  # Wait 5 seconds between checks
                attempt += 1
                
            except Exception as e:
                print(f"❌ Error checking status: {e}")
                await asyncio.sleep(5)
                attempt += 1
        
        print("❌ Timeout waiting for podcast generation to complete")
        return None

async def test_text_file_resources(task_id):
    """Test accessing text file resources via MCP."""
    print(f"\n📂 Step 3: Testing text file resource access for {task_id}...")
    
    async with SimpleMCPTestClient(MCP_SERVER_URL) as client:
        # Test podcast outline resource
        print("🔍 Testing podcast outline resource...")
        try:
            outline_uri = f"podcast://{task_id}/outline"
            outline_result = await client.mcp_client.read_resource(outline_uri)
            
            if outline_result:
                # FastMCP returns content objects
                if isinstance(outline_result, list) and outline_result:
                    content = outline_result[0]
                    if hasattr(content, 'text'):
                        import json
                        outline_data = json.loads(content.text)
                        has_outline = outline_data.get("has_outline", False)
                        outline_path = outline_data.get("outline_file_path", "")
                        
                        print(f"✅ Outline resource accessible: has_outline={has_outline}")
                        print(f"📁 Outline path: {outline_path}")
                        
                        # Check if it's a cloud URL
                        if outline_path.startswith(('gs://', 'http://', 'https://')):
                            print("☁️  Outline stored in cloud storage! ✅")
                        else:
                            print("💻 Outline stored locally (expected in dev mode)")
                    else:
                        print(f"✅ Outline resource returned: {outline_result}")
                else:
                    print(f"✅ Outline resource returned: {outline_result}")
            else:
                print("❌ No outline resource returned")
                
        except Exception as e:
            print(f"❌ Error testing outline resource: {e}")
        
        # Test persona research resources - first list all resources
        print("\n🔍 Testing persona research resources...")
        try:
            resources = await client.mcp_client.list_resources()
            
            research_resources = [
                r for r in resources
                if hasattr(r, 'uri') and r.uri.startswith(f"research://{task_id}/")
            ]
            
            print(f"📋 Found {len(research_resources)} persona research resources")
            
            # Test accessing first few research resources
            for resource in research_resources[:2]:  # Test first 2 only
                person_id = resource.uri.split("/")[-1]
                
                print(f"🔍 Testing research resource for person: {person_id}")
                
                try:
                    research_result = await client.mcp_client.read_resource(resource.uri)
                    
                    if research_result and isinstance(research_result, list) and research_result:
                        content = research_result[0]
                        if hasattr(content, 'text'):
                            import json
                            research_data = json.loads(content.text)
                            file_exists = research_data.get("file_exists", False)
                            file_path = research_data.get("research_file_path", "")
                            
                            print(f"✅ Research resource accessible: file_exists={file_exists}")
                            print(f"📁 Research path: {file_path}")
                            
                            # Check if it's a cloud URL
                            if file_path.startswith(('gs://', 'http://', 'https://')):
                                print(f"☁️  Research for {person_id} stored in cloud storage! ✅")
                            else:
                                print(f"💻 Research for {person_id} stored locally (expected in dev mode)")
                        else:
                            print(f"✅ Research resource returned: {research_result}")
                    else:
                        print(f"❌ No research resource returned for {person_id}")
                        
                except Exception as e:
                    print(f"❌ Error testing research resource for {person_id}: {e}")
                    
        except Exception as e:
            print(f"❌ Error testing persona research resources: {e}")

async def test_caching_performance(task_id):
    """Test caching performance for text file access."""
    print(f"\n⚡ Step 4: Testing caching performance for {task_id}...")
    
    # Test outline caching
    print("🔄 Testing outline caching (3 requests)...")
    times = []
    
    async with SimpleMCPTestClient(MCP_SERVER_URL) as client:
        for i in range(3):
            start_time = time.time()
            try:
                outline_uri = f"podcast://{task_id}/outline"
                outline_result = await client.mcp_client.read_resource(outline_uri)
                end_time = time.time()
                
                if outline_result:
                    request_time = (end_time - start_time) * 1000  # Convert to ms
                    times.append(request_time)
                    print(f"  Request {i+1}: {request_time:.2f}ms")
                else:
                    print(f"  Request {i+1}: Failed (no result)")
                    
            except Exception as e:
                print(f"  Request {i+1}: Error - {e}")
    
    if len(times) >= 2:
        print(f"📊 Caching analysis:")
        print(f"  First request: {times[0]:.2f}ms (cache miss)")
        print(f"  Subsequent avg: {sum(times[1:])/(len(times)-1):.2f}ms (cache hit)")
        
        if times[0] > times[1] * 1.5:  # First request should be slower
            print("✅ Caching appears to be working!")
        else:
            print("⚠️  Caching may not be working as expected")

async def main():
    """Main test function."""
    print(f"🚀 Starting MySalonCast Text Storage Test at {datetime.now()}")
    
    # Step 1: Generate podcast
    task_id = await test_podcast_generation()
    if not task_id:
        print("\n❌ Test failed at podcast generation step")
        sys.exit(1)
    
    # Step 2: Monitor progress
    final_status = await monitor_task_progress(task_id)
    if not final_status:
        print("\n❌ Test failed at monitoring step")
        sys.exit(1)
    
    # Step 3: Test text file resources
    await test_text_file_resources(task_id)
    
    # Step 4: Test caching
    await test_caching_performance(task_id)
    
    print("\n🎉 Text file cloud storage integration test completed!")
    print("=" * 60)
    print(f"📋 Test Summary for task_id: {task_id}")
    print("✅ Podcast generation: Success")
    print("✅ Text file resource access: Tested")
    print("✅ Caching performance: Analyzed")
    print("\n💡 Check the logs above for detailed results about cloud vs local storage!")

if __name__ == "__main__":
    asyncio.run(main())
