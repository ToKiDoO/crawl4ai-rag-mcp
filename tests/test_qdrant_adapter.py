"""
Unit tests specific to the Qdrant adapter implementation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestQdrantAdapter:
    """Test Qdrant-specific functionality"""

    @pytest.fixture
    async def mock_qdrant_client(self):
        """Mock Qdrant client for testing"""
        client = MagicMock()
        # Mock collection operations - these are sync methods
        client.create_collection = MagicMock()
        client.get_collection = MagicMock()
        client.upsert = MagicMock()
        client.delete = MagicMock()
        client.search = MagicMock()
        client.retrieve = MagicMock()
        client.scroll = MagicMock()
        client.count = MagicMock(return_value=0)
        client.set_payload = MagicMock()

        # Mock search results
        mock_search_result = [
            MagicMock(
                id="test-id-1",
                score=0.9,
                payload={
                    "url": "https://test.com",
                    "chunk_number": 1,
                    "content": "Test content",
                    "metadata": {},
                    "source_id": "test.com",
                },
            ),
        ]
        client.search.return_value = mock_search_result

        # Mock scroll results - return empty list for empty searches
        client.scroll.return_value = ([], None)

        # Mock retrieve results - return empty list by default
        client.retrieve.return_value = []

        return client

    @pytest.fixture
    async def qdrant_adapter(self, mock_qdrant_client):
        """Create Qdrant adapter with mocked client"""
        with patch(
            "database.qdrant_adapter.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            from database.qdrant_adapter import QdrantAdapter

            adapter = QdrantAdapter(url="http://localhost:6333")
            adapter.client = mock_qdrant_client
            return adapter

    @pytest.mark.asyncio
    async def test_initialization_creates_collections(self):
        """Test that initialization creates necessary collections"""
        # Create a fresh mock client
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection = AsyncMock()

        with patch("database.qdrant_adapter.QdrantClient", return_value=mock_client):
            from database.qdrant_adapter import QdrantAdapter

            adapter = QdrantAdapter(url="http://localhost:6333")
            adapter.client = mock_client  # Ensure the mocked client is used

            await adapter.initialize()

            # Verify collections were created
            assert (
                mock_client.create_collection.call_count >= 3
            )  # crawled_pages, code_examples, sources

            # Verify correct vector config
            calls = mock_client.create_collection.call_args_list
            for call in calls:
                # The second argument should be VectorParams
                if len(call.args) >= 2:
                    config = call.args[1]
                    # Should be configured for OpenAI embeddings (1536 dimensions)
                    assert config.size == 1536

    @pytest.mark.asyncio
    async def test_add_documents_generates_ids(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test that documents are added with proper ID generation"""
        urls = ["https://test.com/page1", "https://test.com/page2"]

        await qdrant_adapter.add_documents(
            urls=urls,
            chunk_numbers=[1, 2],
            contents=["Content 1", "Content 2"],
            metadatas=[{"type": "doc"}, {"type": "doc"}],
            embeddings=[[0.1] * 1536, [0.2] * 1536],
            source_ids=["test.com", "test.com"],
        )

        # Verify upsert was called
        mock_qdrant_client.upsert.assert_called()

        # Get the points that were upserted
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args.kwargs.get("points") or call_args.args[1]

        # Verify points have proper structure
        assert len(points) == 2
        for point in points:
            assert hasattr(point, "id")
            assert hasattr(point, "vector")
            assert hasattr(point, "payload")
            assert len(point.vector) == 1536

    @pytest.mark.asyncio
    async def test_search_documents_with_score_conversion(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test search returns results with proper similarity scores"""
        query_embedding = [0.5] * 1536

        results = await qdrant_adapter.search_documents(
            query_embedding=query_embedding,
            match_count=10,
        )

        # Verify search was called on correct collection
        assert mock_qdrant_client.search.called

        # Verify results have correct structure
        assert len(results) == 1
        result = results[0]
        assert "id" in result
        assert "similarity" in result  # Interface expects similarity
        assert 0 <= result["similarity"] <= 1
        assert result["url"] == "https://test.com"

    @pytest.mark.asyncio
    async def test_search_with_metadata_filter(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test search with metadata filtering"""

        query_embedding = [0.5] * 1536
        filter_metadata = {"language": "python"}

        await qdrant_adapter.search_documents(
            query_embedding=query_embedding,
            match_count=5,
            filter_metadata=filter_metadata,
        )

        # Verify filter was constructed properly
        call_args = mock_qdrant_client.search.call_args
        query_filter = call_args.kwargs.get("query_filter")

        assert query_filter is not None
        # The filter should check metadata.language = "python"

    @pytest.mark.asyncio
    async def test_search_with_source_filter(self, qdrant_adapter, mock_qdrant_client):
        """Test search with source filtering"""
        query_embedding = [0.5] * 1536
        source_filter = "docs.python.org"

        await qdrant_adapter.search_documents(
            query_embedding=query_embedding,
            match_count=5,
            source_filter=source_filter,
        )

        # Verify filter includes source_id condition
        call_args = mock_qdrant_client.search.call_args
        query_filter = call_args.kwargs.get("query_filter")
        assert query_filter is not None

    @pytest.mark.asyncio
    async def test_empty_input_handling(self, qdrant_adapter, mock_qdrant_client):
        """Test handling of empty inputs"""
        # Empty lists should not cause errors
        await qdrant_adapter.add_documents(
            urls=[],
            chunk_numbers=[],
            contents=[],
            metadatas=[],
            embeddings=[],
            source_ids=[],
        )

        # Should not call upsert with empty data
        mock_qdrant_client.upsert.assert_not_called()

        # Empty URL string for deletion
        await qdrant_adapter.delete_documents_by_url("")

        # Should handle empty URL gracefully (might still call scroll)
        # but shouldn't find any documents to delete

    @pytest.mark.asyncio
    async def test_large_batch_handling(self, qdrant_adapter, mock_qdrant_client):
        """Test handling of large batches"""
        # Create 500 documents to test batch processing
        num_docs = 500
        urls = [f"https://test.com/page{i}" for i in range(num_docs)]

        await qdrant_adapter.add_documents(
            urls=urls,
            chunk_numbers=list(range(num_docs)),
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"index": i} for i in range(num_docs)],
            embeddings=[[i / 1000] * 1536 for i in range(num_docs)],
            source_ids=["test.com"] * num_docs,
        )

        # Verify upsert was called multiple times due to batch processing
        assert mock_qdrant_client.upsert.called

        # Collect all points from all batch calls
        total_points = []
        for call in mock_qdrant_client.upsert.call_args_list:
            # upsert is called with positional args: (collection_name, points)
            points = call.args[1] if len(call.args) > 1 else []
            total_points.extend(points)

        # Verify all documents were processed across batches
        assert len(total_points) == num_docs

    @pytest.mark.asyncio
    async def test_special_characters_handling(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test handling of special characters in content"""
        special_content = (
            "Test with 'quotes' and \"double quotes\" and \n newlines \t tabs"
        )
        special_url = "https://test.com/page?query=test&foo=bar#section"

        await qdrant_adapter.add_documents(
            urls=[special_url],
            chunk_numbers=[0],
            contents=[special_content],
            metadatas=[{"special": True}],
            embeddings=[[0.1] * 1536],
            source_ids=["test.com"],
        )

        # Should complete without errors
        mock_qdrant_client.upsert.assert_called()
        call_args = mock_qdrant_client.upsert.call_args
        # upsert is called with positional args: (collection_name, points)
        points = call_args.args[1] if len(call_args.args) > 1 else []
        assert len(points) > 0
        point = points[0]
        assert point.payload["content"] == special_content
        assert point.payload["url"] == special_url

    @pytest.mark.asyncio
    async def test_duplicate_handling(self, qdrant_adapter, mock_qdrant_client):
        """Test handling of duplicate documents"""
        # Add same document twice - should use consistent ID
        url = "https://test.com/duplicate"
        chunk_number = 0

        # First add
        await qdrant_adapter.add_documents(
            urls=[url],
            chunk_numbers=[chunk_number],
            contents=["Content version 1"],
            metadatas=[{"version": 1}],
            embeddings=[[0.1] * 1536],
            source_ids=["test.com"],
        )

        first_call = mock_qdrant_client.upsert.call_args
        # upsert is called with positional args: (collection_name, points)
        first_points = first_call.args[1] if len(first_call.args) > 1 else []
        assert len(first_points) > 0
        first_id = first_points[0].id

        # Second add with same URL and chunk
        await qdrant_adapter.add_documents(
            urls=[url],
            chunk_numbers=[chunk_number],
            contents=["Content version 2"],
            metadatas=[{"version": 2}],
            embeddings=[[0.2] * 1536],
            source_ids=["test.com"],
        )

        second_call = mock_qdrant_client.upsert.call_args
        # upsert is called with positional args: (collection_name, points)
        second_points = second_call.args[1] if len(second_call.args) > 1 else []
        assert len(second_points) > 0
        second_id = second_points[0].id

        # IDs should be the same (deterministic)
        assert first_id == second_id

    @pytest.mark.asyncio
    async def test_get_documents_by_url(self, qdrant_adapter, mock_qdrant_client):
        """Test retrieving documents by URL"""
        # Mock scroll response
        mock_points = [
            MagicMock(
                id="id1",
                payload={
                    "url": "https://test.com",
                    "chunk_number": 0,
                    "content": "Chunk 0",
                },
            ),
            MagicMock(
                id="id2",
                payload={
                    "url": "https://test.com",
                    "chunk_number": 1,
                    "content": "Chunk 1",
                },
            ),
        ]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        # Test
        results = await qdrant_adapter.get_documents_by_url("https://test.com")

        # Verify
        assert len(results) == 2
        assert results[0]["content"] == "Chunk 0"
        assert results[1]["content"] == "Chunk 1"
        assert results[0]["id"] == "id1"

    @pytest.mark.asyncio
    async def test_keyword_search_documents(self, qdrant_adapter, mock_qdrant_client):
        """Test keyword search functionality"""
        # Mock scroll response for keyword search
        mock_points = [
            MagicMock(
                id="id1",
                payload={
                    "content": "Python programming guide",
                    "url": "https://test.com",
                },
            ),
        ]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        # Test without source filter
        results = await qdrant_adapter.search_documents_by_keyword(
            keyword="Python",
            match_count=10,
        )

        assert len(results) == 1
        assert results[0]["content"] == "Python programming guide"

        # Verify scroll was called with text filter
        call_args = mock_qdrant_client.scroll.call_args
        assert call_args.kwargs["collection_name"] == "crawled_pages"
        assert call_args.kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_source_operations(self, qdrant_adapter, mock_qdrant_client):
        """Test source info operations"""
        # Mock retrieve to return empty (no existing source)
        mock_qdrant_client.retrieve.return_value = []

        # Test update source info
        await qdrant_adapter.update_source_info(
            source_id="test.com",
            summary="Test website",
            word_count=1500,
        )

        # Verify upsert was called on sources collection
        call_args = mock_qdrant_client.upsert.call_args
        collection_name = call_args.kwargs.get("collection_name") or call_args.args[0]
        assert collection_name == "sources"
        points = call_args.kwargs.get("points") or call_args.args[1]
        assert len(points) == 1
        point = points[0]
        assert point.payload["source_id"] == "test.com"
        assert point.payload["summary"] == "Test website"
        assert point.payload["total_word_count"] == 1500

        # Test get sources
        mock_points = [
            MagicMock(
                payload={
                    "source_id": "test.com",
                    "summary": "Test",
                    "total_word_count": 1000,
                },
            ),
        ]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        sources = await qdrant_adapter.get_sources()
        assert len(sources) == 1
        assert sources[0]["source_id"] == "test.com"

    @pytest.mark.asyncio
    async def test_connection_error_handling(self, qdrant_adapter, mock_qdrant_client):
        """Test handling of connection errors"""
        # Simulate connection error
        mock_qdrant_client.upsert.side_effect = Exception("Connection refused")

        # Should raise exception for connection errors
        with pytest.raises(Exception) as exc_info:
            await qdrant_adapter.add_documents(
                urls=["https://test.com"],
                chunk_numbers=[0],
                contents=["Test"],
                metadatas=[{}],
                embeddings=[[0.1] * 1536],
                source_ids=["test.com"],
            )

        assert "Connection refused" in str(exc_info.value)
        # Verify upsert was attempted
        assert mock_qdrant_client.upsert.called

    @pytest.mark.asyncio
    async def test_initialization_error_handling(self):
        """Test handling of initialization errors"""
        # Create a fresh mock client that fails on get_collection
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.side_effect = Exception("Creation failed")

        with patch("database.qdrant_adapter.QdrantClient", return_value=mock_client):
            from database.qdrant_adapter import QdrantAdapter

            adapter = QdrantAdapter(url="http://localhost:6333")

            # Should handle gracefully and not crash
            await adapter.initialize()

            # Should have attempted to create collections
            assert mock_client.create_collection.call_count > 0

    @pytest.mark.asyncio
    async def test_delete_documents_by_url(self, qdrant_adapter, mock_qdrant_client):
        """Test deletion of documents by URL"""
        urls = ["https://test1.com"]

        # Mock scroll to return points for this URL
        mock_points = [
            MagicMock(id="id1", payload={"url": "https://test1.com"}),
            MagicMock(id="id2", payload={"url": "https://test1.com"}),
        ]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        await qdrant_adapter.delete_documents_by_url(urls)

        # Should use scroll to find documents with this URL
        assert mock_qdrant_client.scroll.called

        # Should delete the found IDs
        mock_qdrant_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_source_operations_in_metadata_collection(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test source operations use a metadata collection"""
        # Mock retrieve to return empty (no existing source)
        mock_qdrant_client.retrieve.return_value = []

        # Test update source
        await qdrant_adapter.update_source_info(
            source_id="test.com",
            summary="Updated summary",
            word_count=1000,
        )

        # Should create a new source using upsert (since retrieve returned empty)
        assert mock_qdrant_client.upsert.called
        call_args = mock_qdrant_client.upsert.call_args
        assert call_args.args[0] == "sources"

        # Test get sources
        mock_qdrant_client.scroll.return_value = (
            [
                MagicMock(
                    id="test.com",
                    payload={
                        "source_id": "test.com",
                        "summary": "Test source",
                        "total_word_count": 1000,
                    },
                ),
            ],
            None,
        )

        sources = await qdrant_adapter.get_sources()

        assert len(sources) == 1
        assert sources[0]["source_id"] == "test.com"

    @pytest.mark.asyncio
    async def test_code_examples_operations(self, qdrant_adapter, mock_qdrant_client):
        """Test code example specific operations"""
        # Test add code examples with correct parameter name 'code_examples'
        await qdrant_adapter.add_code_examples(
            urls=["https://test.com/docs"],
            chunk_numbers=[1],
            code_examples=["def hello(): pass"],  # Correct parameter name
            summaries=["Hello function"],
            metadatas=[{"language": "python"}],
            embeddings=[[0.3] * 1536],
            # Note: source_ids is not a parameter for add_code_examples
        )

        # Verify upsert to code_examples collection
        call_args = mock_qdrant_client.upsert.call_args
        assert (
            call_args.kwargs.get("collection_name") == "code_examples"
            or call_args.args[0] == "code_examples"
        )

        # Test search code examples
        await qdrant_adapter.search_code_examples(
            query_embedding=[0.3] * 1536,
            match_count=5,
        )

        # Verify search on code_examples collection
        call_args = mock_qdrant_client.search.call_args
        assert (
            call_args.kwargs.get("collection_name") == "code_examples"
            or call_args.args[0] == "code_examples"
        )

    @pytest.mark.asyncio
    async def test_batch_processing(self, qdrant_adapter, mock_qdrant_client):
        """Test that large batches are processed correctly"""
        # Create 100 documents
        num_docs = 100
        urls = [f"https://test.com/page{i}" for i in range(num_docs)]

        await qdrant_adapter.add_documents(
            urls=urls,
            chunk_numbers=list(range(num_docs)),
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"index": i} for i in range(num_docs)],
            embeddings=[[i / 1000] * 1536 for i in range(num_docs)],
            source_ids=["test.com"] * num_docs,
        )

        # Verify upsert was called with batches
        assert mock_qdrant_client.upsert.call_count > 0

        # Verify total points across all batches
        total_points = 0
        for call in mock_qdrant_client.upsert.call_args_list:
            points = call.kwargs.get("points") or call.args[1]
            total_points += len(points)

        assert total_points == num_docs

    @pytest.mark.asyncio
    async def test_error_handling(self, qdrant_adapter, mock_qdrant_client):
        """Test error handling in operations"""
        # Make search fail
        mock_qdrant_client.search.side_effect = Exception("Connection error")

        # Should propagate error up
        with pytest.raises(Exception) as exc_info:
            await qdrant_adapter.search_documents(
                query_embedding=[0.5] * 1536,
                match_count=10,
            )
        assert "Connection error" in str(exc_info.value)

        # Reset side effect
        mock_qdrant_client.search.side_effect = None
        mock_qdrant_client.search.return_value = []

        # Make upsert fail
        mock_qdrant_client.upsert.side_effect = Exception("Write error")

        # Should handle error by raising exception
        with pytest.raises(Exception) as exc_info:
            await qdrant_adapter.add_documents(
                urls=["https://test.com"],
                chunk_numbers=[1],
                contents=["Test"],
                metadatas=[{}],
                embeddings=[[0.1] * 1536],
                source_ids=["test.com"],
            )
        assert "Write error" in str(exc_info.value)
