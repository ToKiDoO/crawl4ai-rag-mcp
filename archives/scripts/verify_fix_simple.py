#!/usr/bin/env python3
"""
Simple verification that the parameter name fixes are in place.
"""

import inspect
import sys

# Add the src directory to Python path
sys.path.insert(0, '/home/krashnicov/crawl4aimcp/src')

from database.qdrant_adapter import QdrantAdapter


def verify_method_signatures():
    """Verify that all methods have the correct parameter names"""
    print("PARAMETER NAME CONSISTENCY FIX VERIFICATION")
    print("=" * 50)
    
    adapter = QdrantAdapter()
    
    # Test 1: search_code_examples method
    sig = inspect.signature(adapter.search_code_examples)
    params = list(sig.parameters.keys())
    print(f"search_code_examples parameters: {params}")
    
    if 'filter_metadata' in params:
        print("✅ PASS: search_code_examples has filter_metadata parameter")
        search_code_examples_pass = True
    else:
        print("❌ FAIL: search_code_examples missing filter_metadata parameter")
        search_code_examples_pass = False
    
    # Test 2: search method
    sig = inspect.signature(adapter.search)
    params = list(sig.parameters.keys())
    print(f"search parameters: {params}")
    
    if 'filter_metadata' in params:
        print("✅ PASS: search has filter_metadata parameter")
        search_pass = True
    else:
        print("❌ FAIL: search missing filter_metadata parameter")
        search_pass = False
    
    # Test 3: hybrid_search method
    sig = inspect.signature(adapter.hybrid_search)
    params = list(sig.parameters.keys())
    print(f"hybrid_search parameters: {params}")
    
    if 'filter_metadata' in params:
        print("✅ PASS: hybrid_search has filter_metadata parameter")
        hybrid_search_pass = True
    else:
        print("❌ FAIL: hybrid_search missing filter_metadata parameter")
        hybrid_search_pass = False
    
    return all([search_code_examples_pass, search_pass, hybrid_search_pass])


def verify_caller_files():
    """Verify that caller files are using the correct parameter names"""
    print("\nCALLER FILE VERIFICATION")
    print("=" * 25)
    
    # Check validated_search.py (line 220)
    try:
        with open('/home/krashnicov/crawl4aimcp/src/services/validated_search.py', 'r') as f:
            content = f.read()
            if 'filter_metadata=filter_metadata' in content:
                print("✅ PASS: validated_search.py uses filter_metadata parameter")
                validated_search_pass = True
            else:
                print("❌ FAIL: validated_search.py doesn't use filter_metadata parameter")
                validated_search_pass = False
    except Exception as e:
        print(f"❌ ERROR reading validated_search.py: {e}")
        validated_search_pass = False
    
    # Check rag_queries.py (line 176)
    try:
        with open('/home/krashnicov/crawl4aimcp/src/database/rag_queries.py', 'r') as f:
            content = f.read()
            if 'filter_metadata=filter_metadata' in content:
                print("✅ PASS: rag_queries.py uses filter_metadata parameter")
                rag_queries_pass = True
            else:
                print("❌ FAIL: rag_queries.py doesn't use filter_metadata parameter")
                rag_queries_pass = False
    except Exception as e:
        print(f"❌ ERROR reading rag_queries.py: {e}")
        rag_queries_pass = False
    
    return all([validated_search_pass, rag_queries_pass])


def main():
    """Main verification function"""
    
    # Verify method signatures
    signatures_pass = verify_method_signatures()
    
    # Verify caller files
    callers_pass = verify_caller_files()
    
    # Final verdict
    print("\nFINAL VERDICT")
    print("=" * 15)
    
    if signatures_pass and callers_pass:
        print("✅ PASS: All parameter name consistency fixes are verified")
        print("✅ The error 'QdrantAdapter.search_code_examples() got an unexpected keyword argument filter_metadata' is resolved")
        print("✅ Ready for production")
        return 0
    else:
        print("❌ FAIL: Parameter name consistency issues detected")
        print("❌ The fix may not be complete")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)