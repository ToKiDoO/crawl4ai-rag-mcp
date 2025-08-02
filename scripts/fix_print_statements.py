#!/usr/bin/env python3
"""
Fix print statements in utils.py and utils_refactored.py to use stderr
"""
import re
import sys
from pathlib import Path

def fix_print_statements(file_path):
    """Replace print() statements with stderr output"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Replace print statements that don't already have file=sys.stderr
    # Pattern matches print(...) but not print(..., file=...)
    pattern = r'(\s*)print\((.*?)\)(?!\s*,\s*file\s*=)'
    replacement = r'\1print(\2, file=sys.stderr)'
    
    # First add import if not present
    if 'import sys' not in content:
        # Add after other imports
        import_pattern = r'(import .+\n)'
        if re.search(import_pattern, content):
            content = re.sub(import_pattern, r'\1import sys\n', content, count=1)
        else:
            # Add at the beginning after docstring
            content = re.sub(r'("""[\s\S]*?"""\n)', r'\1import sys\n', content, count=1)
    
    # Replace all print statements
    new_content = re.sub(pattern, replacement, content)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    # Count changes
    changes = len(re.findall(pattern, content))
    return changes

def main():
    src_dir = Path(__file__).parent.parent / 'src'
    
    files_to_fix = [
        src_dir / 'utils.py',
        src_dir / 'utils_refactored.py'
    ]
    
    total_changes = 0
    for file_path in files_to_fix:
        if file_path.exists():
            changes = fix_print_statements(file_path)
            print(f"Fixed {changes} print statements in {file_path.name}")
            total_changes += changes
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nTotal changes: {total_changes}")

if __name__ == "__main__":
    main()