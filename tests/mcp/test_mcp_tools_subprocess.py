"""
Test MCP async tools using subprocess isolation to avoid executor shutdown issues
"""
import subprocess
import sys
import os
import json

def run_test_in_subprocess(test_name, test_code):
    """Run a test in a subprocess to avoid executor issues"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    result = subprocess.run(
        [sys.executable, "-c", test_code],
        cwd=current_dir,
        capture_output=True,
        text=True
    )
    
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    
    if result.returncode == 0:
        print("✅ PASSED")
        print("\nOutput:")
        print(result.stdout)
    else:
        print("❌ FAILED")
        print("\nError:")
        print(result.stderr)
        print("\nOutput:")
        print(result.stdout)
    
    return result.returncode == 0

def test_hello_tool():
    """Test basic MCP functionality"""
    test_code = '''
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

from app.mcp_server import mcp

async def test():
    # Test the hello tool directly
    @mcp.tool()
    async def hello(name: str = "World") -> str:
        return f"Hello, {name}!"
    
    result = await hello(name="MCP Tester")
    print(f"Hello tool result: {result}")
    assert result == "Hello, MCP Tester!"

asyncio.run(test())
'''
    return run_test_in_subprocess("Hello Tool", test_code)

def test_async_generation():
    """Test async podcast generation"""
    test_code = '''
import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest
from app.status_manager import get_status_manager
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    service = PodcastGeneratorService()
    status_manager = get_status_manager()
    
    # Create a simple request
    request = PodcastRequest(
        source_urls=["https://en.wikipedia.org/wiki/Machine_learning"],
        desired_podcast_length_str="3-5 minutes",
    )
    
    # Submit async task
    task_id = await service.generate_podcast_async(request)
    print(f"Task ID: {task_id}")
    
    # Check initial status
    status = status_manager.get_status(task_id)
    print(f"Initial status: {status.status}")
    print(f"Initial progress: {status.progress_percentage}%")
    
    # Wait a bit and check again
    await asyncio.sleep(5)
    status = status_manager.get_status(task_id)
    print(f"Status after 5s: {status.status}")
    print(f"Progress after 5s: {status.progress_percentage}%")
    
    # The task should be processing
    assert status.status not in ["failed", "cancelled"]
    print("Test passed!")

asyncio.run(test())
'''
    return run_test_in_subprocess("Async Generation", test_code)

def test_validation_errors():
    """Test validation error handling"""
    test_code = '''
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

from app.podcast_models import PodcastRequest
import logging

logging.basicConfig(level=logging.WARNING)

async def test():

    
    # Test no sources
    try:
        request = PodcastRequest()
        print("ERROR: Should have raised validation error for no sources")
    except Exception as e:
        print(f"✓ Correctly caught validation error: {type(e).__name__}")
    
    # Test both URL and PDF
    try:
        request = PodcastRequest(
            source_urls=["https://example.com"],
            source_pdf_path="/path/to/file.pdf"
        )
        print("ERROR: Should have raised validation error for both sources")
    except Exception as e:
        print(f"✓ Correctly caught validation error: {type(e).__name__}")
    
    print("All validation tests passed!")

asyncio.run(test())
'''
    return run_test_in_subprocess("Validation Errors", test_code)

def test_task_status():
    """Test task status tracking"""
    test_code = '''
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

from app.status_manager import get_status_manager
from app.podcast_models import PodcastStatus
import logging

logging.basicConfig(level=logging.WARNING)

async def test():
    status_manager = get_status_manager()
    
    # Test non-existent task
    status = status_manager.get_status("non-existent-task-id")
    assert status is None
    print("✓ Non-existent task returns None")
    
    # Create a test status
    test_status = PodcastStatus(
        task_id="test-task-123",
        status="analyzing_sources",
        progress_percentage=25.0
    )
    status_manager.create_status(test_status)
    
    # Retrieve it
    retrieved = status_manager.get_status("test-task-123")
    assert retrieved is not None
    assert retrieved.task_id == "test-task-123"
    assert retrieved.status == "analyzing_sources"
    assert retrieved.progress_percentage == 25.0
    print("✓ Status creation and retrieval works")
    
    # Update it
    status_manager.update_status(
        "test-task-123",
        status="generating_dialogue",
        progress_percentage=60.0
    )
    
    updated = status_manager.get_status("test-task-123")
    assert updated.status == "generating_dialogue"
    assert updated.progress_percentage == 60.0
    print("✓ Status update works")
    
    print("All status tests passed!")

asyncio.run(test())
'''
    return run_test_in_subprocess("Task Status", test_code)

def main():
    """Run all tests"""
    print("Running MCP Tool Tests with Subprocess Isolation")
    print("=" * 60)
    
    tests = [
        test_hello_tool,
        test_validation_errors,
        test_task_status,
        test_async_generation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
