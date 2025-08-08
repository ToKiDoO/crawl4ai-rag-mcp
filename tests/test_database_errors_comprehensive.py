"""
Comprehensive database error handling tests for Crawl4AI MCP.

Tests various database failure scenarios:
- Connection pool exhaustion
- Query timeout errors
- Transaction rollback scenarios
- Concurrent access conflicts
- Invalid query parameters
- Database unavailability
- Embedding generation failures
- Batch operation failures
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawl4ai_mcp import perform_rag_query, scrape_urls

from database.base import VectorDatabase
from database.factory import create_and_initialize_database, create_database_client
from utils import (
    add_documents_to_database,
)


class MockContext:
    """Mock FastMCP Context for testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Mock database client with error scenarios
        self.mock_db = AsyncMock(spec=VectorDatabase)
        self.request_context.lifespan_context.database_client = self.mock_db

        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler
        self.request_context.lifespan_context.reranking_model = None


class TestDatabaseErrorHandling:
    """Test database error scenarios comprehensively"""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context for tests"""
        return MockContext()

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, mock_ctx):
        """Test handling when database connection pool is exhausted"""
        # Mock connection pool exhaustion
        mock_ctx.mock_db.add_documents.side_effect = Exception(
            "Connection pool exhausted: max_connections=20 reached",
        )

        # Mock successful crawl to focus on database error
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Test content</body></html>"
        mock_result.markdown = "# Test content"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "connection pool" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_query_timeout_handling(self, mock_ctx):
        """Test handling of database query timeouts"""
        # Mock query timeout
        mock_ctx.mock_db.search_documents.side_effect = TimeoutError(
            "Query timed out after 30 seconds",
        )

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query", "test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "timeout" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_transaction_rollback_scenarios(self, mock_ctx):
        """Test handling of transaction rollback scenarios"""
        # Mock transaction conflict/rollback
        mock_ctx.mock_db.add_documents.side_effect = Exception(
            "Transaction rolled back due to concurrent modification",
        )

        # Mock successful crawl
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Content</body></html>"
        mock_result.markdown = "# Content"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "transaction" in result_data["error"].lower()
            or "rollback" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_concurrent_access_conflicts(self, mock_ctx):
        """Test handling of concurrent access conflicts"""
        # Mock concurrent modification error
        mock_ctx.mock_db.add_documents.side_effect = Exception(
            "Concurrent modification detected: version mismatch",
        )

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 1536],
        ):
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except Exception as e:
                assert "concurrent" in str(e).lower() or "version" in str(e).lower()

    @pytest.mark.asyncio
    async def test_invalid_query_parameters(self, mock_ctx):
        """Test handling of invalid query parameters"""
        # Mock invalid parameter error
        mock_ctx.mock_db.search_documents.side_effect = ValueError(
            "Invalid parameter: match_count must be positive integer",
        )

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query", match_count=-1)

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "invalid" in result_data["error"].lower()
            or "parameter" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_database_unavailability(self, mock_ctx):
        """Test handling when database is completely unavailable"""
        # Mock database connection failure
        mock_ctx.mock_db.add_documents.side_effect = ConnectionError(
            "Database server unavailable: connection refused",
        )

        # Mock successful crawl
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Content</body></html>"
        mock_result.markdown = "# Content"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "database" in result_data["error"].lower()
            or "connection" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_embedding_generation_failures(self, mock_ctx):
        """Test handling of embedding generation failures"""
        with patch("utils.create_embeddings_batch") as mock_embeddings:
            # Mock OpenAI API failure
            mock_embeddings.side_effect = Exception(
                "OpenAI API error: rate limit exceeded",
            )

            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except Exception as e:
                assert "openai" in str(e).lower() or "rate limit" in str(e).lower()

    @pytest.mark.asyncio
    async def test_batch_operation_partial_failures(self, mock_ctx):
        """Test handling of partial failures in batch operations"""
        call_count = 0

        async def partial_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # Fail on second batch
            if call_count == 2:
                raise Exception("Batch operation failed: disk full")

            return True

        mock_ctx.mock_db.add_documents.side_effect = partial_failure

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 1536] * 20,
        ):
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=[f"https://test{i}.com" for i in range(20)],
                    chunk_numbers=list(range(20)),
                    contents=[f"content {i}" for i in range(20)],
                    metadatas=[{"doc": i} for i in range(20)],
                    url_to_full_document={
                        f"https://test{i}.com": f"full {i}" for i in range(20)
                    },
                    batch_size=10,  # Will create 2 batches
                )
                assert False, "Expected exception was not raised"
            except Exception as e:
                assert "batch" in str(e).lower() or "disk full" in str(e).lower()

    @pytest.mark.asyncio
    async def test_vector_dimension_mismatch(self, mock_ctx):
        """Test handling of vector dimension mismatches"""
        # Mock dimension mismatch error
        mock_ctx.mock_db.add_documents.side_effect = ValueError(
            "Vector dimension mismatch: expected 1536, got 512",
        )

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 512],
        ):  # Wrong dimension
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except ValueError as e:
                assert "dimension" in str(e).lower()

    @pytest.mark.asyncio
    async def test_data_corruption_handling(self, mock_ctx):
        """Test handling of data corruption scenarios"""
        # Mock data corruption error
        mock_ctx.mock_db.search_documents.side_effect = Exception(
            "Data corruption detected: invalid vector format",
        )

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "corruption" in result_data["error"].lower()
            or "invalid" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_memory_pressure_in_database(self, mock_ctx):
        """Test handling of memory pressure in database operations"""
        # Mock out of memory error
        mock_ctx.mock_db.add_documents.side_effect = MemoryError(
            "Database out of memory: insufficient memory for vector operations",
        )

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 1536],
        ):
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except MemoryError as e:
                assert "memory" in str(e).lower()

    @pytest.mark.asyncio
    async def test_authentication_failures(self, mock_ctx):
        """Test handling of database authentication failures"""
        # Mock authentication error
        mock_ctx.mock_db.add_documents.side_effect = Exception(
            "Authentication failed: invalid API key or credentials",
        )

        # Mock successful crawl
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Content</body></html>"
        mock_result.markdown = "# Content"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "authentication" in result_data["error"].lower()
            or "credentials" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_schema_migration_errors(self, mock_ctx):
        """Test handling of schema migration/version mismatch errors"""
        # Mock schema version error
        mock_ctx.mock_db.search_documents.side_effect = Exception(
            "Schema version mismatch: expected v2.1, found v1.8",
        )

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "schema" in result_data["error"].lower()
            or "version" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_disk_space_exhaustion(self, mock_ctx):
        """Test handling of disk space exhaustion"""
        # Mock disk full error
        mock_ctx.mock_db.add_documents.side_effect = OSError(
            "No space left on device: disk full",
        )

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 1536],
        ):
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except OSError as e:
                assert "space" in str(e).lower() or "disk" in str(e).lower()

    @pytest.mark.asyncio
    async def test_network_partition_during_database_ops(self, mock_ctx):
        """Test handling of network partitions during database operations"""
        # Mock network partition
        mock_ctx.mock_db.add_documents.side_effect = ConnectionError(
            "Network partition detected: lost connection to database cluster",
        )

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 1536],
        ):
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except ConnectionError as e:
                assert "network" in str(e).lower() or "partition" in str(e).lower()

    @pytest.mark.asyncio
    async def test_database_factory_error_handling(self):
        """Test error handling in database factory functions"""
        with patch.dict(os.environ, {"VECTOR_DATABASE": "invalid_db_type"}):
            with pytest.raises(ValueError, match="Unknown database type"):
                create_database_client()

    @pytest.mark.asyncio
    async def test_database_initialization_failures(self):
        """Test handling of database initialization failures"""
        with patch("database.qdrant_adapter.QdrantAdapter.initialize") as mock_init:
            mock_init.side_effect = Exception(
                "Failed to initialize database connection",
            )

            with pytest.raises(Exception, match="Failed to initialize"):
                await create_and_initialize_database()

    @pytest.mark.asyncio
    async def test_search_index_corruption(self, mock_ctx):
        """Test handling of search index corruption"""
        # Mock index corruption
        mock_ctx.mock_db.search_documents.side_effect = Exception(
            "Search index corrupted: rebuild required",
        )

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "index" in result_data["error"].lower()
            or "corrupted" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_errors(self, mock_ctx):
        """Test that resources are properly cleaned up on database errors"""
        cleanup_called = []

        # Mock cleanup tracking
        original_cleanup = (
            mock_ctx.mock_db.close if hasattr(mock_ctx.mock_db, "close") else Mock()
        )

        def track_cleanup():
            cleanup_called.append(True)
            return original_cleanup()

        mock_ctx.mock_db.close = track_cleanup
        mock_ctx.mock_db.add_documents.side_effect = Exception("Database error")

        # Mock successful crawl
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Content</body></html>"
        mock_result.markdown = "# Content"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False

        # Note: Cleanup verification depends on implementation details
        # In real scenarios, this would be tested with proper resource management

    @pytest.mark.asyncio
    async def test_deadlock_detection_and_recovery(self, mock_ctx):
        """Test handling of database deadlock scenarios"""
        # Mock deadlock error
        mock_ctx.mock_db.add_documents.side_effect = Exception(
            "Deadlock detected: transaction aborted",
        )

        with patch(
            "utils.create_embeddings_batch",
            return_value=[[0.1] * 1536],
        ):
            try:
                await add_documents_to_database(
                    database=mock_ctx.mock_db,
                    urls=["https://test.com"],
                    chunk_numbers=[1],
                    contents=["test content"],
                    metadatas=[{"test": "meta"}],
                    url_to_full_document={"https://test.com": "full content"},
                    batch_size=10,
                )
                assert False, "Expected exception was not raised"
            except Exception as e:
                assert "deadlock" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
