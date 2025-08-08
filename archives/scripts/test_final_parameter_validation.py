#!/usr/bin/env python3
"""Final validation test for parameter name consistency fixes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_parameter_signatures():
    """Test that all methods accept filter_metadata parameter."""
    print("Testing parameter name consistency fixes...")
    
    try:
        from src.database.qdrant_adapter import QdrantAdapter
        import inspect
        
        # Check QdrantAdapter methods
        methods_to_check = [
            ('search_code_examples', QdrantAdapter.search_code_examples),
            ('search', QdrantAdapter.search),
            ('hybrid_search', QdrantAdapter.hybrid_search),
            ('search_documents', QdrantAdapter.search_documents),
        ]
        
        all_pass = True
        for method_name, method in methods_to_check:
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            if 'filter_metadata' in params:
                print(f"✅ {method_name}: Uses correct parameter 'filter_metadata'")
            elif 'metadata_filter' in params:
                print(f"❌ {method_name}: Still uses incorrect parameter 'metadata_filter'")
                all_pass = False
            else:
                print(f"ℹ️ {method_name}: No filter parameter")
        
        if all_pass:
            print("\n✅ All methods use consistent parameter naming!")
            return True
        else:
            print("\n❌ Some methods still have inconsistent parameter names")
            return False
            
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False

if __name__ == "__main__":
    success = test_parameter_signatures()
    sys.exit(0 if success else 1)