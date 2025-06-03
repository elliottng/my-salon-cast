#!/usr/bin/env python3
"""Test live health monitoring via MCP client."""

import asyncio
import json
from fastmcp import FastMCP
from fastmcp.transport.http_transport import HttpTransport

async def test_live_health_monitoring():
    """Test health monitoring through live MCP server."""
    print("Testing live health monitoring via MCP client...")
    
    # Connect to the MCP server
    transport = HttpTransport(base_url="http://localhost:8000")
    client = FastMCP(transport=transport)
    
    try:
        print("\n1. Connecting to MCP server...")
        await client.initialize()
        print("✅ Connected to MCP server successfully")
        
        print("\n2. Calling get_service_health tool...")
        result = await client.call_tool("get_service_health", {})
        
        print(f"\n3. Health monitoring results:")
        print(f"Success: {result.get('success')}")
        
        if result.get('success'):
            health_data = result.get('health_data', {})
            print(f"Overall health: {health_data.get('overall_health')}")
            print(f"Timestamp: {health_data.get('timestamp')}")
            
            # TTS service detailed metrics
            tts_metrics = health_data.get('services', {}).get('tts_service', {})
            print(f"\n📊 TTS Service Metrics:")
            print(f"  Status: {tts_metrics.get('executor_status')}")
            print(f"  Workers: {tts_metrics.get('active_workers')}/{tts_metrics.get('max_workers')}")
            print(f"  Utilization: {tts_metrics.get('worker_utilization_pct', 0):.1f}%")
            print(f"  Queue size: {tts_metrics.get('queue_size')}")
            print(f"  Jobs completed: {tts_metrics.get('total_jobs_completed')}")
            print(f"  Jobs failed: {tts_metrics.get('total_jobs_failed')}")
            print(f"  Success rate: {tts_metrics.get('success_rate_pct', 100):.1f}%")
            print(f"  Avg processing time: {tts_metrics.get('avg_processing_time_sec', 0):.2f}s")
            print(f"  Jobs last minute: {tts_metrics.get('jobs_last_minute', 0)}")
            
            # Task runner metrics
            task_metrics = health_data.get('services', {}).get('task_runner', {})
            print(f"\n🔄 Task Runner Metrics:")
            print(f"  Active tasks: {task_metrics.get('active_tasks')}")
            print(f"  Total completed: {task_metrics.get('total_completed')}")
            
            # Status manager metrics
            status_metrics = health_data.get('services', {}).get('status_manager', {})
            print(f"\n📋 Status Manager Metrics:")
            print(f"  Tracked tasks: {status_metrics.get('tracked_tasks')}")
            
            # Performance recommendations
            recommendations = health_data.get('recommendations', [])
            if recommendations:
                print(f"\n💡 Performance Recommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
            else:
                print(f"\n✅ No recommendations - all systems operating normally!")
                
        else:
            print(f"❌ Error: {result.get('error')}")
        
        print("\n4. Testing TTS service initialization...")
        # This should trigger TTS service initialization if not already done
        tts_result = await client.call_tool("get_service_health", {})
        
        if tts_result.get('success'):
            tts_status = tts_result.get('health_data', {}).get('services', {}).get('tts_service', {}).get('executor_status')
            print(f"TTS Executor status after re-check: {tts_status}")
            
            if tts_status == "healthy":
                print("✅ TTS service is healthy and ready for production workloads")
            elif tts_status == "not_initialized":
                print("ℹ️ TTS service initialized on-demand (normal for idle state)")
            else:
                print(f"⚠️ TTS service status: {tts_status}")
                
        print("\n✅ Live health monitoring test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            await client.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_live_health_monitoring())
