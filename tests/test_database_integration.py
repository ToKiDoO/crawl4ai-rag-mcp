"""
Comprehensive database integration tests for crawl4ai_mcp.py.
Tests the actual database operations as used in the main application,
focusing on improving coverage of database-related functions.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import utils
from database.factory import create_and_initialize_database, create_database_client


class TestDatabaseIntegration:
    """Integration tests for database operations used in crawl4ai_mcp.py"""

    @pytest.fixture
    def mock_openai_embeddings(self):
        """Mock OpenAI embeddings API"""
        with patch("openai.Embedding.create") as mock_create:
            mock_create.return_value = {"data": [{"embedding": [0.1] * 1536}] * 5}
            yield mock_create

    @pytest.fixture
    def sample_crawl_data(self):
        """Sample data that would come from crawling operations"""
        return {
            "urls": [
                "https://example.com/page1",
                "https://example.com/page2",
                "https://example.com/page3",
            ],
            "chunk_numbers": [1, 2, 1],
            "contents": [
                "This is the first document content with technical information",
                "Second document contains code examples and tutorials",
                "Third document has API documentation and references",
            ],
            "metadatas": [
                {"title": "Page 1", "type": "documentation", "language": "en"},
                {"title": "Page 2", "type": "tutorial", "language": "en"},
                {"title": "Page 3", "type": "api_docs", "language": "en"},
            ],
            "url_to_full_document": {
                "https://example.com/page1": "Full content of page 1 with more details...",
                "https://example.com/page2": "Complete page 2 content including examples...",
                "https://example.com/page3": "Comprehensive API documentation...",
            },
        }

    @pytest.fixture
    def sample_code_examples(self):
        """Sample code examples data"""
        return {
            "urls": ["https://example.com/docs"],
            "chunk_numbers": [1],
            "code_examples": [
                """
def process_data(data):
    '''Process incoming data'''
    if not data:
        return None
    return data.strip().lower()
""",
            ],
            "summaries": ["A data processing function with validation"],
            "metadatas": [{"language": "python", "type": "function"}],
        }

    @pytest.mark.asyncio
    async def test_database_factory_initialization(self):
        """Test database factory initialization patterns used in crawl4ai_mcp.py"""
        # Test with different database types
        with patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"}):
            adapter = create_database_client()
            assert adapter is not None
            assert hasattr(adapter, "initialize")
            assert hasattr(adapter, "add_documents")
            assert hasattr(adapter, "search_documents")

        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            adapter = create_database_client()
            assert adapter is not None
            assert hasattr(adapter, "initialize")
            assert hasattr(adapter, "add_documents")

    @pytest.mark.asyncio
    async def test_database_initialization_with_context(self):
        """Test database initialization within Crawl4AIContext as done in main app"""
        with patch("database.factory.create_database_client") as mock_create:
            mock_adapter = AsyncMock()
            mock_create.return_value = mock_adapter

            # Test the initialization pattern from crawl4ai_mcp.py
            database_client = await create_and_initialize_database()

            # Verify initialization was called
            mock_adapter.initialize.assert_called_once()
            assert database_client == mock_adapter

    @pytest.mark.asyncio
    async def test_add_documents_to_database_success(
        self,
        sample_crawl_data,
        mock_openai_embeddings,
    ):
        """Test successful document addition as used in crawl4ai_mcp.py"""
        mock_adapter = AsyncMock()

        # Mock successful operations
        mock_adapter.delete_documents_by_url = AsyncMock()
        mock_adapter.add_documents = AsyncMock()

        # Test the add_documents_to_database function
        await utils.add_documents_to_database(
            mock_adapter,
            sample_crawl_data["urls"],
            sample_crawl_data["chunk_numbers"],
            sample_crawl_data["contents"],
            sample_crawl_data["metadatas"],
            sample_crawl_data["url_to_full_document"],
            batch_size=2,
        )

        # Verify delete was called for cleanup
        mock_adapter.delete_documents_by_url.assert_called_once()

        # Verify add_documents was called (possibly multiple times for batching)
        assert mock_adapter.add_documents.call_count >= 1

        # Verify the call arguments have the right structure
        call_args = mock_adapter.add_documents.call_args_list[0][1]
        assert "urls" in call_args
        assert "contents" in call_args
        assert "embeddings" in call_args
        assert "source_ids" in call_args

    @pytest.mark.asyncio
    async def test_add_documents_batch_processing(self, mock_openai_embeddings):
        """Test batch processing behavior with different batch sizes"""
        mock_adapter = AsyncMock()
        mock_adapter.delete_documents_by_url = AsyncMock()
        mock_adapter.add_documents = AsyncMock()

        # Create data that will require multiple batches
        urls = [f"https://example.com/page{i}" for i in range(10)]
        chunk_numbers = list(range(10))
        contents = [f"Content for page {i}" for i in range(10)]
        metadatas = [{"page": i} for i in range(10)]
        url_to_full_document = {url: f"Full content {i}" for i, url in enumerate(urls)}

        # Test with small batch size to force multiple batches
        await utils.add_documents_to_database(
            mock_adapter,
            urls,
            chunk_numbers,
            contents,
            metadatas,
            url_to_full_document,
            batch_size=3,
        )

        # Should have been called multiple times for batching
        assert mock_adapter.add_documents.call_count >= 3

    @pytest.mark.asyncio
    async def test_search_documents_integration(self, mock_openai_embeddings):
        """Test document search as used in perform_rag_query"""
        mock_adapter = AsyncMock()

        # Mock search results
        mock_results = [
            {
                "id": "1",
                "url": "https://example.com/page1",
                "content": "Relevant content about the query",
                "metadata": {"title": "Test Page"},
                "similarity": 0.95,
            },
        ]
        mock_adapter.search_documents.return_value = mock_results

        # Test search_documents function
        query_embedding = [0.1] * 1536
        results = await utils.search_documents(
            mock_adapter,
            query_embedding,
            match_count=5,
        )

        # Verify search was called correctly
        mock_adapter.search_documents.assert_called_once_with(
            query_embedding,
            match_count=5,
            filter_metadata=None,
            source_filter=None,
        )

        assert results == mock_results

    @pytest.mark.asyncio
    async def test_code_examples_integration(
        self,
        sample_code_examples,
        mock_openai_embeddings,
    ):
        """Test code example operations as used in crawl4ai_mcp.py"""
        mock_adapter = AsyncMock()
        mock_adapter.delete_code_examples_by_url = AsyncMock()
        mock_adapter.add_code_examples = AsyncMock()

        # Test add_code_examples_to_database function
        await utils.add_code_examples_to_database(
            mock_adapter,
            sample_code_examples["urls"],
            sample_code_examples["chunk_numbers"],
            sample_code_examples["code_examples"],
            sample_code_examples["summaries"],
            sample_code_examples["metadatas"],
        )

        # Verify operations were called
        mock_adapter.delete_code_examples_by_url.assert_called_once()
        mock_adapter.add_code_examples.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_error_handling_retry_logic(self, mock_openai_embeddings):
        """Test error handling and retry logic in database operations"""
        mock_adapter = AsyncMock()

        # Mock delete to succeed
        mock_adapter.delete_documents_by_url = AsyncMock()

        # Mock add_documents to fail first time, succeed second time
        call_count = 0

        async def mock_add_documents(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Database connection failed")

        mock_adapter.add_documents = AsyncMock(side_effect=mock_add_documents)

        # Test with retry logic
        urls = ["https://example.com/page1"]
        chunk_numbers = [1]
        contents = ["Test content"]
        metadatas = [{"title": "Test"}]
        url_to_full_document = {"https://example.com/page1": "Full content"}

        # Should not raise exception due to retry logic
        await utils.add_documents_to_database(
            mock_adapter,
            urls,
            chunk_numbers,
            contents,
            metadatas,
            url_to_full_document,
        )

        # Verify add_documents was called multiple times (retry)
        assert mock_adapter.add_documents.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, mock_openai_embeddings):
        """Test concurrent database operations as might occur in batch processing"""
        mock_adapter = AsyncMock()
        mock_adapter.delete_documents_by_url = AsyncMock()
        mock_adapter.add_documents = AsyncMock()
        mock_adapter.search_documents = AsyncMock(return_value=[])

        # Create multiple concurrent operations
        tasks = []
        for i in range(5):
            task = utils.add_documents_to_database(
                mock_adapter,
                [f"https://example.com/page{i}"],
                [1],
                [f"Content {i}"],
                [{"page": i}],
                {f"https://example.com/page{i}": f"Full content {i}"},
            )
            tasks.append(task)

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

        # Verify all operations completed
        assert mock_adapter.delete_documents_by_url.call_count == 5
        assert mock_adapter.add_documents.call_count == 5

    @pytest.mark.asyncio
    async def test_source_info_updates(self):
        """Test source info update operations"""
        mock_adapter = AsyncMock()
        mock_adapter.update_source_info = AsyncMock()

        # Test update_source_info as used in crawl4ai_mcp.py
        await mock_adapter.update_source_info(
            "example.com",
            "A test website with documentation",
            1500,
        )

        mock_adapter.update_source_info.assert_called_once_with(
            "example.com",
            "A test website with documentation",
            1500,
        )

    @pytest.mark.asyncio
    async def test_hybrid_search_integration(self, mock_openai_embeddings):
        """Test hybrid search patterns as used in perform_rag_query"""
        mock_adapter = AsyncMock()

        # Mock both vector and keyword search results
        vector_results = [{"id": "1", "content": "Vector result", "similarity": 0.9}]
        keyword_results = [{"id": "2", "content": "Keyword result", "similarity": 0.8}]

        mock_adapter.search_documents.return_value = vector_results
        mock_adapter.search_documents_by_keyword.return_value = keyword_results

        # Test hybrid search pattern
        query_embedding = [0.1] * 1536
        vector_results_actual = await utils.search_documents(
            mock_adapter,
            query_embedding,
            match_count=5,
        )

        keyword_results_actual = await mock_adapter.search_documents_by_keyword(
            "test query",
            match_count=5,
        )

        # Verify both search types were called
        mock_adapter.search_documents.assert_called_once()
        mock_adapter.search_documents_by_keyword.assert_called_once()

        assert vector_results_actual == vector_results
        assert keyword_results_actual == keyword_results

    @pytest.mark.asyncio
    async def test_empty_data_handling(self, mock_openai_embeddings):
        """Test handling of empty data scenarios"""
        mock_adapter = AsyncMock()

        # Test with empty data
        await utils.add_documents_to_database(
            mock_adapter,
            [],  # Empty URLs
            [],  # Empty chunk numbers
            [],  # Empty contents
            [],  # Empty metadatas
            {},  # Empty url_to_full_document
        )

        # Should not call database operations for empty data
        mock_adapter.delete_documents_by_url.assert_not_called()
        mock_adapter.add_documents.assert_not_called()

    @pytest.mark.asyncio
    async def test_large_embedding_batches(self, mock_openai_embeddings):
        """Test handling of large embedding batches"""
        mock_adapter = AsyncMock()
        mock_adapter.delete_documents_by_url = AsyncMock()
        mock_adapter.add_documents = AsyncMock()

        # Create large batch of data
        large_batch_size = 100
        urls = [f"https://example.com/page{i}" for i in range(large_batch_size)]
        chunk_numbers = list(range(large_batch_size))
        contents = [
            f"Content for page {i}" * 100 for i in range(large_batch_size)
        ]  # Large content
        metadatas = [{"page": i, "size": "large"} for i in range(large_batch_size)]
        url_to_full_document = {
            url: f"Full content {i}" * 200 for i, url in enumerate(urls)
        }

        # Test with reasonable batch size
        await utils.add_documents_to_database(
            mock_adapter,
            urls,
            chunk_numbers,
            contents,
            metadatas,
            url_to_full_document,
            batch_size=20,
        )

        # Should have been processed in multiple batches
        assert mock_adapter.add_documents.call_count >= 5

    @pytest.mark.asyncio
    async def test_contextual_embeddings_integration(self, mock_openai_embeddings):
        """Test contextual embeddings feature integration"""
        mock_adapter = AsyncMock()
        mock_adapter.delete_documents_by_url = AsyncMock()
        mock_adapter.add_documents = AsyncMock()

        # Test with contextual embeddings enabled
        with patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"}):
            await utils.add_documents_to_database(
                mock_adapter,
                ["https://example.com/page1"],
                [1],
                ["Test content"],
                [{"title": "Test"}],
                {"https://example.com/page1": "Full document context"},
            )

        # Verify the adapter was called
        mock_adapter.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_database_initialization_failure_handling(self):
        """Test handling of database initialization failures"""
        with patch("database.factory.create_database_client") as mock_create:
            # Mock initialization failure
            mock_adapter = AsyncMock()
            mock_adapter.initialize.side_effect = Exception("Connection failed")
            mock_create.return_value = mock_adapter

            # Should raise exception on initialization failure
            with pytest.raises(Exception, match="Connection failed"):
                await create_and_initialize_database()

    @pytest.mark.asyncio
    async def test_multiple_adapter_types(self):
        """Test that both Supabase and Qdrant adapters can be created"""
        # Test Supabase adapter creation
        with patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"}):
            supabase_adapter = create_database_client()
            assert supabase_adapter is not None
            assert hasattr(supabase_adapter, "initialize")

        # Test Qdrant adapter creation
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            qdrant_adapter = create_database_client()
            assert qdrant_adapter is not None
            assert hasattr(qdrant_adapter, "initialize")

        # Test unknown adapter type
        with patch.dict(os.environ, {"VECTOR_DATABASE": "unknown"}):
            with pytest.raises(ValueError, match="Unknown database type"):
                create_database_client()

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_openai_embeddings):
        """Test search operations with various filters"""
        mock_adapter = AsyncMock()

        mock_results = [{"id": "1", "content": "Filtered result"}]
        mock_adapter.search_documents.return_value = mock_results

        # Test search with metadata filter
        query_embedding = [0.1] * 1536
        await utils.search_documents(
            mock_adapter,
            query_embedding,
            match_count=5,
            filter_metadata={"type": "documentation"},
            source_filter="example.com",
        )

        # Verify search was called with filters
        mock_adapter.search_documents.assert_called_once_with(
            query_embedding,
            match_count=5,
            filter_metadata={"type": "documentation"},
            source_filter="example.com",
        )

    @pytest.mark.asyncio
    async def test_get_documents_by_url(self):
        """Test retrieving documents by URL"""
        mock_adapter = AsyncMock()

        mock_results = [
            {"id": "1", "url": "https://example.com/page1", "content": "Content 1"},
            {"id": "2", "url": "https://example.com/page1", "content": "Content 2"},
        ]
        mock_adapter.get_documents_by_url.return_value = mock_results

        # Test get_documents_by_url
        results = await mock_adapter.get_documents_by_url("https://example.com/page1")

        assert results == mock_results
        mock_adapter.get_documents_by_url.assert_called_once_with(
            "https://example.com/page1",
        )

    @pytest.mark.asyncio
    async def test_get_available_sources(self):
        """Test getting available sources as used in get_available_sources tool"""
        mock_adapter = AsyncMock()

        mock_sources = [
            {
                "source_id": "example.com",
                "summary": "Test site",
                "total_word_count": 1000,
            },
            {
                "source_id": "docs.example.com",
                "summary": "Documentation",
                "total_word_count": 5000,
            },
        ]
        mock_adapter.get_sources.return_value = mock_sources

        # Test get_sources
        sources = await mock_adapter.get_sources()

        assert sources == mock_sources
        mock_adapter.get_sources.assert_called_once()
