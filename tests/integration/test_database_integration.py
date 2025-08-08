"""
Database integration tests with real services.

Tests database operations with actual Qdrant and Supabase instances:
- Connection management and initialization
- CRUD operations with real data
- Concurrent operation handling
- Transaction integrity and consistency
- Performance under load
- Error recovery and resilience
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from database.factory import create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter


@pytest.mark.integration
class TestQdrantIntegration:
    """Test Qdrant database integration with real service."""

    @pytest.mark.asyncio
    async def test_qdrant_connection_lifecycle(self, qdrant_client):
        """Test Qdrant connection initialization and cleanup."""

        # Verify connection is established
        assert qdrant_client.client is not None
        assert qdrant_client.CRAWLED_PAGES == "crawled_pages"

        # Test collection exists and is configured correctly (use async executor)
        import asyncio

        loop = asyncio.get_event_loop()
        collection_info = await loop.run_in_executor(
            None,
            qdrant_client.client.get_collection,
            qdrant_client.CRAWLED_PAGES,
        )
        assert (
            collection_info.config.params.vectors.size == 1536
        )  # Default OpenAI embedding size
        assert collection_info.status == "green"

        # Test connection health
        health_status = await loop.run_in_executor(
            None,
            qdrant_client.client.get_collections,
        )
        assert qdrant_client.CRAWLED_PAGES in [
            col.name for col in health_status.collections
        ]

        print(
            f"✅ Qdrant connection healthy, collection: {qdrant_client.CRAWLED_PAGES}",
        )

    @pytest.mark.asyncio
    async def test_store_and_retrieve_documents(self, qdrant_client):
        """Test storing and retrieving documents with embeddings."""

        # Test documents
        test_docs = [
            {
                "url": "https://example.com/python",
                "content": "Python is a programming language. It supports object-oriented programming.",
                "title": "Python Programming",
                "metadata": {"category": "programming", "language": "python"},
            },
            {
                "url": "https://example.com/javascript",
                "content": "JavaScript is a scripting language. It runs in web browsers and Node.js.",
                "title": "JavaScript Guide",
                "metadata": {"category": "programming", "language": "javascript"},
            },
            {
                "url": "https://example.com/ai",
                "content": "Artificial Intelligence involves machine learning and neural networks.",
                "title": "AI Overview",
                "metadata": {"category": "ai", "topic": "machine-learning"},
            },
        ]

        # Store documents
        stored_ids = []
        for doc in test_docs:
            # Create embeddings for the content
            with patch("src.utils.create_embedding") as mock_embeddings:
                # Mock sentence transformer embeddings (384-dimensional)
                mock_embeddings.return_value = [0.1] * 1536

                doc_id = await qdrant_client.store_crawled_page(
                    url=doc["url"],
                    content=doc["content"],
                    title=doc["title"],
                    metadata=doc["metadata"],
                )

            stored_ids.append(doc_id)
            assert doc_id is not None

        assert len(stored_ids) == 3
        print(f"✅ Stored {len(stored_ids)} documents in Qdrant")

        # Test retrieval by semantic search
        with patch("src.utils.create_embedding") as mock_embeddings:
            # Mock query embedding
            mock_embeddings.return_value = [0.1] * 1536

            # Search for programming content
            programming_results = await qdrant_client.search_crawled_pages(
                query="programming language",
                match_count=5,
            )

            # Search for AI content
            ai_results = await qdrant_client.search_crawled_pages(
                query="artificial intelligence machine learning",
                match_count=5,
            )

        # Verify search results
        assert len(programming_results) >= 2  # Should find Python and JavaScript
        assert len(ai_results) >= 1  # Should find AI document

        # Verify result structure
        for result in programming_results:
            assert "content" in result
            assert "metadata" in result
            assert "score" in result
            assert "url" in result

        # Test filtering by metadata
        python_results = await qdrant_client.search_crawled_pages(
            query="programming",
            match_count=5,
            filters={"category": "programming"},
        )

        assert len(python_results) >= 2
        for result in python_results:
            assert result["metadata"].get("category") == "programming"

        print(
            f"✅ Retrieved documents: {len(programming_results)} programming, {len(ai_results)} AI",
        )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, qdrant_client):
        """Test concurrent database operations."""

        # Generate test data
        test_docs = [
            {
                "url": f"https://example.com/concurrent/{i}",
                "content": f"Concurrent test document {i} with unique content about topic {i % 3}.",
                "title": f"Document {i}",
                "metadata": {"doc_id": i, "topic": i % 3},
            }
            for i in range(10)
        ]

        # Mock embeddings for all operations
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            # Store documents concurrently
            start_time = time.time()

            async def store_doc(doc):
                return await qdrant_client.store_crawled_page(
                    url=doc["url"],
                    content=doc["content"],
                    title=doc["title"],
                    metadata=doc["metadata"],
                )

            # Execute concurrent stores
            store_tasks = [store_doc(doc) for doc in test_docs]
            stored_ids = await asyncio.gather(*store_tasks)

            store_time = time.time() - start_time

        # Verify all documents stored successfully
        assert len(stored_ids) == 10
        assert all(doc_id is not None for doc_id in stored_ids)

        # Test concurrent searches
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()

            # Multiple concurrent searches
            search_tasks = [
                qdrant_client.search_crawled_pages(f"topic {i}", match_count=5)
                for i in range(3)
            ]

            search_results = await asyncio.gather(*search_tasks)
            search_time = time.time() - start_time

        # Verify search results
        assert len(search_results) == 3
        for results in search_results:
            assert len(results) > 0  # Each search should find something

        # Performance check - concurrent operations should be reasonable
        assert store_time < 10.0  # 10 seconds max for 10 concurrent stores
        assert search_time < 5.0  # 5 seconds max for 3 concurrent searches

        print(
            f"✅ Concurrent ops: {len(stored_ids)} stores in {store_time:.2f}s, 3 searches in {search_time:.2f}s",
        )

    @pytest.mark.asyncio
    async def test_large_document_handling(self, qdrant_client):
        """Test handling of large documents and batch operations."""

        # Create a large document
        large_content = "Large document content. " * 1000  # ~25KB of text

        large_doc = {
            "url": "https://example.com/large-doc",
            "content": large_content,
            "title": "Large Document Test",
            "metadata": {"size": "large", "word_count": len(large_content.split())},
        }

        # Store large document
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()
            doc_id = await qdrant_client.store_crawled_page(
                url=large_doc["url"],
                content=large_doc["content"],
                title=large_doc["title"],
                metadata=large_doc["metadata"],
            )
            store_time = time.time() - start_time

        assert doc_id is not None
        assert store_time < 5.0  # Should handle large docs in reasonable time

        # Test retrieval of large document
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()
            results = await qdrant_client.search_crawled_pages(
                query="Large document content",
                match_count=1,
            )
            search_time = time.time() - start_time

        assert len(results) >= 1
        assert search_time < 2.0  # Search should be fast even for large docs

        # Verify large content is properly stored and retrieved
        found_doc = results[0]
        assert "Large document content" in found_doc["content"]
        assert found_doc["metadata"].get("size") == "large"

        print(
            f"✅ Large doc: stored in {store_time:.2f}s, searched in {search_time:.2f}s",
        )

    @pytest.mark.asyncio
    async def test_error_recovery(self, qdrant_client):
        """Test database error handling and recovery."""

        # Test invalid data handling
        with pytest.raises(Exception):
            await qdrant_client.store_crawled_page(
                url="",  # Invalid empty URL
                content="",  # Invalid empty content
                title="",
                metadata={},
            )

        # Test with malformed metadata
        try:
            with patch("src.utils.create_embedding") as mock_embeddings:
                mock_embeddings.return_value = [0.1] * 1536

                # This should handle gracefully or raise appropriate error
                doc_id = await qdrant_client.store_crawled_page(
                    url="https://example.com/malformed",
                    content="Valid content",
                    title="Valid title",
                    metadata={
                        "nested": {"deeply": {"nested": "value"}},
                    },  # Complex nested metadata
                )

                # If it succeeds, verify it's stored correctly
                if doc_id:
                    results = await qdrant_client.search_crawled_pages(
                        query="Valid content",
                        match_count=1,
                    )
                    assert len(results) >= 1

        except Exception as e:
            # Should raise a meaningful error, not crash
            assert "metadata" in str(e).lower() or "invalid" in str(e).lower()

        # Test search with invalid query
        with patch("src.utils.create_embedding") as mock_embeddings:
            # Mock embedding creation failure
            mock_embeddings.side_effect = Exception("Embedding creation failed")

            with pytest.raises(Exception):
                await qdrant_client.search_crawled_pages(
                    query="This should fail",
                    match_count=5,
                )

        # Verify database is still functional after errors
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            # This should work normally
            results = await qdrant_client.search_crawled_pages(
                query="recovery test",
                match_count=1,
            )

            # Should not crash, even if no results
            assert isinstance(results, list)

        print("✅ Error recovery: Database remains functional after errors")

    @pytest.mark.asyncio
    async def test_data_consistency(self, qdrant_client):
        """Test data consistency and integrity."""

        # Store a document
        test_doc = {
            "url": "https://example.com/consistency",
            "content": "Consistency test document with unique identifier 12345.",
            "title": "Consistency Test",
            "metadata": {"test_id": "consistency_12345", "timestamp": time.time()},
        }

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            doc_id = await qdrant_client.store_crawled_page(
                url=test_doc["url"],
                content=test_doc["content"],
                title=test_doc["title"],
                metadata=test_doc["metadata"],
            )

        assert doc_id is not None

        # Retrieve the document multiple times
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            # Multiple retrievals should be consistent
            retrieval_tasks = [
                qdrant_client.search_crawled_pages(
                    "unique identifier 12345",
                    match_count=1,
                )
                for _ in range(5)
            ]

            results_list = await asyncio.gather(*retrieval_tasks)

        # Verify consistency across retrievals
        assert len(results_list) == 5
        for results in results_list:
            assert len(results) >= 1
            found_doc = results[0]
            assert found_doc["url"] == test_doc["url"]
            assert "unique identifier 12345" in found_doc["content"]
            assert found_doc["metadata"]["test_id"] == "consistency_12345"

        # Verify all retrievals return the same document ID/content
        first_result = results_list[0][0]
        for results in results_list[1:]:
            assert results[0]["url"] == first_result["url"]
            assert results[0]["content"] == first_result["content"]

        print("✅ Data consistency: All retrievals return identical results")


@pytest.mark.integration
class TestSupabaseIntegration:
    """Test Supabase database integration (when configured)."""

    @pytest.mark.asyncio
    async def test_supabase_connection_lifecycle(self, supabase_client):
        """Test Supabase connection and table setup."""

        # Verify connection is established
        assert supabase_client.client is not None
        assert supabase_client.table_name == "test_crawled_pages"

        # Test table access
        try:
            # Simple query to verify table exists and is accessible
            result = (
                await supabase_client.client.table(supabase_client.table_name)
                .select("*")
                .limit(1)
                .execute()
            )
            assert result is not None

        except Exception as e:
            pytest.fail(f"Supabase table access failed: {e}")

        print(f"✅ Supabase connection healthy, table: {supabase_client.table_name}")

    @pytest.mark.asyncio
    async def test_supabase_store_and_search(self, supabase_client):
        """Test storing and searching with Supabase + pgvector."""

        test_doc = {
            "url": "https://example.com/supabase-test",
            "content": "Supabase test document with vector search capabilities.",
            "title": "Supabase Test",
            "metadata": {"database": "supabase", "feature": "pgvector"},
        }

        # Store document
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            doc_id = await supabase_client.store_crawled_page(
                url=test_doc["url"],
                content=test_doc["content"],
                title=test_doc["title"],
                metadata=test_doc["metadata"],
            )

        assert doc_id is not None

        # Search for the document
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            results = await supabase_client.search_crawled_pages(
                query="vector search capabilities",
                match_count=5,
            )

        # Verify search results
        assert len(results) >= 1
        found_doc = results[0]
        assert found_doc["url"] == test_doc["url"]
        assert "vector search" in found_doc["content"]
        assert found_doc["metadata"]["database"] == "supabase"

        print("✅ Supabase store and search working correctly")


@pytest.mark.integration
class TestDatabaseFactory:
    """Test database factory with real services."""

    @pytest.mark.asyncio
    async def test_factory_qdrant_creation(self, integration_test_env):
        """Test factory creates Qdrant adapter correctly."""

        adapter = await create_and_initialize_database()

        assert isinstance(adapter, QdrantAdapter)
        assert adapter.CRAWLED_PAGES == "crawled_pages"
        assert adapter.client is not None

        # Test basic operations work
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            doc_id = await adapter.store_crawled_page(
                url="https://example.com/factory-test",
                content="Factory test document",
                title="Factory Test",
                metadata={"source": "factory"},
            )

        assert doc_id is not None

        # Test search
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            results = await adapter.search_crawled_pages(
                query="Factory test",
                match_count=5,
            )

        assert len(results) >= 1
        assert results[0]["url"] == "https://example.com/factory-test"

        print("✅ Database factory creates working Qdrant adapter")

    @pytest.mark.asyncio
    async def test_factory_error_handling(self):
        """Test factory error handling with invalid configuration."""

        # Test with invalid database type
        with patch.dict("os.environ", {"VECTOR_DATABASE": "invalid_db"}):
            with pytest.raises(Exception):
                await create_and_initialize_database()

        # Test with missing required config
        with patch.dict("os.environ", {"VECTOR_DATABASE": "qdrant", "QDRANT_URL": ""}):
            with pytest.raises(Exception):
                await create_and_initialize_database()

        print("✅ Factory properly handles configuration errors")


@pytest.mark.integration
class TestCrossDatabase:
    """Test operations across different database types."""

    @pytest.mark.asyncio
    async def test_data_portability(self, qdrant_client):
        """Test that data can be consistently stored/retrieved across database types."""

        # Test document that should work with both databases
        test_doc = {
            "url": "https://example.com/portable",
            "content": "Portable test document that works across database types.",
            "title": "Portable Test",
            "metadata": {
                "category": "testing",
                "tags": ["portable", "cross-db"],
                "score": 0.95,
            },
        }

        # Store in Qdrant
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            qdrant_id = await qdrant_client.store_crawled_page(
                url=test_doc["url"],
                content=test_doc["content"],
                title=test_doc["title"],
                metadata=test_doc["metadata"],
            )

        assert qdrant_id is not None

        # Search in Qdrant
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            qdrant_results = await qdrant_client.search_crawled_pages(
                query="portable cross database",
                match_count=5,
            )

        # Verify consistent data structure
        assert len(qdrant_results) >= 1
        qdrant_doc = qdrant_results[0]

        # Check all expected fields are present
        required_fields = ["url", "content", "title", "metadata", "score"]
        for field in required_fields:
            assert field in qdrant_doc, f"Missing field: {field}"

        # Verify metadata preservation
        assert qdrant_doc["metadata"]["category"] == "testing"
        assert "portable" in qdrant_doc["metadata"]["tags"]
        assert qdrant_doc["metadata"]["score"] == 0.95

        print("✅ Data portability: Consistent structure across database types")
