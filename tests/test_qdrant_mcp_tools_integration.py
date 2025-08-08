"""
Qdrant integration tests for MCP tools in crawl4ai_mcp.py.
Tests the actual MCP tools with Qdrant backend to ensure end-to-end functionality.
"""

import asyncio
import json
import os
import sys
import time
from unittest.mock import Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


import crawl4ai_mcp

from database.factory import create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter
from tests.test_qdrant_config import get_qdrant_url, requires_qdrant


class MockContext:
    """Mock MCP context for testing"""

    def __init__(self, database_client):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()
        self.request_context.lifespan_context.database_client = database_client
        self.request_context.lifespan_context.crawler = Mock()
        self.request_context.lifespan_context.reranking_model = None
        self.request_context.lifespan_context.knowledge_validator = None
        self.request_context.lifespan_context.repo_extractor = None


@requires_qdrant
class TestQdrantMCPToolsIntegration:
    """Test MCP tools integration with Qdrant database"""

    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = get_qdrant_url()
        os.environ["QDRANT_API_KEY"] = ""
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
        os.environ["USE_RERANKING"] = "false"
        os.environ["USE_HYBRID_SEARCH"] = "false"
        os.environ["USE_CONTEXTUAL_EMBEDDINGS"] = "false"
        os.environ["USE_AGENTIC_RAG"] = "false"
        os.environ["MODEL_CHOICE"] = "gpt-4.1-nano-2025-04-14"

    @pytest.fixture
    async def qdrant_database(self):
        """Create and initialize Qdrant database for testing"""
        database = await create_and_initialize_database()
        assert isinstance(database, QdrantAdapter)

        # Clean up any existing test data
        await self._cleanup_test_data(database)

        yield database

        # Clean up after test
        await self._cleanup_test_data(database)

    async def _cleanup_test_data(self, database: QdrantAdapter):
        """Clean up test data from Qdrant"""
        test_urls = [
            "https://mcp-test.example.com",
            "https://search-test.example.com",
            "https://code-test.example.com",
        ]

        for url in test_urls:
            try:
                await database.delete_documents_by_url(url)
            except Exception:
                pass  # Ignore cleanup errors

    @pytest.mark.asyncio
    async def test_search_crawled_pages_tool_with_qdrant(self, qdrant_database):
        """Test the search_crawled_pages MCP tool with Qdrant backend"""
        database = qdrant_database
        ctx = MockContext(database)

        # First, store some test documents
        test_embedding = [0.1] * 1536

        await database.add_documents(
            urls=[
                "https://search-test.example.com/doc1",
                "https://search-test.example.com/doc2",
            ],
            chunk_numbers=[1, 1],
            contents=[
                "Python async programming with asyncio and coroutines",
                "JavaScript promises and async await patterns",
            ],
            metadatas=[
                {"title": "Python Async Guide", "language": "python"},
                {"title": "JavaScript Async Guide", "language": "javascript"},
            ],
            embeddings=[test_embedding, [0.2] * 1536],
        )

        await asyncio.sleep(1)  # Allow indexing

        # Mock the search embedding to match our test data
        with patch("utils.create_embedding", return_value=test_embedding):
            # Test the actual MCP tool
            result = await crawl4ai_mcp.search_crawled_pages(
                ctx=ctx,
                query="Python async programming",
                source="search-test.example.com",
                match_count=5,
            )

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify the search results
        assert result_data["success"] is True
        assert "results" in result_data
        assert len(result_data["results"]) >= 1

        # Check the first result
        first_result = result_data["results"][0]
        assert "Python async programming" in first_result["content"]
        assert first_result["metadata"]["language"] == "python"
        assert "similarity_score" in first_result

    @pytest.mark.asyncio
    async def test_get_available_sources_tool_with_qdrant(self, qdrant_database):
        """Test the get_available_sources MCP tool with Qdrant backend"""
        database = qdrant_database
        ctx = MockContext(database)

        # Add some source information
        await database.update_source_info(
            source_id="mcp-test.example.com",
            summary="Test website for MCP integration",
            word_count=2500,
        )

        await asyncio.sleep(1)

        # Test the MCP tool
        result = await crawl4ai_mcp.get_available_sources(ctx=ctx)

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify the results
        assert result_data["success"] is True
        assert "sources" in result_data

        # Find our test source
        test_sources = [
            s
            for s in result_data["sources"]
            if s["source_id"] == "mcp-test.example.com"
        ]
        assert len(test_sources) == 1

        test_source = test_sources[0]
        assert test_source["summary"] == "Test website for MCP integration"
        assert test_source["total_word_count"] == 2500

    @pytest.mark.asyncio
    async def test_search_code_examples_tool_with_qdrant(self, qdrant_database):
        """Test the search_code_examples MCP tool with Qdrant backend"""
        database = qdrant_database
        ctx = MockContext(database)

        # Add some code examples
        test_embedding = [0.1] * 1536

        await database.add_code_examples(
            urls=["https://code-test.example.com/example1"],
            chunk_numbers=[1],
            codes=[
                """
async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
""",
            ],
            summaries=["Async function to fetch JSON data from URL"],
            metadatas=[{"language": "python", "framework": "aiohttp"}],
            embeddings=[test_embedding],
        )

        await asyncio.sleep(1)

        # Mock the search embedding
        with patch("utils.create_embedding", return_value=test_embedding):
            # Test the MCP tool
            result = await crawl4ai_mcp.search_code_examples(
                ctx=ctx,
                query="async fetch data aiohttp",
                match_count=3,
            )

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify the results
        assert result_data["success"] is True
        assert "code_examples" in result_data
        assert len(result_data["code_examples"]) >= 1

        # Check the first result
        code_example = result_data["code_examples"][0]
        assert "async def fetch_data" in code_example["code"]
        assert code_example["summary"] == "Async function to fetch JSON data from URL"
        assert code_example["metadata"]["language"] == "python"

    @pytest.mark.asyncio
    async def test_smart_crawl_url_tool_storage_with_qdrant(self, qdrant_database):
        """Test the smart_crawl_url MCP tool storage functionality with Qdrant"""
        database = qdrant_database
        ctx = MockContext(database)

        # Mock the crawler to return test data
        mock_crawl_results = [
            {
                "url": "https://mcp-test.example.com/page1",
                "markdown": "This is a test page about Python async programming.\n\n## Section 1\n\nContent about asyncio and coroutines.\n\n## Section 2\n\nMore content about async patterns.",
            },
        ]

        # Mock the smart_chunk_markdown function
        def mock_chunk_markdown(content, chunk_size=5000):
            # Split content into chunks for testing
            if len(content) > chunk_size:
                chunks = []
                for i in range(0, len(content), chunk_size):
                    chunks.append(content[i : i + chunk_size])
                return chunks
            return [content]

        # Mock all the crawler functions
        with (
            patch("crawl4ai_mcp.is_txt", return_value=False),
            patch("crawl4ai_mcp.is_sitemap", return_value=False),
            patch(
                "crawl4ai_mcp.crawl_recursive_internal_links",
                return_value=mock_crawl_results,
            ),
            patch("crawl4ai_mcp.smart_chunk_markdown", side_effect=mock_chunk_markdown),
            patch(
                "crawl4ai_mcp.extract_section_info",
                return_value={"word_count": 50, "section": "main"},
            ),
            patch(
                "crawl4ai_mcp.extract_source_summary",
                return_value="Test page summary",
            ),
            patch(
                "utils.create_embeddings_batch",
                return_value=[[0.1] * 1536],
            ),
        ):
            # Test the MCP tool
            result = await crawl4ai_mcp.smart_crawl_url(
                ctx=ctx,
                url="https://mcp-test.example.com/page1",
                max_depth=1,
                chunk_size=2000,
            )

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify the crawl was successful
        assert result_data["success"] is True
        assert "summary" in result_data
        assert result_data["summary"]["pages_crawled"] == 1
        assert result_data["summary"]["chunks_stored"] >= 1

        # Verify data was actually stored in Qdrant
        await asyncio.sleep(1)  # Allow indexing

        stored_docs = await database.get_documents_by_url(
            "https://mcp-test.example.com/page1",
        )
        assert len(stored_docs) >= 1

        # Verify content
        assert "Python async programming" in stored_docs[0]["content"]
        assert stored_docs[0]["metadata"]["source"] == "mcp-test.example.com"

    @pytest.mark.asyncio
    async def test_delete_source_tool_with_qdrant(self, qdrant_database):
        """Test the delete_source MCP tool with Qdrant backend"""
        database = qdrant_database
        ctx = MockContext(database)

        # First, add some test data
        await database.add_documents(
            urls=[
                "https://delete-test.example.com/doc1",
                "https://delete-test.example.com/doc2",
            ],
            chunk_numbers=[1, 1],
            contents=["Content to be deleted 1", "Content to be deleted 2"],
            metadatas=[{"test": "delete"}, {"test": "delete"}],
            embeddings=[[0.1] * 1536, [0.2] * 1536],
        )

        # Add source info
        await database.update_source_info(
            source_id="delete-test.example.com",
            summary="Source to be deleted",
            word_count=100,
        )

        await asyncio.sleep(1)

        # Verify data exists
        docs_before = await database.get_documents_by_url(
            "https://delete-test.example.com/doc1",
        )
        assert len(docs_before) >= 1

        # Test the delete_source MCP tool
        result = await crawl4ai_mcp.delete_source(
            ctx=ctx,
            source_id="delete-test.example.com",
        )

        # Parse the JSON result
        result_data = json.loads(result)

        # Verify deletion was successful
        assert result_data["success"] is True
        assert "delete-test.example.com" in result_data["message"]

        # Verify data was actually deleted
        await asyncio.sleep(1)

        docs_after = await database.get_documents_by_url(
            "https://delete-test.example.com/doc1",
        )
        assert len(docs_after) == 0

    @pytest.mark.asyncio
    async def test_error_handling_in_mcp_tools(self, qdrant_database):
        """Test error handling in MCP tools when Qdrant operations fail"""
        database = qdrant_database
        ctx = MockContext(database)

        # Mock a database operation to fail
        with patch.object(
            database,
            "search_documents",
            side_effect=Exception("Qdrant search failed"),
        ):
            # Test that errors are properly handled and returned
            result = await crawl4ai_mcp.search_crawled_pages(
                ctx=ctx,
                query="test query",
                match_count=5,
            )

            # Parse the JSON result
            result_data = json.loads(result)

            # Verify error is properly handled
            assert result_data["success"] is False
            assert "error" in result_data
            assert "Qdrant search failed" in str(result_data["error"])

    @pytest.mark.asyncio
    async def test_concurrent_mcp_tool_operations(self, qdrant_database):
        """Test concurrent MCP tool operations with Qdrant"""
        database = qdrant_database

        # Prepare test data
        test_embedding = [0.1] * 1536

        await database.add_documents(
            urls=[f"https://concurrent-test.example.com/doc{i}" for i in range(5)],
            chunk_numbers=[1] * 5,
            contents=[f"Document {i} content for concurrent testing" for i in range(5)],
            metadatas=[{"doc_id": i, "test": "concurrent"} for i in range(5)],
            embeddings=[[0.1 + i * 0.01] * 1536 for i in range(5)],
        )

        await asyncio.sleep(1)

        # Create multiple contexts for concurrent operations
        contexts = [MockContext(database) for _ in range(3)]

        async def concurrent_search(ctx, worker_id):
            """Perform concurrent searches"""
            with patch(
                "utils.create_embedding",
                return_value=test_embedding,
            ):
                result = await crawl4ai_mcp.search_crawled_pages(
                    ctx=ctx,
                    query=f"Document {worker_id} concurrent testing",
                    match_count=3,
                )
            return json.loads(result)

        # Run concurrent searches
        tasks = [concurrent_search(contexts[i], i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # Verify all searches completed successfully
        for i, result in enumerate(results):
            assert result["success"] is True
            assert len(result["results"]) >= 1

    @pytest.mark.asyncio
    async def test_large_dataset_performance_with_mcp_tools(self, qdrant_database):
        """Test MCP tool performance with larger datasets"""
        database = qdrant_database
        ctx = MockContext(database)

        # Add a larger dataset
        num_docs = 50

        await database.add_documents(
            urls=[f"https://perf-test.example.com/doc{i}" for i in range(num_docs)],
            chunk_numbers=[1] * num_docs,
            contents=[
                f"Performance test document {i} with topic {i % 5}"
                for i in range(num_docs)
            ],
            metadatas=[
                {"doc_id": i, "topic": f"topic_{i % 5}"} for i in range(num_docs)
            ],
            embeddings=[[0.1 + i * 0.001] * 1536 for i in range(num_docs)],
        )

        await asyncio.sleep(2)  # Allow indexing

        # Test search performance
        start_time = time.time()

        with patch("utils.create_embedding", return_value=[0.1] * 1536):
            result = await crawl4ai_mcp.search_crawled_pages(
                ctx=ctx,
                query="Performance test document topic",
                match_count=10,
            )

        search_time = time.time() - start_time

        # Parse result
        result_data = json.loads(result)

        # Verify performance and results
        assert result_data["success"] is True
        assert len(result_data["results"]) >= 5  # Should find multiple documents
        assert search_time < 5.0  # Should complete within 5 seconds

        print(
            f"Search completed in {search_time:.2f}s with {len(result_data['results'])} results",
        )

    @pytest.mark.asyncio
    async def test_qdrant_specific_features_in_mcp_tools(self, qdrant_database):
        """Test Qdrant-specific features through MCP tools"""
        database = qdrant_database
        ctx = MockContext(database)

        # Test with metadata filtering (Qdrant-specific filtering syntax)
        test_embedding = [0.1] * 1536

        await database.add_documents(
            urls=[
                "https://filter-test.example.com/doc1",
                "https://filter-test.example.com/doc2",
            ],
            chunk_numbers=[1, 1],
            contents=["Python programming guide", "Java programming guide"],
            metadatas=[
                {"language": "python", "level": "beginner", "category": "programming"},
                {"language": "java", "level": "advanced", "category": "programming"},
            ],
            embeddings=[test_embedding, [0.2] * 1536],
        )

        await asyncio.sleep(1)

        # Test search with metadata filter
        with patch("utils.create_embedding", return_value=test_embedding):
            result = await crawl4ai_mcp.search_crawled_pages(
                ctx=ctx,
                query="programming guide",
                source="filter-test.example.com",
                match_count=5,
            )

        result_data = json.loads(result)

        # Verify filtering works
        assert result_data["success"] is True
        assert len(result_data["results"]) >= 1

        # All results should be from the specified source
        for doc in result_data["results"]:
            assert "filter-test.example.com" in doc["url"]
