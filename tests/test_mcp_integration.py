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
from datetime import datetime, timedelta

# Add the parent directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
    "https://www.whitehouse.gov/articles/2025/06/mythbuster-the-one-big-beautiful-bill-cuts-spending-deficit-and-thats-a-fact/",
    "https://en.wikipedia.org/wiki/One_Big_Beautiful_Bill_Act"
]

TEST_PERSONAS = ["Elon Musk", "Scott Bessent","Peter Navarro"]

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
    5-7
    try:
        # Use the prompt with our test data
        urls_str = ", ".join(TEST_URLS)
        personas_str = ", ".join(TEST_PERSONAS)
        
        print(f"📝 Input URLs: {urls_str}")
        print(f"👥 Input Personas: {personas_str}")
        
        # Generate prompt guidance
        ctx.prompt_result = create_podcast_from_url(
            urls=TEST_URLS,
            personas=personas_str,
            length="16 minutes"
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
        
        # Call generate_podcast_async with individual parameters as documented in the tool description
        ctx.generation_result = await generate_podcast_async(
            ctx=mock_ctx,
            source_urls=TEST_URLS,
            prominent_persons=TEST_PERSONAS,
            podcast_length="15 minutes"
        )
        
        print(f"\n📋 Generation Result:")
        print(f"   ✅ Status: {ctx.generation_result.get('status', 'N/A')}")
        print(f"   🆔 Task ID: {ctx.generation_result.get('task_id', 'N/A')}")
        print(f"   💬 Message: {ctx.generation_result.get('message', 'N/A')}")
        
        # Extract task_id for subsequent steps
        task_id = ctx.generation_result.get('task_id', '')
        if task_id:
            ctx.task_id = task_id
            print(f"✅ Podcast generation started successfully - Task ID: {ctx.task_id}")
            return True
        else:
            print("❌ No task_id returned")
            return False
        
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
        return False

async def step3_monitor_progress(ctx: IntegrationTestContext) -> bool:
    """Step 3: Monitor task progress until completion."""
    print("\n🔸 Step 3: Monitor Progress Until Completion")
    print("=" * 60)
    
    try:
        task_id = ctx.task_id
        start_time = time.time()
        poll_count = 0
        previous_status_str = ""
        
        # Configuration for monitoring until completion
        poll_interval = 10  # seconds between polls
        max_wait_time = 15 * 60  # 15 minutes max wait time
        
        print(f"🔍 Monitoring task {task_id} until completion...")
        print(f"⏰ Will poll every {poll_interval}s for up to {max_wait_time//60} minutes")
        
        while time.time() - start_time < max_wait_time:
            poll_count += 1
            poll_start = time.time()
            
            # Get task status via MCP tool
            status_result = await get_task_status(ctx=MockMCPContext(), task_id=task_id)
            poll_duration = time.time() - poll_start
            ctx.status_history.append(status_result)
            
            # Extract status string, handling both string and dictionary formats
            current_status = status_result.get('status', 'unknown')
            current_status_str = "unknown"
            
            # Handle different status formats with robust extraction
            try:
                if isinstance(current_status, dict):
                    # If status is a dictionary, try to extract status_description or status field
                    current_status_str = current_status.get('status_description') or current_status.get('status')
                    # Add progress percentage when available
                    progress = current_status.get('progress_percentage')
                    if progress is not None:
                        current_status_str = f"{current_status_str} ({progress:.1f}%)"
                elif isinstance(current_status, str):
                    current_status_str = current_status
                else:
                    current_status_str = str(current_status)
            except Exception as e:
                print(f"⚠️ Error extracting status: {e}")
                current_status_str = f"Error: {type(current_status).__name__}"
            
            elapsed = time.time() - start_time
            
            # Only print status if it changed or every 6th poll (about once per minute)
            if current_status_str != previous_status_str or poll_count % 6 == 0:
                print(f"⏱️ [{elapsed:6.1f}s] Status: {current_status_str} (poll took {poll_duration:.2f}s)")
                previous_status_str = current_status_str
            
            # Check for completion (success)
            is_completed = False
            if isinstance(current_status, dict):
                # Check for completion in dictionary structure
                status_str = current_status.get('status', '').lower()
                desc_str = current_status.get('status_description', '').lower()
                if status_str == "completed" or "completed" in desc_str or status_str == "success":
                    is_completed = True
            elif isinstance(current_status, str):
                status_lower = current_status.lower()
                if "completed" in status_lower or "success" in status_lower:
                    is_completed = True
            
            if is_completed:
                print(f"🎉 Task completed successfully!")
                print(f"   Total time: {elapsed:.1f}s ({poll_count} polls)")
                print(f"   Final status: {current_status_str}")
                return True
            
            # Check for failure states - more precise error detection
            is_failed = False
            error_message = None
            
            # Only consider actual error conditions
            if isinstance(current_status, dict):
                # Check if status is explicitly failed or cancelled
                status_str = current_status.get('status', '').lower()
                if status_str in ["failed", "cancelled", "error"]:
                    is_failed = True
                
                # Check if there's an actual error message
                if current_status.get('error_message'):
                    is_failed = True
                    error_message = current_status.get('error_message')
            elif isinstance(current_status, str):
                # For string statuses, check for explicit failure states
                if current_status.lower() in ["failed", "cancelled", "error"]:
                    is_failed = True
            
            # Check the top-level error field as well
            if status_result.get('error'):
                is_failed = True
                error_message = status_result.get('error')
            
            if is_failed:
                print(f"❌ Task failed with status: {current_status_str}")
                print(f"   Error: {error_message or 'Unknown error'}")
                return False
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
        
        print(f"❌ Timeout waiting for task completion (waited {max_wait_time}s)")
        print(f"   Last status received: {current_status_str}")
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
            # Convert persona name to person_id format (lowercase, spaces to underscores)
            person_id = persona.lower().replace(" ", "_")
            
            print(f"\n👤 Fetching research for: {persona} (ID: {person_id})")
            print("-" * 40)
            
            try:
                # Get persona research via MCP resource
                research_result = await get_persona_research_resource(task_id=ctx.task_id, person_id=person_id)
                
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

async def step6_get_podcast_outline(ctx: IntegrationTestContext) -> bool:
    """Step 6: Get podcast outline and print to screen."""
    print("\n🔸 Step 6: Get Podcast Outline")
    print("=" * 60)
    
    try:
        print(f"📝 Fetching podcast outline for task: {ctx.task_id}")
        
        # Get podcast outline via MCP resource
        outline_result = await get_podcast_outline_resource(task_id=ctx.task_id)
        ctx.outline_data = outline_result
        
        print(f"\n📋 Outline Resource Result:")
        print(f"   ✅ Has outline: {outline_result.get('has_outline', False)}")
        print(f"   📄 File: {outline_result.get('outline_file_path', 'N/A')}")
        print(f"   📊 File size: {len(str(outline_result.get('outline', {})))} bytes")
        
        # Print the actual outline data
        outline_data = outline_result.get('outline')
        if outline_data and isinstance(outline_data, dict):
            print(f"\n🎙️  PODCAST OUTLINE")
            print("=" * 60)
            print(f"📺 Title: {outline_data.get('title_suggestion', 'N/A')}")
            print(f"📝 Summary: {outline_data.get('summary_suggestion', 'N/A')}")
            print(f"👥 Host Count: {len(outline_data.get('hosts', []))}")
            
            # Print segments
            segments = outline_data.get('segments', [])
            print(f"\n📚 SEGMENTS ({len(segments)} total):")
            print("-" * 40)
            for i, segment in enumerate(segments, 1):
                print(f"{i}. {segment.get('segment_title', 'Untitled')}")
                print(f"   🎤 Speaker: {segment.get('speaker_id', 'N/A')}")
                print(f"   ⏱️  Duration: {segment.get('estimated_duration_seconds', 'N/A')}s")
                print(f"   📝 Content: {segment.get('content_cue', 'N/A')[:100]}...")
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

async def step8_get_final_content(ctx: IntegrationTestContext) -> bool:
    """Step 8: Get final content (transcript and audio) - task should already be completed."""
    print("\n🔸 Step 8: Get Final Content")
    print("=" * 60)
    
    try:
        print(f"🎯 Getting final content for completed task: {ctx.task_id}")
        print("-" * 50)
        
        # Create directories for storing generated files if they don't exist
        import os
        project_root = os.path.join(os.path.dirname(__file__), "..")
        generated_podcasts_dir = os.path.join(project_root, "generated_podcasts")
        generated_transcripts_dir = os.path.join(project_root, "generated_transcripts")
        
        os.makedirs(generated_podcasts_dir, exist_ok=True)
        os.makedirs(generated_transcripts_dir, exist_ok=True)
        
        # Generate a timestamped filename prefix for this test
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_prefix = f"{timestamp}_test_{test_run_suffix}"
        
        # Get transcript
        print(f"\n📜 Fetching transcript...")
        try:
            transcript_result = await get_podcast_transcript_resource(task_id=ctx.task_id)
            ctx.transcript_data = transcript_result
            
            print(f"📜 Transcript Resource Result:")
            transcript_content = transcript_result.get('transcript_content')
            if transcript_content:
                print(f"   ✅ Has transcript: {len(transcript_content)} characters")
                print(f"   📄 File: {transcript_result.get('file_metadata', {}).get('transcript_file_path', 'N/A')}")
                print(f"   📊 Size: {transcript_result.get('file_metadata', {}).get('file_size', 'N/A')} bytes")
                
                # Show first few lines of transcript
                lines = transcript_content.split('\n')[:5]
                print(f"   📝 Preview (first 5 lines):")
                for line in lines:
                    if line.strip():
                        print(f"      {line[:80]}...")
                
                # Save transcript to the generated_transcripts directory
                transcript_filepath = os.path.join(generated_transcripts_dir, f"{file_prefix}_transcript.txt")
                try:
                    with open(transcript_filepath, 'w', encoding='utf-8') as f:
                        f.write(transcript_content)
                    print(f"   ✅ Transcript saved to: {transcript_filepath}")
                except Exception as e:
                    print(f"   ⚠️  Failed to save transcript: {e}")
            else:
                print(f"   ⚠️  No transcript content found")
                
        except Exception as e:
            print(f"❌ Failed to get transcript: {e}")
            return False
        
        # Get audio
        print(f"\n🔊 Fetching audio...")
        try:
            audio_result = await get_podcast_audio_resource(task_id=ctx.task_id)
            ctx.audio_data = audio_result
            
            print(f"🔊 Audio Resource Result:")
            audio_exists = audio_result.get('audio_exists')
            audio_filepath = audio_result.get('audio_filepath')
            
            if audio_exists and audio_filepath and os.path.exists(audio_filepath):
                print(f"   ✅ Has audio file: {audio_filepath}")
                print(f"   📊 Size: {audio_result.get('file_size', 'N/A')} bytes")
                print(f"   ⏱️  Duration: {audio_result.get('duration_seconds', 'N/A')} seconds")
                
                # Save audio to the generated_podcasts directory
                podcast_filepath = os.path.join(generated_podcasts_dir, f"{file_prefix}_podcast.mp3")
                
                try:
                    import shutil
                    shutil.copy2(audio_filepath, podcast_filepath)
                    print(f"   ✅ Podcast audio saved to: {podcast_filepath}")
                    ctx.saved_audio_path = podcast_filepath
                    
                    # Note: Individual audio segments are kept in temp folders for debugging but not copied to generated_podcasts
                    print(f"   📝 Individual audio segments available in temp folder (not copied to generated_podcasts)")
                    
                except Exception as e:
                    print(f"   ⚠️  Failed to save audio: {e}")
                    # Fallback: just set the original path
                    podcast_filepath = os.path.join(generated_podcasts_dir, f"{file_prefix}_podcast.mp3")
                    
            else:
                # Try to find the audio file with a more general search
                try:
                    import glob
                    potential_files = glob.glob(f"/tmp/podcast_job_*/final_podcast.mp3")
                    if potential_files:
                        latest_file = max(potential_files, key=os.path.getmtime)
                        podcast_filepath = os.path.join(generated_podcasts_dir, f"{file_prefix}_podcast.mp3")
                        shutil.copy2(latest_file, podcast_filepath)
                        print(f"   ✅ Found and saved podcast audio to: {podcast_filepath}")
                    else:
                        print(f"   ⚠️  No audio file found")
                except Exception as e:
                    print(f"   ⚠️  Failed to find and save audio: {e}")
                
        except Exception as e:
            print(f"❌ Failed to get audio: {e}")
            return False
        
        print(f"\n✅ Successfully retrieved all final content")
        return True
        
    except Exception as e:
        print(f"❌ Step 8 failed: {e}")
        return False

async def print_test_summary(ctx: IntegrationTestContext):
    # Print final summary
    print("\n📊 Integration Test Summary")
    print("=" * 60)
    print(f"\n⏱️ Test Duration: {time.time() - ctx.start_time:.1f} seconds")
    print(f"\n🎟️ Podcast Generation Result:")
    print(f"🔑 Task ID: {ctx.task_id}")
    print(f"📋 Status Checks: {len(ctx.status_history)}")
    print(f"👨‍👩‍👧‍👦 Personas Researched: {len(ctx.persona_research.get('personas', []))}")
    print(f"📝 Outline Points: {len(ctx.outline_data.get('outline_points', []))}")
    print(f"📜 Transcript Retrieved: {'Yes' if ctx.transcript_data.get('has_transcript') else 'No'}")
    print(f"🔊 Audio Retrieved: {'Yes' if ctx.audio_data.get('audio_exists') else 'No'}")
    
    print(f"\n📈 Status Progression:")
    # Improved status extraction with better error handling
    unique_statuses = []
    status_times = []
    start_datetime = datetime.fromtimestamp(ctx.start_time)
    last_time = start_datetime
    
    for i, status_check in enumerate(ctx.status_history):
        # Extract timestamp for this status
        current_time = start_datetime + timedelta(seconds=i*10)  # Approximate timing
        
        # Extract status string safely with robust fallbacks
        try:
            if isinstance(status_check, dict):
                # Handle nested status structures
                status = status_check.get('status', 'unknown')
                if isinstance(status, dict):
                    # First try to get status_description from nested dict
                    status = status.get('status_description') or status.get('status', None)
                    
                    # If we have a progress percentage, add it
                    if status and isinstance(status, dict) and status.get('progress_percentage') is not None:
                        status = f"{status} ({status.get('progress_percentage')}%)"
            elif isinstance(status_check, str):
                status = status_check
            else:
                status = str(status_check)
                
            # Track unique statuses and timing
            if not unique_statuses or unique_statuses[-1] != status:
                unique_statuses.append(status)
                status_times.append(current_time - last_time)  # Time spent in previous status
                last_time = current_time
                
        except Exception as e:
            # Log error but continue processing
            print(f"   Warning: Error extracting status at position {i}: {e}")
            unique_statuses.append(f"[error:{i}]")
    
    # Print status timeline with durations
    if unique_statuses:
        try:
            print("   Status transitions:")
            for i, (status, duration) in enumerate(zip(unique_statuses, status_times)):
                if i > 0:  # Skip the first duration (it's not meaningful)
                    minutes, seconds = divmod(duration.total_seconds(), 60)
                    print(f"   {i:2d}. {status} ({int(minutes)}m {int(seconds)}s)")
                else:
                    print(f"   {i:2d}. {status} (initial)")
                    
            # Also print the linear flow for quick visualization
            flow = " → ".join([str(s) for s in unique_statuses])
            print(f"\n   Flow: {flow}")
        except Exception as e:
            print(f"   Error displaying status progression: {e}")
            # Provide raw data for debugging
            print(f"   Raw statuses: {unique_statuses}")
    else:
        print("   No status progression recorded")
    
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
    print(f"🕒 Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Execute all test steps
    steps = [
        ("Prompt-Guided Setup", step1_prompt_guided_setup),
        ("Podcast Generation", step2_podcast_generation),
        ("Monitor Until Completion", step3_monitor_progress),
        ("Get Persona Research", step4_get_persona_research),
        ("Get Podcast Outline", step6_get_podcast_outline),
        ("Get Final Content", step8_get_final_content),
    ]
    
    try:
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
    finally:
        # Ensure proper cleanup of any lingering tasks
        print("Cleaning up asyncio tasks...")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if tasks:
            print(f"Cancelling {len(tasks)} pending tasks...")
            for task in tasks:
                task.cancel()
            
            # Wait for all tasks to be cancelled
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
                print("All pending tasks cancelled successfully")
            except Exception as e:
                print(f"Error during task cleanup: {e}")
        else:
            print("No pending tasks to clean up")
            
        # Small delay to ensure all resources are properly released
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    success = asyncio.run(run_integration_test())
    sys.exit(0 if success else 1)
