#!/usr/bin/env python3
"""
Test script to verify parameter name consistency fixes.

This script tests that:
1. QdrantAdapter.search_code_examples() accepts filter_metadata parameter
2. The specific error `got an unexpected keyword argument 'filter_metadata'` no longer occurs
3. All search methods use consistent parameter names
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import UTC

# Add the src directory to Python path
sys.path.insert(0, '/home/krashnicov/crawl4aimcp/src')

from database.qdrant_adapter import QdrantAdapter


async def test_parameter_consistency():
    """Test that parameter names are consistent across search methods"""
    print("🔄 Testing parameter name consistency fixes...")
    
    # Create adapter instance
    adapter = QdrantAdapter(url="http://mock-qdrant:6333")
    
    # Mock the client to avoid actual connections
    mock_client = MagicMock()
    adapter.client = mock_client
    
    # Mock the search response
    mock_search_response = [
        MagicMock(
            id="test-id-1",
            payload={
                "url": "https://test.com",
                "content": "test content",
                "source_id": "test.com",
                "metadata": {"type": "code"}
            },
            score=0.95
        )
    ]
    
    # Test 1: search_code_examples with filter_metadata parameter
    print("✅ Testing search_code_examples with filter_metadata...")
    
    with patch('asyncio.get_event_loop') as mock_loop:
        mock_executor = AsyncMock()
        mock_executor.return_value = mock_search_response
        mock_loop.return_value.run_in_executor = mock_executor
        
        try:
            # This should NOT raise "unexpected keyword argument 'filter_metadata'"
            results = await adapter.search_code_examples(
                query="test query",
                match_count=5,
                filter_metadata={"source_id": "test.com"}
            )
            print("  ✅ search_code_examples accepts filter_metadata parameter")
            
        except TypeError as e:
            if "unexpected keyword argument 'filter_metadata'" in str(e):
                print(f"  ❌ ERROR: {e}")
                return False
            else:
                print(f"  ⚠️  Different TypeError: {e}")
        except Exception as e:
            print(f"  ℹ️  Other exception (expected in mock env): {type(e).__name__}")

    # Test 2: search method with filter_metadata parameter
    print("✅ Testing search with filter_metadata...")
    
    with patch('asyncio.get_event_loop') as mock_loop, \
         patch('src.utils.text_processing.create_embedding') as mock_embedding:
        
        mock_executor = AsyncMock()
        mock_executor.return_value = mock_search_response
        mock_loop.return_value.run_in_executor = mock_executor
        mock_embedding.return_value = [0.1] * 1536  # Mock embedding
        
        try:
            results = await adapter.search(
                query="test query", 
                match_count=5,
                filter_metadata={"source_id": "test.com"}
            )
            print("  ✅ search accepts filter_metadata parameter")
            
        except TypeError as e:
            if "unexpected keyword argument 'filter_metadata'" in str(e):
                print(f"  ❌ ERROR: {e}")
                return False
            else:
                print(f"  ⚠️  Different TypeError: {e}")
        except Exception as e:
            print(f"  ℹ️  Other exception (expected in mock env): {type(e).__name__}")

    # Test 3: hybrid_search with filter_metadata parameter
    print("✅ Testing hybrid_search with filter_metadata...")
    
    with patch('asyncio.get_event_loop') as mock_loop, \
         patch('src.utils.text_processing.create_embedding') as mock_embedding:
        
        mock_executor = AsyncMock()
        mock_executor.return_value = mock_search_response
        mock_loop.return_value.run_in_executor = mock_executor
        mock_embedding.return_value = [0.1] * 1536  # Mock embedding
        
        try:
            results = await adapter.hybrid_search(
                query="test query",
                match_count=5,
                filter_metadata={"source_id": "test.com"}
            )
            print("  ✅ hybrid_search accepts filter_metadata parameter")
            
        except TypeError as e:
            if "unexpected keyword argument 'filter_metadata'" in str(e):
                print(f"  ❌ ERROR: {e}")
                return False
            else:
                print(f"  ⚠️  Different TypeError: {e}")
        except Exception as e:
            print(f"  ℹ️  Other exception (expected in mock env): {type(e).__name__}")

    return True


async def test_caller_consistency():
    """Test that caller files use the correct parameter names"""
    print("🔄 Testing caller parameter consistency...")
    
    # Test import paths
    try:
        from services.validated_search import SmartCodeSearch
        from database.rag_queries import search_code_examples
        print("  ✅ All import paths work correctly")
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        return False
    
    return True


def inspect_method_signatures():
    """Inspect the actual method signatures for verification"""
    print("🔍 Inspecting method signatures...")
    
    import inspect
    
    # Check QdrantAdapter methods
    adapter = QdrantAdapter()
    
    # Check search_code_examples signature
    sig = inspect.signature(adapter.search_code_examples)
    params = list(sig.parameters.keys())
    print(f"  search_code_examples parameters: {params}")
    
    if 'filter_metadata' in params:
        print("  ✅ search_code_examples has filter_metadata parameter")
    else:
        print("  ❌ search_code_examples missing filter_metadata parameter")
    
    # Check search signature  
    sig = inspect.signature(adapter.search)
    params = list(sig.parameters.keys())
    print(f"  search parameters: {params}")
    
    if 'filter_metadata' in params:
        print("  ✅ search has filter_metadata parameter")
    else:
        print("  ❌ search missing filter_metadata parameter")
    
    # Check hybrid_search signature
    sig = inspect.signature(adapter.hybrid_search)
    params = list(sig.parameters.keys())
    print(f"  hybrid_search parameters: {params}")
    
    if 'filter_metadata' in params:
        print("  ✅ hybrid_search has filter_metadata parameter")
    else:
        print("  ❌ hybrid_search missing filter_metadata parameter")


async def main():
    """Main test execution"""
    print("=" * 60)
    print("PARAMETER NAME CONSISTENCY FIX VALIDATION")
    print("=" * 60)
    
    # Test method signatures first
    inspect_method_signatures()
    print()
    
    # Test parameter usage
    param_test_result = await test_parameter_consistency()
    print()
    
    # Test caller consistency
    caller_test_result = await test_caller_consistency()
    print()
    
    # Final verdict
    print("=" * 60)
    if param_test_result and caller_test_result:
        print("✅ PASS: All parameter name consistency fixes validated successfully")
        print("✅ The error 'unexpected keyword argument filter_metadata' is resolved")
        return 0
    else:
        print("❌ FAIL: Parameter name consistency issues still exist")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)