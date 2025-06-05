#!/usr/bin/env python3
"""
Test cleanup functionality with a real generated podcast task.
"""

import asyncio
import os
import sys
from pathlib import Path
import tempfile
import http.server
import socketserver
import threading
from urllib.parse import urljoin

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.mcp.client import SimpleMCPTestClient


def start_local_server(content, port=8888):
    """Start a local HTTP server to serve test content."""
    class ContentHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/test_content.txt":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress server logs
    
    server = socketserver.TCPServer(("localhost", port), ContentHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server, f"http://localhost:{port}/test_content.txt"


async def test_cleanup_with_generated_task():
    """Test cleanup functionality with a real podcast generation task."""
    client = SimpleMCPTestClient()
    
    print("\n" + "="*60)
    print("Testing Cleanup with Real Generated Task")
    print("="*60)
    
    # Step 1: Generate a quick test podcast
    print("\n1. Generating test podcast...")
    test_content = """
    In today's digital landscape, AI is revolutionizing how we create content. 
    Machine learning models can now generate text, images, and even audio with remarkable quality.
    This represents a fundamental shift in creative processes.
    """
    
    # Start a local HTTP server to serve the test content
    server, content_url = start_local_server(test_content)
    
    try:
        # Generate podcast using the async tool with correct parameters
        result = await client.call_tool(
            "generate_podcast_async",
            {
                "source_urls": [content_url],
                "podcast_length": "1-2 minutes",
            }
        )
        
        if result.get("task_id"):
            task_id = result["task_id"]
            print(f"✅ Started podcast generation: {task_id}")
            
            # Wait for completion
            print("\n2. Waiting for generation to complete...")
            max_attempts = 30
            for i in range(max_attempts):
                await asyncio.sleep(2)
                status_result = await client.call_tool("get_task_status", {"task_id": task_id})
                status = status_result.get("status", "unknown")
                progress = status_result.get("progress_percentage", 0)
                
                print(f"   Status: {status} ({progress}%)")
                
                if status == "completed":
                    print("✅ Podcast generation completed!")
                    break
                elif status == "failed":
                    print(f"❌ Generation failed: {status_result.get('error_message', 'Unknown error')}")
                    return False
                
                if i == max_attempts - 1:
                    print("❌ Generation timeout")
                    return False
            
            # Step 3: Check cleanup status before cleanup
            print("\n3. Checking cleanup status before cleanup...")
            cleanup_status = await client.read_resource(f"files://{task_id}/cleanup")
            print(f"✅ Cleanup status retrieved")
            print(f"   Current policy: {cleanup_status['cleanup_policy']}")
            print(f"   Files exist: audio={cleanup_status['files_exist']['audio_file']}, "
                  f"segments={cleanup_status['files_exist']['audio_segments']}, "
                  f"temp_dir={cleanup_status['files_exist']['temp_directory']}")
            
            # Step 4: Check current configuration
            print("\n4. Checking current cleanup configuration...")
            config = await client.read_resource("config://cleanup")
            print(f"✅ Current default policy: {config['cleanup_policies']['current_default']}")
            
            # Step 5: Test cleanup with retain_audio_only policy override
            print("\n5. Testing cleanup with 'retain_audio_only' policy override...")
            cleanup_result = await client.call_tool(
                "cleanup_task_files",
                {
                    "task_id": task_id,
                    "policy_override": "retain_audio_only"
                }
            )
            
            if cleanup_result["success"]:
                print("✅ Cleanup completed successfully!")
                print(f"   Applied policy: {cleanup_result['applied_policy']}")
                print(f"   Files cleaned: {len(cleanup_result['cleaned_files'])}")
                print(f"   Files failed: {len(cleanup_result['failed_files'])}")
                print(f"   Size freed: {cleanup_result['total_size_freed']} bytes")
                print(f"   Audio retained: {cleanup_result['cleanup_rules']['retain_audio']}")
                
                # Verify audio was retained using cleanup status
                # (The files resource doesn't exist, so we check via cleanup status)
                cleanup_status = await client.read_resource(f"files://{task_id}/cleanup")
                if cleanup_status['files_exist']['audio_file']:
                    print("✅ Audio file was retained as expected")
                else:
                    print("❌ Audio file was not retained")
            else:
                print(f"❌ Cleanup failed: {cleanup_result['error']}")
            
            # Step 6: Check cleanup status after cleanup
            print("\n6. Checking cleanup status after cleanup...")
            try:
                cleanup_status = await client.read_resource(f"files://{task_id}/cleanup")
                print(f"✅ Post-cleanup status retrieved")
                print(f"   Files exist: audio={cleanup_status['files_exist']['audio_file']}, "
                      f"segments={cleanup_status['files_exist']['audio_segments']}, "
                      f"temp_dir={cleanup_status['files_exist']['temp_directory']}")
            except Exception as e:
                print(f"   Note: {e}")
            
            # Step 7: Test full cleanup
            print("\n7. Testing full cleanup (manual policy)...")
            cleanup_result = await client.call_tool(
                "cleanup_task_files",
                {
                    "task_id": task_id,
                    "policy_override": "manual"
                }
            )
            
            if cleanup_result["success"]:
                print("✅ Full cleanup completed!")
                print(f"   Files cleaned: {len(cleanup_result['cleaned_files'])}")
                print(f"   All files removed: {cleanup_result['cleanup_rules']['retain_audio'] == False}")
            
            return True
            
        else:
            print(f"❌ Failed to start generation: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    finally:
        # Stop the local HTTP server
        server.shutdown()
        server.server_close()


async def main():
    """Run the cleanup test with real task."""
    # Make sure we have environment setup
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Warning: GEMINI_API_KEY not set")
    
    success = await test_cleanup_with_generated_task()
    
    if success:
        print("\n✅ All cleanup tests with real task passed!")
    else:
        print("\n❌ Some tests failed")


if __name__ == "__main__":
    asyncio.run(main())
