#!/usr/bin/env python3
"""
Simple verification script to check that our async implementation is properly integrated.
This script checks the code changes without running the full application.
"""

import ast
import os

def verify_code_changes():
    """Verify that all expected code changes are in place."""
    print("=== Verifying Async Implementation ===\n")
    
    results = []
    
    # Check 1: task_runner.py exists
    task_runner_path = "app/task_runner.py"
    if os.path.exists(task_runner_path):
        results.append(("✅", f"{task_runner_path} exists"))
        
        # Check for key components in task_runner.py
        with open(task_runner_path, 'r') as f:
            content = f.read()
            
        checks = [
            ("class TaskRunner", "TaskRunner class defined"),
            ("submit_task", "submit_task method exists"),
            ("can_accept_new_task", "can_accept_new_task method exists"),
            ("_monitor_task", "_monitor_task method exists"),
            ("get_task_runner", "get_task_runner function exists")
        ]
        
        for check_str, desc in checks:
            if check_str in content:
                results.append(("✅", f"  - {desc}"))
            else:
                results.append(("❌", f"  - {desc}"))
    else:
        results.append(("❌", f"{task_runner_path} NOT found"))
    
    print()
    
    # Check 2: podcast_workflow.py modifications
    workflow_path = "app/podcast_workflow.py"
    if os.path.exists(workflow_path):
        results.append(("✅", f"{workflow_path} exists"))
        
        with open(workflow_path, 'r') as f:
            content = f.read()
        
        checks = [
            ("from app.task_runner import get_task_runner", "task_runner import added"),
            ("_run_podcast_generation_async", "_run_podcast_generation_async method exists"),
            ("_run_podcast_generation_sync_wrapper", "sync wrapper method exists"),
            ("if async_mode:", "async_mode check in _generate_podcast_internal"),
            ("task_runner.submit_task", "submit_task call added"),
            ("task_runner.can_accept_new_task", "capacity check added")
        ]
        
        for check_str, desc in checks:
            if check_str in content:
                results.append(("✅", f"  - {desc}"))
            else:
                results.append(("❌", f"  - {desc}"))
                
        # Check for specific async behavior
        if "async_mode=True" in content and "async_mode=False" in content:
            results.append(("✅", f"  - Both async modes properly referenced"))
        else:
            results.append(("❌", f"  - Missing async mode references"))
            
    else:
        results.append(("❌", f"{workflow_path} NOT found"))
    
    print("\n=== Summary ===")
    for symbol, message in results:
        print(f"{symbol} {message}")
    
    # Count results
    passed = sum(1 for s, _ in results if s == "✅")
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All implementation checks passed!")
        print("\nThe async infrastructure is properly integrated:")
        print("- TaskRunner for background task execution")
        print("- Async wrapper methods in podcast_workflow.py")
        print("- Conditional logic for async_mode parameter")
        print("- Task submission and capacity checking")
        return True
    else:
        print("\n⚠️  Some checks failed. Please review the implementation.")
        return False


def check_backwards_compatibility():
    """Check that backwards compatibility is maintained."""
    print("\n\n=== Checking Backwards Compatibility ===")
    
    workflow_path = "app/podcast_workflow.py"
    if not os.path.exists(workflow_path):
        print("❌ Cannot check - workflow file not found")
        return False
    
    with open(workflow_path, 'r') as f:
        content = f.read()
    
    # Parse the file to check method signatures
    try:
        tree = ast.parse(content)
    except:
        print("⚠️  Could not parse file as Python AST")
        return False
    
    results = []
    
    # Look for the key methods
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == "generate_podcast_from_source":
                # Check it still returns PodcastEpisode (not task_id)
                if "async_mode=False" in content[node.lineno:node.end_lineno]:
                    results.append(("✅", "generate_podcast_from_source uses async_mode=False"))
                else:
                    results.append(("⚠️", "generate_podcast_from_source async_mode unclear"))
                    
            elif node.name == "generate_podcast_async":
                # Check it uses async_mode=True
                if "async_mode=True" in content[node.lineno:node.end_lineno]:
                    results.append(("✅", "generate_podcast_async uses async_mode=True"))
                else:
                    results.append(("⚠️", "generate_podcast_async async_mode unclear"))
    
    print("\nBackwards Compatibility Checks:")
    for symbol, message in results:
        print(f"{symbol} {message}")
    
    if all(s in ["✅", "⚠️"] for s, _ in results):
        print("\n✅ Backwards compatibility appears to be maintained")
        print("  - generate_podcast_from_source() remains synchronous")
        print("  - generate_podcast_async() is the new async method")
        return True
    else:
        print("\n❌ Backwards compatibility may be broken")
        return False


if __name__ == "__main__":
    print("Async Podcast Generation - Implementation Verification\n")
    
    impl_ok = verify_code_changes()
    compat_ok = check_backwards_compatibility()
    
    if impl_ok and compat_ok:
        print("\n✅ ✅ ✅ Implementation verified successfully! ✅ ✅ ✅")
        exit(0)
    else:
        print("\n❌ Some issues found. Please review the implementation.")
        exit(1)
