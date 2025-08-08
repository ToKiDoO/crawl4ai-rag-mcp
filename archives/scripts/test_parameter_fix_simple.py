#!/usr/bin/env python3
"""
Simple test to validate the specific parameter fix.
Test DateTime: Thu Aug  7 17:07:59 BST 2025
"""

import sys
import os
import inspect

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_search_code_examples_parameter():
    """Test that search_code_examples method has filter_metadata parameter"""
    print("=== Testing search_code_examples parameter ===")
    
    try:
        from database.qdrant_adapter import QdrantAdapter
        
        # Get method signature
        sig = inspect.signature(QdrantAdapter.search_code_examples)
        params = list(sig.parameters.keys())
        
        print(f"search_code_examples parameters: {params}")
        
        # Check for the specific parameter that was causing the error
        if 'filter_metadata' in params:
            print("✅ PASS: search_code_examples has 'filter_metadata' parameter")
            
            # Also check it's not using the old incorrect parameter name
            if 'source_id' in params:
                print("⚠️  WARNING: Method also has 'source_id' parameter (legacy?)")
            
            return True
        else:
            print("❌ FAIL: search_code_examples missing 'filter_metadata' parameter")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error: {e}")
        return False

def test_no_unexpected_parameter_error():
    """Test that we can call search_code_examples with filter_metadata without TypeError"""
    print("\n=== Testing method call with filter_metadata ===")
    
    try:
        from database.qdrant_adapter import QdrantAdapter
        
        # Get the method
        method = QdrantAdapter.search_code_examples
        sig = inspect.signature(method)
        
        # Try to create a bound arguments object with filter_metadata
        # This would fail if the parameter doesn't exist
        test_args = {
            'query': 'test query',
            'match_count': 5,
            'filter_metadata': {'source': 'test'},
            'source_filter': None,
            'query_embedding': None
        }
        
        bound_args = sig.bind_partial(**test_args)  # bind_partial allows self to be missing
        print(f"✅ PASS: Successfully bound arguments: {list(bound_args.arguments.keys())}")
        
        return True
        
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            print(f"❌ FAIL: Still getting unexpected keyword argument error: {e}")
        else:
            print(f"❌ FAIL: Other TypeError: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False

def main():
    """Run validation tests"""
    print("Parameter Fix Validation Test")
    print("=" * 40)
    print("Testing fix for: QdrantAdapter.search_code_examples() got an unexpected keyword argument 'filter_metadata'")
    print()
    
    test1_result = test_search_code_examples_parameter()
    test2_result = test_no_unexpected_parameter_error()
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    
    if test1_result and test2_result:
        print("✅ PASS: Parameter fix validation successful")
        print("The error 'unexpected keyword argument filter_metadata' should be resolved")
        return True
    else:
        print("❌ FAIL: Parameter fix validation failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)