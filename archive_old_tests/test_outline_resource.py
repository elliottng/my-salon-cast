#!/usr/bin/env python3
"""
Test script specifically for the new podcast://{task_id}/outline resource.
This will generate a podcast and test accessing the outline data.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.mcp.client import SimpleMCPTestClient

async def test_outline_resource_workflow():
    """Test complete workflow including outline resource access."""
    print("🎯 Testing Podcast Outline Resource Workflow...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        # Step 1: Generate a podcast
        print("\n📝 Step 1: Generating a test podcast...")
        
        # Generate a podcast using real test URLs from workflow
        generation_response = await client.call_tool("generate_podcast_async", {
            "source_urls": [
                "https://en.wikipedia.org/wiki/Battle_of_Jutland"
            ],
            "podcast_name": "Battle of Jutland Historical Analysis",
            "podcast_tagline": "Naval History Deep Dive",
            "output_language": "en",
            "dialogue_style": "engaging",
            "podcast_length": "5 minutes",
            "prominent_persons": ["Jason Calacanis", "David Friedberg"]
        })
        
        if not generation_response.get('success'):
            print(f"❌ Podcast generation failed: {generation_response}")
            return False
        
        task_id = generation_response.get('task_id')
        print(f"✅ Podcast generation started. Task ID: {task_id}")
        
        # Step 2: Wait for completion (with timeout)
        print("\n⏳ Step 2: Waiting for podcast completion...")
        
        max_attempts = 30  # 5 minutes max wait
        attempt = 0
        completed = False
        
        while attempt < max_attempts and not completed:
            try:
                status_response = await client.call_tool("get_task_status", {"task_id": task_id})
                
                if status_response.get('success'):
                    status = status_response.get('status')
                    progress = status_response.get('progress_percentage', 0)
                    stage = status_response.get('stage', 'unknown')
                    
                    print(f"   Status: {status} | Progress: {progress:.1f}% | Stage: {stage}")
                    
                    if status == "completed":
                        completed = True
                        print("✅ Podcast generation completed!")
                        break
                    elif status == "failed":
                        print(f"❌ Podcast generation failed: {status_response.get('message', 'Unknown error')}")
                        return False
                
            except Exception as e:
                print(f"⚠️  Error checking status: {e}")
            
            attempt += 1
            await asyncio.sleep(10)  # Wait 10 seconds between checks
        
        if not completed:
            print("❌ Timeout waiting for podcast completion")
            return False
        
        # Step 3: Test all podcast resources including outline
        print(f"\n🔍 Step 3: Testing all podcast resources for task {task_id}...")
        
        # Test outline resource (our new one)
        print("\n📋 Testing outline resource...")
        try:
            outline_data = await client.read_resource(f"podcast://{task_id}/outline")
            print(f"✅ Outline resource accessible")
            
            # Check outline structure
            if 'outline' in outline_data:
                outline = outline_data['outline']
                print(f"✅ Outline data type: {type(outline)}")
                
                if isinstance(outline, dict):
                    print(f"✅ Outline keys: {list(outline.keys())}")
                    
                    # Check for common outline fields
                    if 'title_suggestion' in outline:
                        print(f"✅ Outline title: {outline['title_suggestion']}")
                    if 'segments' in outline and isinstance(outline['segments'], list):
                        print(f"✅ Outline segments: {len(outline['segments'])} segments")
                else:
                    print(f"⚠️  Outline data is not a dict: {outline}")
            else:
                print(f"⚠️  No 'outline' key in response: {list(outline_data.keys())}")
                
        except Exception as e:
            print(f"❌ Error accessing outline resource: {e}")
            return False
        
        # Test other resources for comparison
        print("\n📄 Testing other podcast resources...")
        
        try:
            transcript = await client.read_resource(f"podcast://{task_id}/transcript")
            print(f"✅ Transcript resource: {len(transcript) if isinstance(transcript, str) else 'not string'} chars")
        except Exception as e:
            print(f"⚠️  Transcript resource error: {e}")
        
        try:
            audio_data = await client.read_resource(f"podcast://{task_id}/audio")
            print(f"✅ Audio resource: {audio_data.get('format', 'unknown')} format")
        except Exception as e:
            print(f"⚠️  Audio resource error: {e}")
        
        try:
            metadata = await client.read_resource(f"podcast://{task_id}/metadata")
            print(f"✅ Metadata resource: {metadata.get('title', 'no title')}")
        except Exception as e:
            print(f"⚠️  Metadata resource error: {e}")
        
        print("\n🎉 Outline resource test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_outline_resource_error_cases():
    """Test error cases for outline resource."""
    print("\n🔍 Testing outline resource error cases...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        # Test non-existent task
        try:
            await client.read_resource("podcast://non-existent-task/outline")
            print("❌ Should have failed for non-existent task")
            return False
        except Exception as e:
            print(f"✅ Correctly failed for non-existent task: {e}")
        
        print("✅ Error case testing completed")
        return True
        
    except Exception as e:
        print(f"❌ Error case testing failed: {e}")
        return False

async def main():
    """Run outline resource tests."""
    print("=" * 80)
    print("PODCAST OUTLINE RESOURCE TEST")
    print("=" * 80)
    
    # Test workflow
    success1 = await test_outline_resource_workflow()
    
    # Test error cases
    success2 = await test_outline_resource_error_cases()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✅ ALL OUTLINE RESOURCE TESTS PASSED")
        return 0
    else:
        print("❌ SOME OUTLINE RESOURCE TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
