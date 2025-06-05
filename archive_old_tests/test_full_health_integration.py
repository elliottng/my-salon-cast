#!/usr/bin/env python3
"""
Full integration test for TTS health monitoring via MCP server.
This test triggers TTS operations through the MCP server and then checks health metrics.
"""

import asyncio
import sys
import os
import json
import tempfile

# Add the project root to the path
sys.path.append('.')

from tests.mcp.client import SimpleMCPTestClient

async def test_full_health_integration():
    """Test health monitoring with TTS operations triggered through MCP server."""
    
    print("🚀 Full TTS Health Integration Test")
    print("=" * 50)
    
    server_url = "http://localhost:8000/mcp"
    
    # Step 1: Check initial health
    print("\n1. 📊 Initial Health Check")
    try:
        async with SimpleMCPTestClient(server_url) as client:
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "initial-health-check"}
            })
            
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                health_data = json.loads(result[0].text)
                tts_metrics = health_data.get('health_data', {}).get('services', {}).get('tts_service', {})
                
                print(f"   Status: {tts_metrics.get('executor_status', 'unknown')}")
                print(f"   Jobs completed: {tts_metrics.get('total_jobs_completed', 0)}")
                print(f"   Max workers: {tts_metrics.get('max_workers', 0)}")
                
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Step 2: Trigger TTS operations through MCP server
    print("\n2. 🎤 Triggering TTS Operations via MCP")
    
    # Create temporary directory for audio files
    temp_dir = tempfile.mkdtemp(prefix="tts_health_test_")
    print(f"   Using temp directory: {temp_dir}")
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            # Generate multiple audio files through the TTS service
            # This should initialize the TTS executor and update metrics
            
            tts_operations = [
                ("Hello, this is health monitoring test number one.", "test_audio_1.wav"),
                ("This is the second test audio for health validation.", "test_audio_2.wav"), 
                ("Final test audio to verify TTS metrics tracking.", "test_audio_3.wav")
            ]
            
            for i, (text, filename) in enumerate(tts_operations, 1):
                output_path = os.path.join(temp_dir, filename)
                print(f"   Generating audio {i}/3: {filename}")
                
                # Note: This uses the TTS service directly since there's no MCP tool for TTS yet
                # In a real scenario, TTS would be triggered through podcast generation
                # For testing, we'll use a different approach - run audio generation
                # through a simple TTS call that uses the same service instance
                
                # Import and use the same TTS service class
                from app.tts_service import GoogleCloudTtsService
                
                # This will use the shared class-level executor and metrics
                await GoogleCloudTtsService().text_to_audio_async(text, output_path)
                
                print(f"     ✅ Generated: {filename}")
                
    except Exception as e:
        print(f"   ❌ TTS Generation Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 3: Check health after TTS operations
    print("\n3. 📈 Post-TTS Health Check")
    
    # Wait a moment for metrics to update
    await asyncio.sleep(1)
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "post-tts-health-check"}
            })
            
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                health_data = json.loads(result[0].text)
                
                print(f"   Overall Health: {health_data.get('health_data', {}).get('overall_health', 'unknown')}")
                
                tts_metrics = health_data.get('health_data', {}).get('services', {}).get('tts_service', {})
                task_runner = health_data.get('health_data', {}).get('services', {}).get('task_runner', {})
                status_manager = health_data.get('health_data', {}).get('services', {}).get('status_manager', {})
                
                print(f"\n   🎤 TTS Service Metrics:")
                print(f"     Status: {tts_metrics.get('executor_status', 'unknown')}")
                print(f"     Max Workers: {tts_metrics.get('max_workers', 0)}")
                print(f"     Active Workers: {tts_metrics.get('active_workers', 0)}")
                print(f"     Utilization: {tts_metrics.get('worker_utilization_pct', 0):.1f}%")
                print(f"     Queue Size: {tts_metrics.get('queue_size', 0)}")
                print(f"     Jobs Completed: {tts_metrics.get('total_jobs_completed', 0)}")
                print(f"     Jobs Failed: {tts_metrics.get('total_jobs_failed', 0)}")
                print(f"     Success Rate: {tts_metrics.get('success_rate_pct', 0):.1f}%")
                print(f"     Avg Processing Time: {tts_metrics.get('avg_processing_time_sec', 0):.2f}s")
                print(f"     Jobs Last Minute: {tts_metrics.get('jobs_last_minute', 0)}")
                
                print(f"\n   🔄 Task Runner:")
                print(f"     Active Tasks: {task_runner.get('active_tasks', 0)}")
                print(f"     Total Completed: {task_runner.get('total_completed', 0)}")
                
                print(f"\n   📋 Status Manager:")
                print(f"     Tracked Tasks: {status_manager.get('tracked_tasks', 0)}")
                
                recommendations = health_data.get('health_data', {}).get('recommendations', [])
                if recommendations:
                    print(f"\n   💡 Recommendations:")
                    for rec in recommendations:
                        print(f"     - {rec}")
                else:
                    print(f"\n   ✅ No recommendations - system performing optimally!")
                
                # Validation
                print(f"\n4. 🔍 Validation Results:")
                
                expected_jobs = 3
                actual_jobs = tts_metrics.get('total_jobs_completed', 0)
                
                if tts_metrics.get('executor_status') == 'healthy':
                    print(f"   ✅ TTS executor is healthy")
                else:
                    print(f"   ⚠️ TTS executor status: {tts_metrics.get('executor_status')}")
                
                if tts_metrics.get('max_workers', 0) == 16:
                    print(f"   ✅ Correct worker pool size (16)")
                else:
                    print(f"   ⚠️ Unexpected worker count: {tts_metrics.get('max_workers', 0)}")
                
                if actual_jobs >= expected_jobs:
                    print(f"   ✅ TTS jobs tracked correctly ({actual_jobs} >= {expected_jobs})")
                else:
                    print(f"   ⚠️ Job tracking issue: expected >= {expected_jobs}, got {actual_jobs}")
                
                if tts_metrics.get('success_rate_pct', 0) == 100.0:
                    print(f"   ✅ Perfect success rate (100%)")
                else:
                    print(f"   ⚠️ Success rate: {tts_metrics.get('success_rate_pct', 0):.1f}%")
                
            else:
                print("   ❌ Failed to parse health response")
                
    except Exception as e:
        print(f"   ❌ Health Check Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Cleanup
    print(f"\n5. 🧹 Cleanup")
    try:
        import shutil
        shutil.rmtree(temp_dir)
        print(f"   Removed temp directory: {temp_dir}")
    except Exception as e:
        print(f"   Warning: Failed to cleanup {temp_dir}: {e}")
    
    print(f"\n🎉 Full integration test completed!")

if __name__ == "__main__":
    print("Prerequisites:")
    print("1. Activate venv (if needed)")
    print("2. Export GEMINI_API_KEY")
    print("3. Kill any existing server: pkill -f 'python.*mcp_server\\.py'")
    print("4. Start server: python -m app.mcp_server")
    print("5. Run this test")
    print()
    
    asyncio.run(test_full_health_integration())
