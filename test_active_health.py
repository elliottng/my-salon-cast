#!/usr/bin/env python3
"""
Test TTS health monitoring with active TTS operations.
This test runs TTS operations and checks health metrics in real-time.
"""

import asyncio
import sys
import os
import json

# Add the project root to the path
sys.path.append('.')

from tests.mcp.client import SimpleMCPTestClient
from app.tts_service import GoogleCloudTtsService

async def test_active_tts_health():
    """Test health monitoring during active TTS operations."""
    
    print("🚀 Testing TTS health monitoring with active operations...")
    
    # Step 1: Initialize TTS service and run some operations
    print("\n1. Running TTS operations to initialize executor...")
    service = GoogleCloudTtsService()
    
    # Run multiple TTS calls to fully initialize the service
    for i in range(3):
        output_file = f"/tmp/test_health_{i}.wav"
        text = f"Hello, this is test audio number {i+1} for health monitoring validation."
        await service.text_to_audio_async(text, output_file)
        print(f"   ✅ Completed TTS call {i+1}")
    
    # Step 2: Check health immediately after TTS operations
    print("\n2. Checking health metrics with active TTS executor...")
    
    try:
        async with SimpleMCPTestClient("http://localhost:8000/mcp") as client:
            # Call health monitoring tool
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "test-active-health", "client_name": "active-health-test"}
            })
            
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                health_data = json.loads(result[0].text)
                
                print(f"\n📊 Health Monitoring Results (Post-TTS):")
                print(f"Overall Health: {health_data.get('overall_health', 'unknown')}")
                print(f"Timestamp: {health_data.get('timestamp', 'unknown')}")
                
                tts_metrics = health_data.get('tts_service', {})
                print(f"\n🎤 TTS Service:")
                print(f"  Status: {tts_metrics.get('status', 'unknown')}")
                print(f"  Max Workers: {tts_metrics.get('max_workers', 0)}")
                print(f"  Active Workers: {tts_metrics.get('active_workers', 0)}")
                print(f"  Utilization: {tts_metrics.get('worker_utilization_pct', 0)}%")
                print(f"  Queue Size: {tts_metrics.get('queue_size', 0)}")
                print(f"  Jobs Completed: {tts_metrics.get('total_jobs_completed', 0)}")
                print(f"  Jobs Failed: {tts_metrics.get('total_jobs_failed', 0)}")
                print(f"  Success Rate: {tts_metrics.get('success_rate_pct', 0)}%")
                print(f"  Avg Processing Time: {tts_metrics.get('avg_processing_time_sec', 0):.2f}s")
                print(f"  Jobs Last Minute: {tts_metrics.get('jobs_last_minute', 0)}")
                
                # Validate expected behavior
                print(f"\n🔍 Validation:")
                if tts_metrics.get('status') == 'healthy':
                    print("  ✅ TTS service properly initialized")
                else:
                    print(f"  ⚠️ TTS service status: {tts_metrics.get('status')}")
                
                if tts_metrics.get('max_workers', 0) == 16:
                    print("  ✅ Thread pool properly configured (16 workers)")
                else:
                    print(f"  ⚠️ Unexpected worker count: {tts_metrics.get('max_workers', 0)}")
                
                if tts_metrics.get('total_jobs_completed', 0) >= 3:
                    print("  ✅ TTS jobs successfully tracked")
                else:
                    print(f"  ⚠️ Expected ≥3 completed jobs, got: {tts_metrics.get('total_jobs_completed', 0)}")
                
                recommendations = health_data.get('recommendations', [])
                if recommendations:
                    print(f"\n💡 Recommendations:")
                    for rec in recommendations:
                        print(f"  - {rec}")
                else:
                    print(f"\n✅ No recommendations - system performing optimally!")
                
            else:
                print("❌ Failed to get health data from MCP tool")
                
    except Exception as e:
        print(f"❌ Error during health check: {e}")
        import traceback
        traceback.print_exc()
    
    # Clean up test files
    print(f"\n🧹 Cleaning up test files...")
    for i in range(3):
        output_file = f"/tmp/test_health_{i}.wav"
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"   Removed: {output_file}")

if __name__ == "__main__":
    print("Use this script after:")
    print("1. Activate venv (if needed)")
    print("2. Export GEMINI_API_KEY")
    print("3. Kill any existing server")
    print("4. Start server: python -m app.mcp_server")
    print("5. Run this test")
    print()
    
    asyncio.run(test_active_tts_health())
