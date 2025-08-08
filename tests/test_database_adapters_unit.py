"""
Comprehensive unit tests for database adapters.

This module tests both QdrantAdapter and SupabaseAdapter with comprehensive mocking
to ensure no real database calls are made. Tests cover CRUD operations, batch processing,
error handling, retry logic, and edge cases.

Target coverage: >90% for both src/database/qdrant_adapter.py and src/database/supabase_adapter.py
"""

import asyncio
import os

# Import test utilities
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestQdrantAdapter:
    """Comprehensive tests for QdrantAdapter"""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a comprehensive mock for QdrantClient"""
        client = MagicMock()

        # Mock collection operations
        client.create_collection = MagicMock()
        client.get_collection = MagicMock()
        client.upsert = MagicMock()
        client.delete = MagicMock()
        client.search = MagicMock()
        client.retrieve = MagicMock()
        client.scroll = MagicMock()
        client.set_payload = MagicMock()

        # Default return values
        client.scroll.return_value = ([], None)
        client.retrieve.return_value = []
        client.search.return_value = []

        return client

    @pytest.fixture
    async def qdrant_adapter(self, mock_qdrant_client):
        """Create QdrantAdapter with mocked client"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()
        adapter.client = mock_qdrant_client
        return adapter

    @pytest.mark.asyncio
    async def test_initialization_default_values(self):
        """Test QdrantAdapter initialization with default values"""
        from database.qdrant_adapter import QdrantAdapter

        with patch.dict(os.environ, {}, clear=True):
            adapter = QdrantAdapter()

            assert adapter.url == "http://localhost:6333"
            assert adapter.api_key is None
            assert adapter.client is None
            assert adapter.batch_size == 100
            assert adapter.CRAWLED_PAGES == "crawled_pages"
            assert adapter.CODE_EXAMPLES == "code_examples"
            assert adapter.SOURCES == "sources"

    @pytest.mark.asyncio
    async def test_initialization_with_params(self):
        """Test QdrantAdapter initialization with custom parameters"""
        from database.qdrant_adapter import QdrantAdapter

        custom_url = "http://custom:6333"
        custom_key = "test-api-key"

        adapter = QdrantAdapter(url=custom_url, api_key=custom_key)

        assert adapter.url == custom_url
        assert adapter.api_key == custom_key

    @pytest.mark.asyncio
    async def test_initialization_with_env_vars(self):
        """Test QdrantAdapter initialization with environment variables"""
        from database.qdrant_adapter import QdrantAdapter

        env_vars = {"QDRANT_URL": "http://env:6333", "QDRANT_API_KEY": "env-api-key"}

        with patch.dict(os.environ, env_vars):
            adapter = QdrantAdapter()

            assert adapter.url == "http://env:6333"
            assert adapter.api_key == "env-api-key"

    @pytest.mark.asyncio
    async def test_initialize_creates_client_and_collections(self, mock_qdrant_client):
        """Test initialize method creates client and ensures collections exist"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()

        with patch(
            "database.qdrant_adapter.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Mock get_collection to raise exception (collection doesn't exist)
            mock_qdrant_client.get_collection.side_effect = Exception(
                "Collection not found",
            )

            await adapter.initialize()

            assert adapter.client == mock_qdrant_client
            # Should try to create all 3 collections
            assert mock_qdrant_client.create_collection.call_count == 3

    @pytest.mark.asyncio
    async def test_initialize_handles_existing_collections(self, mock_qdrant_client):
        """Test initialize gracefully handles existing collections"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()

        with patch(
            "database.qdrant_adapter.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            # Mock get_collection to succeed (collections exist)
            mock_qdrant_client.get_collection.return_value = MagicMock()

            await adapter.initialize()

            assert adapter.client == mock_qdrant_client
            # Should not try to create collections
            mock_qdrant_client.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_initialize_handles_create_collection_errors(
        self,
        mock_qdrant_client,
    ):
        """Test initialize handles collection creation errors gracefully"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()

        with patch(
            "database.qdrant_adapter.QdrantClient",
            return_value=mock_qdrant_client,
        ):
            mock_qdrant_client.get_collection.side_effect = Exception(
                "Collection not found",
            )
            mock_qdrant_client.create_collection.side_effect = Exception(
                "Create failed",
            )

            # Should not raise exception despite create failures
            await adapter.initialize()

            assert adapter.client == mock_qdrant_client

    def test_generate_point_id_deterministic(self, qdrant_adapter):
        """Test _generate_point_id produces deterministic results"""
        url = "https://test.com/page"
        chunk_number = 1

        id1 = qdrant_adapter._generate_point_id(url, chunk_number)
        id2 = qdrant_adapter._generate_point_id(url, chunk_number)

        assert id1 == id2
        assert isinstance(id1, str)
        assert len(id1) == 32  # MD5 hex string length

    def test_generate_point_id_different_inputs(self, qdrant_adapter):
        """Test _generate_point_id produces different IDs for different inputs"""
        url = "https://test.com/page"

        id1 = qdrant_adapter._generate_point_id(url, 1)
        id2 = qdrant_adapter._generate_point_id(url, 2)
        id3 = qdrant_adapter._generate_point_id("https://other.com/page", 1)

        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    @pytest.mark.asyncio
    async def test_add_documents_success(self, qdrant_adapter, mock_qdrant_client):
        """Test successful document addition"""
        urls = ["https://test.com/1", "https://test.com/2"]
        chunk_numbers = [1, 2]
        contents = ["Content 1", "Content 2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        source_ids = ["test.com", "test.com"]

        # Mock delete operation
        mock_qdrant_client.scroll.return_value = ([], None)

        await qdrant_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should call upsert with proper points
        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args

        assert call_args[0][0] == "crawled_pages"  # Collection name
        points = call_args[0][1]
        assert len(points) == 2

    @pytest.mark.asyncio
    async def test_add_documents_without_source_ids(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test document addition without source_ids"""
        urls = ["https://test.com/1"]
        chunk_numbers = [1]
        contents = ["Content 1"]
        metadatas = [{"key": "value1"}]
        embeddings = [[0.1] * 1536]

        mock_qdrant_client.scroll.return_value = ([], None)

        await qdrant_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            None,
        )

        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents_batch_processing(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test document addition with batch processing"""
        # Create more documents than batch size to test batching
        batch_size = qdrant_adapter.batch_size
        num_docs = batch_size + 50

        urls = [f"https://test.com/{i}" for i in range(num_docs)]
        chunk_numbers = list(range(num_docs))
        contents = [f"Content {i}" for i in range(num_docs)]
        metadatas = [{"index": i} for i in range(num_docs)]
        embeddings = [[0.1] * 1536 for _ in range(num_docs)]
        source_ids = ["test.com"] * num_docs

        mock_qdrant_client.scroll.return_value = ([], None)

        await qdrant_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should be called twice due to batching
        assert mock_qdrant_client.upsert.call_count == 2

    @pytest.mark.asyncio
    async def test_add_documents_deletes_existing(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test that add_documents deletes existing documents for URLs"""
        urls = ["https://test.com/1"]
        chunk_numbers = [1]
        contents = ["Content 1"]
        metadatas = [{"key": "value1"}]
        embeddings = [[0.1] * 1536]
        source_ids = ["test.com"]

        # Mock existing documents to delete
        mock_points = [MagicMock(id="existing-id")]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        await qdrant_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should call delete for existing documents (once per unique URL)
        mock_qdrant_client.delete.assert_called()
        # Check that delete was called with existing point IDs
        delete_calls = mock_qdrant_client.delete.call_args_list
        assert len(delete_calls) >= 1

    @pytest.mark.asyncio
    async def test_add_documents_handles_delete_error(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test add_documents handles delete errors gracefully"""
        with patch.object(
            qdrant_adapter,
            "delete_documents_by_url",
            side_effect=Exception("Delete failed"),
        ):
            urls = ["https://test.com/1"]
            chunk_numbers = [1]
            contents = ["Content 1"]
            metadatas = [{"key": "value1"}]
            embeddings = [[0.1] * 1536]
            source_ids = ["test.com"]

            # Should not raise exception despite delete failure
            await qdrant_adapter.add_documents(
                urls,
                chunk_numbers,
                contents,
                metadatas,
                embeddings,
                source_ids,
            )

            mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents_handles_upsert_error(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test add_documents handles upsert errors"""
        mock_qdrant_client.scroll.return_value = ([], None)
        mock_qdrant_client.upsert.side_effect = Exception("Upsert failed")

        urls = ["https://test.com/1"]
        chunk_numbers = [1]
        contents = ["Content 1"]
        metadatas = [{"key": "value1"}]
        embeddings = [[0.1] * 1536]
        source_ids = ["test.com"]

        with pytest.raises(Exception, match="Upsert failed"):
            await qdrant_adapter.add_documents(
                urls,
                chunk_numbers,
                contents,
                metadatas,
                embeddings,
                source_ids,
            )

    @pytest.mark.asyncio
    async def test_search_documents_basic(self, qdrant_adapter, mock_qdrant_client):
        """Test basic document search"""
        query_embedding = [0.1] * 1536

        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "test-id"
        mock_result.score = 0.9
        mock_result.payload = {
            "url": "https://test.com",
            "chunk_number": 1,
            "content": "Test content",
            "metadata": {"key": "value"},
        }
        mock_qdrant_client.search.return_value = [mock_result]

        results = await qdrant_adapter.search_documents(query_embedding, match_count=5)

        assert len(results) == 1
        assert results[0]["url"] == "https://test.com"
        assert results[0]["similarity"] == 0.9
        assert results[0]["id"] == "test-id"

        mock_qdrant_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents_with_filters(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test document search with metadata and source filters"""
        query_embedding = [0.1] * 1536
        filter_metadata = {"type": "article"}
        source_filter = "test.com"

        mock_qdrant_client.search.return_value = []

        await qdrant_adapter.search_documents(
            query_embedding,
            match_count=10,
            filter_metadata=filter_metadata,
            source_filter=source_filter,
        )

        # Verify search was called with filters
        call_args = mock_qdrant_client.search.call_args
        assert call_args[1]["query_filter"] is not None

    @pytest.mark.asyncio
    async def test_search_documents_by_keyword(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test keyword-based document search"""
        keyword = "python"

        # Mock scroll results
        mock_point = MagicMock()
        mock_point.id = "test-id"
        mock_point.payload = {
            "url": "https://test.com",
            "content": "Python programming",
            "chunk_number": 1,
        }
        mock_qdrant_client.scroll.return_value = ([mock_point], None)

        results = await qdrant_adapter.search_documents_by_keyword(
            keyword,
            match_count=5,
        )

        assert len(results) == 1
        assert results[0]["content"] == "Python programming"
        mock_qdrant_client.scroll.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_documents_by_keyword_with_source_filter(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test keyword search with source filter"""
        keyword = "python"
        source_filter = "test.com"

        mock_qdrant_client.scroll.return_value = ([], None)

        await qdrant_adapter.search_documents_by_keyword(
            keyword,
            match_count=5,
            source_filter=source_filter,
        )

        # Verify scroll was called with proper filter
        call_args = mock_qdrant_client.scroll.call_args
        assert call_args[1]["scroll_filter"] is not None

    @pytest.mark.asyncio
    async def test_get_documents_by_url(self, qdrant_adapter, mock_qdrant_client):
        """Test retrieving documents by URL"""
        url = "https://test.com/page"

        # Mock scroll results with multiple chunks
        mock_points = [
            MagicMock(
                id="id1",
                payload={"url": url, "chunk_number": 2, "content": "Content 2"},
            ),
            MagicMock(
                id="id2",
                payload={"url": url, "chunk_number": 1, "content": "Content 1"},
            ),
        ]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        results = await qdrant_adapter.get_documents_by_url(url)

        assert len(results) == 2
        # Should be sorted by chunk number
        assert results[0]["chunk_number"] == 1
        assert results[1]["chunk_number"] == 2

    @pytest.mark.asyncio
    async def test_delete_documents_by_url(self, qdrant_adapter, mock_qdrant_client):
        """Test deleting documents by URL"""
        urls = ["https://test.com/1", "https://test.com/2"]

        # Mock points to delete
        mock_points = [MagicMock(id="id1"), MagicMock(id="id2")]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        await qdrant_adapter.delete_documents_by_url(urls)

        # Should call scroll for each URL and delete points
        assert mock_qdrant_client.scroll.call_count == 2
        assert mock_qdrant_client.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_documents_by_url_no_points(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test deleting documents when no points exist"""
        urls = ["https://test.com/nonexistent"]

        mock_qdrant_client.scroll.return_value = ([], None)

        await qdrant_adapter.delete_documents_by_url(urls)

        # Should not call delete if no points found
        mock_qdrant_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_code_examples(self, qdrant_adapter, mock_qdrant_client):
        """Test adding code examples"""
        urls = ["https://test.com/code"]
        chunk_numbers = [1]
        code_examples = ["def hello(): pass"]
        summaries = ["Simple function"]
        metadatas = [{"language": "python"}]
        embeddings = [[0.1] * 1536]
        source_ids = ["test.com"]

        await qdrant_adapter.add_code_examples(
            urls,
            chunk_numbers,
            code_examples,
            summaries,
            metadatas,
            embeddings,
            source_ids,
        )

        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args
        assert call_args[0][0] == "code_examples"  # Collection name

    @pytest.mark.asyncio
    async def test_search_code_examples(self, qdrant_adapter, mock_qdrant_client):
        """Test searching code examples"""
        query_embedding = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.id = "code-id"
        mock_result.score = 0.8
        mock_result.payload = {
            "url": "https://test.com",
            "code": "def test(): pass",
            "summary": "Test function",
        }
        mock_qdrant_client.search.return_value = [mock_result]

        results = await qdrant_adapter.search_code_examples(query_embedding)

        assert len(results) == 1
        assert results[0]["code"] == "def test(): pass"
        assert results[0]["similarity"] == 0.8

    @pytest.mark.asyncio
    async def test_search_code_examples_by_keyword(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test searching code examples by keyword"""
        keyword = "function"

        mock_point = MagicMock()
        mock_point.id = "code-id"
        mock_point.payload = {"code": "def function(): pass", "summary": "A function"}
        mock_qdrant_client.scroll.return_value = ([mock_point], None)

        results = await qdrant_adapter.search_code_examples_by_keyword(keyword)

        assert len(results) == 1
        assert results[0]["code"] == "def function(): pass"

    @pytest.mark.asyncio
    async def test_delete_code_examples_by_url(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test deleting code examples by URL"""
        urls = ["https://test.com/code"]

        mock_points = [MagicMock(id="code-id")]
        mock_qdrant_client.scroll.return_value = (mock_points, None)

        await qdrant_adapter.delete_code_examples_by_url(urls)

        mock_qdrant_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_source(self, qdrant_adapter, mock_qdrant_client):
        """Test adding a source"""
        source_id = "test-source"
        url = "https://test.com"
        title = "Test Source"
        description = "A test source"
        metadata = {"type": "website"}
        embedding = [0.1] * 1536

        await qdrant_adapter.add_source(
            source_id,
            url,
            title,
            description,
            metadata,
            embedding,
        )

        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args
        assert call_args[0][0] == "sources"

    @pytest.mark.asyncio
    async def test_search_sources(self, qdrant_adapter, mock_qdrant_client):
        """Test searching sources"""
        query_embedding = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.id = "source-id"
        mock_result.score = 0.9
        mock_result.payload = {
            "source_id": "test-source",
            "title": "Test Source",
            "description": "A test source",
        }
        mock_qdrant_client.search.return_value = [mock_result]

        results = await qdrant_adapter.search_sources(query_embedding)

        assert len(results) == 1
        assert results[0]["source_id"] == "test-source"
        assert results[0]["similarity"] == 0.9

    @pytest.mark.asyncio
    async def test_update_source_success(self, qdrant_adapter, mock_qdrant_client):
        """Test successful source update"""
        source_id = "test-source"
        updates = {"title": "Updated Title"}

        # Mock existing source
        mock_point = MagicMock()
        mock_point.payload = {"source_id": source_id, "title": "Old Title"}
        mock_qdrant_client.retrieve.return_value = [mock_point]

        await qdrant_adapter.update_source(source_id, updates)

        mock_qdrant_client.set_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_source_not_found(self, qdrant_adapter, mock_qdrant_client):
        """Test update source when source doesn't exist"""
        source_id = "nonexistent-source"
        updates = {"title": "Updated Title"}

        mock_qdrant_client.retrieve.return_value = []

        with pytest.raises(ValueError, match="Source .* not found"):
            await qdrant_adapter.update_source(source_id, updates)

    @pytest.mark.asyncio
    async def test_get_sources(self, qdrant_adapter, mock_qdrant_client):
        """Test getting all sources"""
        # Mock multiple batches of sources
        batch1_points = [
            MagicMock(
                id="id1",
                payload={"source_id": "source1", "summary": "Summary 1"},
            ),
            MagicMock(
                id="id2",
                payload={"source_id": "source2", "summary": "Summary 2"},
            ),
        ]
        batch2_points = [
            MagicMock(
                id="id3",
                payload={"source_id": "source3", "summary": "Summary 3"},
            ),
        ]

        # Mock scroll to return batches then empty
        mock_qdrant_client.scroll.side_effect = [
            (batch1_points, "next_offset"),
            (batch2_points, None),  # None indicates end
        ]

        results = await qdrant_adapter.get_sources()

        assert len(results) == 3
        assert results[0]["source_id"] == "source1"
        assert mock_qdrant_client.scroll.call_count == 2

    @pytest.mark.asyncio
    async def test_get_sources_error_handling(self, qdrant_adapter, mock_qdrant_client):
        """Test get_sources handles errors gracefully"""
        mock_qdrant_client.scroll.side_effect = Exception("Database error")

        results = await qdrant_adapter.get_sources()

        assert results == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_update_source_info(self, qdrant_adapter, mock_qdrant_client):
        """Test updating source info (upsert operation)"""
        source_id = "test-source"
        summary = "Updated summary"
        word_count = 1000

        # Mock existing source
        mock_point = MagicMock()
        mock_point.payload = {"source_id": source_id, "summary": "Old summary"}
        mock_qdrant_client.retrieve.return_value = [mock_point]

        await qdrant_adapter.update_source_info(source_id, summary, word_count)

        mock_qdrant_client.set_payload.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_source_info_create_new(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test update_source_info creates new source when not found"""
        source_id = "new-source"
        summary = "New summary"
        word_count = 1000

        # Mock source not found
        mock_qdrant_client.retrieve.side_effect = Exception("Not found")

        await qdrant_adapter.update_source_info(source_id, summary, word_count)

        # Should call upsert to create new source
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_new_source_embedding_generation(
        self,
        qdrant_adapter,
        mock_qdrant_client,
    ):
        """Test _create_new_source generates proper embedding"""
        source_id = "test-source"
        summary = "Test summary"
        word_count = 500
        timestamp = "2023-01-01T00:00:00Z"
        point_id = "test-point-id"

        await qdrant_adapter._create_new_source(
            source_id,
            summary,
            word_count,
            timestamp,
            point_id,
        )

        mock_qdrant_client.upsert.assert_called_once()
        call_args = mock_qdrant_client.upsert.call_args
        points = call_args[0][1]

        assert len(points) == 1
        point = points[0]
        assert len(point.vector) == 1536  # OpenAI embedding size
        assert point.payload["source_id"] == source_id
        assert point.payload["summary"] == summary
        assert point.payload["total_word_count"] == word_count


class TestSupabaseAdapter:
    """Comprehensive tests for SupabaseAdapter"""

    @pytest.fixture
    def mock_supabase_client(self):
        """Create comprehensive mock for Supabase client"""
        client = MagicMock()

        # Mock table operations
        table_mock = MagicMock()
        table_mock.insert = MagicMock(return_value=table_mock)
        table_mock.delete = MagicMock(return_value=table_mock)
        table_mock.select = MagicMock(return_value=table_mock)
        table_mock.update = MagicMock(return_value=table_mock)
        table_mock.eq = MagicMock(return_value=table_mock)
        table_mock.in_ = MagicMock(return_value=table_mock)
        table_mock.ilike = MagicMock(return_value=table_mock)
        table_mock.or_ = MagicMock(return_value=table_mock)
        table_mock.limit = MagicMock(return_value=table_mock)
        table_mock.order = MagicMock(return_value=table_mock)
        table_mock.execute = MagicMock(return_value=MagicMock(data=[]))

        client.table = MagicMock(return_value=table_mock)

        # Mock RPC operations
        rpc_mock = MagicMock()
        rpc_mock.execute = MagicMock(return_value=MagicMock(data=[]))
        client.rpc = MagicMock(return_value=rpc_mock)

        return client

    @pytest.fixture
    async def supabase_adapter(self, mock_supabase_client):
        """Create SupabaseAdapter with mocked client"""
        from database.supabase_adapter import SupabaseAdapter

        adapter = SupabaseAdapter()
        adapter.client = mock_supabase_client
        return adapter

    @pytest.mark.asyncio
    async def test_initialization_default_values(self):
        """Test SupabaseAdapter initialization"""
        from database.supabase_adapter import SupabaseAdapter

        adapter = SupabaseAdapter()

        assert adapter.client is None
        assert adapter.batch_size == 20
        assert adapter.max_retries == 3
        assert adapter.retry_delay == 1.0

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_supabase_client):
        """Test successful initialization with environment variables"""
        from database.supabase_adapter import SupabaseAdapter

        env_vars = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_KEY": "test-service-key",
        }

        with patch.dict(os.environ, env_vars):
            with patch(
                "database.supabase_adapter.create_client",
                return_value=mock_supabase_client,
            ):
                adapter = SupabaseAdapter()
                await adapter.initialize()

                assert adapter.client == mock_supabase_client

    @pytest.mark.asyncio
    async def test_initialize_missing_env_vars(self):
        """Test initialization fails with missing environment variables"""
        from database.supabase_adapter import SupabaseAdapter

        with patch.dict(os.environ, {}, clear=True):
            adapter = SupabaseAdapter()

            with pytest.raises(
                ValueError,
                match="SUPABASE_URL and SUPABASE_SERVICE_KEY must be set",
            ):
                await adapter.initialize()

    @pytest.mark.asyncio
    async def test_add_documents_not_initialized(self):
        """Test add_documents fails when not initialized"""
        from database.supabase_adapter import SupabaseAdapter

        adapter = SupabaseAdapter()

        with pytest.raises(RuntimeError, match="Database not initialized"):
            await adapter.add_documents([], [], [], [], [], [])

    @pytest.mark.asyncio
    async def test_add_documents_success(self, supabase_adapter, mock_supabase_client):
        """Test successful document addition"""
        urls = ["https://test.com/1", "https://test.com/2"]
        chunk_numbers = [1, 2]
        contents = ["Content 1", "Content 2"]
        metadatas = [{"key": "value1"}, {"key": "value2"}]
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        source_ids = ["test.com", "test.com"]

        await supabase_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should call delete for existing URLs and insert for new documents
        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.assert_called()
        table_mock.insert.assert_called()

    @pytest.mark.asyncio
    async def test_add_documents_extracts_source_id_from_url(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test add_documents extracts source_id from URL when not provided"""
        urls = ["https://example.com/page"]
        chunk_numbers = [1]
        contents = ["Content"]
        metadatas = [{}]
        embeddings = [[0.1] * 1536]
        source_ids = []  # Empty source_ids

        await supabase_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should still work by extracting source_id from URL
        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.assert_called()

    @pytest.mark.asyncio
    async def test_add_documents_batch_processing(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test document addition with batch processing"""
        batch_size = supabase_adapter.batch_size
        num_docs = batch_size + 5

        urls = [f"https://test.com/{i}" for i in range(num_docs)]
        chunk_numbers = list(range(num_docs))
        contents = [f"Content {i}" for i in range(num_docs)]
        metadatas = [{"index": i} for i in range(num_docs)]
        embeddings = [[0.1] * 1536 for _ in range(num_docs)]
        source_ids = ["test.com"] * num_docs

        await supabase_adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should call insert multiple times due to batching
        table_mock = mock_supabase_client.table.return_value
        assert table_mock.insert.call_count >= 2

    @pytest.mark.asyncio
    async def test_search_documents_success(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test successful document search"""
        query_embedding = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "test-id",
                "url": "https://test.com",
                "content": "Test content",
                "similarity": 0.9,
            },
        ]

        rpc_mock = mock_supabase_client.rpc.return_value
        rpc_mock.execute.return_value = mock_result

        results = await supabase_adapter.search_documents(query_embedding)

        assert len(results) == 1
        assert results[0]["url"] == "https://test.com"
        mock_supabase_client.rpc.assert_called_once_with(
            "match_crawled_pages",
            {"query_embedding": query_embedding, "match_count": 10},
        )

    @pytest.mark.asyncio
    async def test_search_documents_with_filters(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test document search with filters"""
        query_embedding = [0.1] * 1536
        filter_metadata = {"type": "article"}
        source_filter = "test.com"

        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(data=[])

        await supabase_adapter.search_documents(
            query_embedding,
            match_count=5,
            filter_metadata=filter_metadata,
            source_filter=source_filter,
        )

        # Should include filters in RPC parameters
        call_args = mock_supabase_client.rpc.call_args
        params = call_args[0][1]
        assert "filter" in params
        assert "source_filter" in params
        assert params["match_count"] == 5

    @pytest.mark.asyncio
    async def test_search_documents_error_handling(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test search documents handles errors gracefully"""
        query_embedding = [0.1] * 1536

        mock_supabase_client.rpc.return_value.execute.side_effect = Exception(
            "RPC failed",
        )

        results = await supabase_adapter.search_documents(query_embedding)

        assert results == []  # Should return empty list on error

    @pytest.mark.asyncio
    async def test_delete_documents_by_url(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test deleting documents by URL"""
        urls = ["https://test.com/1", "https://test.com/2"]

        await supabase_adapter.delete_documents_by_url(urls)

        # Should call _delete_documents_batch
        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.assert_called()

    @pytest.mark.asyncio
    async def test_add_code_examples_success(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test successful code example addition"""
        urls = ["https://test.com/code"]
        chunk_numbers = [1]
        code_examples = ["def hello(): pass"]
        summaries = ["Simple function"]
        metadatas = [{"language": "python"}]
        embeddings = [[0.1] * 1536]
        source_ids = ["test.com"]

        await supabase_adapter.add_code_examples(
            urls,
            chunk_numbers,
            code_examples,
            summaries,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should delete existing and insert new
        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.assert_called()
        table_mock.insert.assert_called()

    @pytest.mark.asyncio
    async def test_add_code_examples_empty_urls(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test add_code_examples with empty URLs list"""
        await supabase_adapter.add_code_examples([], [], [], [], [], [], [])

        # Should not make any database calls
        mock_supabase_client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_code_examples_handles_delete_error(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test add_code_examples handles delete errors gracefully"""
        urls = ["https://test.com/code"]
        chunk_numbers = [1]
        code_examples = ["def hello(): pass"]
        summaries = ["Simple function"]
        metadatas = [{"language": "python"}]
        embeddings = [[0.1] * 1536]
        source_ids = ["test.com"]

        # Mock delete to fail
        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.return_value.eq.return_value.execute.side_effect = Exception(
            "Delete failed",
        )

        # Should not raise exception despite delete failure
        await supabase_adapter.add_code_examples(
            urls,
            chunk_numbers,
            code_examples,
            summaries,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should still call insert
        table_mock.insert.assert_called()

    @pytest.mark.asyncio
    async def test_search_code_examples(self, supabase_adapter, mock_supabase_client):
        """Test searching code examples"""
        query_embedding = [0.1] * 1536

        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "code-id",
                "content": "def test(): pass",
                "summary": "Test function",
            },
        ]

        rpc_mock = mock_supabase_client.rpc.return_value
        rpc_mock.execute.return_value = mock_result

        results = await supabase_adapter.search_code_examples(query_embedding)

        assert len(results) == 1
        assert results[0]["content"] == "def test(): pass"
        mock_supabase_client.rpc.assert_called_once_with(
            "match_code_examples",
            {"query_embedding": query_embedding, "match_count": 10},
        )

    @pytest.mark.asyncio
    async def test_delete_code_examples_by_url(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test deleting code examples by URL"""
        urls = ["https://test.com/code1", "https://test.com/code2"]

        await supabase_adapter.delete_code_examples_by_url(urls)

        table_mock = mock_supabase_client.table.return_value
        # Should call delete for each URL
        assert table_mock.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_code_examples_handles_errors(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test delete_code_examples handles errors gracefully"""
        urls = ["https://test.com/code"]

        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.return_value.eq.return_value.execute.side_effect = Exception(
            "Delete failed",
        )

        # Should not raise exception
        await supabase_adapter.delete_code_examples_by_url(urls)

    @pytest.mark.asyncio
    async def test_update_source_info_update_existing(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test updating existing source info"""
        source_id = "test-source"
        summary = "Updated summary"
        word_count = 1000

        # Mock successful update (returns data)
        table_mock = mock_supabase_client.table.return_value
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}],
        )

        await supabase_adapter.update_source_info(source_id, summary, word_count)

        table_mock.update.assert_called_once()
        table_mock.insert.assert_not_called()  # Should not insert

    @pytest.mark.asyncio
    async def test_update_source_info_create_new(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test creating new source info when update returns no data"""
        source_id = "new-source"
        summary = "New summary"
        word_count = 1000

        # Mock update returns no data (source doesn't exist)
        table_mock = mock_supabase_client.table.return_value
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[],
        )

        await supabase_adapter.update_source_info(source_id, summary, word_count)

        table_mock.update.assert_called_once()
        table_mock.insert.assert_called_once()  # Should insert new

    @pytest.mark.asyncio
    async def test_update_source_info_handles_error(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test update_source_info handles errors gracefully"""
        source_id = "test-source"
        summary = "Updated summary"
        word_count = 1000

        table_mock = mock_supabase_client.table.return_value
        table_mock.update.side_effect = Exception("Update failed")

        # Should not raise exception
        await supabase_adapter.update_source_info(source_id, summary, word_count)

    @pytest.mark.asyncio
    async def test_get_documents_by_url(self, supabase_adapter, mock_supabase_client):
        """Test getting documents by URL"""
        url = "https://test.com/page"

        mock_data = [
            {"id": 1, "url": url, "content": "Content 1"},
            {"id": 2, "url": url, "content": "Content 2"},
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=mock_data,
        )

        results = await supabase_adapter.get_documents_by_url(url)

        assert len(results) == 2
        assert results[0]["content"] == "Content 1"
        table_mock.select.assert_called_once_with("*")

    @pytest.mark.asyncio
    async def test_get_documents_by_url_handles_error(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test get_documents_by_url handles errors gracefully"""
        url = "https://test.com/page"

        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.eq.return_value.execute.side_effect = Exception(
            "Query failed",
        )

        results = await supabase_adapter.get_documents_by_url(url)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_documents_by_keyword(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test searching documents by keyword"""
        keyword = "python"

        mock_data = [
            {"id": 1, "content": "Python programming", "url": "https://test.com"},
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.ilike.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_data,
        )

        results = await supabase_adapter.search_documents_by_keyword(keyword)

        assert len(results) == 1
        assert results[0]["content"] == "Python programming"
        table_mock.ilike.assert_called_once_with("content", f"%{keyword}%")

    @pytest.mark.asyncio
    async def test_search_documents_by_keyword_with_source_filter(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test keyword search with source filter"""
        keyword = "python"
        source_filter = "test.com"

        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.ilike.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[],
        )

        await supabase_adapter.search_documents_by_keyword(
            keyword,
            source_filter=source_filter,
        )

        table_mock.eq.assert_called_once_with("source_id", source_filter)

    @pytest.mark.asyncio
    async def test_search_code_examples_by_keyword(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test searching code examples by keyword"""
        keyword = "function"

        mock_data = [
            {"id": 1, "content": "def function(): pass", "summary": "A function"},
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.or_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=mock_data,
        )

        results = await supabase_adapter.search_code_examples_by_keyword(keyword)

        assert len(results) == 1
        assert results[0]["content"] == "def function(): pass"
        table_mock.or_.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_sources(self, supabase_adapter, mock_supabase_client):
        """Test getting all sources"""
        mock_data = [
            {"source_id": "source1", "summary": "Summary 1"},
            {"source_id": "source2", "summary": "Summary 2"},
        ]

        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.order.return_value.execute.return_value = (
            MagicMock(data=mock_data)
        )

        results = await supabase_adapter.get_sources()

        assert len(results) == 2
        assert results[0]["source_id"] == "source1"
        table_mock.order.assert_called_once_with("source_id")

    @pytest.mark.asyncio
    async def test_delete_documents_batch_success(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test successful batch deletion"""
        urls = ["https://test.com/1", "https://test.com/2"]

        await supabase_adapter._delete_documents_batch(urls)

        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.return_value.in_.assert_called_once_with("url", urls)

    @pytest.mark.asyncio
    async def test_delete_documents_batch_fallback(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test batch deletion fallback to individual deletion"""
        urls = ["https://test.com/1", "https://test.com/2"]

        table_mock = mock_supabase_client.table.return_value
        # Mock batch delete to fail
        table_mock.delete.return_value.in_.return_value.execute.side_effect = Exception(
            "Batch delete failed",
        )

        await supabase_adapter._delete_documents_batch(urls)

        # Should call individual deletes as fallback
        assert table_mock.delete.call_count >= 2  # Batch attempt + individual attempts

    @pytest.mark.asyncio
    async def test_insert_with_retry_success_first_attempt(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test successful insert on first attempt"""
        table_name = "test_table"
        batch_data = [{"id": 1, "data": "test"}]

        await supabase_adapter._insert_with_retry(table_name, batch_data)

        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.assert_called_once_with(batch_data)

    @pytest.mark.asyncio
    async def test_insert_with_retry_success_after_retries(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test successful insert after retries"""
        table_name = "test_table"
        batch_data = [{"id": 1, "data": "test"}]

        table_mock = mock_supabase_client.table.return_value
        # Fail first 2 attempts, succeed on 3rd
        table_mock.insert.return_value.execute.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            MagicMock(),  # Success
        ]

        with patch("time.sleep"):  # Mock sleep to speed up test
            await supabase_adapter._insert_with_retry(table_name, batch_data)

        assert table_mock.insert.call_count == 3

    @pytest.mark.asyncio
    async def test_insert_with_retry_fallback_to_individual(
        self,
        supabase_adapter,
        mock_supabase_client,
    ):
        """Test insert with retry falls back to individual inserts after all batch attempts fail"""
        table_name = "test_table"
        batch_data = [{"id": 1, "data": "test1"}, {"id": 2, "data": "test2"}]

        table_mock = mock_supabase_client.table.return_value
        # All batch attempts fail
        table_mock.insert.return_value.execute.side_effect = Exception(
            "Batch insert failed",
        )

        with patch("time.sleep"):  # Mock sleep to speed up test
            await supabase_adapter._insert_with_retry(table_name, batch_data)

        # Should attempt batch insert max_retries times, then individual inserts
        expected_calls = supabase_adapter.max_retries + len(batch_data)
        assert table_mock.insert.call_count == expected_calls


class TestDatabaseAdapterEdgeCases:
    """Test edge cases and error scenarios for both adapters"""

    @pytest.mark.asyncio
    async def test_empty_data_handling_qdrant(self):
        """Test QdrantAdapter handles empty data gracefully"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()
        adapter.client = MagicMock()
        adapter.client.scroll.return_value = ([], None)

        # Test with empty lists
        await adapter.add_documents([], [], [], [], [], [])

        # Should not call upsert with empty data
        adapter.client.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_data_handling_supabase(self):
        """Test SupabaseAdapter handles empty data gracefully"""
        from database.supabase_adapter import SupabaseAdapter

        adapter = SupabaseAdapter()
        adapter.client = MagicMock()

        # Test with empty lists
        await adapter.add_documents([], [], [], [], [], [])

        # Should not make database calls with empty data
        adapter.client.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_large_batch_processing_qdrant(self):
        """Test QdrantAdapter handles very large batches correctly"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()
        adapter.client = MagicMock()
        adapter.client.scroll.return_value = ([], None)
        adapter.batch_size = 10  # Small batch size for testing

        # Create large dataset
        size = 25
        urls = [f"https://test.com/{i}" for i in range(size)]
        chunk_numbers = list(range(size))
        contents = [f"Content {i}" for i in range(size)]
        metadatas = [{"index": i} for i in range(size)]
        embeddings = [[0.1] * 1536 for _ in range(size)]
        source_ids = ["test.com"] * size

        await adapter.add_documents(
            urls,
            chunk_numbers,
            contents,
            metadatas,
            embeddings,
            source_ids,
        )

        # Should call upsert multiple times due to batching
        expected_batches = (size + adapter.batch_size - 1) // adapter.batch_size
        assert adapter.client.upsert.call_count == expected_batches

    @pytest.mark.asyncio
    async def test_concurrent_operations_qdrant(self):
        """Test QdrantAdapter handles concurrent operations"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()
        adapter.client = MagicMock()
        adapter.client.scroll.return_value = ([], None)
        adapter.client.search.return_value = []

        # Simulate concurrent operations
        tasks = []
        for i in range(5):
            task = adapter.add_documents(
                [f"https://test.com/{i}"],
                [1],
                [f"Content {i}"],
                [{}],
                [[0.1] * 1536],
                ["test.com"],
            )
            tasks.append(task)

        # All should complete without errors
        await asyncio.gather(*tasks)

        assert adapter.client.upsert.call_count == 5

    @pytest.mark.asyncio
    async def test_malformed_embeddings_qdrant(self):
        """Test QdrantAdapter handles malformed embeddings"""
        from database.qdrant_adapter import QdrantAdapter

        adapter = QdrantAdapter()
        adapter.client = MagicMock()
        adapter.client.scroll.return_value = ([], None)

        # Test with wrong embedding dimension
        wrong_embeddings = [[0.1] * 100]  # Wrong size

        await adapter.add_documents(
            ["https://test.com"],
            [1],
            ["Content"],
            [{}],
            wrong_embeddings,
            ["test.com"],
        )

        # Should still call upsert (Qdrant will handle the validation)
        adapter.client.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_unicode_content_handling(self):
        """Test both adapters handle unicode content correctly"""
        from database.qdrant_adapter import QdrantAdapter
        from database.supabase_adapter import SupabaseAdapter

        unicode_content = "测试内容 🚀 émojis and spéciål characters"

        # Test QdrantAdapter
        qdrant_adapter = QdrantAdapter()
        qdrant_adapter.client = MagicMock()
        qdrant_adapter.client.scroll.return_value = ([], None)

        await qdrant_adapter.add_documents(
            ["https://test.com"],
            [1],
            [unicode_content],
            [{}],
            [[0.1] * 1536],
            ["test.com"],
        )

        qdrant_adapter.client.upsert.assert_called_once()

        # Test SupabaseAdapter
        supabase_adapter = SupabaseAdapter()
        supabase_adapter.client = MagicMock()
        table_mock = supabase_adapter.client.table.return_value
        table_mock.delete.return_value.in_.return_value.execute.return_value = (
            MagicMock()
        )

        await supabase_adapter.add_documents(
            ["https://test.com"],
            [1],
            [unicode_content],
            [{}],
            [[0.1] * 1536],
            ["test.com"],
        )

        table_mock.insert.assert_called_once()


# Mark the update_todo task as completed
@pytest.fixture(autouse=True)
def update_todo_progress():
    """Update todo progress as tests are created"""
    # This fixture runs automatically and can be used to track progress
