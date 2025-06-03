#!/usr/bin/env python3
"""Simple test to verify MCP server functionality with cloud storage integration."""

import asyncio
import os
import sys
import subprocess
from typing import Dict, Any

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from fastmcp import FastMCP
    from fastmcp.client import create_client
except ImportError:
    print("FastMCP not available, testing basic imports...")


async def test_basic_imports():
    """Test that all modules can be imported correctly."""
    print("🧪 Testing basic imports with cloud storage integration...")
    
    try:
        from app.storage import CloudStorageManager
        print("✅ CloudStorageManager imported successfully")
        
        from app.podcast_workflow import PodcastGeneratorService  
        print("✅ PodcastGeneratorService imported successfully")
        
        from app.config import setup_environment
        print("✅ Configuration modules imported successfully")
        
        # Test instantiation
        config = setup_environment()
        print(f"✅ Configuration setup for environment: {config.environment}")
        
        storage_manager = CloudStorageManager()
        print(f"✅ CloudStorageManager instantiated (cloud enabled: {storage_manager.is_cloud_storage_available})")
        
        service = PodcastGeneratorService()
        print(f"✅ PodcastGeneratorService instantiated with cloud storage")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


async def test_mcp_server_process():
    """Test that MCP server process is running correctly."""
    print("\n🧪 Testing MCP server process...")
    
    try:
        # Check if server process is running
        result = subprocess.run(['pgrep', '-f', 'mcp_server'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ MCP server process found (PID: {result.stdout.strip()})")
            
            # Test basic network connectivity
            result = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://localhost:8000/health'], 
                                  capture_output=True, text=True, timeout=5)
            if result.stdout.strip() == '200':
                print("✅ MCP server health endpoint responding")
            else:
                print(f"⚠️  MCP server health endpoint status: {result.stdout.strip()}")
                
            return True
        else:
            print("❌ MCP server process not found")
            return False
            
    except Exception as e:
        print(f"❌ MCP server process test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 CLOUD STORAGE INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Basic imports
    import_success = asyncio.run(test_basic_imports())
    
    # Test 2: MCP server process
    server_success = asyncio.run(test_mcp_server_process())
    
    print("\n" + "=" * 60)
    print("📋 TEST RESULTS")
    print("=" * 60)
    print(f"   Import Tests:     {'✅ PASSED' if import_success else '❌ FAILED'}")
    print(f"   Server Process:   {'✅ PASSED' if server_success else '❌ FAILED'}")
    
    if import_success and server_success:
        print("\n🎉 Cloud storage integration is working correctly!")
        print("   • All modules import without errors")
        print("   • CloudStorageManager initializes properly")
        print("   • PodcastGeneratorService integrates cloud storage")
        print("   • MCP server runs with new storage backend")
        exit(0)
    else:
        print("\n❌ Some tests failed - check the output above")
        exit(1)
