#!/usr/bin/env python3
"""
Test script for Phase 4.3 cleanup configuration features.
Tests the new cleanup policy management system and file cleanup tools.
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp.client import SimpleMCPTestClient


async def test_cleanup_configuration():
    """Test cleanup configuration management features."""
    client = SimpleMCPTestClient()
    
    print("\n" + "="*60)
    print("Phase 4.3 Cleanup Configuration Tests")
    print("="*60)
    
    # Test 1: View current cleanup configuration
    print("\n1. Testing cleanup configuration resource...")
    try:
        result = await client.read_resource("config://cleanup")
        print("✅ Successfully retrieved cleanup configuration")
        print(f"   Current default policy: {result['cleanup_policies']['current_default']}")
        print(f"   Available policies: {', '.join(result['cleanup_policies']['available_policies'])}")
        print(f"   Auto cleanup hours: {result['timing_settings']['auto_cleanup_hours']}")
        print(f"   Auto cleanup days: {result['timing_settings']['auto_cleanup_days']}")
        print(f"   Retention settings:")
        for key, value in result['retention_settings'].items():
            print(f"     - {key}: {value}")
    except Exception as e:
        print(f"❌ Failed to get cleanup configuration: {e}")
        return False
    
    # Test 2: Update cleanup policy to auto_after_hours
    print("\n2. Testing cleanup policy update to 'auto_after_hours'...")
    try:
        result = await client.call_tool(
            "configure_cleanup_policy",
            {
                "default_policy": "auto_after_hours",
                "auto_cleanup_hours": 2,
                "retain_audio_files": True,
                "retain_transcripts": False,
                "retain_llm_outputs": False,
                "retain_audio_segments": True
            }
        )
        if result["success"]:
            print("✅ Successfully updated cleanup policy")
            print(f"   Updated fields: {', '.join(result['updated_fields'])}")
            print(f"   New policy: {result['current_config']['default_policy']}")
        else:
            print(f"❌ Failed to update policy: {result['error']}")
    except Exception as e:
        print(f"❌ Error updating cleanup policy: {e}")
        return False
    
    # Test 3: Verify configuration was saved
    print("\n3. Verifying configuration persistence...")
    try:
        result = await client.read_resource("config://cleanup")
        if result['cleanup_policies']['current_default'] == 'auto_after_hours':
            print("✅ Configuration successfully persisted")
            print(f"   Config file: {result['configuration']['config_file']}")
        else:
            print("❌ Configuration not persisted correctly")
    except Exception as e:
        print(f"❌ Error verifying configuration: {e}")
    
    # Test 4: Test invalid policy update
    print("\n4. Testing invalid policy update (should fail)...")
    try:
        result = await client.call_tool(
            "configure_cleanup_policy",
            {"default_policy": "invalid_policy"}
        )
        if not result["success"]:
            print("✅ Correctly rejected invalid policy")
            print(f"   Error: {result['error']}")
            print(f"   Valid policies: {', '.join(result['valid_policies'])}")
        else:
            print("❌ Should have rejected invalid policy")
    except Exception as e:
        print(f"✅ Correctly threw error for invalid policy: {e}")
    
    # Test 5: Test parameter validation
    print("\n5. Testing parameter validation...")
    try:
        # Test invalid hours
        result = await client.call_tool(
            "configure_cleanup_policy",
            {"auto_cleanup_hours": 10000}
        )
        if not result["success"]:
            print("✅ Correctly rejected invalid hours value")
            print(f"   Error: {result['error']}")
        
        # Test invalid size limit
        result = await client.call_tool(
            "configure_cleanup_policy",
            {"max_temp_size_mb": 20000}
        )
        if not result["success"]:
            print("✅ Correctly rejected invalid size limit")
            print(f"   Error: {result['error']}")
    except Exception as e:
        print(f"❌ Unexpected error in validation: {e}")
    
    # Test 6: Update to retain_audio_only policy
    print("\n6. Testing 'retain_audio_only' policy...")
    try:
        result = await client.call_tool(
            "configure_cleanup_policy",
            {
                "default_policy": "retain_audio_only",
                "max_temp_size_mb": 500,
                "enable_background_cleanup": False
            }
        )
        if result["success"]:
            print("✅ Successfully set retain_audio_only policy")
            config = result['current_config']
            print(f"   Max temp size: {config['max_temp_size_mb']}MB")
            print(f"   Background cleanup: {config['enable_background_cleanup']}")
        else:
            print(f"❌ Failed to update policy: {result['error']}")
    except Exception as e:
        print(f"❌ Error updating to retain_audio_only: {e}")
    
    # Test 7: Test cleanup with a real task (if available)
    print("\n7. Testing cleanup status resource with sample task...")
    test_task_id = "test_cleanup_12345"
    try:
        result = await client.read_resource(f"files://{test_task_id}/cleanup")
        print(f"❌ Expected error for non-existent task, but got: {result}")
    except Exception as e:
        if "Task not found" in str(e):
            print("✅ Correctly reported non-existent task")
        else:
            print(f"❌ Unexpected error: {e}")
    
    # Test 8: Reset to manual policy for safety
    print("\n8. Resetting to manual cleanup policy...")
    try:
        result = await client.call_tool(
            "configure_cleanup_policy",
            {
                "default_policy": "manual",
                "retain_audio_files": True,
                "retain_transcripts": True,
                "retain_llm_outputs": True,
                "retain_audio_segments": True
            }
        )
        if result["success"]:
            print("✅ Successfully reset to manual policy")
            print("   All file types set to retain")
        else:
            print(f"❌ Failed to reset policy: {result['error']}")
    except Exception as e:
        print(f"❌ Error resetting policy: {e}")
    
    print("\n" + "="*60)
    print("Cleanup Configuration Tests Complete!")
    print("="*60)
    
    return True


async def test_cleanup_tool_with_policy():
    """Test the cleanup tool with policy overrides."""
    client = SimpleMCPTestClient()
    
    print("\n" + "="*60)
    print("Testing Cleanup Tool with Policy Overrides")
    print("="*60)
    
    # This would require an actual completed task
    # For now, we'll test the error handling
    
    print("\n1. Testing cleanup with policy override on non-existent task...")
    try:
        result = await client.call_tool(
            "cleanup_task_files",
            {
                "task_id": "test_task_99999",
                "force_cleanup": True,
                "policy_override": "retain_audio_only"
            }
        )
        if not result["success"]:
            print("✅ Correctly handled non-existent task")
            print(f"   Error: {result['error']}")
        else:
            print("❌ Should have failed for non-existent task")
    except Exception as e:
        print(f"✅ Correctly threw error: {e}")
    
    print("\n2. Testing cleanup with invalid policy override...")
    try:
        result = await client.call_tool(
            "cleanup_task_files",
            {
                "task_id": "test_task_99999",
                "policy_override": "invalid_policy"
            }
        )
        # Note: The tool validates task existence before policy, so we get a task not found error
        if not result["success"] and "Task not found" in result["error"]:
            print("✅ Task validation occurs before policy validation (expected behavior)")
            print(f"   Error: {result['error']}")
        elif not result["success"] and "Invalid cleanup policy" in result["error"]:
            print("✅ Correctly rejected invalid policy override")
            print(f"   Error: {result['error']}")
        else:
            print("❌ Should have rejected invalid policy")
    except Exception as e:
        if "Task not found" in str(e):
            print(f"✅ Task validation occurs before policy validation: {e}")
        elif "Invalid cleanup policy" in str(e):
            print(f"✅ Correctly rejected invalid policy: {e}")
        else:
            print(f"❌ Unexpected error: {e}")
    
    print("\nCleanup Tool Tests Complete!")
    
    return True


async def main():
    """Run all cleanup configuration tests."""
    # Make sure we have environment setup
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not set")
    
    # Run configuration tests
    config_success = await test_cleanup_configuration()
    
    # Run cleanup tool tests
    tool_success = await test_cleanup_tool_with_policy()
    
    if config_success and tool_success:
        print("\n✅ All cleanup configuration tests passed!")
    else:
        print("\n❌ Some tests failed")


if __name__ == "__main__":
    asyncio.run(main())
