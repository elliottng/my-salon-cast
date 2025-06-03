#!/usr/bin/env python3
"""
Debug script to understand the TTS health monitoring discrepancy.
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append('.')

from app.tts_service import GoogleCloudTtsService

async def debug_tts_health():
    """Debug TTS service health metrics."""
    
    print("🔍 Debugging TTS service health...")
    
    # Step 1: Check initial class state
    print("\n1. Initial class state:")
    initial_metrics = GoogleCloudTtsService.get_current_metrics()
    print(f"   Executor: {GoogleCloudTtsService._executor}")
    print(f"   Metrics: {GoogleCloudTtsService._metrics}")
    print(f"   Status: {initial_metrics.get('executor_status')}")
    print(f"   Jobs completed: {initial_metrics.get('total_jobs_completed')}")
    
    # Step 2: Create instance and run operations
    print("\n2. Creating instance and running TTS operations...")
    service = GoogleCloudTtsService()
    
    for i in range(2):
        output_file = f"/tmp/debug_health_{i}.wav"
        text = f"Debug test number {i+1}."
        print(f"   Running TTS call {i+1}...")
        await service.text_to_audio_async(text, output_file)
    
    # Step 3: Check class state after operations
    print("\n3. Class state after TTS operations:")
    post_metrics = GoogleCloudTtsService.get_current_metrics()
    print(f"   Executor: {GoogleCloudTtsService._executor}")
    print(f"   Metrics instance: {GoogleCloudTtsService._metrics}")
    print(f"   Status: {post_metrics.get('executor_status')}")
    print(f"   Max workers: {post_metrics.get('max_workers')}")
    print(f"   Jobs completed: {post_metrics.get('total_jobs_completed')}")
    print(f"   Success rate: {post_metrics.get('success_rate_pct')}")
    
    # Step 4: Check metrics directly
    print("\n4. Direct metrics check:")
    if GoogleCloudTtsService._metrics:
        print(f"   Jobs completed (direct): {GoogleCloudTtsService._metrics.jobs_completed}")
        print(f"   Jobs failed (direct): {GoogleCloudTtsService._metrics.jobs_failed}")
        print(f"   Last minute jobs: {GoogleCloudTtsService._metrics.get_jobs_last_minute()}")
    else:
        print("   No metrics instance found!")
    
    # Step 5: Test the exact call pattern used by MCP server
    print("\n5. Testing MCP server call pattern:")
    try:
        # This is exactly what the MCP server does
        mcp_metrics = GoogleCloudTtsService.get_current_metrics()
        print(f"   MCP call result:")
        print(f"     Status: {mcp_metrics.get('executor_status')}")
        print(f"     Max workers: {mcp_metrics.get('max_workers')}")
        print(f"     Jobs completed: {mcp_metrics.get('total_jobs_completed')}")
        print(f"     Success rate: {mcp_metrics.get('success_rate_pct')}")
    except Exception as e:
        print(f"   Error in MCP call: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up
    print(f"\n🧹 Cleaning up...")
    for i in range(2):
        output_file = f"/tmp/debug_health_{i}.wav"
        if os.path.exists(output_file):
            os.remove(output_file)

if __name__ == "__main__":
    asyncio.run(debug_tts_health())
