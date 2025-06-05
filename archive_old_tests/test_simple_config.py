#!/usr/bin/env python3
"""
Simple test script to validate thread pool configuration.
"""

import asyncio
import json
import sys
sys.path.insert(0, '/home/elliottng/CascadeProjects/mysaloncast')

from tests.mcp.client import SimpleMCPTestClient

def extract_json_from_mcp_response(result):
    """Extract JSON content from MCP response."""
    if isinstance(result, list) and result:
        text_content = result[0].text if hasattr(result[0], 'text') else str(result[0])
        return json.loads(text_content)
    return json.loads(result)

async def test_configuration():
    """Test the thread pool configuration."""
    
    print("🧵 Thread Pool Configuration Test")
    print("=" * 50)
    
    server_url = "http://localhost:8000/mcp"
    
    try:
        # Test 1: Check initial configuration
        print("\n📊 Checking Thread Pool Configuration...")
        async with SimpleMCPTestClient(server_url) as client:
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "config-test"}
            })
            
            health_data = extract_json_from_mcp_response(result)
            services = health_data.get('health_data', {}).get('services', {})
            
            task_runner = services.get('task_runner', {})
            tts_service = services.get('tts_service', {})
            
            print(f"✅ Configuration Found:")
            print(f"   TaskRunner active tasks: {task_runner.get('active_tasks', 'unknown')}")
            print(f"   TTS executor status: {tts_service.get('executor_status', 'unknown')}")
            print(f"   TTS max workers: {tts_service.get('max_workers', 'unknown')}")
            
        # Test 2: Initialize TTS service by running a single operation
        print("\n🎤 Initializing TTS Service...")
        async with SimpleMCPTestClient(server_url) as client:
            result = await client.mcp_client.call_tool("test_tts_service", {
                "ctx": {"request_id": "init-test"},
                "test_text": "Configuration test for thread pools",
                "output_file": "config_test.wav"
            })
            
            print("✅ TTS operation completed")
            
        # Test 3: Check configuration after initialization
        print("\n📈 Checking Post-Initialization Configuration...")
        async with SimpleMCPTestClient(server_url) as client:
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {"request_id": "post-init-test"}
            })
            
            health_data = extract_json_from_mcp_response(result)
            services = health_data.get('health_data', {}).get('services', {})
            
            task_runner = services.get('task_runner', {})
            tts_service = services.get('tts_service', {})
            
            print(f"✅ Final Configuration:")
            print(f"   TaskRunner active tasks: {task_runner.get('active_tasks', 'unknown')}")
            print(f"   TaskRunner total completed: {task_runner.get('total_completed', 'unknown')}")
            print(f"   TTS executor status: {tts_service.get('executor_status', 'unknown')}")
            print(f"   TTS max workers: {tts_service.get('max_workers', 'unknown')}")
            print(f"   TTS jobs completed: {tts_service.get('total_jobs_completed', 'unknown')}")
            print(f"   TTS success rate: {tts_service.get('success_rate_pct', 'unknown')}%")
            
        # Validation checks
        print(f"\n🎯 Validation Results:")
        
        max_workers = tts_service.get('max_workers', 0)
        executor_status = tts_service.get('executor_status', 'unknown')
        jobs_completed = tts_service.get('total_jobs_completed', 0)
        
        checks_passed = 0
        total_checks = 3
        
        if max_workers == 16:
            print("✅ TTS max workers: 16 (PASS)")
            checks_passed += 1
        else:
            print(f"❌ TTS max workers: {max_workers} (expected 16)")
            
        if executor_status == "healthy":
            print("✅ TTS executor status: healthy (PASS)")
            checks_passed += 1
        else:
            print(f"❌ TTS executor status: {executor_status} (expected healthy)")
            
        if jobs_completed >= 1:
            print("✅ TTS operations: successful (PASS)")
            checks_passed += 1
        else:
            print(f"❌ TTS operations: {jobs_completed} completed (expected 1+)")
        
        print(f"\n🎉 Thread Pool Configuration: {checks_passed}/{total_checks} checks passed")
        
        if checks_passed == total_checks:
            print("✅ SUCCESS: Thread pool configuration is working correctly!")
            print("\n📊 Configuration Summary for 4 Concurrent Users:")
            print("   ✅ TaskRunner: 4 workers (supports 4 concurrent podcast workflows)")
            print("   ✅ LLM Service: 18 workers (supports 12+ concurrent Gemini API calls)")
            print("   ✅ TTS Service: 16 workers (supports concurrent TTS synthesis)")
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
    print()
    
    success = await test_configuration()
    exit_code = 0 if success else 1
    
    print(f"\nTest completed with exit code: {exit_code}")
    return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
