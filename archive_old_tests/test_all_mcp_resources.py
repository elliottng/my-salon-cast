"""
Master Test Runner for All MCP Resources
Runs all resource test suites: jobs, podcast, and persona resources
"""

import asyncio
import sys
import os
import subprocess
from datetime import datetime, timezone

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


def run_test_suite(test_file):
    """Run a test suite in a subprocess"""
    print(f"\n{'='*80}")
    print(f"🚀 Running {test_file}")
    print(f"{'='*80}")
    
    result = subprocess.run(
        [sys.executable, test_file],
        cwd=current_dir,
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0


def main():
    """Run all MCP resource test suites"""
    print("🎯 MySalonCast MCP Resources - Complete Test Suite")
    print(f"⏰ Started: {datetime.now(timezone.utc).isoformat()}")
    print(f"📂 Working Directory: {current_dir}")
    
    # Test suites to run
    test_suites = [
        ("Job Resources", "test_mcp_job_resources.py"),
        ("Podcast Resources", "test_mcp_podcast_resources.py"),
        ("Persona Resources", "test_mcp_persona_resources.py")
    ]
    
    results = {}
    
    # Run each test suite
    for suite_name, test_file in test_suites:
        print(f"\n🔄 Starting {suite_name} tests...")
        success = run_test_suite(test_file)
        results[suite_name] = success
        
        if success:
            print(f"✅ {suite_name}: PASSED")
        else:
            print(f"❌ {suite_name}: FAILED")
        
        # Small delay between test suites
        print("⏸️  Waiting 3 seconds before next suite...")
        import time
        time.sleep(3)
    
    # Final summary
    print(f"\n{'='*80}")
    print("📊 COMPLETE TEST SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for suite_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {suite_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} test suites passed")
    print(f"⏰ Completed: {datetime.now(timezone.utc).isoformat()}")
    
    if passed == total:
        print("\n🎉 ALL MCP RESOURCE TESTS PASSED!")
        print("✨ The MySalonCast MCP server resources are working correctly!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test suite(s) failed")
        print("🔧 Please check the output above for details")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
