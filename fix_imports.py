#!/usr/bin/env python
import os
import re
import glob

def fix_imports_in_file(file_path):
    """Fix relative imports to absolute imports in a Python file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace "from ." with "from " (removing the dot)
    modified_content = re.sub(r'from\s+\.\s*', 'from ', content)
    
    # Also handle "from .module" patterns
    modified_content = re.sub(r'from\s+\.([a-zA-Z0-9_]+)', r'from \1', modified_content)
    
    if content != modified_content:
        print(f"Fixing imports in {file_path}")
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    return False

def main():
    # Find all Python files in the app directory
    python_files = glob.glob('app/*.py')
    fixed_count = 0
    
    for py_file in python_files:
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"Fixed imports in {fixed_count} files")

if __name__ == "__main__":
    main()
