#!/usr/bin/env python3
"""
Complete MCP Health Monitoring Validation Test

This test validates that TTS health monitoring works correctly when TTS operations
are triggered within the MCP server process (not test process) with proper ctx flow.

Test Flow:
1. Check initial health via MCP
2. Trigger TTS operations via MCP (within server process) 
3. Check health again via MCP
4. Validate metrics reflect the TTS activity
"""

import asyncio
import sys
import os
import json

# Add the project root to the path
sys.path.append('.')

from tests.mcp.client import SimpleMCPTestClient

async def test_mcp_health_validation():
    """Complete end-to-end validation of MCP health monitoring."""
    
    print("🚀 MCP Health Monitoring Validation")
    print("=" * 60)
    print("Testing TTS health monitoring with operations triggered")
    print("WITHIN the MCP server process using proper ctx flow")
    print("=" * 60)
    
    server_url = "http://localhost:8000/mcp"
    test_ctx = {
        "request_id": "health-validation-test",
        "client_name": "health-validator", 
        "test_phase": "validation"
    }
    
    # Phase 1: Initial Health Check
    print("\n📊 Phase 1: Initial Health Assessment")
    print("-" * 40)
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            print("Calling get_service_health...")
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": test_ctx,
                "include_details": True
            })
            
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                initial_health = json.loads(result[0].text)
                initial_tts = initial_health.get('health_data', {}).get('services', {}).get('tts_service', {})
                
                print(f"✅ Initial Health Status: {initial_health.get('health_data', {}).get('overall_health', 'unknown')}")
                print(f"   TTS Executor Status: {initial_tts.get('executor_status', 'unknown')}")
                print(f"   TTS Jobs Completed: {initial_tts.get('total_jobs_completed', 0)}")
                print(f"   TTS Max Workers: {initial_tts.get('max_workers', 0)}")
                print(f"   TTS Success Rate: {initial_tts.get('success_rate_pct', 0):.1f}%")
                
                initial_job_count = initial_tts.get('total_jobs_completed', 0)
                
            else:
                print("❌ Failed to get initial health data")
                return False
                
    except Exception as e:
        print(f"❌ Initial health check failed: {e}")
        return False
    
    # Phase 2: Trigger TTS Operations via MCP Server
    print("\n🎤 Phase 2: TTS Operations via MCP Server")
    print("-" * 40)
    
    tts_operations = [
        ("Health monitoring validation test number one", "validation_test_1.wav"),
        ("Second TTS test for comprehensive health metrics validation", "validation_test_2.wav"),
        ("Final validation test to confirm metrics tracking accuracy", "validation_test_3.wav")
    ]
    
    operation_results = []
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            for i, (text, filename) in enumerate(tts_operations, 1):
                print(f"   Running TTS operation {i}/3: {filename}")
                
                # Use our new test_tts_service tool with proper ctx flow
                tts_ctx = {
                    **test_ctx,
                    "operation_id": f"tts-op-{i}",
                    "operation_text": text[:20] + "..."
                }
                
                result = await client.mcp_client.call_tool("test_tts_service", {
                    "ctx": tts_ctx,
                    "text": text,
                    "output_filename": filename
                })
                
                if result and len(result) > 0 and hasattr(result[0], 'text'):
                    tts_result = json.loads(result[0].text)
                    operation_results.append(tts_result)
                    
                    if tts_result.get('success', False):
                        metrics = tts_result.get('metrics', {})
                        print(f"     ✅ Success: Jobs {metrics.get('jobs_before', 0)} → {metrics.get('jobs_after', 0)} (+{metrics.get('jobs_incremented', 0)})")
                        print(f"        File size: {tts_result.get('file_size_bytes', 0)} bytes")
                        print(f"        Executor: {metrics.get('executor_status', 'unknown')}")
                    else:
                        print(f"     ❌ Failed: {tts_result.get('error', 'Unknown error')}")
                        
                else:
                    print(f"     ❌ No response from TTS operation {i}")
                    operation_results.append({"success": False, "error": "No response"})
                
                # Small delay between operations
                await asyncio.sleep(0.5)
                
    except Exception as e:
        print(f"❌ TTS operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Phase 3: Final Health Check
    print("\n📈 Phase 3: Post-Operation Health Assessment")
    print("-" * 40)
    
    # Wait for metrics to settle
    await asyncio.sleep(1)
    
    try:
        async with SimpleMCPTestClient(server_url) as client:
            print("Calling get_service_health after TTS operations...")
            result = await client.mcp_client.call_tool("get_service_health", {
                "ctx": {**test_ctx, "phase": "post-operation"},
                "include_details": True
            })
            
            if result and len(result) > 0 and hasattr(result[0], 'text'):
                final_health = json.loads(result[0].text)
                final_tts = final_health.get('health_data', {}).get('services', {}).get('tts_service', {})
                
                print(f"✅ Final Health Status: {final_health.get('health_data', {}).get('overall_health', 'unknown')}")
                print(f"   TTS Executor Status: {final_tts.get('executor_status', 'unknown')}")
                print(f"   TTS Jobs Completed: {final_tts.get('total_jobs_completed', 0)}")
                print(f"   TTS Max Workers: {final_tts.get('max_workers', 0)}")
                print(f"   TTS Active Workers: {final_tts.get('active_workers', 0)}")
                print(f"   TTS Utilization: {final_tts.get('worker_utilization_pct', 0):.1f}%")
                print(f"   TTS Queue Size: {final_tts.get('queue_size', 0)}")
                print(f"   TTS Success Rate: {final_tts.get('success_rate_pct', 0):.1f}%")
                print(f"   TTS Avg Time: {final_tts.get('avg_processing_time_sec', 0):.2f}s")
                print(f"   TTS Last Minute: {final_tts.get('jobs_last_minute', 0)}")
                
                final_job_count = final_tts.get('total_jobs_completed', 0)
                
            else:
                print("❌ Failed to get final health data")
                return False
                
    except Exception as e:
        print(f"❌ Final health check failed: {e}")
        return False
    
    # Phase 4: Validation and Analysis
    print("\n🔍 Phase 4: Validation Results")
    print("-" * 40)
    
    # Count successful TTS operations
    successful_operations = sum(1 for result in operation_results if result.get('success', False))
    expected_job_increment = successful_operations
    actual_job_increment = final_job_count - initial_job_count
    
    print(f"Expected TTS job increment: {expected_job_increment}")
    print(f"Actual TTS job increment: {actual_job_increment}")
    print(f"Successful TTS operations: {successful_operations}/{len(tts_operations)}")
    
    # Validation checks
    validation_results = []
    
    # Check 1: Job count increment
    if actual_job_increment >= expected_job_increment:
        print("✅ Job count tracking: PASS")
        validation_results.append(("job_tracking", True, f"Jobs incremented by {actual_job_increment}"))
    else:
        print("❌ Job count tracking: FAIL")
        validation_results.append(("job_tracking", False, f"Expected +{expected_job_increment}, got +{actual_job_increment}"))
    
    # Check 2: Executor health
    if final_tts.get('executor_status') == 'healthy':
        print("✅ Executor health: PASS")
        validation_results.append(("executor_health", True, "Executor is healthy"))
    else:
        print("❌ Executor health: FAIL")
        validation_results.append(("executor_health", False, f"Status: {final_tts.get('executor_status')}"))
    
    # Check 3: Worker pool configuration
    if final_tts.get('max_workers', 0) == 16:
        print("✅ Worker pool size: PASS")
        validation_results.append(("worker_pool", True, "16 workers configured"))
    else:
        print("❌ Worker pool size: FAIL") 
        validation_results.append(("worker_pool", False, f"Expected 16, got {final_tts.get('max_workers', 0)}"))
    
    # Check 4: Success rate
    success_rate = final_tts.get('success_rate_pct', 0)
    if success_rate >= 95.0:  # Allow for some tolerance
        print("✅ Success rate: PASS")
        validation_results.append(("success_rate", True, f"{success_rate:.1f}%"))
    else:
        print("❌ Success rate: FAIL")
        validation_results.append(("success_rate", False, f"{success_rate:.1f}% < 95%"))
    
    # Check 5: Recent activity tracking
    recent_jobs = final_tts.get('jobs_last_minute', 0)
    if recent_jobs >= expected_job_increment:
        print("✅ Recent activity tracking: PASS")
        validation_results.append(("recent_activity", True, f"{recent_jobs} jobs in last minute"))
    else:
        print("❌ Recent activity tracking: FAIL")
        validation_results.append(("recent_activity", False, f"Expected ≥{expected_job_increment}, got {recent_jobs}"))
    
    # Overall assessment
    passed_checks = sum(1 for _, passed, _ in validation_results if passed)
    total_checks = len(validation_results)
    
    print(f"\n🎯 Overall Validation: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 SUCCESS: MCP Health Monitoring is working correctly!")
        print("   ✅ TTS operations trigger within MCP server process")
        print("   ✅ Health metrics accurately reflect TTS activity")
        print("   ✅ Context flows properly from client to server")
        print("   ✅ Health monitoring is production-ready")
        return True
    else:
        print("⚠️  PARTIAL SUCCESS: Some validation checks failed")
        for check_name, passed, details in validation_results:
            status = "✅" if passed else "❌"
            print(f"   {status} {check_name}: {details}")
        return False

def print_test_prerequisites():
    """Print test setup instructions."""
    print("Prerequisites for MCP Health Validation:")
    print("1. Activate virtual environment (if needed)")
    print("2. Export GEMINI_API_KEY (for LLM operations)")
    print("3. Kill any existing MCP server:")
    print("   pkill -f 'python.*mcp_server\\.py'")
    print("4. Start fresh MCP server:")
    print("   python -m app.mcp_server")
    print("5. Run this validation test:")
    print("   python test_mcp_health_validation.py")
    print()

if __name__ == "__main__":
    print_test_prerequisites()
    
    try:
        success = asyncio.run(test_mcp_health_validation())
        exit_code = 0 if success else 1
        print(f"\nTest completed with exit code: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nTest failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
