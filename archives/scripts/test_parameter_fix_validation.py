#!/usr/bin/env python3
"""
Test DateTime: Thu Aug  7 17:07:59 BST 2025
Test to validate the parameter name consistency fix for QdrantAdapter methods.
This test specifically verifies that the error:
'QdrantAdapter.search_code_examples() got an unexpected keyword argument 'filter_metadata''
has been resolved.
"""

import sys
import os
import asyncio
import inspect

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_parameter_signatures():
    """Test that QdrantAdapter methods have consistent parameter names"""
    print("=== PARAMETER SIGNATURE VALIDATION ===")
    
    try:
        from database.qdrant_adapter import QdrantAdapter
        
        # Get method signatures
        search_sig = inspect.signature(QdrantAdapter.search)
        search_code_examples_sig = inspect.signature(QdrantAdapter.search_code_examples)
        hybrid_search_sig = inspect.signature(QdrantAdapter.hybrid_search)
        
        print(f"search method parameters: {list(search_sig.parameters.keys())}")
        print(f"search_code_examples method parameters: {list(search_code_examples_sig.parameters.keys())}")
        print(f"hybrid_search method parameters: {list(hybrid_search_sig.parameters.keys())}")
        
        # Check for filter_metadata parameter
        search_has_filter_metadata = 'filter_metadata' in search_sig.parameters
        search_code_examples_has_filter_metadata = 'filter_metadata' in search_code_examples_sig.parameters
        hybrid_search_has_filter_metadata = 'filter_metadata' in hybrid_search_sig.parameters
        
        print(f"\nsearch has 'filter_metadata': {search_has_filter_metadata}")
        print(f"search_code_examples has 'filter_metadata': {search_code_examples_has_filter_metadata}")
        print(f"hybrid_search has 'filter_metadata': {hybrid_search_has_filter_metadata}")
        
        # Verify all methods have consistent parameter naming
        if search_has_filter_metadata and search_code_examples_has_filter_metadata and hybrid_search_has_filter_metadata:
            print("✅ PASS: All methods have consistent 'filter_metadata' parameter")
            return True
        else:
            print("❌ FAIL: Inconsistent parameter naming across methods")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error during signature validation: {e}")
        return False

def test_method_call_compatibility():
    """Test that methods can be called with filter_metadata parameter"""
    print("\n=== METHOD CALL COMPATIBILITY TEST ===")
    
    try:
        from database.qdrant_adapter import QdrantAdapter
        
        # Create a mock adapter (we don't need real Qdrant connection for this test)
        class MockQdrantAdapter(QdrantAdapter):
            def __init__(self):
                # Don't call super().__init__ to avoid Qdrant client creation
                self.CRAWLED_PAGES = "test_collection"
                self.CODE_EXAMPLES = "test_code_collection"
                pass
                
            async def _get_or_create_embedding(self, text):
                # Mock embedding
                return [0.1] * 384
        
        adapter = MockQdrantAdapter()
        
        # Test that methods accept filter_metadata without raising TypeError
        try:
            # We just check if the methods accept the parameter without execution
            search_sig = inspect.signature(adapter.search)
            search_code_examples_sig = inspect.signature(adapter.search_code_examples)
            hybrid_search_sig = inspect.signature(adapter.hybrid_search)
            
            # Try to bind parameters - this will raise TypeError if parameter doesn't exist
            search_sig.bind(
                adapter, query="test", match_count=5, filter_metadata={"source": "test"}
            )
            print("✅ search method accepts filter_metadata parameter")
            
            search_code_examples_sig.bind(
                adapter, query="test", match_count=5, filter_metadata={"source": "test"}
            )
            print("✅ search_code_examples method accepts filter_metadata parameter")
            
            hybrid_search_sig.bind(
                adapter, query="test", match_count=5, filter_metadata={"source": "test"}
            )
            print("✅ hybrid_search method accepts filter_metadata parameter")
            
            print("✅ PASS: All methods accept filter_metadata parameter correctly")
            return True
            
        except TypeError as e:
            print(f"❌ FAIL: Parameter binding error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error during compatibility test: {e}")
        return False

def test_caller_imports():
    """Test that caller modules can import and use the fixed methods"""
    print("\n=== CALLER IMPORT TEST ===")
    
    try:
        # Test importing validated_search service
        from services.validated_search import ValidatedCodeSearchService
        print("✅ ValidatedCodeSearchService imports successfully")
        
        # Test importing rag_queries
        from database.rag_queries import search_code_examples
        print("✅ rag_queries.search_code_examples imports successfully")
        
        print("✅ PASS: Caller modules import successfully")
        return True
        
    except ImportError as e:
        print(f"❌ FAIL: Import error in caller modules: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("Parameter Name Consistency Fix Validation")
    print("=" * 50)
    print(f"Test DateTime: Thu Aug  7 17:07:59 BST 2025")
    print(f"Environment: {os.getcwd()}")
    print()
    
    tests = [
        test_parameter_signatures,
        test_method_call_compatibility,
        test_caller_imports,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("FINAL TEST RESULTS:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("✅ OVERALL VERDICT: PASS - Parameter fix validation successful")
        return True
    else:
        print("❌ OVERALL VERDICT: FAIL - Parameter fix validation failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)