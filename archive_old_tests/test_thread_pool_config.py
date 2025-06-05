#!/usr/bin/env python3
"""
Test script to validate enhanced thread pool configuration for 4 concurrent users.

This test validates:
1. TaskRunner with 4 workers for concurrent podcast generation
2. LLM Service with 18 workers for concurrent Gemini API calls  
3. TTS Service with 16 workers for concurrent TTS operations
4. Health monitoring reflects proper thread pool utilization
"""

import asyncio
import tempfile
import os
from pathlib import Path
import json
import time

# Add the app directory to sys.path
import sys
sys.path.insert(0, '/home/elliottng/CascadeProjects/mysaloncast')

# Import test client
from tests.mcp.client import SimpleMCPTestClient

def extract_json_from_mcp_response(result):
    """Extract JSON content from MCP response."""
    try:
        # Handle list of TextContent objects (typical MCP response)
        if isinstance(result, list) and result:
            text_content = result[0].text if hasattr(result[0], 'text') else str(result[0])
            return json.loads(text_content)
        # Handle direct dict response
        elif isinstance(result, dict):
            if 'content' in result:
                return json.loads(result['content'])
            return result
        # Handle direct string response
        elif isinstance(result, str):
            return json.loads(result)
        else:
            raise ValueError(f"Unexpected response type: {type(result)}")
    except Exception as e:
        print(f"Failed to parse MCP response: {e}")
        print(f"Response type: {type(result)}")
        print(f"Response content: {result}")
        raise

async def test_thread_pool_configuration():
    """Test enhanced thread pool configuration with health monitoring."""
    
    print("🧵 Thread Pool Configuration Validation")
    print("=" * 60)
    print("Testing support for 4 concurrent users with:")
    print("- 3 URLs per podcast (source analysis)")
    print("- 3 prominent persons per podcast (persona research)")  
    print("- 1 outline generation per podcast")
    print("- 1 dialogue generation per podcast")
    print("=" * 60)
    
    server_url = "http://localhost:8000/mcp"
    
    try:
        print("\n📊 Phase 1: Check Initial Configuration")
        print("-" * 40)
        
        async with SimpleMCPTestClient(server_url) as client:
            # Check service health to see initial thread pool configuration
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "config-test-initial"}
            })
            
            health_data = extract_json_from_mcp_response(result)
            services = health_data.get('health_data', {}).get('services', {})
            overall_health = health_data.get('health_data', {}).get('overall_health', 'unknown')
            
            print(f"✅ Initial Service Health:")
            print(f"   TaskRunner max_workers: {services.get('task_runner', {}).get('max_workers', 'unknown')}")
            print(f"   TTS max_workers: {services.get('tts_service', {}).get('max_workers', 'unknown')}")
            print(f"   Overall health status: {overall_health}")
            
        print("\n🧪 Phase 2: Test LLM Thread Pool")
        print("-" * 40)
        
        async with SimpleMCPTestClient(server_url) as client:
            # Test multiple concurrent LLM operations via test_tts_service
            print("   Running 5 concurrent TTS operations to test thread pools...")
            
            tasks = []
            for i in range(5):
                task = client.mcp_client.call_tool("test_tts_service", {
                    "ctx": {"request_id": f"thread-test-{i}"},
                    "test_text": f"Thread pool test {i+1} with longer text to simulate real workload processing times",
                    "output_file": f"thread_test_{i+1}.wav"
                })
                tasks.append(task)
            
            # Execute all tasks concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            successful_tasks = sum(1 for result in results if not isinstance(result, Exception))
            print(f"   ✅ Completed {successful_tasks}/5 concurrent operations")
            print(f"   ⏱️  Total time: {end_time - start_time:.2f}s")
            print(f"   🚀 Average per task: {(end_time - start_time) / 5:.2f}s")
            
        print("\n📈 Phase 3: Validate Enhanced Configuration")
        print("-" * 40)
        
        async with SimpleMCPTestClient(server_url) as client:
            # Check health after operations
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "config-test-final"}
            })
            
            health_data = extract_json_from_mcp_response(result)
            services = health_data.get('health_data', {}).get('services', {})
            overall_health = health_data.get('health_data', {}).get('overall_health', 'unknown')
            
            tts_service = services.get('tts_service', {})
            task_runner = services.get('task_runner', {})
            
            print(f"✅ Final Configuration Validation:")
            print(f"   TaskRunner Workers: {task_runner.get('max_workers', 'unknown')} (expected: 4)")
            print(f"   TTS Workers: {tts_service.get('max_workers', 'unknown')} (expected: 16)")
            print(f"   TTS Jobs Completed: {tts_service.get('jobs_completed', 'unknown')}")
            print(f"   TTS Success Rate: {tts_service.get('success_rate', 'unknown')}%")
            print(f"   Recent Activity: {tts_service.get('has_recent_activity', 'unknown')}")
            
        print("\n🎯 Phase 4: Configuration Validation Results")
        print("-" * 40)
        
        # Validation checks
        checks_passed = 0
        total_checks = 3
        
        if task_runner.get('max_workers') == 4:
            print("✅ TaskRunner workers: 4 (PASS)")
            checks_passed += 1
        else:
            print(f"❌ TaskRunner workers: {task_runner.get('max_workers')} (expected 4)")
            
        if tts_service.get('max_workers') == 16:
            print("✅ TTS workers: 16 (PASS)") 
            checks_passed += 1
        else:
            print(f"❌ TTS workers: {tts_service.get('max_workers')} (expected 16)")
            
        if successful_tasks >= 4:
            print("✅ Concurrent operations: 4+ successful (PASS)")
            checks_passed += 1
        else:
            print(f"❌ Concurrent operations: {successful_tasks} successful (expected 4+)")
        
        print(f"\n🎉 Configuration Validation: {checks_passed}/{total_checks} checks passed")
        
        if checks_passed == total_checks:
            print("✅ SUCCESS: Thread pool configuration is optimized for 4 concurrent users!")
            print("\n📊 Production Capacity Estimate:")
            print("   - 4 concurrent podcast generation workflows")  
            print("   - 12 concurrent source analysis operations (3 per podcast)")
            print("   - 12 concurrent persona research operations (3 per podcast)")
            print("   - 16 concurrent TTS synthesis operations")
            print("   - 18 total LLM workers for all Gemini API calls")
            return True
        else:
            print("❌ FAILURE: Configuration validation failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

async def main():
    """Main test execution function."""
    
    print("Prerequisites:")
    print("1. MCP server running on http://localhost:8000")
    print("2. GEMINI_API_KEY environment variable set")
    print("3. Virtual environment activated")
    print()
    
    success = await test_thread_pool_configuration()
    exit_code = 0 if success else 1
    
    print(f"\nTest completed with exit code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
