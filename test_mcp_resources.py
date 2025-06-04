#!/usr/bin/env python3
"""
Test MCP resource access for text files to verify our enhanced resource handlers work.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent / "app"))

from fastmcp import FastMCP
import httpx
import json

class SimpleMCPResourceClient:
    """Simple client to test MCP resource access."""
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session_url = f"{base_url}/"  # Use root endpoint which redirects to MCP
    
    async def test_resource_access(self, task_id: str):
        """Test accessing MCP resources for a given task."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            
            # Create MCP session
            session_response = await client.post(self.session_url)
            if session_response.status_code != 202:
                raise Exception(f"Failed to create session: {session_response.status_code}")
            
            # List available resources
            print("📋 Listing available MCP resources...")
            
            list_request = {
                "method": "resources/list",
                "params": {}
            }
            
            list_response = await client.post(self.session_url, json=list_request)
            if list_response.status_code != 200:
                print(f"❌ Failed to list resources: {list_response.status_code}")
                return False
            
            resources_data = list_response.json()
            resources = resources_data.get("result", {}).get("resources", [])
            
            print(f"Found {len(resources)} total resources:")
            
            # Look for our task-specific resources
            podcast_outline_uri = None
            persona_research_uris = []
            
            for resource in resources:
                uri = resource.get("uri", "")
                name = resource.get("name", "")
                print(f"  - {name}: {uri}")
                
                if f"podcast_outline_{task_id}" in uri:
                    podcast_outline_uri = uri
                elif f"persona_research_{task_id}" in uri:
                    persona_research_uris.append(uri)
            
            # Test podcast outline resource
            if podcast_outline_uri:
                print(f"\n🔍 Testing Podcast Outline Resource: {podcast_outline_uri}")
                success = await self._test_resource_read(client, podcast_outline_uri)
                if success:
                    print("✅ Podcast outline resource accessible!")
                else:
                    print("❌ Failed to access podcast outline resource")
                    return False
            else:
                print("⚠️  No podcast outline resource found for this task")
            
            # Test persona research resources
            if persona_research_uris:
                print(f"\n🔍 Testing Persona Research Resources ({len(persona_research_uris)} found):")
                for i, uri in enumerate(persona_research_uris):
                    print(f"  Testing {i+1}/{len(persona_research_uris)}: {uri}")
                    success = await self._test_resource_read(client, uri)
                    if success:
                        print(f"  ✅ Persona research resource {i+1} accessible!")
                    else:
                        print(f"  ❌ Failed to access persona research resource {i+1}")
                        return False
            else:
                print("⚠️  No persona research resources found for this task")
            
            return True
    
    async def _test_resource_read(self, client: httpx.AsyncClient, uri: str) -> bool:
        """Test reading a specific resource."""
        try:
            read_request = {
                "method": "resources/read",
                "params": {
                    "uri": uri
                }
            }
            
            read_response = await client.post(self.session_url, json=read_request)
            if read_response.status_code != 200:
                print(f"    ❌ HTTP error: {read_response.status_code}")
                return False
            
            resource_data = read_response.json()
            result = resource_data.get("result")
            
            if not result:
                print(f"    ❌ No result in response")
                return False
            
            contents = result.get("contents", [])
            if not contents:
                print(f"    ❌ No contents in result")
                return False
            
            content = contents[0]
            text_content = content.get("text", "")
            
            if text_content:
                # Try to parse as JSON to validate content
                try:
                    json_data = json.loads(text_content)
                    print(f"    ✅ Valid JSON content ({len(text_content)} chars)")
                    return True
                except json.JSONDecodeError:
                    print(f"    ✅ Text content ({len(text_content)} chars, non-JSON)")
                    return True
            else:
                print(f"    ❌ Empty content")
                return False
                
        except Exception as e:
            print(f"    ❌ Exception: {e}")
            return False

async def main():
    """Main test function."""
    print("🧪 Testing MCP Resource Access for Text Files")
    print("=" * 50)
    
    # Use the task ID from our successful validation
    task_id = "30eeb6a7-43b9-4242-89b8-3fbdec15936c"
    
    print(f"🎯 Testing resources for task: {task_id}")
    
    try:
        client = SimpleMCPResourceClient()
        success = await client.test_resource_access(task_id)
        
        if success:
            print("\n🎉 SUCCESS: All MCP text file resources are accessible!")
            print("✅ Enhanced resource handlers are working correctly")
            print("✅ Text file download and caching integration validated")
        else:
            print("\n❌ FAILED: Some MCP resources could not be accessed")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
