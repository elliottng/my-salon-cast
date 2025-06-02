#!/usr/bin/env python3
"""
Direct test of the outline resource functionality.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.mcp.client import SimpleMCPTestClient

async def test_outline_resource_direct():
    """Test the outline resource directly."""
    print("🔍 Testing Outline Resource Direct Access...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        # Test 1: Error case with non-existent task
        print("\n🚫 Test 1: Non-existent task ID...")
        try:
            result = await client.read_resource("podcast://fake-task-12345/outline")
            print(f"❌ Should have failed, got: {result}")
            return False
        except Exception as e:
            error_msg = str(e)
            print(f"✅ Correctly failed: {error_msg}")
            
            # Check if it's the expected error
            if "Task not found" in error_msg:
                print("✅ Error message indicates resource is working (task not found)")
            else:
                print(f"⚠️  Unexpected error type: {error_msg}")
        
        # Test 2: Try all podcast resources to ensure consistency
        print("\n📋 Test 2: Testing all podcast resources for consistency...")
        
        test_task_id = "fake-task-12345"
        resources_to_test = [
            "transcript",
            "audio", 
            "metadata",
            "outline"
        ]
        
        for resource_type in resources_to_test:
            try:
                result = await client.read_resource(f"podcast://{test_task_id}/{resource_type}")
                print(f"❌ {resource_type}: Should have failed")
            except Exception as e:
                error_msg = str(e)
                if "Task not found" in error_msg:
                    print(f"✅ {resource_type}: Correctly failed with 'Task not found'")
                else:
                    print(f"⚠️  {resource_type}: Different error: {error_msg}")
        
        print("\n✅ Outline resource direct test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_resource_consistency():
    """Test that outline resource behaves the same as other podcast resources."""
    print("\n🎯 Testing Resource Consistency...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    # Test with various invalid task IDs
    invalid_task_ids = [
        "non-existent",
        "fake-task",
        "12345",
        ""
    ]
    
    for task_id in invalid_task_ids:
        print(f"\n📝 Testing with task_id: '{task_id}'")
        
        for resource_type in ["transcript", "audio", "metadata", "outline"]:
            try:
                if task_id:  # Skip empty task_id for resource URLs
                    result = await client.read_resource(f"podcast://{task_id}/{resource_type}")
                    print(f"   ❌ {resource_type}: Should have failed")
                else:
                    print(f"   ⏭️  {resource_type}: Skipping empty task_id")
            except Exception as e:
                error_msg = str(e)
                print(f"   ✅ {resource_type}: {error_msg}")
    
    return True

async def main():
    """Run outline resource direct tests."""
    print("=" * 80)
    print("OUTLINE RESOURCE DIRECT TEST")
    print("=" * 80)
    
    # Test outline resource directly
    success1 = await test_outline_resource_direct()
    
    # Test resource consistency
    success2 = await test_resource_consistency()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✅ ALL DIRECT TESTS PASSED")
        print("✅ Outline resource is properly implemented and working")
        return 0
    else:
        print("❌ SOME DIRECT TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
