"""
Tests for Qdrant connection failures, initialization edge cases, and error recovery.
Focuses on robustness and error handling in the Qdrant integration.
"""

import asyncio
import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


from database.factory import create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter

from .test_doubles import FakeQdrantClient


class TestQdrantConnectionFailures:
    """Test various Qdrant connection failure scenarios"""

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
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_qdrant_client_creation_failure(self):
        """Test failure during QdrantClient instantiation"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client_class.side_effect = ConnectionError(
                "Unable to connect to Qdrant",
            )

            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)

            with pytest.raises(ConnectionError, match="Unable to connect to Qdrant"):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_qdrant_network_timeout(self):
        """Test network timeout during connection"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client_class.side_effect = TimeoutError("Connection timed out")

            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)

            with pytest.raises(TimeoutError, match="Connection timed out"):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_qdrant_authentication_failure(self):
        """Test authentication failure with invalid API key"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client_class.side_effect = Exception(
                "Authentication failed: Invalid API key",
            )

            adapter = QdrantAdapter(url="http://localhost:6333", api_key="invalid-key")

            with pytest.raises(Exception, match="Authentication failed"):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_qdrant_collection_check_failure(self):
        """Test failure when checking if collections exist"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Make get_collection calls fail
            mock_client.get_collection.side_effect = Exception(
                "Collection check failed",
            )
            # Make create_collection succeed
            mock_client.create_collection.return_value = Mock()

            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
            adapter.client = mock_client

            # Should proceed to create collections despite check failure
            await adapter.initialize()

            # Verify collections were created
            assert mock_client.create_collection.call_count == 3

    @pytest.mark.asyncio
    async def test_qdrant_partial_collection_creation_failure(self):
        """Test when some collections fail to create"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Make get_collection fail (collections don't exist)
            mock_client.get_collection.side_effect = Exception("Collection not found")

            # Make create_collection fail for specific collections
            def create_collection_side_effect(name, *args, **kwargs):
                if name == "crawled_pages":
                    return Mock()  # Success
                if name == "code_examples":
                    raise Exception(f"Failed to create {name}")
                # sources
                return Mock()  # Success

            mock_client.create_collection.side_effect = create_collection_side_effect

            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
            adapter.client = mock_client

            with pytest.raises(Exception, match="Failed to create code_examples"):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_qdrant_asyncio_executor_failure(self):
        """Test failure in asyncio.run_in_executor calls"""
        adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
        adapter.client = Mock()

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.side_effect = RuntimeError("Executor failed")

            with pytest.raises(RuntimeError, match="Executor failed"):
                await adapter._ensure_collections()

    @pytest.mark.asyncio
    async def test_qdrant_concurrent_initialization(self):
        """Test concurrent initialization calls"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_collection.return_value = Mock()  # Collections exist

            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)

            # Run multiple initialize calls concurrently
            tasks = [adapter.initialize() for _ in range(5)]
            await asyncio.gather(*tasks)

            # Client should only be created once
            assert mock_client_class.call_count == 1

    @pytest.mark.asyncio
    async def test_qdrant_connection_recovery(self):
        """Test connection recovery after initial failure"""
        call_count = 0

        def create_client_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("First attempt failed")
            return Mock()  # Second attempt succeeds

        with patch(
            "database.qdrant_adapter.QdrantClient",
            side_effect=create_client_side_effect,
        ):
            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)

            # First initialization should fail
            with pytest.raises(ConnectionError):
                await adapter.initialize()

            # Second initialization should succeed
            await adapter.initialize()
            assert adapter.client is not None

    @pytest.mark.asyncio
    async def test_factory_initialization_failure(self):
        """Test create_and_initialize_database with Qdrant failure"""
        with patch("database.qdrant_adapter.QdrantClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Qdrant server unavailable")

            with pytest.raises(Exception, match="Qdrant server unavailable"):
                await create_and_initialize_database()

    @pytest.mark.asyncio
    async def test_qdrant_url_environment_variable_handling(self):
        """Test handling of different QDRANT_URL formats"""
        test_cases = [
            ("http://localhost:6333", "http://localhost:6333"),
            ("https://cloud.qdrant.io:443", "https://cloud.qdrant.io:443"),
            ("qdrant-server:6333", "qdrant-server:6333"),
            ("", "http://localhost:6333"),  # Default fallback
        ]

        for env_url, expected_url in test_cases:
            with patch.dict(os.environ, {"QDRANT_URL": env_url}):
                adapter = QdrantAdapter()
                assert adapter.url == expected_url

    @pytest.mark.asyncio
    async def test_qdrant_api_key_environment_handling(self):
        """Test handling of QDRANT_API_KEY environment variable"""
        test_cases = [
            ("valid-api-key", "valid-api-key"),
            ("", None),  # Empty string should become None
            (None, None),  # No env var should be None
        ]

        for env_key, expected_key in test_cases:
            env_dict = {}
            if env_key is not None:
                env_dict["QDRANT_API_KEY"] = env_key

            with patch.dict(os.environ, env_dict, clear=True):
                # Add back required env vars
                os.environ["VECTOR_DATABASE"] = "qdrant"
                adapter = QdrantAdapter()
                assert adapter.api_key == expected_key


class TestQdrantOperationFailures:
    """Test failures during Qdrant operations"""

    @pytest.fixture(autouse=True)
    def setup_qdrant_env(self):
        """Setup Qdrant environment"""
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            yield

    @pytest.fixture
    def adapter_with_failing_client(self):
        """Create adapter with a client that can be set to fail"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()
        return adapter

    @pytest.mark.asyncio
    async def test_upsert_operation_failure(self, adapter_with_failing_client):
        """Test failure during upsert operations"""
        adapter = adapter_with_failing_client
        adapter.client.should_fail = True

        with pytest.raises(Exception, match="Upsert failed"):
            await adapter.add_documents(
                urls=["https://example.com"],
                chunk_numbers=[1],
                contents=["Test content"],
                metadatas=[{"title": "Test"}],
                embeddings=[[0.1] * 1536],
            )

    @pytest.mark.asyncio
    async def test_search_operation_failure(self, adapter_with_failing_client):
        """Test failure during search operations"""
        adapter = adapter_with_failing_client
        adapter.client.should_fail = True

        with pytest.raises(Exception, match="Search failed"):
            await adapter.search_documents(query_embedding=[0.1] * 1536, match_count=10)

    @pytest.mark.asyncio
    async def test_delete_operation_failure(self, adapter_with_failing_client):
        """Test failure during delete operations"""
        adapter = adapter_with_failing_client
        adapter.client.should_fail = True

        # Delete operations are currently handled gracefully (errors logged but not re-raised)
        # This test verifies the current behavior
        try:
            await adapter.delete_documents_by_url("https://example.com")
            # Should not raise exception even if delete fails
        except Exception:
            pytest.fail("Delete failures should be handled gracefully")

    @pytest.mark.asyncio
    async def test_batch_operation_partial_failure(self, adapter_with_failing_client):
        """Test partial failure in batch operations"""
        adapter = adapter_with_failing_client

        # Set up a client that fails on second batch
        call_count = 0
        original_upsert = adapter.client.upsert

        def failing_upsert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second batch
                raise Exception("Second batch failed")
            return original_upsert(*args, **kwargs)

        adapter.client.upsert = failing_upsert

        # Create data that will be split into multiple batches
        urls = [f"https://example{i}.com" for i in range(10)]
        chunk_numbers = [1] * 10
        contents = [f"Content {i}" for i in range(10)]
        metadatas = [{"page": i} for i in range(10)]
        embeddings = [[0.1] * 1536] * 10

        with pytest.raises(Exception, match="Second batch failed"):
            await adapter.add_documents(
                urls=urls,
                chunk_numbers=chunk_numbers,
                contents=contents,
                metadatas=metadatas,
                embeddings=embeddings,
            )

    @pytest.mark.asyncio
    async def test_invalid_vector_dimensions(self, adapter_with_failing_client):
        """Test handling of invalid vector dimensions"""
        adapter = adapter_with_failing_client

        # Try to add documents with wrong embedding dimensions
        with pytest.raises(Exception):
            await adapter.add_documents(
                urls=["https://example.com"],
                chunk_numbers=[1],
                contents=["Test content"],
                metadatas=[{"title": "Test"}],
                embeddings=[[0.1] * 512],  # Wrong dimension (should be 1536)
            )

    @pytest.mark.asyncio
    async def test_mismatched_input_lengths(self, adapter_with_failing_client):
        """Test handling of mismatched input array lengths"""
        adapter = adapter_with_failing_client

        # Mismatched lengths should cause an error
        with pytest.raises((IndexError, ValueError)):
            await adapter.add_documents(
                urls=["https://example.com"],  # 1 item
                chunk_numbers=[1, 2],  # 2 items - mismatch!
                contents=["Test content"],  # 1 item
                metadatas=[{"title": "Test"}],  # 1 item
                embeddings=[[0.1] * 1536],  # 1 item
            )

    @pytest.mark.asyncio
    async def test_empty_embeddings_handling(self, adapter_with_failing_client):
        """Test handling of empty embeddings"""
        adapter = adapter_with_failing_client

        # Empty inputs should be handled gracefully
        await adapter.add_documents(
            urls=[],
            chunk_numbers=[],
            contents=[],
            metadatas=[],
            embeddings=[],
        )

        # Should not have attempted any operations
        assert len(adapter.client.collections.get("crawled_pages", [])) == 0


class TestQdrantEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture(autouse=True)
    def setup_qdrant_env(self):
        """Setup Qdrant environment"""
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            yield

    @pytest.mark.asyncio
    async def test_very_large_content_chunks(self):
        """Test handling of very large content chunks"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()

        # Create a very large content chunk (1MB)
        large_content = "x" * (1024 * 1024)

        await adapter.add_documents(
            urls=["https://example.com/large"],
            chunk_numbers=[1],
            contents=[large_content],
            metadatas=[{"size": "large"}],
            embeddings=[[0.1] * 1536],
        )

        # Verify it was stored
        stored_docs = adapter.client.collections["crawled_pages"]
        assert len(stored_docs) == 1
        assert len(stored_docs[0]["payload"]["content"]) == 1024 * 1024

    @pytest.mark.asyncio
    async def test_special_characters_in_urls(self):
        """Test handling of URLs with special characters"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()

        special_urls = [
            "https://example.com/页面",  # Unicode
            "https://example.com/page?query=test&param=value",  # Query params
            "https://example.com/path/with%20spaces",  # URL encoding
            "https://example.com/page#fragment",  # Fragment
        ]

        for i, url in enumerate(special_urls):
            await adapter.add_documents(
                urls=[url],
                chunk_numbers=[1],
                contents=[f"Content for {url}"],
                metadatas=[{"url_type": "special"}],
                embeddings=[[0.1] * 1536],
            )

        # Verify all were stored with unique IDs
        stored_docs = adapter.client.collections["crawled_pages"]
        assert len(stored_docs) == len(special_urls)

        # Verify unique point IDs
        ids = [doc["id"] for doc in stored_docs]
        assert len(set(ids)) == len(special_urls)

    @pytest.mark.asyncio
    async def test_metadata_with_nested_objects(self):
        """Test handling of complex nested metadata"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()

        complex_metadata = {
            "author": {"name": "John Doe", "email": "john@example.com"},
            "tags": ["python", "tutorial", "beginner"],
            "stats": {"views": 1000, "likes": 50},
            "config": {"nested": {"deep": {"value": True}}},
        }

        await adapter.add_documents(
            urls=["https://example.com/complex"],
            chunk_numbers=[1],
            contents=["Content with complex metadata"],
            metadatas=[complex_metadata],
            embeddings=[[0.1] * 1536],
        )

        # Verify metadata was preserved
        stored_docs = adapter.client.collections["crawled_pages"]
        assert len(stored_docs) == 1
        stored_metadata = stored_docs[0]["payload"]["metadata"]
        assert stored_metadata["author"]["name"] == "John Doe"
        assert stored_metadata["tags"] == ["python", "tutorial", "beginner"]
        assert stored_metadata["config"]["nested"]["deep"]["value"] is True

    @pytest.mark.asyncio
    async def test_maximum_batch_size_handling(self):
        """Test handling of maximum batch sizes"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()

        # Set a very small batch size to test batching logic
        adapter.batch_size = 2

        # Create data for 5 documents
        num_docs = 5
        urls = [f"https://example{i}.com" for i in range(num_docs)]

        await adapter.add_documents(
            urls=urls,
            chunk_numbers=[1] * num_docs,
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"doc": i} for i in range(num_docs)],
            embeddings=[[0.1] * 1536] * num_docs,
        )

        # All documents should be stored despite small batch size
        stored_docs = adapter.client.collections["crawled_pages"]
        assert len(stored_docs) == num_docs

    @pytest.mark.asyncio
    async def test_concurrent_operations_on_same_collection(self):
        """Test concurrent operations on the same collection"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()

        async def add_batch(batch_id):
            await adapter.add_documents(
                urls=[f"https://batch{batch_id}.example.com"],
                chunk_numbers=[1],
                contents=[f"Content from batch {batch_id}"],
                metadatas=[{"batch_id": batch_id}],
                embeddings=[[0.1 * batch_id] * 1536],
            )

        # Run multiple concurrent add operations
        tasks = [add_batch(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # All documents should be stored
        stored_docs = adapter.client.collections["crawled_pages"]
        assert len(stored_docs) == 10

        # Verify all batches are represented
        batch_ids = [doc["payload"]["metadata"]["batch_id"] for doc in stored_docs]
        assert set(batch_ids) == set(range(10))
