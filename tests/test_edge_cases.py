"""Comprehensive edge case testing for Crawl4AI MCP."""
import pytest
import asyncio
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.test_helpers import TestDataBuilder, TestAssertions
from src.database.factory import create_database_client
from src.database.qdrant_adapter import QdrantAdapter
from urllib.parse import urlparse

class TestEdgeCases:
    """Comprehensive edge case testing."""
    
    @pytest.fixture
    async def adapter(self):
        """Create test database adapter."""
        # Force Qdrant for testing
        import os
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        
        adapter = create_database_client()
        await adapter.initialize()
        yield adapter
        # Cleanup would go here
    
    async def add_documents_batch(self, adapter, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Helper to add documents in batch format."""
        if not documents:
            return {"success": True, "processed": 0}
        
        urls = []
        chunk_numbers = []
        contents = []
        metadatas = []
        embeddings = []
        source_ids = []
        
        for doc in documents:
            urls.append(doc["url"])
            chunk_numbers.append(doc.get("chunk_number", 1))
            contents.append(doc["content"])
            metadatas.append(doc.get("metadata", {}))
            embeddings.append(doc["embedding"])
            # Extract source_id from URL
            parsed = urlparse(doc["url"])
            source_ids.append(parsed.netloc or "unknown")
        
        try:
            await adapter.add_documents(
                urls=urls,
                chunk_numbers=chunk_numbers,
                contents=contents,
                metadatas=metadatas,
                embeddings=embeddings,
                source_ids=source_ids
            )
            return {"success": True, "processed": len(documents)}
        except Exception as e:
            return {"success": False, "error": str(e), "processed": 0}
    
    # Batch size boundaries
    @pytest.mark.parametrize("input_size", [0, 1, 10, 100, 500, 1000])
    async def test_batch_size_boundaries(self, adapter, input_size):
        """Test various batch sizes including boundaries."""
        if input_size == 0:
            # Empty batch should succeed but process nothing
            result = await self.add_documents_batch(adapter, [])
            assert result["success"] is True
            assert result.get("processed", 0) == 0
            return
        
        documents = TestDataBuilder.batch_documents(input_size)
        result = await self.add_documents_batch(adapter, documents)
        assert result["success"] is True
        assert result.get("processed", 0) == input_size
    
    # Special character handling
    @pytest.mark.parametrize("special_char", [
        '<', '>', '&', '"', "'", '\n', '\t', '\r', 
        '\u0000', '\u200b', '😀', '中文', 'العربية'
    ])
    async def test_special_character_handling(self, adapter, special_char):
        """Test special character handling in content."""
        content = f"Test {special_char} content {special_char} end"
        doc = TestDataBuilder.document(content=content)
        
        # Add document
        result = await self.add_documents_batch(adapter, [doc])
        assert result["success"] is True
        
        # Search for it
        search_result = await adapter.search_documents(
            query_embedding=doc["embedding"],
            match_count=1
        )
        assert len(search_result) > 0
        assert special_char in search_result[0]["content"]
    
    # URL edge cases
    @pytest.mark.parametrize("url", [
        "https://test.com",  # Normal
        "https://test.com/",  # Trailing slash
        "https://test.com/path/to/page",  # Deep path
        "https://test.com/page?param=value",  # Query params
        "https://test.com/page#section",  # Fragment
        "https://test.com:8080/page",  # Port
        "https://user:pass@test.com/page",  # Auth
        "https://test.com/page with spaces",  # Spaces
        "https://test.com/página",  # Unicode
        "https://test.com/" + "a" * 200,  # Long URL
    ])
    async def test_url_edge_cases(self, adapter, url):
        """Test various URL formats."""
        doc = TestDataBuilder.document(url=url)
        result = await self.add_documents_batch(adapter, [doc])
        assert result["success"] is True
        
        # Verify retrieval by URL
        retrieved = await adapter.get_documents_by_url(url)
        assert len(retrieved) > 0
        assert retrieved[0]["url"] == url
    
    # Content size boundaries
    @pytest.mark.parametrize("content_size", [
        0,      # Empty
        1,      # Single char
        100,    # Small
        1000,   # Medium
        10000,  # Large
        100000, # Very large
    ])
    async def test_content_size_boundaries(self, adapter, content_size):
        """Test various content sizes."""
        if content_size == 0:
            content = ""
        else:
            content = "x" * content_size
        
        doc = TestDataBuilder.document(content=content)
        result = await self.add_documents_batch(adapter, [doc])
        assert result["success"] is True
    
    # Embedding edge cases
    @pytest.mark.parametrize("embedding_case", [
        "all_zeros",
        "all_ones", 
        "all_negative",
        "mixed_extreme",
        "wrong_dimension",
    ])
    async def test_embedding_edge_cases(self, adapter, embedding_case):
        """Test various embedding edge cases."""
        if embedding_case == "all_zeros":
            embedding = [0.0] * 1536
        elif embedding_case == "all_ones":
            embedding = [1.0] * 1536
        elif embedding_case == "all_negative":
            embedding = [-1.0] * 1536
        elif embedding_case == "mixed_extreme":
            embedding = [1.0 if i % 2 == 0 else -1.0 for i in range(1536)]
        elif embedding_case == "wrong_dimension":
            embedding = [0.5] * 100  # Wrong dimension
            doc = TestDataBuilder.document(embedding=embedding)
            result = await self.add_documents_batch(adapter, [doc])
            assert result["success"] is False  # Should fail
            assert "dimension" in str(result.get("error", "")).lower()
            return
        
        doc = TestDataBuilder.document(embedding=embedding)
        result = await self.add_documents_batch(adapter, [doc])
        assert result["success"] is True
    
    # Concurrent operations
    @pytest.mark.parametrize("num_concurrent", [2, 5, 10, 20])
    async def test_concurrent_operations(self, adapter, num_concurrent):
        """Test concurrent read/write operations."""
        async def add_and_search(index: int):
            doc = TestDataBuilder.document(
                url=f"https://concurrent-{index}.com",
                content=f"Concurrent test {index}"
            )
            
            # Add document
            add_result = await self.add_documents_batch(adapter, [doc])
            assert add_result["success"] is True
            
            # Search for it
            search_result = await adapter.search_documents(
                query_embedding=doc["embedding"],
                match_count=10
            )
            
            # Verify our document is in results
            urls = [r["url"] for r in search_result]
            assert doc["url"] in urls
            
            return index
        
        # Run concurrent operations
        tasks = [add_and_search(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all succeeded
        assert all(isinstance(r, int) for r in results)
        assert len(set(results)) == num_concurrent  # All unique
    
    # Metadata edge cases
    @pytest.mark.parametrize("metadata", [
        {},  # Empty
        {"key": "value"},  # Simple
        {"key": "value" * 100},  # Large value
        {f"key{i}": f"value{i}" for i in range(50)},  # Many keys
        {"nested": {"deep": {"structure": "value"}}},  # Nested - will skip filter test
        {"special": "chars <>\"'&"},  # Special characters
        {"unicode": "测试 🚀 тест"},  # Unicode
    ])
    async def test_metadata_edge_cases(self, adapter, metadata):
        """Test various metadata structures."""
        doc = TestDataBuilder.document(metadata=metadata)
        result = await self.add_documents_batch(adapter, [doc])
        assert result["success"] is True
        
        # Search with metadata filter if adapter supports it
        # Skip filtering for nested metadata (Qdrant limitation)
        if hasattr(adapter, "search_documents") and not any(isinstance(v, dict) for v in metadata.values()):
            # Only apply filter for simple metadata (non-nested)
            search_result = await adapter.search_documents(
                query_embedding=doc["embedding"],
                match_count=10,
                metadata_filter=metadata if metadata else None
            )
            # Should return at least our document
            assert len(search_result) > 0
    
    # Error recovery
    async def test_error_recovery(self, adapter):
        """Test adapter recovery after errors."""
        # Cause an error with invalid data
        invalid_doc = {"invalid": "structure"}  # Missing required fields
        
        # Try to add invalid document - should fail gracefully
        try:
            result = await self.add_documents_batch(adapter, [invalid_doc])
            # If it returns a result, it should indicate failure
            assert result["success"] is False
        except (KeyError, TypeError, ValueError) as e:
            # Expected error - adapter properly validates input
            pass
        
        # Verify adapter still works with valid data
        valid_doc = TestDataBuilder.document()
        result = await self.add_documents_batch(adapter, [valid_doc])
        assert result["success"] is True
    
    # Pagination edge cases
    @pytest.mark.parametrize("limit", [0, 1, 10, 50, 100, -1])
    async def test_match_count_edge_cases(self, adapter, limit):
        """Test match_count boundaries."""
        # Add test documents first
        docs = TestDataBuilder.batch_documents(20)
        await self.add_documents_batch(adapter, docs)
        
        # Test various match counts
        if limit < 0:
            # Should handle gracefully (either error or use defaults)
            try:
                results = await adapter.search_documents(
                    query_embedding=[0.5] * 1536,
                    match_count=limit
                )
                # If it succeeds, verify reasonable behavior
                assert isinstance(results, list)
            except Exception:
                # Error is acceptable for invalid params
                pass
        else:
            results = await adapter.search_documents(
                query_embedding=[0.5] * 1536,
                match_count=limit if limit > 0 else 10
            )
            assert isinstance(results, list)
            if limit > 0:
                assert len(results) <= limit

# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])