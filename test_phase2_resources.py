#!/usr/bin/env python3
"""
Quick test script for Phase 2.1 static resources.
Tests the new config://app, docs://api, and examples://requests resources.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.mcp.client import SimpleMCPTestClient

async def test_phase2_static_resources():
    """Test all Phase 2.1 static resources."""
    print("🔍 Testing Phase 2.1 Static Resources...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        # Test config://app resource
        print("\n📋 Testing config://app resource...")
        app_config = await client.read_resource("config://app")
        print(f"✅ App Name: {app_config.get('app_name')}")
        print(f"✅ Version: {app_config.get('version')}")
        print(f"✅ Max Concurrent Tasks: {app_config.get('limits', {}).get('max_concurrent_tasks')}")
        print(f"✅ LLM Provider: {app_config.get('ai_services', {}).get('llm_provider')}")
        
        # Test docs://api resource
        print("\n📚 Testing docs://api resource...")
        api_docs = await client.read_resource("docs://api")
        tools_count = len(api_docs.get('tools', {}))
        resources_count = len(api_docs.get('resources', {}))
        print(f"✅ Documented Tools: {tools_count}")
        print(f"✅ Documented Resources: {resources_count}")
        print(f"✅ Rate Limits: {api_docs.get('rate_limits')}")
        
        # Test examples://requests resource
        print("\n💡 Testing examples://requests resource...")
        examples = await client.read_resource("examples://requests")
        example_names = list(examples.keys())
        print(f"✅ Available Examples: {len(example_names)}")
        for name in example_names:
            description = examples[name].get('description', 'No description')
            print(f"   - {name}: {description}")
        
        # Test workflow example
        workflow = examples.get('workflow_example', {})
        if workflow:
            steps = workflow.get('steps', [])
            print(f"✅ Workflow Example: {len(steps)} steps")
        
        print("\n🎉 All Phase 2.1 static resources working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing Phase 2.1 resources: {e}")
        return False

async def test_list_all_resources():
    """List all available resources."""
    print("\n🔍 Listing all available MCP resources...")
    
    client = SimpleMCPTestClient("http://localhost:8000/mcp")
    
    try:
        # List all resources
        resources = await client.list_resources()
        print(f"✅ Found {len(resources)} MCP resources:")
        
        for resource in resources:
            uri = resource.uri if hasattr(resource, 'uri') else str(resource)
            name = resource.name if hasattr(resource, 'name') else 'Unnamed'
            print(f"   - {uri}: {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing resources: {e}")
        return False

async def main():
    """Run all Phase 2.1 tests."""
    print("=" * 80)
    print("PHASE 2.1 STATIC RESOURCES TEST")
    print("=" * 80)
    
    # Test resource listing
    success1 = await test_list_all_resources()
    
    # Test individual resources
    success2 = await test_phase2_static_resources()
    
    print("\n" + "=" * 80)
    if success1 and success2:
        print("✅ ALL PHASE 2.1 TESTS PASSED")
        return 0
    else:
        print("❌ SOME PHASE 2.1 TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
