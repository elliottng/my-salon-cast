#!/usr/bin/env python3
"""Test TTS monitoring and metrics collection functionality."""

import asyncio
from app.tts_service import GoogleCloudTtsService

async def test_tts_monitoring():
    """Test TTS service monitoring and metrics."""
    print("Testing TTS monitoring functionality...")
    
    # Get initial metrics
    print("\n1. Getting initial TTS metrics:")
    metrics = GoogleCloudTtsService.get_current_metrics()
    print(f"Executor status: {metrics.get('executor_status')}")
    print(f"Max workers: {metrics.get('max_workers')}")
    print(f"Active workers: {metrics.get('active_workers')}")
    print(f"Queue size: {metrics.get('queue_size')}")
    print(f"Worker utilization: {metrics.get('worker_utilization_pct', 0):.1f}%")
    print(f"Total jobs completed: {metrics.get('total_jobs_completed')}")
    print(f"Success rate: {metrics.get('success_rate_pct', 100):.1f}%")
    
    # Test TTS service health
    print("\n2. Testing TTS service health check:")
    try:
        tts_service = GoogleCloudTtsService()
        print("✅ TTS service initialization successful")
        
        # Test voice cache
        voice_cache_size = len(tts_service.voice_cache)
        print(f"Voice cache size: {voice_cache_size}")
        
        # Get executor health
        executor = tts_service._get_executor()
        if executor and not executor._shutdown:
            print("✅ Thread pool executor is healthy")
        else:
            print("❌ Thread pool executor is shutdown")
            
    except Exception as e:
        print(f"❌ TTS service error: {e}")
    
    # Get updated metrics
    print("\n3. Getting updated TTS metrics:")
    updated_metrics = GoogleCloudTtsService.get_current_metrics()
    print(f"Executor status: {updated_metrics.get('executor_status')}")
    print(f"Metrics updated: {updated_metrics.get('last_updated')}")
    
    print("\n✅ TTS monitoring test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_tts_monitoring())
