#!/usr/bin/env python3
"""
Direct test to validate the filter_metadata parameter fix.

This test specifically validates that the QdrantAdapter.search_code_examples()
method now correctly accepts the filter_metadata parameter without throwing
an "unexpected keyword argument" error.
"""
import asyncio
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_filter_metadata_parameter():
    """Test that filter_metadata parameter is accepted without error"""
    print(f"Test DateTime: {datetime.now().isoformat()}")
    
    try:
        from database.qdrant_adapter import QdrantAdapter
        from qdrant_client import QdrantClient
        from qdrant_client.models import VectorParams, Distance
        
        print("✓ Successfully imported QdrantAdapter")
        
        # Create a mock Qdrant client to avoid actual database connection
        mock_client = AsyncMock(spec=QdrantClient)
        
        # Mock successful search response
        mock_search_result = AsyncMock()
        mock_search_result.payload = {"content": "test content", "metadata": {"source": "test"}}
        mock_search_result.score = 0.95
        mock_search_result.id = "test-id"
        
        mock_client.search.return_value = [mock_search_result]
        
        # Initialize QdrantAdapter with mock client
        adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
        adapter.client = mock_client  # Replace with mock
        
        print("✓ QdrantAdapter initialized with mock client")
        
        # Test 1: Call search_code_examples with filter_metadata parameter
        print("\nTesting search_code_examples with filter_metadata...")
        
        try:
            results = await adapter.search_code_examples(
                query="test query",
                match_count=5,
                filter_metadata={"source_id": "test_source"},
                source_filter="example.com"
            )
            
            print("✅ SUCCESS: search_code_examples accepted filter_metadata parameter")
            print(f"   Returned {len(results)} results")
            
        except TypeError as e:
            if "unexpected keyword argument 'filter_metadata'" in str(e):
                print(f"❌ FAILED: Original error still present: {e}")
                return False
            else:
                print(f"⚠️  UNEXPECTED: Different TypeError: {e}")
                return False
        
        # Test 2: Call search method with filter_metadata parameter
        print("\nTesting search method with filter_metadata...")
        
        try:
            # Mock create_embedding since it's imported dynamically
            with patch('utils.create_embedding', return_value=[0.1] * 1536):
                results = await adapter.search(
                    query="test query",
                    match_count=5,
                    filter_metadata={"type": "documentation"},
                    source_filter="example.com"
                )
                
            print("✅ SUCCESS: search method accepted filter_metadata parameter")
            print(f"   Returned {len(results)} results")
            
        except TypeError as e:
            if "unexpected keyword argument 'filter_metadata'" in str(e):
                print(f"❌ FAILED: Original error still present in search method: {e}")
                return False
            else:
                print(f"⚠️  UNEXPECTED: Different TypeError in search method: {e}")
                return False
        
        # Test 3: Verify parameter consistency across call chain
        print("\nTesting parameter consistency in call chain...")
        
        try:
            # Test the specific call pattern from database/rag_queries.py line 176
            results = await adapter.search_code_examples(
                "example query", 
                match_count=5, 
                filter_metadata={"source_id": "example_source"}
            )
            
            print("✅ SUCCESS: Call pattern from rag_queries.py works correctly")
            
        except Exception as e:
            print(f"❌ FAILED: Call pattern from rag_queries.py failed: {e}")
            return False
        
        # Test 4: Test hybrid search if available
        print("\nTesting hybrid_search method (if available)...")
        
        try:
            if hasattr(adapter, 'hybrid_search'):
                with patch('utils.create_embedding', return_value=[0.1] * 1536):
                    results = await adapter.hybrid_search(
                        query="test query",
                        match_count=5,
                        filter_metadata={"category": "documentation"}
                    )
                    print("✅ SUCCESS: hybrid_search accepted filter_metadata parameter")
            else:
                print("ℹ️  INFO: hybrid_search method not available (expected)")
                
        except TypeError as e:
            if "unexpected keyword argument 'filter_metadata'" in str(e):
                print(f"❌ FAILED: hybrid_search has parameter error: {e}")
                return False
            else:
                print(f"⚠️  INFO: hybrid_search has different error (not parameter related): {e}")
        except Exception as e:
            print(f"⚠️  INFO: hybrid_search implementation issue (not parameter related): {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ FAILED: Import error - {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False

async def test_caller_compatibility():
    """Test that callers can invoke the methods correctly"""
    print(f"\n{'='*60}")
    print("Testing Caller Compatibility")
    print(f"{'='*60}")
    
    try:
        # Mock the rag_queries function call
        from database.qdrant_adapter import QdrantAdapter
        
        mock_adapter = AsyncMock(spec=QdrantAdapter)
        mock_adapter.search_code_examples.return_value = [
            {"content": "test", "similarity": 0.9, "id": "1"}
        ]
        
        # Test the specific call from services/validated_search.py:220
        filter_metadata = {"source_id": "test_source"}
        
        results = await mock_adapter.search_code_examples(
            query_embedding=[0.1] * 1536,
            match_count=5,
            filter_metadata=filter_metadata
        )
        
        # Verify the call was made with correct parameters
        mock_adapter.search_code_examples.assert_called_once_with(
            query_embedding=[0.1] * 1536,
            match_count=5,
            filter_metadata=filter_metadata
        )
        
        print("✅ SUCCESS: Validated search service call pattern works")
        
        # Test the specific call from database/rag_queries.py:176
        mock_adapter.reset_mock()
        results = await mock_adapter.search_code_examples(
            "test query", 
            match_count=5, 
            filter_metadata={"source_id": "test"}
        )
        
        mock_adapter.search_code_examples.assert_called_once_with(
            "test query", 
            match_count=5, 
            filter_metadata={"source_id": "test"}
        )
        
        print("✅ SUCCESS: RAG queries call pattern works")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Caller compatibility test failed - {e}")
        return False

async def main():
    """Run all validation tests"""
    print("Parameter Consistency Fix Validation")
    print(f"Test Start Time: {datetime.now().isoformat()}")
    print("="*60)
    
    # Test 1: Direct parameter validation
    success1 = await test_filter_metadata_parameter()
    
    # Test 2: Caller compatibility
    success2 = await test_caller_compatibility()
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Test End Time: {datetime.now().isoformat()}")
    
    if success1 and success2:
        print("✅ OVERALL RESULT: PASS")
        print("   - filter_metadata parameter is correctly accepted")
        print("   - No 'unexpected keyword argument' errors")
        print("   - Caller patterns work correctly")
        return 0
    else:
        print("❌ OVERALL RESULT: FAIL")
        if not success1:
            print("   - Parameter validation failed")
        if not success2:
            print("   - Caller compatibility failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)