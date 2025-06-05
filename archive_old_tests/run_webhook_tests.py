#!/usr/bin/env python3
"""
Test runner that executes each webhook test in a separate subprocess
to avoid executor shutdown issues between tests.
"""
import subprocess
import sys
import os
import time

def run_test_in_subprocess(test_name):
    """Run a single test function in a subprocess"""
    print(f"\n{'='*60}")
    print(f"Running {test_name} in isolated subprocess...")
    print('='*60)
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create a small Python script that runs just one test
    test_script = f"""
import asyncio
import sys
import os
sys.path.insert(0, r'{current_dir}')

from test_webhook import {test_name}

async def main():
    await {test_name}()

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    # Run the test in a subprocess
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=current_dir,
        capture_output=True,
        text=True
    )
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr, file=sys.stderr)
    
    if result.returncode != 0:
        print(f"\n❌ {test_name} failed with return code {result.returncode}")
        return False
    else:
        print(f"\n✅ {test_name} completed successfully")
        return True

def main():
    """Run all webhook tests in separate subprocesses"""
    print("\n=== Starting Webhook Tests with Process Isolation ===\n")
    
    # Note: Each test will start its own mock webhook server
    print("Note: Each test will start its own mock webhook server on port 8090\n")
    
    tests = [
        "test_webhook_success",
        "test_webhook_failure",
        "test_webhook_cancellation",
        "test_webhook_invalid_url"
    ]
    
    results = []
    for test in tests:
        success = run_test_in_subprocess(test)
        results.append((test, success))
        
        # Small delay between tests to ensure port is freed
        time.sleep(2)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for test, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test}: {status}")
    
    print(f"\nTotal: {len(results)} tests, {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
