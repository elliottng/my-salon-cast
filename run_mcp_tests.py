#!/usr/bin/env python3
"""
MCP Tests Runner with Subprocess Isolation

This script runs MCP tests in separate subprocesses to avoid
ThreadPoolExecutor shutdown errors between tests.
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

def run_test_in_subprocess(test_name: str) -> tuple[bool, str, str]:
    """Run a single test in subprocess isolation"""
    current_dir = Path(__file__).parent / "tests" / "mcp"
    
    test_script = f'''
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path  
project_root = Path("{Path(__file__).parent}")
sys.path.insert(0, str(project_root))

from tests.mcp.test_mcp_client import {test_name}

async def main():
    try:
        success = await {test_name}()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with exception: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=current_dir,
        capture_output=True,
        text=True
    )
    
    return result.returncode == 0, result.stdout, result.stderr

def main():
    """Run all MCP tests with subprocess isolation"""
    print("="*80)
    print("MCP CLIENT TESTS WITH SUBPROCESS ISOLATION")
    print("="*80)
    print()
    
    # List of test functions to run
    tests = [
        "test_list_tools_and_resources",
        "test_hello_tool", 
        "test_supported_formats_resource",
        "test_validation_error",
        "test_generate_podcast_async",
        "test_non_existent_task"
    ]
    
    results = {}
    passed = 0
    failed = 0
    
    for test_name in tests:
        print(f"Running {test_name}...")
        
        start_time = time.time()
        success, stdout, stderr = run_test_in_subprocess(test_name)
        duration = time.time() - start_time
        
        results[test_name] = {
            'success': success,
            'duration': duration,
            'stdout': stdout,
            'stderr': stderr
        }
        
        if success:
            passed += 1
            print(f"✅ PASSED: {test_name} ({duration:.2f}s)")
        else:
            failed += 1
            print(f"❌ FAILED: {test_name} ({duration:.2f}s)")
            if stderr:
                print(f"   stderr: {stderr.strip()}")
        
        # Show test output for debugging
        if stdout:
            for line in stdout.strip().split('\n'):
                if line.strip():
                    print(f"   {line}")
        
        print()
        
        # Small delay between tests to avoid resource conflicts
        time.sleep(1)
    
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {passed/len(tests)*100:.1f}%")
    
    if failed > 0:
        print("\nFailed tests:")
        for test_name, result in results.items():
            if not result['success']:
                print(f"  - {test_name}")
    
    # Exit with error code if any tests failed
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
