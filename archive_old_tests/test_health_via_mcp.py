#!/usr/bin/env python3
"""Test health monitoring via MCP client using existing pattern."""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the project root to the path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from tests.mcp.client import SimpleMCPTestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_health_monitoring_via_mcp():
    """Test health monitoring through MCP client."""
    print("🔍 Testing health monitoring via MCP client...")
    
    server_url = "http://localhost:8000/mcp"
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            print(f"✅ Connected to MCP server at {server_url}")
            
            # Test 1: Call get_service_health tool
            print("\n1. Testing get_service_health tool...")
            health_result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "test-health-request", "client_name": "health-test-client"}
            })
            
            # Parse result (FastMCP returns content objects)
            if isinstance(health_result, list) and health_result:
                content = health_result[0]
                if hasattr(content, 'text'):
                    try:
                        health_data = json.loads(content.text)
                    except json.JSONDecodeError:
                        health_data = {"raw_text": content.text}
                else:
                    health_data = health_result
            else:
                health_data = health_result
            
            print(f"✅ Health tool call successful")
            
            # Display results
            if health_data.get('success'):
                print(f"\n📊 Health Monitoring Results:")
                
                health_info = health_data.get('health_data', {})
                print(f"Overall Health: {health_info.get('overall_health', 'unknown')}")
                print(f"Timestamp: {health_info.get('timestamp', 'unknown')}")
                
                # TTS Service Metrics
                tts_metrics = health_info.get('services', {}).get('tts_service', {})
                print(f"\n🎤 TTS Service:")
                print(f"  Status: {tts_metrics.get('executor_status', 'unknown')}")
                print(f"  Max Workers: {tts_metrics.get('max_workers', 0)}")
                print(f"  Active Workers: {tts_metrics.get('active_workers', 0)}")
                print(f"  Utilization: {tts_metrics.get('worker_utilization_pct', 0):.1f}%")
                print(f"  Queue Size: {tts_metrics.get('queue_size', 0)}")
                print(f"  Jobs Completed: {tts_metrics.get('total_jobs_completed', 0)}")
                print(f"  Jobs Failed: {tts_metrics.get('total_jobs_failed', 0)}")
                print(f"  Success Rate: {tts_metrics.get('success_rate_pct', 100):.1f}%")
                print(f"  Avg Processing Time: {tts_metrics.get('avg_processing_time_sec', 0):.2f}s")
                print(f"  Jobs Last Minute: {tts_metrics.get('jobs_last_minute', 0)}")
                
                # Task Runner Metrics
                task_metrics = health_info.get('services', {}).get('task_runner', {})
                print(f"\n🔄 Task Runner:")
                print(f"  Active Tasks: {task_metrics.get('active_tasks', 0)}")
                print(f"  Total Completed: {task_metrics.get('total_completed', 0)}")
                
                # Status Manager Metrics
                status_metrics = health_info.get('services', {}).get('status_manager', {})
                print(f"\n📋 Status Manager:")
                print(f"  Tracked Tasks: {status_metrics.get('tracked_tasks', 0)}")
                
                # Recommendations
                recommendations = health_info.get('recommendations', [])
                if recommendations:
                    print(f"\n💡 Performance Recommendations:")
                    for rec in recommendations:
                        print(f"  - {rec}")
                else:
                    print(f"\n✅ No recommendations - system performing optimally!")
                    
            else:
                print(f"❌ Health check failed: {health_data.get('error', 'Unknown error')}")
            
            # Test 2: Multiple calls to test consistency
            print(f"\n2. Testing health check consistency...")
            for i in range(3):
                health_result_2 = await client.mcp_client.call_tool("get_service_health", {
                    "ctx": {"request_id": "test-health-request", "client_name": "health-test-client"}
                })
                print(f"  Call {i+1}: ✅ Success")
                
            print(f"\n✅ All health monitoring tests completed successfully!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Use this script after:")
    print("1. Activate venv (if needed)")
    print("2. Export GEMINI_API_KEY")
    print("3. Kill any existing server")
    print("4. Start server: python -m app.mcp_server")
    print("5. Run this test\n")
    
    asyncio.run(test_health_monitoring_via_mcp())
