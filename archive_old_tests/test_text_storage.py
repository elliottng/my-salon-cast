#!/usr/bin/env python3
"""
Test script for Phase 2.3 text file cloud storage integration.
Tests both local development mode and cloud storage functionality.
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

# Test configuration
MCP_SERVER_URL = "http://localhost:8000"
TEST_TOPIC = "Testing text file cloud storage integration for MySalonCast"
TEST_DESCRIPTION = "This is a test to verify that podcast outlines and persona research files are properly uploaded to cloud storage and accessible via MCP resources."

def test_podcast_generation():
    """Test podcast generation with text file storage."""
    print("🧪 Testing Phase 2.3: Text File Cloud Storage Integration")
    print("=" * 60)
    
    # Step 1: Generate a podcast episode
    print("\n📝 Step 1: Starting podcast generation...")
    generate_payload = {
        "topic": TEST_TOPIC,
        "description": TEST_DESCRIPTION,
        "max_people": 2,  # Keep it small for testing
        "max_references": 3
    }
    
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/generate-podcast",
            json=generate_payload,
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to start podcast generation: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        result = response.json()
        task_id = result.get("task_id")
        
        if not task_id:
            print("❌ No task_id returned from podcast generation")
            return None
        
        print(f"✅ Podcast generation started with task_id: {task_id}")
        return task_id
        
    except Exception as e:
        print(f"❌ Error starting podcast generation: {e}")
        return None

def monitor_task_progress(task_id):
    """Monitor task progress until completion."""
    print(f"\n⏳ Step 2: Monitoring task progress for {task_id}...")
    
    max_attempts = 120  # 10 minutes max wait
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{MCP_SERVER_URL}/status/{task_id}")
            
            if response.status_code != 200:
                print(f"❌ Failed to get status: {response.status_code}")
                return None
            
            status_data = response.json()
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
            
            time.sleep(5)  # Wait 5 seconds between checks
            attempt += 1
            
        except Exception as e:
            print(f"❌ Error checking status: {e}")
            time.sleep(5)
            attempt += 1
    
    print("❌ Timeout waiting for podcast generation to complete")
    return None

def test_text_file_resources(task_id):
    """Test accessing text file resources via MCP."""
    print(f"\n📂 Step 3: Testing text file resource access for {task_id}...")
    
    # Test podcast outline resource
    print("🔍 Testing podcast outline resource...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/resources/podcast/{task_id}/outline")
        
        if response.status_code == 200:
            outline_data = response.json()
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
            print(f"❌ Failed to access outline resource: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing outline resource: {e}")
    
    # Test persona research resources
    print("\n🔍 Testing persona research resources...")
    try:
        # First, get the list of available resources
        response = requests.get(f"{MCP_SERVER_URL}/resources")
        
        if response.status_code == 200:
            resources = response.json()
            research_resources = [
                r for r in resources.get("resources", [])
                if r.get("uri", "").startswith(f"research://{task_id}/")
            ]
            
            print(f"📋 Found {len(research_resources)} persona research resources")
            
            # Test accessing each research resource
            for resource in research_resources[:2]:  # Test first 2 only
                resource_uri = resource.get("uri", "")
                person_id = resource_uri.split("/")[-1]
                
                print(f"🔍 Testing research resource for person: {person_id}")
                
                try:
                    response = requests.get(f"{MCP_SERVER_URL}/resources/research/{task_id}/{person_id}")
                    
                    if response.status_code == 200:
                        research_data = response.json()
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
                        print(f"❌ Failed to access research resource for {person_id}: {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Error testing research resource for {person_id}: {e}")
        else:
            print(f"❌ Failed to get resource list: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing persona research resources: {e}")

def test_caching_performance(task_id):
    """Test caching performance for text file access."""
    print(f"\n⚡ Step 4: Testing caching performance for {task_id}...")
    
    # Test outline caching
    print("🔄 Testing outline caching (3 requests)...")
    times = []
    
    for i in range(3):
        start_time = time.time()
        try:
            response = requests.get(f"{MCP_SERVER_URL}/resources/podcast/{task_id}/outline")
            end_time = time.time()
            
            if response.status_code == 200:
                request_time = (end_time - start_time) * 1000  # Convert to ms
                times.append(request_time)
                print(f"  Request {i+1}: {request_time:.2f}ms")
            else:
                print(f"  Request {i+1}: Failed ({response.status_code})")
                
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

def main():
    """Main test function."""
    print(f"🚀 Starting MySalonCast Text Storage Test at {datetime.now()}")
    
    # Step 1: Generate podcast
    task_id = test_podcast_generation()
    if not task_id:
        print("\n❌ Test failed at podcast generation step")
        sys.exit(1)
    
    # Step 2: Monitor progress
    final_status = monitor_task_progress(task_id)
    if not final_status:
        print("\n❌ Test failed at monitoring step")
        sys.exit(1)
    
    # Step 3: Test text file resources
    test_text_file_resources(task_id)
    
    # Step 4: Test caching
    test_caching_performance(task_id)
    
    print("\n🎉 Text file cloud storage integration test completed!")
    print("=" * 60)
    print(f"📋 Test Summary for task_id: {task_id}")
    print("✅ Podcast generation: Success")
    print("✅ Text file resource access: Tested")
    print("✅ Caching performance: Analyzed")
    print("\n💡 Check the logs above for detailed results about cloud vs local storage!")

if __name__ == "__main__":
    main()
