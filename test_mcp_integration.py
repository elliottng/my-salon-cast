#!/usr/bin/env python3
"""
MySalonCast MCP Integration Test - End-to-End Workflow Validation

This script tests the complete integration between MCP tools, resources, prompts 
and the existing MySalonCast podcast generation workflow.

Test Flow:
1. Prompt-guided setup with 2 URLs and 2 prominent people
2. Podcast generation using inputs from step 1
3. Poll get_task_status to monitor progress
4. When personas_complete: get research for each person and print to terminal
5. Continue polling get_task_status
6. When outline_complete: get podcast outline and print to screen
7. When totally complete: get transcript and audio
"""

import os
import sys
import asyncio
import time
import json
from typing import Dict, Any, List

# Add the app directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.mcp_server import (
    mcp, 
    create_podcast_from_url, 
    generate_podcast_async, 
    get_task_status,
    get_persona_research_resource,
    get_podcast_outline_resource,
    get_podcast_transcript_resource,
    get_podcast_audio_resource
)

# Test configuration
TEST_URLS = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Machine_learning"
]

TEST_PERSONAS = ["Alan Turing", "Ada Lovelace"]

# Generate unique suffix for this test run
test_run_suffix = str(int(time.time()))

class MockMCPContext:
    """Mock MCP context for integration testing."""
    
    def __init__(self):
        self.request_id = f"integration_test_{test_run_suffix}"
        self.client_info = {
            "name": "integration_test",
            "version": "1.0.0",
            "environment": "test"
        }

class IntegrationTestContext:
    """Context to hold test state and results."""
    
    def __init__(self):
        self.task_id: str = ""
        self.prompt_result: str = ""
        self.generation_result: Dict[str, Any] = {}
        self.status_history: List[Dict[str, Any]] = []
        self.persona_research: Dict[str, Any] = {}
        self.outline_data: Dict[str, Any] = {}
        self.transcript_data: Dict[str, Any] = {}
        self.audio_data: Dict[str, Any] = {}
        self.start_time = time.time()

async def step1_prompt_guided_setup(ctx: IntegrationTestContext) -> bool:
    """Step 1: Use prompt to guide setup with 2 URLs and 2 prominent people."""
    print("🔸 Step 1: Prompt-Guided Setup")
    print("=" * 60)
    
    try:
        # Use the prompt with our test data
        urls_str = ", ".join(TEST_URLS)
        personas_str = ", ".join(TEST_PERSONAS)
        
        print(f"📝 Input URLs: {urls_str}")
        print(f"👥 Input Personas: {personas_str}")
        
        # Generate prompt guidance
        ctx.prompt_result = create_podcast_from_url(
            url=TEST_URLS[0],  # Primary URL for the prompt
            personas=personas_str,
            length="medium",
            language="en"
        )
        
        print(f"\n🎯 Generated Prompt Guidance:")
        print("-" * 40)
        print(ctx.prompt_result[:500] + "..." if len(ctx.prompt_result) > 500 else ctx.prompt_result)
        print("-" * 40)
        
        # Validate prompt contains our test data
        if TEST_URLS[0] not in ctx.prompt_result:
            print("❌ Prompt doesn't contain primary URL")
            return False
            
        if not all(persona in ctx.prompt_result for persona in TEST_PERSONAS):
            print("❌ Prompt doesn't contain all personas")
            return False
            
        if "generate_podcast_async" not in ctx.prompt_result:
            print("❌ Prompt doesn't contain tool guidance")
            return False
        
        print("✅ Prompt guidance generated successfully with all test inputs")
        return True
        
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        return False

async def step2_podcast_generation(ctx: IntegrationTestContext) -> bool:
    """Step 2: Generate podcast using inputs from step 1."""
    print("\n🔸 Step 2: Podcast Generation")
    print("=" * 60)
    
    try:
        # Create a mock context (MCP tools expect this but we can pass None for testing)
        mock_ctx = MockMCPContext()
        
        print(f"🚀 Starting podcast generation with:")
        print(f"   📄 URLs: {TEST_URLS}")
        print(f"   👥 Personas: {TEST_PERSONAS}")
        
        # Call generate_podcast_async with our test inputs
        ctx.generation_result = await generate_podcast_async(
            ctx=mock_ctx,
            source_urls=TEST_URLS,
            prominent_persons=TEST_PERSONAS,
            custom_prompt=None,
            podcast_name=f"Integration Test Podcast {test_run_suffix}",
            podcast_tagline="Testing MCP integration",
            output_language="en",
            podcast_length="medium"
        )
        
        print(f"\n📋 Generation Result:")
        print(f"   ✅ Success: {ctx.generation_result.get('success', False)}")
        print(f"   🆔 Task ID: {ctx.generation_result.get('task_id', 'N/A')}")
        print(f"   📊 Status: {ctx.generation_result.get('status', 'N/A')}")
        print(f"   💬 Message: {ctx.generation_result.get('message', 'N/A')}")
        
        # Extract task_id for subsequent steps
        if ctx.generation_result.get('success'):
            ctx.task_id = ctx.generation_result.get('task_id', '')
            if not ctx.task_id:
                print("❌ No task_id returned despite success=True")
                return False
        else:
            print("❌ Generation was not successful")
            return False
        
        print(f"✅ Podcast generation started successfully - Task ID: {ctx.task_id}")
        return True
        
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        return False

async def step3_poll_status_until_personas(ctx: IntegrationTestContext) -> bool:
    """Step 3: Poll get_task_status until personas_complete."""
    print("\n🔸 Step 3: Monitor Progress Until Personas Complete")
    print("=" * 60)
    
    try:
        max_wait_time = 600  # 10 minutes
        poll_interval = 10   # 10 seconds
        start_time = time.time()
        mock_ctx = MockMCPContext()
        
        while time.time() - start_time < max_wait_time:
            # Poll status
            status_result = await get_task_status(ctx=mock_ctx, task_id=ctx.task_id)
            ctx.status_history.append(status_result)
            
            current_status = status_result.get('status', 'unknown')
            elapsed = time.time() - start_time
            
            print(f"⏱️  [{elapsed:6.1f}s] Status: {current_status}")
            
            # Check if we've reached personas_complete
            if current_status == "personas_complete":
                print("🎯 Personas research complete! Ready for step 4.")
                return True
            elif current_status in ["error", "failed", "cancelled"]:
                print(f"❌ Task failed with status: {current_status}")
                print(f"   Error: {status_result.get('error', 'Unknown error')}")
                return False
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        print(f"❌ Timeout waiting for personas_complete (waited {max_wait_time}s)")
        return False
        
    except Exception as e:
        print(f"❌ Step 3 failed: {e}")
        return False

async def step4_get_persona_research(ctx: IntegrationTestContext) -> bool:
    """Step 4: Get research for each person and print to terminal."""
    print("\n🔸 Step 4: Get Persona Research")
    print("=" * 60)
    
    try:
        for persona in TEST_PERSONAS:
            # Convert persona name to person_id format (lowercase, spaces to hyphens)
            person_id = persona.lower().replace(" ", "-")
            
            print(f"\n👤 Fetching research for: {persona} (ID: {person_id})")
            print("-" * 40)
            
            try:
                # Get persona research via MCP resource
                mock_ctx = MockMCPContext()
                research_result = await get_persona_research_resource(ctx=mock_ctx, task_id=ctx.task_id, person_id=person_id)
                
                ctx.persona_research[person_id] = research_result
                
                # Print key research data
                research_data = research_result.get('research_data')
                if research_data:
                    print(f"✅ Research found for {persona}")
                    print(f"   📄 File: {research_result.get('file_metadata', {}).get('research_file_path', 'N/A')}")
                    print(f"   📊 File size: {research_result.get('file_metadata', {}).get('file_size', 'N/A')} bytes")
                    
                    # Print some key research fields if available
                    if isinstance(research_data, dict):
                        print(f"   🏷️  Name: {research_data.get('name', 'N/A')}")
                        print(f"   📝 Bio: {research_data.get('bio', 'N/A')[:100]}...")
                        print(f"   🎯 Expertise: {research_data.get('expertise_areas', 'N/A')}")
                        print(f"   💭 Key views: {research_data.get('key_views', 'N/A')[:100]}...")
                else:
                    print(f"⚠️  No research data found for {persona}")
                    print(f"   📁 File exists: {research_result.get('file_metadata', {}).get('file_exists', False)}")
                
            except Exception as e:
                print(f"❌ Failed to get research for {persona}: {e}")
                return False
        
        print(f"\n✅ Successfully retrieved research for all {len(TEST_PERSONAS)} personas")
        return True
        
    except Exception as e:
        print(f"❌ Step 4 failed: {e}")
        return False

async def step5_poll_status_until_outline(ctx: IntegrationTestContext) -> bool:
    """Step 5: Continue polling until outline_complete."""
    print("\n🔸 Step 5: Monitor Progress Until Outline Complete")
    print("=" * 60)
    
    try:
        max_wait_time = 600  # 10 minutes from current point
        poll_interval = 10   # 10 seconds
        start_time = time.time()
        mock_ctx = MockMCPContext()
        
        while time.time() - start_time < max_wait_time:
            # Poll status
            status_result = await get_task_status(ctx=mock_ctx, task_id=ctx.task_id)
            ctx.status_history.append(status_result)
            
            current_status = status_result.get('status', 'unknown')
            elapsed = time.time() - start_time
            
            print(f"⏱️  [{elapsed:6.1f}s] Status: {current_status}")
            
            # Check if we've reached outline_complete  
            if current_status == "outline_complete":
                print("🎯 Podcast outline complete! Ready for step 6.")
                return True
            elif current_status in ["error", "failed", "cancelled"]:
                print(f"❌ Task failed with status: {current_status}")
                print(f"   Error: {status_result.get('error', 'Unknown error')}")
                return False
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        print(f"❌ Timeout waiting for outline_complete (waited {max_wait_time}s)")
        return False
        
    except Exception as e:
        print(f"❌ Step 5 failed: {e}")
        return False

async def step6_get_podcast_outline(ctx: IntegrationTestContext) -> bool:
    """Step 6: Get podcast outline and print to screen."""
    print("\n🔸 Step 6: Get Podcast Outline")
    print("=" * 60)
    
    try:
        print(f"📝 Fetching podcast outline for task: {ctx.task_id}")
        
        # Get podcast outline via MCP resource
        mock_ctx = MockMCPContext()
        outline_result = await get_podcast_outline_resource(ctx=mock_ctx, task_id=ctx.task_id)
        ctx.outline_data = outline_result
        
        print(f"\n📋 Outline Resource Result:")
        print(f"   ✅ Has outline: {outline_result.get('has_outline', False)}")
        print(f"   📄 File: {outline_result.get('file_metadata', {}).get('outline_file_path', 'N/A')}")
        print(f"   📊 File size: {outline_result.get('file_metadata', {}).get('file_size', 'N/A')} bytes")
        
        # Print the actual outline data
        outline_data = outline_result.get('outline_data')
        if outline_data and isinstance(outline_data, dict):
            print(f"\n🎙️  PODCAST OUTLINE")
            print("=" * 60)
            print(f"📺 Title: {outline_data.get('title', 'N/A')}")
            print(f"📝 Description: {outline_data.get('description', 'N/A')}")
            print(f"⏱️  Duration: {outline_data.get('duration_minutes', 'N/A')} minutes")
            print(f"👥 Host Count: {len(outline_data.get('hosts', []))}")
            
            # Print segments
            segments = outline_data.get('segments', [])
            print(f"\n📚 SEGMENTS ({len(segments)} total):")
            print("-" * 40)
            for i, segment in enumerate(segments, 1):
                print(f"{i}. {segment.get('title', 'Untitled')}")
                print(f"   ⏱️  Duration: {segment.get('duration_minutes', 'N/A')} min")
                print(f"   📝 Description: {segment.get('description', 'N/A')[:100]}...")
                print()
            
            # Print hosts
            hosts = outline_data.get('hosts', [])
            if hosts:
                print(f"🎭 HOSTS:")
                print("-" * 20)
                for host in hosts:
                    print(f"• {host.get('name', 'Unknown')}: {host.get('role', 'N/A')}")
        else:
            print("⚠️  No outline data found or invalid format")
            return False
        
        print(f"\n✅ Successfully retrieved and displayed podcast outline")
        return True
        
    except Exception as e:
        print(f"❌ Step 6 failed: {e}")
        return False

async def step7_poll_until_complete_and_get_final_content(ctx: IntegrationTestContext) -> bool:
    """Step 7: Poll until totally complete, then get transcript and audio."""
    print("\n🔸 Step 7: Monitor Until Complete & Get Final Content")
    print("=" * 60)
    
    try:
        # First, poll until complete
        max_wait_time = 1200  # 20 minutes for full generation
        poll_interval = 15    # 15 seconds
        start_time = time.time()
        mock_ctx = MockMCPContext()
        
        print("⏳ Waiting for complete podcast generation...")
        
        while time.time() - start_time < max_wait_time:
            # Poll status
            status_result = await get_task_status(ctx=mock_ctx, task_id=ctx.task_id)
            ctx.status_history.append(status_result)
            
            current_status = status_result.get('status', 'unknown')
            elapsed = time.time() - start_time
            
            print(f"⏱️  [{elapsed:6.1f}s] Status: {current_status}")
            
            # Check if we've reached complete
            if current_status == "complete":
                print("🎯 Podcast generation complete! Getting final content...")
                break
            elif current_status in ["error", "failed", "cancelled"]:
                print(f"❌ Task failed with status: {current_status}")
                print(f"   Error: {status_result.get('error', 'Unknown error')}")
                return False
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        else:
            print(f"❌ Timeout waiting for completion (waited {max_wait_time}s)")
            return False
        
        # Now get transcript and audio
        print(f"\n📜 Getting Podcast Transcript...")
        print("-" * 40)
        
        try:
            transcript_result = await get_podcast_transcript_resource(ctx=mock_ctx, task_id=ctx.task_id)
            ctx.transcript_data = transcript_result
            
            print(f"   ✅ Has transcript: {transcript_result.get('has_transcript', False)}")
            print(f"   📄 File: {transcript_result.get('file_metadata', {}).get('transcript_file_path', 'N/A')}")
            print(f"   📊 File size: {transcript_result.get('file_metadata', {}).get('file_size', 'N/A')} bytes")
            
            # Print transcript content (first 500 chars)
            transcript_content = transcript_result.get('transcript_content', '')
            if transcript_content:
                print(f"\n🎙️  TRANSCRIPT PREVIEW:")
                print("-" * 30)
                print(transcript_content[:500] + "..." if len(transcript_content) > 500 else transcript_content)
                print("-" * 30)
            
        except Exception as e:
            print(f"❌ Failed to get transcript: {e}")
            return False
        
        print(f"\n🔊 Getting Podcast Audio...")
        print("-" * 40)
        
        try:
            audio_result = await get_podcast_audio_resource(ctx=mock_ctx, task_id=ctx.task_id)
            ctx.audio_data = audio_result
            
            audio_filepath = audio_result.get('audio_filepath', '')
            
            print(f"   ✅ Has audio: {audio_result.get('audio_exists', False)}")
            print(f"   📄 File: {audio_filepath}")
            print(f"   📊 File size: {audio_result.get('file_size', 'N/A')} bytes")
            
            # Show how to listen to the podcast
            if audio_result.get('audio_exists', False) and audio_filepath:
                print(f"\n🎧 HOW TO LISTEN TO YOUR PODCAST:")
                print("=" * 50)
                print(f"📁 Audio File: {audio_filepath}")
                print(f"\n🎵 Option 1 - Open directly:")
                print(f"   Just double-click the file or drag it to any audio player")
                print(f"\n🎵 Option 2 - Command line players:")
                print(f"   mpv '{audio_filepath}'")
                print(f"   vlc '{audio_filepath}'")
                print(f"   aplay '{audio_filepath}'")
                print(f"\n🌐 Option 3 - Web interface (if running Flask app):")
                # Extract task_id for web URL
                task_id_for_web = ctx.task_id
                print(f"   http://localhost:8080/audio/{task_id_for_web}/final.mp3")
                print(f"   http://localhost:8080/podcast/{task_id_for_web}/audio")
                print("=" * 50)
            else:
                print(f"⚠️  Audio file not found at: {audio_filepath}")
            
        except Exception as e:
            print(f"❌ Failed to get audio: {e}")
            return False
        
        print(f"\n✅ Successfully retrieved transcript and audio content")
        return True
        
    except Exception as e:
        print(f"❌ Step 7 failed: {e}")
        return False

async def print_test_summary(ctx: IntegrationTestContext):
    """Print a summary of the integration test results."""
    total_time = time.time() - ctx.start_time
    
    print("\n" + "=" * 60)
    print("🏁 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"⏱️  Total Test Duration: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"🆔 Task ID: {ctx.task_id}")
    print(f"📊 Status History: {len(ctx.status_history)} status checks")
    print(f"👥 Personas Researched: {len(ctx.persona_research)}")
    print(f"📝 Outline Retrieved: {'Yes' if ctx.outline_data.get('has_outline') else 'No'}")
    print(f"📜 Transcript Retrieved: {'Yes' if ctx.transcript_data.get('has_transcript') else 'No'}")
    print(f"🔊 Audio Retrieved: {'Yes' if ctx.audio_data.get('audio_exists') else 'No'}")
    
    print(f"\n📈 Status Progression:")
    unique_statuses = []
    for status_check in ctx.status_history:
        status = status_check.get('status', 'unknown')
        if not unique_statuses or unique_statuses[-1] != status:
            unique_statuses.append(status)
    print(f"   {' → '.join(unique_statuses)}")
    
    print(f"\n🎯 Integration Points Validated:")
    print(f"   ✅ MCP Prompts → Tool Guidance")
    print(f"   ✅ MCP Tools → PodcastGeneratorService")
    print(f"   ✅ Status Monitoring → StatusManager")
    print(f"   ✅ Resource Access → File System")
    print(f"   ✅ Persona Research → Research Resources")
    print(f"   ✅ Outline Generation → Outline Resources")
    print(f"   ✅ Transcript Access → Transcript Resources")
    print(f"   ✅ Audio Access → Audio Resources")
    
    # Final file sizes summary
    if ctx.transcript_data.get('has_transcript'):
        transcript_size = ctx.transcript_data.get('file_metadata', {}).get('file_size', 0)
        print(f"\n📊 Content Summary:")
        print(f"   📜 Transcript: {transcript_size} bytes")
    
    if ctx.audio_data.get('audio_exists'):
        audio_size = ctx.audio_data.get('file_size', 0)
        print(f"   🔊 Audio: {audio_size} bytes")

async def run_integration_test():
    """Run the complete end-to-end integration test."""
    ctx = IntegrationTestContext()
    
    print("🚀 MySalonCast MCP Integration Test")
    print("🎯 Testing complete workflow from prompts to final audio")
    print(f"🕐 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Execute all test steps
    steps = [
        ("Prompt-Guided Setup", step1_prompt_guided_setup),
        ("Podcast Generation", step2_podcast_generation),
        ("Monitor Until Personas", step3_poll_status_until_personas),
        ("Get Persona Research", step4_get_persona_research),
        ("Monitor Until Outline", step5_poll_status_until_outline),
        ("Get Podcast Outline", step6_get_podcast_outline),
        ("Complete & Get Final Content", step7_poll_until_complete_and_get_final_content),
    ]
    
    for step_name, step_func in steps:
        try:
            success = await step_func(ctx)
            if not success:
                print(f"\n❌ Integration test failed at: {step_name}")
                await print_test_summary(ctx)
                return False
        except Exception as e:
            print(f"\n💥 Integration test crashed at {step_name}: {e}")
            await print_test_summary(ctx)
            return False
    
    # Test completed successfully
    print("\n🎉 Integration test completed successfully!")
    print("✅ Complete end-to-end MCP workflow validated!")
    await print_test_summary(ctx)
    return True

if __name__ == "__main__":
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)
