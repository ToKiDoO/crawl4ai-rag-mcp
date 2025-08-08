#!/usr/bin/env python3
"""
Integration Parameter Validation Test
====================================
Test DateTime: 2025-08-07 17:41:23 BST

Purpose: Verify the complete calling chain from rag_queries to QdrantAdapter works correctly.
"""

import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.rag_queries import search_code_examples
from database.qdrant_adapter import QdrantAdapter


async def test_integration_call_chain():
    """Test that the complete call chain works without parameter errors."""
    print("=== Integration Parameter Validation Test ===")
    print(f"Test DateTime: 2025-08-07 17:41:23 BST")
    print()
    
    # Test 1: Mock QdrantAdapter to verify the call pattern
    print("Test 1: Call Chain Parameter Validation")
    print("Input: Calling search_code_examples through rag_queries with mock adapter")
    
    # Create a mock adapter that tracks method calls
    mock_adapter = MagicMock()
    mock_adapter.search_code_examples = MagicMock()
    mock_adapter.search_code_examples.return_value = []
    
    # Set environment to enable code example extraction
    with patch.dict(os.environ, {'USE_AGENTIC_RAG': 'true'}):
        try:
            # Call through the rag_queries function
            result = await search_code_examples(
                database_client=mock_adapter,
                query="test query",
                source_id="test.com",
                match_count=5
            )
            
            # Verify the call was made
            assert mock_adapter.search_code_examples.called
            call_args = mock_adapter.search_code_examples.call_args
            
            print(f"Observed Result: Method called with args: {call_args}")
            
            # Verify the correct parameter name was used
            kwargs = call_args.kwargs if call_args else {}
            has_filter_metadata = 'filter_metadata' in kwargs
            
            print(f"Expected Result: 'filter_metadata' parameter should be in kwargs")
            print(f"Outcome: {'✅ PASS' if has_filter_metadata else '❌ FAIL'}")
            
            # Verify the parameter value is correct
            if has_filter_metadata:
                filter_value = kwargs.get('filter_metadata')
                expected_filter = {'source_id': 'test.com'}
                filter_correct = filter_value == expected_filter
                
                print(f"Filter value verification:")
                print(f"  Observed: {filter_value}")
                print(f"  Expected: {expected_filter}")
                print(f"  Outcome: {'✅ PASS' if filter_correct else '❌ FAIL'}")
            else:
                filter_correct = False
            
            test1_pass = has_filter_metadata and filter_correct
            
        except Exception as e:
            print(f"Observed Result: Exception occurred: {e}")
            print(f"Expected Result: No parameter-related exceptions")
            print(f"Outcome: ❌ FAIL - {type(e).__name__}: {e}")
            test1_pass = False
    
    # Test 2: Verify that actual QdrantAdapter would accept the call
    print()
    print("Test 2: Real Adapter Parameter Acceptance")
    print("Input: Testing QdrantAdapter parameter acceptance")
    
    adapter = QdrantAdapter()
    
    try:
        # This will fail at runtime (no connection) but should not fail on parameters
        await adapter.search_code_examples(
            query="test",
            match_count=5, 
            filter_metadata={"source_id": "test"},
            source_filter="test"
        )
        test2_pass = True
        outcome = "✅ PASS - No parameter error"
    except TypeError as e:
        if "unexpected keyword argument" in str(e):
            test2_pass = False
            outcome = f"❌ FAIL - Parameter error: {e}"
        else:
            test2_pass = True 
            outcome = f"✅ PASS - No parameter error (other TypeError: {e})"
    except Exception as e:
        test2_pass = True
        outcome = f"✅ PASS - No parameter error (runtime error expected: {type(e).__name__})"
    
    print(f"Observed Result: Method call attempt completed")
    print(f"Expected Result: No 'unexpected keyword argument' error")  
    print(f"Outcome: {outcome}")
    
    # Summary
    print()
    print("=== INTEGRATION VALIDATION SUMMARY ===")
    all_tests_passed = test1_pass and test2_pass
    
    if all_tests_passed:
        print("🎯 OVERALL VERDICT: ✅ PASS")
        print("✓ rag_queries calls QdrantAdapter with correct parameter names")
        print("✓ QdrantAdapter accepts filter_metadata parameter correctly")
        print("✓ The original error would NOT occur in production")
    else:
        print("🎯 OVERALL VERDICT: ❌ FAIL")
        print("Parameter name fixes need additional work")
    
    print(f"Timestamp: 2025-08-07T17:41:23+01:00")
    
    return all_tests_passed


if __name__ == "__main__":
    result = asyncio.run(test_integration_call_chain())
    sys.exit(0 if result else 1)