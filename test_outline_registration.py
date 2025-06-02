#!/usr/bin/env python3
"""
Simple test to verify the outline resource is properly registered.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.mcp.client import SimpleMCPTestClient

async def test_outline_resource_registration():
    """Test that the outline resource is properly registered."""
    print("🔍 Testing Outline Resource Registration...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        # Test resource listing
        print("\n📋 Step 1: Listing all available resources...")
        resources = await client.list_resources()
        
        print(f"✅ Found {len(resources)} resources:")
        for resource in resources:
            print(f"   - {resource.uri} | {resource.name}")
        
        # Check if outline resource is present
        outline_resources = [r for r in resources if 'outline' in str(r.uri)]
        if outline_resources:
            print(f"✅ Outline resource found: {outline_resources[0].uri}")
        else:
            print("❌ Outline resource not found in resource list")
            return False
        
        # Test error handling for non-existent task
        print("\n🚫 Step 2: Testing error handling for non-existent task...")
        try:
            await client.read_resource("podcast://fake-task-id/outline")
            print("❌ Should have failed for fake task ID")
            return False
        except Exception as e:
            print(f"✅ Correctly failed for fake task: {e}")
        
        print("\n✅ Outline resource registration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_all_dynamic_resources():
    """Test that all dynamic podcast resources are registered."""
    print("\n🎯 Testing All Dynamic Podcast Resources...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        resources = await client.list_resources()
        
        expected_dynamic_resources = [
            "podcast://{task_id}/transcript",
            "podcast://{task_id}/audio", 
            "podcast://{task_id}/metadata",
            "podcast://{task_id}/outline"
        ]
        
        found_resources = []
        for expected in expected_dynamic_resources:
            matching = [r for r in resources if expected.replace("{task_id}", "") in str(r.uri)]
            if matching:
                found_resources.append(expected)
                print(f"✅ Found: {expected}")
            else:
                print(f"❌ Missing: {expected}")
        
        if len(found_resources) == len(expected_dynamic_resources):
            print(f"\n✅ All {len(expected_dynamic_resources)} dynamic podcast resources found!")
            return True
        else:
            print(f"\n❌ Only found {len(found_resources)}/{len(expected_dynamic_resources)} dynamic resources")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Run outline resource registration tests."""
    print("=" * 80)
    print("OUTLINE RESOURCE REGISTRATION TEST")
    print("=" * 80)
    
    # Test outline resource registration
    success1 = await test_outline_resource_registration()
    
    # Test all dynamic resources
    success2 = await test_all_dynamic_resources()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✅ ALL REGISTRATION TESTS PASSED")
        print("✅ Outline resource is properly implemented and registered")
        return 0
    else:
        print("❌ SOME REGISTRATION TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
