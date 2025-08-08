"""
Qdrant error handling and recovery tests.
Tests various failure scenarios and recovery mechanisms.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


from database.factory import create_and_initialize_database, create_database_client
from database.qdrant_adapter import QdrantAdapter
from utils import add_documents_to_database, search_documents


class TestQdrantErrorHandling:
    """Test Qdrant error handling and recovery scenarios"""

    @pytest.fixture(autouse=True)
    def setup_qdrant_env(self):
        """Setup Qdrant environment variables"""
        with patch.dict(
            os.environ,
            {
                "VECTOR_DATABASE": "qdrant",
                "QDRANT_URL": "http://localhost:6333",
                "QDRANT_API_KEY": "",
                "OPENAI_API_KEY": "test-key",
                "USE_RERANKING": "false",
                "USE_HYBRID_SEARCH": "false",
                "USE_CONTEXTUAL_EMBEDDINGS": "false",
                "USE_AGENTIC_RAG": "false",
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_qdrant_connection_timeout(self):
        """Test handling of Qdrant connection timeouts"""
        # Mock QdrantClient to simulate timeout
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.side_effect = TimeoutError("Connection timeout")
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")

            with pytest.raises(Exception):  # Should propagate timeout error
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_qdrant_connection_refused(self):
        """Test handling when Qdrant connection is refused"""
        # Test with non-existent host
        adapter = QdrantAdapter(url="http://nonexistent-host:6333")

        with pytest.raises(Exception):
            await adapter.initialize()

    @pytest.mark.asyncio
    async def test_collection_creation_failure(self):
        """Test handling of collection creation failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            # First call (get_collection) fails, second call (create_collection) also fails
            mock_client.get_collection.side_effect = Exception("Collection not found")
            mock_client.create_collection.side_effect = Exception(
                "Failed to create collection",
            )
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")

            with pytest.raises(Exception, match="Failed to create collection"):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_upsert_failure_with_retry(self):
        """Test handling of upsert failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            # Setup successful collection operations
            mock_client.get_collection.return_value = Mock()
            # Make upsert fail
            mock_client.upsert.side_effect = Exception("Upsert operation failed")
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test that upsert failure is properly propagated
            with pytest.raises(Exception, match="Upsert operation failed"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 1536],
                )

    @pytest.mark.asyncio
    async def test_search_failure_handling(self):
        """Test handling of search operation failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            # Setup successful collection operations
            mock_client.get_collection.return_value = Mock()
            # Make search fail
            mock_client.search.side_effect = Exception("Search operation failed")
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test that search failure is properly propagated
            with pytest.raises(Exception, match="Search operation failed"):
                await adapter.search_documents(
                    query_embedding=[0.1] * 1536,
                    match_count=5,
                )

    @pytest.mark.asyncio
    async def test_delete_operation_failure(self):
        """Test handling of delete operation failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            # Setup successful collection operations
            mock_client.get_collection.return_value = Mock()
            # Make scroll work but delete fail
            mock_client.scroll.return_value = ([Mock(id="test_id")], None)
            mock_client.delete.side_effect = Exception("Delete operation failed")
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test that delete failure is properly propagated
            with pytest.raises(Exception, match="Delete operation failed"):
                await adapter.delete_documents_by_url("https://test.com")

    @pytest.mark.asyncio
    async def test_invalid_embedding_dimensions(self):
        """Test handling of invalid embedding dimensions"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()
            # Make upsert fail due to dimension mismatch
            mock_client.upsert.side_effect = Exception(
                "Vector dimension mismatch: expected 1536, got 128",
            )
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test with wrong embedding dimensions
            with pytest.raises(Exception, match="Vector dimension mismatch"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 128],  # Wrong dimension
                )

    @pytest.mark.asyncio
    async def test_empty_data_handling(self):
        """Test handling of empty or None data"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test with empty lists
            await adapter.add_documents(
                urls=[],
                chunk_numbers=[],
                contents=[],
                metadatas=[],
                embeddings=[],
            )

            # Should not call upsert for empty data
            mock_client.upsert.assert_not_called()

            # Test with None values
            with pytest.raises((TypeError, ValueError, AttributeError)):
                await adapter.add_documents(
                    urls=None,
                    chunk_numbers=None,
                    contents=None,
                    metadatas=None,
                    embeddings=None,
                )

    @pytest.mark.asyncio
    async def test_network_interruption_during_operation(self):
        """Test handling of network interruptions during operations"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()

            # Simulate network interruption during upsert
            call_count = 0

            def failing_upsert(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ConnectionError("Network connection lost")
                return Mock()

            mock_client.upsert.side_effect = failing_upsert
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Should fail with connection error (no automatic retry in current implementation)
            with pytest.raises(ConnectionError, match="Network connection lost"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 1536],
                )

    @pytest.mark.asyncio
    async def test_malformed_point_data(self):
        """Test handling of malformed point data"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()
            mock_client.upsert.side_effect = ValueError("Invalid point structure")
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test with malformed data that causes PointStruct creation to fail
            with pytest.raises(ValueError, match="Invalid point structure"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 1536],
                )

    @pytest.mark.asyncio
    async def test_concurrent_access_conflicts(self):
        """Test handling of concurrent access conflicts"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()

            # Simulate concurrent modification conflict
            call_count = 0

            def conflicting_operation(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("Concurrent modification detected")
                return Mock()

            mock_client.upsert.side_effect = conflicting_operation
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Should fail with concurrent modification error
            with pytest.raises(Exception, match="Concurrent modification detected"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 1536],
                )

    @pytest.mark.asyncio
    async def test_memory_pressure_during_batch_operations(self):
        """Test handling of memory pressure during large batch operations"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()
            mock_client.upsert.side_effect = MemoryError("Out of memory")
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Test large batch that causes memory error
            large_batch_size = 1000
            with pytest.raises(MemoryError, match="Out of memory"):
                await adapter.add_documents(
                    urls=[f"https://test.com/doc{i}" for i in range(large_batch_size)],
                    chunk_numbers=list(range(large_batch_size)),
                    contents=[f"content {i}" for i in range(large_batch_size)],
                    metadatas=[{"doc": i} for i in range(large_batch_size)],
                    embeddings=[[0.1] * 1536 for _ in range(large_batch_size)],
                )

    @pytest.mark.asyncio
    async def test_utils_function_error_propagation(self):
        """Test that errors from Qdrant adapter are properly propagated through utils functions"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()
            mock_client.upsert.side_effect = Exception("Qdrant storage error")
            mock_client_class.return_value = mock_client

            # Mock embedding creation to avoid OpenAI calls
            with patch(
                "utils.create_embeddings_batch",
                return_value=[[0.1] * 1536],
            ):
                with pytest.raises(Exception, match="Qdrant storage error"):
                    adapter = QdrantAdapter(url="http://localhost:6333")
                    await adapter.initialize()

                    await add_documents_to_database(
                        database=adapter,
                        urls=["https://test.com"],
                        chunk_numbers=[1],
                        contents=["test content"],
                        metadatas=[{"test": "meta"}],
                        url_to_full_document={"https://test.com": "full content"},
                        batch_size=10,
                    )

    @pytest.mark.asyncio
    async def test_search_with_invalid_embedding(self):
        """Test search operations with invalid embeddings"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()
            mock_client.search.side_effect = ValueError(
                "Invalid query vector dimensions",
            )
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Mock invalid embedding
            with patch(
                "utils.create_embedding",
                return_value=[0.1] * 128,
            ):  # Wrong dimension
                with pytest.raises(ValueError, match="Invalid query vector dimensions"):
                    await search_documents(
                        database=adapter,
                        query="test query",
                        match_count=5,
                    )

    @pytest.mark.asyncio
    async def test_partial_batch_failure_recovery(self):
        """Test recovery from partial batch failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()

            # Simulate failure on second batch
            call_count = 0

            def partial_failing_upsert(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Second batch failed")
                return Mock()

            mock_client.upsert.side_effect = partial_failing_upsert
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Mock embedding creation
            with patch(
                "utils.create_embeddings_batch",
                return_value=[[0.1] * 1536] * 10,
            ):
                # Should fail on second batch (batch_size=5, so 2 batches total)
                with pytest.raises(Exception, match="Second batch failed"):
                    await add_documents_to_database(
                        database=adapter,
                        urls=[f"https://test.com/doc{i}" for i in range(10)],
                        chunk_numbers=list(range(10)),
                        contents=[f"content {i}" for i in range(10)],
                        metadatas=[{"doc": i} for i in range(10)],
                        url_to_full_document={
                            f"https://test.com/doc{i}": f"full {i}" for i in range(10)
                        },
                        batch_size=5,
                    )

    @pytest.mark.asyncio
    async def test_api_key_authentication_failure(self):
        """Test handling of API key authentication failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.side_effect = Exception(
                "Authentication failed: Invalid API key",
            )
            mock_client_class.return_value = mock_client

            # Test with invalid API key
            adapter = QdrantAdapter(url="http://localhost:6333", api_key="invalid-key")

            with pytest.raises(Exception, match="Authentication failed"):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_collection_does_not_exist_during_operation(self):
        """Test handling when collection gets deleted during operations"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            # Initially collection exists
            mock_client.get_collection.return_value = Mock()
            # But during upsert, collection doesn't exist
            mock_client.upsert.side_effect = Exception(
                "Collection 'crawled_pages' does not exist",
            )
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            with pytest.raises(Exception, match="Collection.*does not exist"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 1536],
                )

    @pytest.mark.asyncio
    async def test_factory_error_handling(self):
        """Test error handling in database factory functions"""
        # Test with invalid database type
        with patch.dict(os.environ, {"VECTOR_DATABASE": "invalid_db"}):
            with pytest.raises(ValueError, match="Unknown database type"):
                create_database_client()

        # Test factory initialization with connection failure
        with patch(
            "database.qdrant_adapter.QdrantAdapter.initialize",
            side_effect=Exception("Init failed"),
        ):
            with pytest.raises(Exception, match="Init failed"):
                await create_and_initialize_database()

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_failure(self):
        """Test that resources are properly cleaned up on failures"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client.get_collection.return_value = Mock()

            # Track calls to ensure cleanup happens
            cleanup_calls = []

            def track_delete(*args, **kwargs):
                cleanup_calls.append(("delete", args, kwargs))
                return Mock()

            def failing_upsert(*args, **kwargs):
                raise Exception("Storage failed after cleanup")

            mock_client.delete.side_effect = track_delete
            mock_client.scroll.return_value = ([Mock(id="existing_doc")], None)
            mock_client.upsert.side_effect = failing_upsert
            mock_client_class.return_value = mock_client

            adapter = QdrantAdapter(url="http://localhost:6333")
            await adapter.initialize()

            # Should cleanup existing docs but then fail during upsert
            with pytest.raises(Exception, match="Storage failed after cleanup"):
                await adapter.add_documents(
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    embeddings=[[0.1] * 1536],
                )

            # Verify that cleanup was attempted (delete was called)
            assert len(cleanup_calls) > 0
            assert cleanup_calls[0][0] == "delete"
