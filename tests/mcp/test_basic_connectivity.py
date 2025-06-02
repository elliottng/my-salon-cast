"""
Basic connectivity test for MCP server
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from tests.mcp.client import MySalonCastMCPClient, test_hello_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_connectivity():
    """Test basic connectivity to MCP server"""
    client = MySalonCastMCPClient()
    
    try:
        logger.info("Connecting to MCP server...")
        await client.connect()
        logger.info("✓ Connected successfully")
        
        # List available tools
        logger.info("\nListing available tools...")
        tools = await client.list_tools()
        logger.info(f"✓ Found {len(tools)} tools:")
        for tool in tools:
            logger.info(f"  - {tool.name}: {tool.description}")
        
        # Test hello tool
        logger.info("\nTesting hello tool...")
        result = await test_hello_tool(client)
        logger.info(f"✓ Hello tool response: {result}")
        
        # List resources
        logger.info("\nListing available resources...")
        resources = await client.list_resources()
        logger.info(f"✓ Found {len(resources)} resources:")
        for resource in resources:
            logger.info(f"  - {resource.uri}: {resource.name}")
        
        logger.info("\n✅ All basic connectivity tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(test_basic_connectivity())
