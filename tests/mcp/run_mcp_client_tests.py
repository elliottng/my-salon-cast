#!/usr/bin/env python3
"""
Run MCP client tests in isolated subprocesses to avoid executor shutdown issues.
"""
import os
import sys
import subprocess
import time
from typing import List, Tuple

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Define tests to run
TESTS = [
    "test_list_tools_and_resources",
    "test_hello_tool",
    "test_supported_formats_resource",
    "test_non_existent_task",
    "test_validation_error",
    "test_generate_podcast_async",
]

def run_test_in_subprocess(test_name: str) -> Tuple[bool, str]:
    """Run a test in an isolated subprocess"""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"{'='*60}")
    
    # Get Python interpreter path from the virtual environment
    venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                              'venv', 'bin', 'python')
    
    # Build the command to run the test
    cmd = [
        venv_python, 
        "-c", 
        f"import asyncio, sys; from tests.mcp.test_mcp_client import {test_name}; " +
        f"sys.exit(0 if asyncio.run({test_name}()) else 1)"
    ]
    
    # Run the test in a subprocess
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False
    )
    
    # Get output and error
    output = result.stdout.strip()
    error = result.stderr.strip()
    
    # Check if test passed
    passed = result.returncode == 0
    
    # Print output and error
    if output:
        print("\nOutput:")
        print(output)
    
    if error:
        print("\nError:")
        print(error)
        
    # Print result
    if passed:
        print(f"\n✅ PASSED")
    else:
        print(f"\n❌ FAILED")
        
    return passed, error

def run_all_tests() -> bool:
    """Run all tests in isolated subprocesses"""
    print("Running MCP Client Tests with Subprocess Isolation")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name in TESTS:
        # Slight delay to avoid potential port conflicts
        time.sleep(1)
        
        # Run the test
        success, _ = run_test_in_subprocess(test_name)
        
        if success:
            passed += 1
        else:
            failed += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    # Ensure server is ready
    print("Running tests against the MCP server (expected at http://localhost:8080)")
    print("Make sure the server is running before proceeding!")
    print("=" * 60)
    
    # Run all tests
    success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
