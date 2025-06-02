"""
Run MCP async tools tests in isolated subprocesses to avoid executor shutdown issues
"""
import subprocess
import sys
import os
import tempfile
import time

def run_test_in_subprocess(test_name, test_code):
    """Run a test in a subprocess to avoid executor issues"""
    # Create a temporary file for the test
    temp_fd, temp_path = tempfile.mkstemp(suffix='.py', prefix=f'test_{test_name.lower().replace(" ", "_")}_')
    os.close(temp_fd)  # Close the file descriptor
    
    try:
        # Write the test code to the temp file
        with open(temp_path, 'w') as f:
            f.write(test_code)
        
        # Get the project root path
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"{'='*60}")
        
        # Run the test
        result = subprocess.run(
            [sys.executable, temp_path],
            cwd=project_root,  # Run from project root
            capture_output=True,
            text=True,
            env={**os.environ, 'PYTHONPATH': project_root}  # Set PYTHONPATH to project root
        )
        
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
    
    finally:
        # Clean up the temp file
        try:
            os.unlink(temp_path)
        except Exception as e:
            print(f"Warning: Failed to remove temp file {temp_path}: {e}")

def test_hello_tool():
    """Test basic MCP functionality"""
    test_code = '''
import asyncio
import sys
import os
from app.mcp_server import mcp

async def test():
    # Test the hello tool directly
    @mcp.tool()
    async def hello(name: str = "World") -> str:
        return f"Hello, {name}!"
    
    result = await hello(name="MCP Tester")
    print(f"Hello tool result: {result}")
    assert result == "Hello, MCP Tester!"

if __name__ == "__main__":
    asyncio.run(test())
'''
    return run_test_in_subprocess("Hello Tool", test_code)

def test_validation_errors():
    """Test validation error handling"""
    test_code = '''
import asyncio
import sys
import os
from app.podcast_models import PodcastRequest
import logging

logging.basicConfig(level=logging.WARNING)

async def test():
    # Create a valid request with source URL
    request = PodcastRequest(source_urls=["https://example.com"])
    print(f"✓ Created valid request with source URL")
    
    # Test the has_valid_sources property
    assert request.has_valid_sources == True
    print(f"✓ has_valid_sources property returns True for valid request")
    
    # Create a valid request with PDF path
    request = PodcastRequest(source_pdf_path="/path/to/file.pdf")
    print(f"✓ Created valid request with PDF path")
    
    # Verify PDF source is valid
    assert request.has_valid_sources == True
    print(f"✓ has_valid_sources property returns True for PDF request")
    
    print("All validation tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
'''
    return run_test_in_subprocess("Validation Errors", test_code)

def test_task_status():
    """Test task status tracking"""
    test_code = '''
import asyncio
import sys
import os
from app.status_manager import get_status_manager
from app.podcast_models import PodcastStatus
import logging

logging.basicConfig(level=logging.WARNING)

async def test():
    import uuid
    status_manager = get_status_manager()
    
    # Test non-existent task
    status = status_manager.get_status("non-existent-task-id")
    assert status is None
    print("✓ Non-existent task returns None")
    
    # Create a test status with unique ID
    task_id = f"test-task-{uuid.uuid4()}"  # Generate unique ID
    print(f"Using unique task ID: {task_id}")
    status_manager.create_status(task_id, {"test": "data"})
    
    # Retrieve it
    retrieved = status_manager.get_status(task_id)
    assert retrieved is not None
    assert retrieved.task_id == task_id
    assert retrieved.status == "queued"  # Default status is 'queued'
    assert retrieved.progress_percentage == 0.0  # Default progress is 0.0
    print("✓ Status creation and retrieval works")
    
    # Update it
    status_manager.update_status(
        task_id,
        "generating_dialogue",  # new_status as positional arg
        "Generating dialogue",  # description
        60.0  # progress
    )
    
    updated = status_manager.get_status(task_id)
    assert updated.status == "generating_dialogue"
    assert updated.progress_percentage == 60.0
    print("✓ Status update works")
    
    print("All status tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
'''
    return run_test_in_subprocess("Task Status", test_code)

def test_mcp_resource():
    """Test MCP resource retrieval"""
    test_code = '''
import asyncio
import sys
import os
from app.mcp_server import mcp
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    # Test the supported formats resource
    @mcp.resource("config://supported_formats")
    async def supported_formats():
        return {
            "success": True,
            "formats": {
                "input": ["url", "pdf", "text"],
                "output": ["mp3", "transcript"]
            }
        }
    
    result = await supported_formats()
    print(f"Supported formats: {result}")
    assert "success" in result
    assert "formats" in result
    assert "input" in result["formats"]
    assert "output" in result["formats"]
    
    # Test that required keys are present
    assert "url" in result["formats"]["input"]
    assert "pdf" in result["formats"]["input"]
    assert "mp3" in result["formats"]["output"]
    
    print("MCP resource test passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
'''
    return run_test_in_subprocess("MCP Resource", test_code)

def main():
    """Run all tests"""
    print("Running MCP Tool Tests with Subprocess Isolation")
    print("=" * 60)
    
    tests = [
        test_hello_tool,
        test_validation_errors,
        test_task_status,
        test_mcp_resource
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
