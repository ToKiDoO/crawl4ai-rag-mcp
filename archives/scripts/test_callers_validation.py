#!/usr/bin/env python3
"""
Test to validate that the caller modules are using the correct parameter names.
Test DateTime: Thu Aug  7 17:07:59 BST 2025
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_validated_search_caller():
    """Test that validated_search.py uses correct parameter name"""
    print("=== Testing validated_search.py caller ===")
    
    # Read the file and check for the fix
    file_path = os.path.join(os.path.dirname(__file__), 'src', 'services', 'validated_search.py')
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for the specific line that was causing the issue
        if 'filter_metadata=filter_metadata' in content:
            print("✅ PASS: validated_search.py uses 'filter_metadata' parameter")
            
            # Check line around 220 specifically
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'search_code_examples(' in line and i > 215 and i < 225:
                    print(f"Line {i+1}: {line.strip()}")
                    if 'filter_metadata' in line:
                        print("✅ Confirmed: Line uses filter_metadata parameter")
                        return True
            
            print("✅ PASS: filter_metadata parameter found in file")
            return True
        else:
            print("❌ FAIL: validated_search.py doesn't use 'filter_metadata' parameter")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error reading validated_search.py: {e}")
        return False

def test_rag_queries_caller():
    """Test that rag_queries.py uses correct parameter name"""
    print("\n=== Testing rag_queries.py caller ===")
    
    # Read the file and check for the fix
    file_path = os.path.join(os.path.dirname(__file__), 'src', 'database', 'rag_queries.py')
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for the specific line that was causing the issue
        if 'filter_metadata=filter_metadata' in content:
            print("✅ PASS: rag_queries.py uses 'filter_metadata' parameter")
            
            # Check line around 176 specifically
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'search_code_examples(' in line and i > 170 and i < 180:
                    print(f"Line {i+1}: {line.strip()}")
                    if 'filter_metadata' in line:
                        print("✅ Confirmed: Line uses filter_metadata parameter")
                        return True
            
            print("✅ PASS: filter_metadata parameter found in file")
            return True
        else:
            print("❌ FAIL: rag_queries.py doesn't use 'filter_metadata' parameter")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error reading rag_queries.py: {e}")
        return False

def test_no_old_parameter_names():
    """Test that old incorrect parameter names are not being used"""
    print("\n=== Testing for old parameter names ===")
    
    files_to_check = [
        'src/services/validated_search.py',
        'src/database/rag_queries.py'
    ]
    
    old_patterns = [
        'source_id=filter_metadata',  # Incorrect parameter name usage
        'metadata_filter=',  # Alternative incorrect name
    ]
    
    issues_found = []
    
    for file_path in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        
        try:
            with open(full_path, 'r') as f:
                content = f.read()
                
            for pattern in old_patterns:
                if pattern in content:
                    issues_found.append(f"{file_path}: Found old pattern '{pattern}'")
                    
        except Exception as e:
            issues_found.append(f"Error reading {file_path}: {e}")
    
    if not issues_found:
        print("✅ PASS: No old parameter name patterns found")
        return True
    else:
        for issue in issues_found:
            print(f"❌ {issue}")
        return False

def main():
    """Run caller validation tests"""
    print("Caller Parameter Usage Validation")
    print("=" * 40)
    print("Testing that callers use correct parameter names after the fix")
    print()
    
    test1_result = test_validated_search_caller()
    test2_result = test_rag_queries_caller()
    test3_result = test_no_old_parameter_names()
    
    print("\n" + "=" * 40)
    print("CALLER VALIDATION SUMMARY:")
    
    if test1_result and test2_result and test3_result:
        print("✅ PASS: All callers use correct parameter names")
        return True
    else:
        print("❌ FAIL: Issues found with caller parameter usage")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)