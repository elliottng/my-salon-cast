"""
MCP Client wrapper for testing MySalonCast MCP server
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional
from fastmcp import Client

logger = logging.getLogger(__name__)

class MySalonCastMCPClient:
    """MCP client for connecting to MySalonCast server using FastMCP"""
    
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        self.server_url = server_url
        # FastMCP Client automatically uses StreamableHttpTransport for HTTP URLs
        self.client = Client(server_url)
        logger.info(f"Initialized FastMCP client for {server_url}")
    
    async def connect(self) -> None:
        """Connect to the MCP server (handled automatically by FastMCP)"""
        logger.info("FastMCP client ready for requests")
    
    async def list_tools(self) -> list:
        """List available tools from the MCP server"""
        async with self.client:
            tools = await self.client.list_tools()
            return tools
    
    async def list_resources(self) -> list:
        """List available resources from the MCP server"""
        async with self.client:
            resources = await self.client.list_resources()
            return resources
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server"""
        async with self.client:
            result = await self.client.call_tool(tool_name, arguments)
            return result
    
    async def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server"""
        async with self.client:
            result = await self.client.read_resource(uri)
            return result
    
    async def close(self) -> None:
        """Close the client connection (handled automatically by FastMCP context manager)"""
        logger.info("FastMCP client session ended")

# For testing with MCP protocol
class SimpleMCPTestClient:
    """Simplified test client that interacts with the MySalonCast MCP server via FastMCP"""
    
    def __init__(self, server_url: str = "http://localhost:8000/mcp"):
        self.server_url = server_url
        self.mcp_client = MySalonCastMCPClient(server_url)
    
    async def call_generate_podcast_async(self, **kwargs) -> Dict[str, Any]:
        """Generate podcast asynchronously via MCP protocol"""
        result = await self.mcp_client.call_tool("generate_podcast_async", kwargs)
        # FastMCP returns a list of content objects, extract the text and parse as JSON
        if isinstance(result, list) and result:
            content = result[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"text": content.text}  # Return as text if not JSON
        return result
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status via MCP protocol"""
        result = await self.mcp_client.call_tool("get_task_status", {"task_id": task_id})
        # FastMCP returns a list of content objects, extract the text and parse as JSON
        if isinstance(result, list) and result:
            content = result[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"text": content.text}  # Return as text if not JSON
        return result
    
    async def list_tools(self) -> list:
        """List available MCP tools"""
        return await self.mcp_client.list_tools()
    
    async def list_resources(self) -> list:
        """List available MCP resources"""
        return await self.mcp_client.list_resources()
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Call an MCP tool"""
        result = await self.mcp_client.call_tool(tool_name, arguments)
        # FastMCP returns a list of content objects, extract the text and parse as JSON
        if isinstance(result, list) and result:
            content = result[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"text": content.text}  # Return as text if not JSON
        return result
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read an MCP resource"""
        result = await self.mcp_client.read_resource(uri)
        # FastMCP returns a list of TextResourceContents, extract the first one
        if isinstance(result, list) and result:
            content = result[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except json.JSONDecodeError:
                    return {"text": content.text}  # Return as text if not JSON
        return result
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status - placeholder implementation"""
        # This tool doesn't exist in the MCP server yet
        return {
            "success": True,
            "active_tasks": [],
            "queued_tasks": [],
            "available_slots": 3,
            "max_concurrent": 3
        }
    
    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a task - placeholder implementation"""
        # This tool doesn't exist in the MCP server yet
        return {
            "success": True,
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation not implemented in MCP server yet"
        }
        
    async def close(self) -> None:
        """Close the client"""
        await self.mcp_client.close()

# Helper functions for common test operations

async def test_hello_tool(client: MySalonCastMCPClient) -> str:
    """Test the hello tool"""
    result = await client.call_tool("hello", {"name": "MCP Tester"})
    return result

async def submit_podcast_generation(client: SimpleMCPTestClient, 
                                  source_urls: list,
                                  **kwargs) -> str:
    """Submit an async podcast generation task"""
    params = {
        "source_urls": source_urls,
        **kwargs
    }
    result = await client.call_generate_podcast_async(**params)
    return result.get("task_id")

async def check_task_status(client: SimpleMCPTestClient, task_id: str) -> dict:
    """Check the status of a task"""
    return await client.get_task_status(task_id)

async def wait_for_completion(client: SimpleMCPTestClient, 
                            task_id: str,
                            poll_interval: float = 2.0,
                            timeout: float = 300.0) -> dict:
    """Wait for a task to complete, polling periodically"""
    start_time = asyncio.get_event_loop().time()
    
    while True:
        status = await check_task_status(client, task_id)
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            return status
        
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
        
        logger.info(f"Task {task_id}: {status['status']} ({status['progress_percentage']}%)")
        await asyncio.sleep(poll_interval)

async def get_podcast_transcript(client: SimpleMCPTestClient, task_id: str) -> str:
    """Get the transcript of a completed podcast"""
    # Use MCP resource to get transcript
    result = await client.read_resource(f"podcast://{task_id}/transcript")
    return result.get("text", "") if result else ""

async def get_podcast_metadata(client: SimpleMCPTestClient, task_id: str) -> dict:
    """Get metadata of a completed podcast"""
    # Use MCP resource to get metadata
    result = await client.read_resource(f"podcast://{task_id}/metadata")
    return result if result else {}
