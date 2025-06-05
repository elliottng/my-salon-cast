#!/usr/bin/env python3
"""Test MCP health monitoring endpoint."""

import asyncio
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.mcp_server import mcp, get_status_manager, get_task_runner
from fastmcp import Context

async def test_health_endpoint():
    """Test the get_service_health MCP tool."""
    print("Testing MCP service health endpoint...")
    
    # Create a mock context
    class MockContext:
        def __init__(self):
            self.request_id = "health_test_12345"
            
        def info(self, message):
            print(f"[CTX INFO] {message}")
            
        def debug(self, message):
            print(f"[CTX DEBUG] {message}")
            
        def warning(self, message):
            print(f"[CTX WARNING] {message}")
            
        def error(self, message):
            print(f"[CTX ERROR] {message}")
    
    ctx = MockContext()
    
    try:
        # Import the health function from the MCP server
        from app.mcp_server import get_service_health
        
        print("\n1. Calling get_service_health...")
        result = await get_service_health(ctx)
        
        print(f"\n2. Health check result:")
        print(f"Success: {result.get('success')}")
        
        if result.get('success'):
            health_data = result.get('health_data', {})
            print(f"Overall health: {health_data.get('overall_health')}")
            print(f"Timestamp: {health_data.get('timestamp')}")
            
            # TTS service metrics
            tts_metrics = health_data.get('services', {}).get('tts_service', {})
            print(f"\nTTS Service:")
            print(f"  Status: {tts_metrics.get('executor_status')}")
            print(f"  Workers: {tts_metrics.get('active_workers')}/{tts_metrics.get('max_workers')}")
            print(f"  Utilization: {tts_metrics.get('worker_utilization_pct', 0):.1f}%")
            print(f"  Queue size: {tts_metrics.get('queue_size')}")
            print(f"  Success rate: {tts_metrics.get('success_rate_pct', 100):.1f}%")
            
            # Task runner metrics
            task_metrics = health_data.get('services', {}).get('task_runner', {})
            print(f"\nTask Runner:")
            print(f"  Active tasks: {task_metrics.get('active_tasks')}")
            print(f"  Total completed: {task_metrics.get('total_completed')}")
            
            # Status manager metrics
            status_metrics = health_data.get('services', {}).get('status_manager', {})
            print(f"\nStatus Manager:")
            print(f"  Tracked tasks: {status_metrics.get('tracked_tasks')}")
            
            # Recommendations
            recommendations = health_data.get('recommendations', [])
            if recommendations:
                print(f"\nRecommendations:")
                for rec in recommendations:
                    print(f"  - {rec}")
            else:
                print(f"\nNo recommendations - all systems healthy!")
        else:
            print(f"Error: {result.get('error')}")
        
        print("\n✅ Health endpoint test completed successfully!")
        
    except Exception as e:
        print(f"❌ Health endpoint test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_health_endpoint())
