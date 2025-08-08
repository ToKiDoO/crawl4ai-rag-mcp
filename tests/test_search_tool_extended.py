"""
Extended comprehensive tests for search MCP tool

Focus on:
1. Advanced search scenarios
2. Performance testing
3. Error recovery
4. Edge cases
5. Integration testing

Test execution time target: <10 seconds total
Individual test target: <1 second each
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import the module under test
import crawl4ai_mcp


def get_tool_function(tool_name: str):
    """Helper to extract actual function from FastMCP tool wrapper"""
    tool_attr = getattr(crawl4ai_mcp, tool_name, None)
    if hasattr(tool_attr, "fn"):
        return tool_attr.fn
    if callable(tool_attr):
        return tool_attr
    raise AttributeError(f"Cannot find callable function for {tool_name}")


# Shared test data for performance
MOCK_EMBEDDING = [0.1] * 1536
MOCK_SEARCH_RESPONSE = {
    "results": [
        {
            "url": "https://example.com/page1",
            "title": "Python Programming Guide",
            "content": "Learn Python programming",
        },
        {
            "url": "https://example.com/page2",
            "title": "JavaScript Tutorial",
            "content": "Master JavaScript",
        },
        {
            "url": "https://example.com/page3",
            "title": "Data Science",
            "content": "Python for data science",
        },
    ],
}


class MockContext:
    """Mock FastMCP Context for search testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Mock database client
        self.request_context.lifespan_context.database_client = AsyncMock()
        self.request_context.lifespan_context.database_client.store_documents = (
            AsyncMock()
        )
        self.request_context.lifespan_context.database_client.search_documents = (
            AsyncMock()
        )

        # Mock crawler with async context manager support
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun = AsyncMock()
        mock_crawler.arun_many = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler


@pytest.fixture
def mock_context():
    """Provide a mock FastMCP context for testing"""
    return MockContext()


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up test environment variables"""
    env_vars = {
        "SEARXNG_URL": "http://localhost:8888",
        "SEARXNG_USER_AGENT": "MCP-Crawl4AI-RAG-Server/1.0",
        "SEARXNG_TIMEOUT": "30",
        "OPENAI_API_KEY": "test-key-for-mocks",
        "VECTOR_DATABASE": "qdrant",
    }

    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value


@pytest.fixture
def mock_external_dependencies():
    """Mock external dependencies for search tests"""
    with (
        patch("requests.get") as mock_requests,
        patch("openai.embeddings.create") as mock_openai,
        patch("utils.create_embeddings_batch") as mock_embeddings_batch,
    ):
        # Mock OpenAI embeddings
        mock_response = Mock()
        mock_response.data = [Mock(embedding=MOCK_EMBEDDING)]
        mock_openai.return_value = mock_response
        mock_embeddings_batch.return_value = [MOCK_EMBEDDING]

        yield {
            "mock_requests": mock_requests,
            "mock_openai": mock_openai,
            "mock_embeddings_batch": mock_embeddings_batch,
        }


class TestSearchToolAdvanced:
    """Advanced test cases for the search MCP tool"""

    @pytest.mark.asyncio
    async def test_search_with_pagination(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search with various result limits"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {
                            "url": f"https://example.com/page{i}",
                            "content": f"Content {i}",
                        }
                        for i in range(15)
                    ],
                },
            )

            # Test different result limits
            for num_results in [1, 5, 10, 20]:
                result = await search_fn(
                    mock_context,
                    "test query",
                    num_results=num_results,
                )
                result_data = json.loads(result)

                assert result_data["success"] is True
                assert "searxng_results" in result_data

    @pytest.mark.asyncio
    async def test_search_with_batch_processing(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search with different batch sizes"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Test content"},
                    ],
                },
            )

            # Test different batch sizes
            for batch_size in [5, 10, 20]:
                result = await search_fn(
                    mock_context,
                    "test query",
                    batch_size=batch_size,
                    num_results=10,
                )
                result_data = json.loads(result)
                assert result_data["success"] is True

    @pytest.mark.asyncio
    async def test_search_concurrent_processing(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search with different concurrency levels"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Test content"},
                    ],
                },
            )

            # Test different concurrency levels
            for max_concurrent in [1, 3, 5, 10]:
                result = await search_fn(
                    mock_context,
                    "test query",
                    max_concurrent=max_concurrent,
                )
                result_data = json.loads(result)
                assert result_data["success"] is True

    @pytest.mark.asyncio
    async def test_search_rag_vs_raw_modes(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search in both RAG and raw markdown modes"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Test content"},
                    ],
                },
            )

            # Mock perform_rag_query for RAG mode
            with patch(
                "crawl4ai_mcp.perform_rag_query",
                new_callable=AsyncMock,
            ) as mock_rag:
                mock_rag.return_value = json.dumps(
                    {
                        "success": True,
                        "results": [{"content": "RAG result", "similarity": 0.9}],
                    },
                )

                # Test RAG mode
                result_rag = await search_fn(
                    mock_context,
                    "test query",
                    return_raw_markdown=False,
                )
                result_rag_data = json.loads(result_rag)
                assert result_rag_data["success"] is True

                # Test raw markdown mode
                result_raw = await search_fn(
                    mock_context,
                    "test query",
                    return_raw_markdown=True,
                )
                result_raw_data = json.loads(result_raw)
                assert result_raw_data["success"] is True

                # Both modes should succeed but potentially return different structures
                assert "mode" in result_rag_data or "searxng_results" in result_rag_data
                assert "mode" in result_raw_data or "searxng_results" in result_raw_data

    @pytest.mark.asyncio
    async def test_search_query_variations(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search with different query types and lengths"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Test content"},
                    ],
                },
            )

            # Test different query types
            test_queries = [
                "python",  # Short query
                "python programming tutorial",  # Medium query
                "how to learn python programming for data science and machine learning",  # Long query
                "python 3.11 async await performance",  # Technical query
                "what is the best way to optimize database queries in python",  # Question format
            ]

            for query in test_queries:
                result = await search_fn(mock_context, query)
                result_data = json.loads(result)
                assert result_data["success"] is True
                assert result_data["query"] == query


class TestSearchToolErrorHandling:
    """Error handling and edge case tests for search tool"""

    @pytest.mark.asyncio
    async def test_search_network_errors(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search behavior with various network errors"""
        search_fn = get_tool_function("search")

        network_errors = [
            (requests.exceptions.ConnectionError, "Connection failed"),
            (requests.exceptions.Timeout, "Request timed out"),
            (requests.exceptions.HTTPError, "HTTP error"),
            (requests.exceptions.RequestException, "General request error"),
        ]

        for error_class, error_msg in network_errors:
            mock_requests = mock_external_dependencies["mock_requests"]
            mock_requests.side_effect = error_class(error_msg)

            result = await search_fn(mock_context, "test query")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "error" in result_data
            assert len(result_data["error"]) > 0

    @pytest.mark.asyncio
    async def test_search_malformed_responses(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search behavior with malformed SearXNG responses"""
        search_fn = get_tool_function("search")

        # Test different malformed responses
        malformed_responses = [
            {},  # Empty response
            {"results": None},  # Null results
            {"results": "not a list"},  # Wrong type
            {"wrong_key": []},  # Missing results key
        ]

        for malformed_response in malformed_responses:
            mock_requests = mock_external_dependencies["mock_requests"]
            mock_response = Mock()
            mock_response.json.return_value = malformed_response
            mock_response.raise_for_status.return_value = None
            mock_requests.return_value = mock_response

            result = await search_fn(mock_context, "test query")
            result_data = json.loads(result)

            # Should handle malformed responses gracefully
            assert isinstance(result_data, dict)
            assert "success" in result_data

    @pytest.mark.asyncio
    async def test_search_scraping_failures(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search behavior when scraping fails"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search request
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls to fail
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {"success": False, "error": "Scraping failed"},
            )

            result = await search_fn(mock_context, "test query")
            result_data = json.loads(result)

            # Should handle scraping failures gracefully
            assert isinstance(result_data, dict)
            assert "success" in result_data

    @pytest.mark.asyncio
    async def test_search_empty_query(self, mock_context, mock_external_dependencies):
        """Test search behavior with empty or whitespace queries"""
        search_fn = get_tool_function("search")

        empty_queries = ["", "   ", "\t", "\n", None]

        for query in empty_queries:
            try:
                result = await search_fn(mock_context, query)
                result_data = json.loads(result)

                # Should handle empty queries gracefully
                assert isinstance(result_data, dict)
                assert "success" in result_data
            except (TypeError, ValueError):
                # Some empty queries might raise exceptions, which is acceptable
                pass


class TestSearchToolPerformance:
    """Performance tests for search tool"""

    @pytest.mark.asyncio
    async def test_search_response_time_limits(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search completes within reasonable time limits"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Test content"},
                    ],
                },
            )

            # Test performance with different loads
            test_cases = [
                (1, 5),  # 1 result, batch 5
                (5, 10),  # 5 results, batch 10
                (10, 20),  # 10 results, batch 20
            ]

            for num_results, batch_size in test_cases:
                start_time = time.time()

                result = await search_fn(
                    mock_context,
                    "performance test query",
                    num_results=num_results,
                    batch_size=batch_size,
                )

                end_time = time.time()
                execution_time = end_time - start_time

                # Should complete within reasonable time (with mocks)
                assert execution_time < 5.0  # 5 seconds max

                result_data = json.loads(result)
                assert result_data["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_search_requests(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test handling multiple concurrent search requests"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function call
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Test content"},
                    ],
                },
            )

            # Create multiple concurrent search tasks
            search_tasks = []
            for i in range(3):  # 3 concurrent requests
                task = search_fn(mock_context, f"concurrent query {i}")
                search_tasks.append(task)

            start_time = time.time()

            # Execute all searches concurrently
            results = await asyncio.gather(*search_tasks)

            end_time = time.time()
            execution_time = end_time - start_time

            # Should handle concurrent requests efficiently
            assert execution_time < 10.0  # 10 seconds max for 3 concurrent requests
            assert len(results) == 3

            # All results should be valid
            for result in results:
                result_data = json.loads(result)
                assert isinstance(result_data, dict)
                assert "success" in result_data

    @pytest.mark.asyncio
    async def test_search_memory_efficiency(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search doesn't consume excessive memory"""
        search_fn = get_tool_function("search")

        # Setup mocks for successful search
        mock_requests = mock_external_dependencies["mock_requests"]
        mock_response = Mock()
        mock_response.json.return_value = MOCK_SEARCH_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls with large content
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            # Simulate larger response
            large_results = []
            for i in range(20):
                large_results.append(
                    {
                        "url": f"https://example.com/page{i}",
                        "content": "Large content " * 100,  # Simulate larger content
                    },
                )

            mock_scrape.return_value = json.dumps(
                {"success": True, "results": large_results},
            )

            # Execute search with larger dataset
            result = await search_fn(
                mock_context,
                "memory efficiency test",
                num_results=20,
            )

            result_data = json.loads(result)
            assert result_data["success"] is True

            # Memory usage should be reasonable (this is a basic check)
            # In a real scenario, you might use memory profiling tools
            assert len(result) > 0  # Basic sanity check


if __name__ == "__main__":
    # Run tests with: uv run pytest tests/test_search_tool_extended.py -v
    pytest.main([__file__, "-v"])
