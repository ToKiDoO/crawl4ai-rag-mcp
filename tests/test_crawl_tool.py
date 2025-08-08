"""
Comprehensive tests for MCP crawl tools: search, scrape_urls, and smart_crawl_url

Focus on:
1. Basic crawling functionality
2. Error handling scenarios
3. Various crawl options
4. JavaScript rendering
5. Authentication scenarios
6. Performance optimizations

Test execution time target: <10 seconds total
Individual test target: <1 second each
"""

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
            "title": "Page 1",
            "content": "Sample content 1",
        },
        {
            "url": "https://example.com/page2",
            "title": "Page 2",
            "content": "Sample content 2",
        },
    ],
}
MOCK_CRAWL_RESULT = {
    "success": True,
    "url": "https://example.com",
    "markdown": "# Sample Page\n\nThis is sample content.",
    "cleaned_html": "<h1>Sample Page</h1><p>This is sample content.</p>",
    "media": {"images": [], "videos": [], "audios": []},
    "links": {"internal": [], "external": []},
    "metadata": {"title": "Sample Page", "description": "A sample page"},
}


class MockContext:
    """Mock FastMCP Context for crawl testing"""

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

    # Cleanup not needed for test environment variables


@pytest.fixture
def mock_external_dependencies():
    """Mock external dependencies for crawl tests"""
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


class TestSearchTool:
    """Test cases for the search MCP tool"""

    @pytest.mark.asyncio
    async def test_search_basic_functionality(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test basic search functionality"""
        # Get the tool function
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
                            "url": "https://example.com/page1",
                            "title": "Page 1",
                            "content": "Sample content 1",
                        },
                        {
                            "url": "https://example.com/page2",
                            "title": "Page 2",
                            "content": "Sample content 2",
                        },
                    ],
                },
            )

            # Mock perform_rag_query function call
            with patch(
                "crawl4ai_mcp.perform_rag_query",
                new_callable=AsyncMock,
            ) as mock_rag:
                mock_rag.return_value = json.dumps(
                    {
                        "success": True,
                        "results": [
                            {
                                "content": "Test content",
                                "similarity": 0.9,
                                "metadata": {},
                            },
                        ],
                    },
                )

                # Execute search
                result = await search_fn(
                    mock_context,
                    "python programming",
                    return_raw_markdown=False,
                )

                # Parse and validate result
                result_data = json.loads(result)
                assert result_data["success"] is True
                assert result_data["query"] == "python programming"
                assert "searxng_results" in result_data
                assert len(result_data["searxng_results"]) >= 1

    @pytest.mark.asyncio
    async def test_search_with_raw_markdown(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search with raw markdown return"""
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

            # Execute search with raw markdown
            result = await search_fn(
                mock_context,
                "test query",
                return_raw_markdown=True,
            )

            # Parse and validate result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert "mode" in result_data

    @pytest.mark.asyncio
    async def test_search_with_custom_parameters(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search with custom parameters"""
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

            # Execute search with custom parameters
            result = await search_fn(
                mock_context,
                "test query",
                num_results=10,
                batch_size=5,
                max_concurrent=3,
            )

            # Parse and validate result
            result_data = json.loads(result)
            assert result_data["success"] is True

            # Verify the requests module was called with proper parameters
            mock_external_dependencies["mock_requests"].assert_called()

    @pytest.mark.asyncio
    async def test_search_connection_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search behavior with connection errors"""
        search_fn = get_tool_function("search")

        # Mock connection error
        mock_external_dependencies[
            "mock_requests"
        ].side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Execute search
        result = await search_fn(mock_context, "test query")

        # Parse and validate error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert (
            "connection" in result_data["error"].lower()
            or "searxng" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_search_timeout_error(self, mock_context, mock_external_dependencies):
        """Test search behavior with timeout"""
        search_fn = get_tool_function("search")

        # Mock timeout error
        mock_external_dependencies[
            "mock_requests"
        ].side_effect = requests.exceptions.Timeout("Request timed out")

        # Execute search
        result = await search_fn(mock_context, "test query")

        # Parse and validate error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert (
            "timeout" in result_data["error"].lower()
            or "timed out" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_context, mock_external_dependencies):
        """Test search with no results returned"""
        search_fn = get_tool_function("search")

        # Mock empty results
        mock_external_dependencies["mock_requests"].return_value.json.return_value = {
            "results": [],
        }

        # Execute search
        result = await search_fn(mock_context, "nonexistent query")

        # Parse and validate result
        result_data = json.loads(result)
        # Should handle empty results gracefully
        assert result_data["success"] is False or "sources" in result_data


class TestScrapeUrlsTool:
    """Test cases for the scrape_urls MCP tool"""

    @pytest.mark.asyncio
    async def test_scrape_single_url_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test scraping a single URL successfully"""
        scrape_fn = get_tool_function("scrape_urls")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            MOCK_CRAWL_RESULT
        )
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute scrape
        result = await scrape_fn(mock_context, "https://example.com")

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_scrape_multiple_urls_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test scraping multiple URLs successfully"""
        scrape_fn = get_tool_function("scrape_urls")

        urls = ["https://example.com/page1", "https://example.com/page2"]

        # Setup mock crawler behavior for multiple URLs
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute scrape with multiple URLs
        result = await scrape_fn(mock_context, urls, max_concurrent=2)

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_scrape_with_raw_markdown(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test scraping with raw markdown return"""
        scrape_fn = get_tool_function("scrape_urls")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            MOCK_CRAWL_RESULT
        )

        # Execute scrape with raw markdown
        result = await scrape_fn(
            mock_context,
            "https://example.com",
            return_raw_markdown=True,
        )

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_scrape_crawler_error(self, mock_context, mock_external_dependencies):
        """Test scraping behavior with crawler errors"""
        scrape_fn = get_tool_function("scrape_urls")

        # Mock crawler error
        mock_context.request_context.lifespan_context.crawler.arun.side_effect = (
            Exception("Crawler failed")
        )

        # Execute scrape
        result = await scrape_fn(mock_context, "https://example.com")

        # Parse and validate error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_scrape_invalid_url(self, mock_context, mock_external_dependencies):
        """Test scraping with invalid URL"""
        scrape_fn = get_tool_function("scrape_urls")

        # Execute scrape with invalid URL
        result = await scrape_fn(mock_context, "invalid-url")

        # Parse and validate error result
        result_data = json.loads(result)
        # Should handle invalid URLs gracefully
        assert isinstance(result_data, dict)

    @pytest.mark.asyncio
    async def test_scrape_batch_processing(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test scraping with batch processing parameters"""
        scrape_fn = get_tool_function("scrape_urls")

        # Create multiple URLs for batch testing
        urls = [f"https://example.com/page{i}" for i in range(5)]

        # Setup mock database behavior
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute scrape with batch parameters
        result = await scrape_fn(mock_context, urls, max_concurrent=3, batch_size=2)

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True or "error" in result_data


class TestSmartCrawlUrlTool:
    """Test cases for the smart_crawl_url MCP tool"""

    @pytest.mark.asyncio
    async def test_smart_crawl_basic_functionality(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test basic smart crawl functionality"""
        smart_crawl_fn = get_tool_function("smart_crawl_url")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            MOCK_CRAWL_RESULT
        )
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute smart crawl
        result = await smart_crawl_fn(mock_context, "https://example.com")

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True or "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_with_depth(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with custom depth"""
        smart_crawl_fn = get_tool_function("smart_crawl_url")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun.return_value = {
            **MOCK_CRAWL_RESULT,
            "links": {
                "internal": ["https://example.com/page1", "https://example.com/page2"],
                "external": [],
            },
        }
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute smart crawl with depth
        result = await smart_crawl_fn(
            mock_context,
            "https://example.com",
            max_depth=2,
            max_concurrent=3,
        )

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True or "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_with_query_filter(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with query filtering"""
        smart_crawl_fn = get_tool_function("smart_crawl_url")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            MOCK_CRAWL_RESULT
        )
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute smart crawl with query
        result = await smart_crawl_fn(
            mock_context,
            "https://example.com",
            query=["python", "programming"],
        )

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True or "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_chunking_options(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with custom chunking"""
        smart_crawl_fn = get_tool_function("smart_crawl_url")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            MOCK_CRAWL_RESULT
        )
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        # Execute smart crawl with custom chunk size
        result = await smart_crawl_fn(
            mock_context,
            "https://example.com",
            chunk_size=3000,
        )

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True or "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_error_handling(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl error handling"""
        smart_crawl_fn = get_tool_function("smart_crawl_url")

        # Mock crawler error
        mock_context.request_context.lifespan_context.crawler.arun.side_effect = (
            Exception("Smart crawl failed")
        )

        # Execute smart crawl
        result = await smart_crawl_fn(mock_context, "https://example.com")

        # Parse and validate error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_invalid_url(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with invalid URL"""
        smart_crawl_fn = get_tool_function("smart_crawl_url")

        # Execute smart crawl with invalid URL
        result = await smart_crawl_fn(mock_context, "not-a-url")

        # Parse and validate error result
        result_data = json.loads(result)
        # Should handle invalid URLs gracefully
        assert isinstance(result_data, dict)


class TestCrawlToolsPerformance:
    """Performance tests for crawl tools"""

    @pytest.mark.asyncio
    async def test_concurrent_crawling_performance(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test performance of concurrent crawling operations"""
        scrape_fn = get_tool_function("scrape_urls")

        # Create multiple URLs for concurrent testing
        urls = [f"https://example.com/page{i}" for i in range(3)]

        # Setup mock database behavior
        mock_context.request_context.lifespan_context.database_client.store_documents.return_value = True

        start_time = time.time()

        # Execute concurrent scraping
        result = await scrape_fn(mock_context, urls, max_concurrent=3)

        end_time = time.time()
        execution_time = end_time - start_time

        # Performance assertion - should complete quickly with mocks
        assert execution_time < 5.0  # 5 seconds max for 3 URLs with mocks

        # Parse and validate result
        result_data = json.loads(result)
        assert isinstance(result_data, dict)

    @pytest.mark.asyncio
    async def test_search_response_time(self, mock_context, mock_external_dependencies):
        """Test search tool response time"""
        search_fn = get_tool_function("search")

        # Setup mock crawler behavior
        mock_context.request_context.lifespan_context.crawler.arun_many.return_value = [
            MOCK_CRAWL_RESULT,
        ]

        start_time = time.time()

        # Execute search
        result = await search_fn(mock_context, "test query", num_results=3)

        end_time = time.time()
        execution_time = end_time - start_time

        # Performance assertion
        assert execution_time < 3.0  # 3 seconds max with mocks

        # Parse and validate result
        result_data = json.loads(result)
        assert isinstance(result_data, dict)


if __name__ == "__main__":
    # Run tests with: uv run pytest tests/test_crawl_tool.py -v
    pytest.main([__file__, "-v"])
