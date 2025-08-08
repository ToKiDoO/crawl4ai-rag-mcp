"""
Integration tests for SearXNG functionality.
Tests real HTTP requests to SearXNG search endpoint.
"""

import json
import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

# Import the MCP server and related functions
from crawl4ai_mcp import Crawl4AIContext, perform_rag_query, scrape_urls, search

# Mark all tests in this module as integration tests requiring SearXNG
pytestmark = [pytest.mark.integration, pytest.mark.searxng]


class MockContext:
    """Mock context for testing MCP tools"""

    def __init__(self, crawler=None, database_client=None, reranking_model=None):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = Crawl4AIContext(
            crawler=crawler or AsyncMock(),
            database_client=database_client or AsyncMock(),
            reranking_model=reranking_model,
            knowledge_validator=None,
            repo_extractor=None,
        )


class TestSearXNGIntegration:
    """Test suite for SearXNG integration."""

    @pytest.fixture
    def searxng_url(self):
        """Get SearXNG URL from environment or use test default."""
        return os.getenv("SEARXNG_TEST_URL", "http://localhost:8081")

    @pytest.fixture
    async def searxng_health_check(self, searxng_url):
        """Check if SearXNG is healthy before running tests."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{searxng_url}/healthz",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    if response.status != 200:
                        pytest.skip(f"SearXNG not healthy: {response.status}")
        except Exception as e:
            pytest.skip(f"SearXNG not available: {e}")

    async def test_searxng_search_basic(self, searxng_url, searxng_health_check):
        """Test basic search functionality with real SearXNG instance."""
        # Set the environment variable for the test
        with patch.dict(os.environ, {"SEARXNG_URL": searxng_url}):
            ctx = MockContext()
            result = await search(ctx, "python programming")

            # Parse the JSON result
            data = json.loads(result)

            # Verify basic response structure
            assert "results" in data
            assert isinstance(data["results"], list)
            assert len(data["results"]) > 0

            # Check first result structure
            first_result = data["results"][0]
            assert "url" in first_result
            assert "title" in first_result
            assert "content" in first_result

    async def test_searxng_connection_timeout(self):
        """Test handling of SearXNG connection timeout."""
        # Use a non-existent URL to trigger timeout
        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:9999"}):
            ctx = MockContext()
            result = await search(ctx, "test query")

            # Should return error JSON
            data = json.loads(result)
            assert data["success"] is False
            assert "error" in data["message"].lower()

    async def test_searxng_invalid_url(self):
        """Test handling of invalid SearXNG URL."""
        with patch.dict(os.environ, {"SEARXNG_URL": "not-a-valid-url"}):
            ctx = MockContext()
            result = await search(ctx, "test query")

            # Should return error JSON
            data = json.loads(result)
            assert data["success"] is False
            assert "error" in data["message"].lower()

    async def test_searxng_empty_results(self, searxng_url, searxng_health_check):
        """Test handling of empty search results."""
        # Use a very specific query unlikely to return results
        with patch.dict(os.environ, {"SEARXNG_URL": searxng_url}):
            ctx = MockContext()
            result = await search(ctx, "xyzabc123456789 nonexistentquery")

            # Parse the JSON result
            data = json.loads(result)

            # Should still have valid structure even with no results
            assert "results" in data
            assert isinstance(data["results"], list)
            # May or may not have results depending on search engine

    async def test_searxng_malformed_response(self, searxng_url, searxng_health_check):
        """Test handling of malformed JSON response from SearXNG."""
        # This would require mocking the actual HTTP response
        # Since we're testing against real SearXNG, we'll mock the session

        async def mock_get(*args, **kwargs):
            @asynccontextmanager
            async def mock_response():
                response = AsyncMock()
                response.status = 200
                response.text = AsyncMock(return_value="not valid json")
                yield response

            return mock_response()

        with patch.dict(os.environ, {"SEARXNG_URL": searxng_url}):
            with patch("aiohttp.ClientSession.get", side_effect=mock_get):
                ctx = MockContext()
                result = await search(ctx, "test query")

                # Should handle gracefully
                data = json.loads(result)
                assert data["success"] is False
                assert "error" in data["message"].lower()

    async def test_full_pipeline_search_scrape_store(
        self,
        searxng_url,
        searxng_health_check,
    ):
        """Test the full pipeline: search → scrape → store → RAG query."""
        # This test requires database to be available
        # Mock the database operations for isolation

        with patch.dict(os.environ, {"SEARXNG_URL": searxng_url}):
            # Step 1: Search for a topic
            ctx = MockContext()
            search_result = await search(ctx, "Python asyncio tutorial")
            search_data = json.loads(search_result)

            assert search_data.get(
                "success",
                True,
            )  # Default to True for backward compatibility
            assert len(search_data["results"]) > 0

            # Get first URL from results
            first_url = search_data["results"][0]["url"]

            # Step 2: Mock scraping since we don't want to hit real websites
            with patch("crawl4ai_mcp.AsyncWebCrawler") as mock_crawler_class:
                mock_crawler = AsyncMock()
                mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

                mock_result = AsyncMock()
                mock_result.success = True
                mock_result.markdown = (
                    "# Python Asyncio Tutorial\n\nThis is a test content about asyncio."
                )
                mock_result.metadata = {"title": "Test Page"}
                mock_result.media = {"images": [], "videos": []}
                mock_result.links = {"internal": [], "external": []}
                mock_crawler.arun.return_value = mock_result

                # Mock database operations
                with patch("crawl4ai_mcp.db_manager") as mock_db:
                    mock_db.add_documents = AsyncMock()
                    mock_db.search_documents = AsyncMock(
                        return_value=[
                            {
                                "content": "This is a test content about asyncio.",
                                "url": first_url,
                                "metadata": {"title": "Test Page"},
                                "similarity_score": 0.9,
                            },
                        ],
                    )

                    # Scrape the URL
                    scrape_result = await scrape_urls(ctx, first_url)
                    scrape_data = json.loads(scrape_result)

                    assert scrape_data["success"] is True
                    assert scrape_data["results"][0]["url"] == first_url

                    # Step 3: Perform RAG query
                    rag_result = await perform_rag_query(
                        ctx,
                        "What is asyncio?",
                        max_results=5,
                    )
                    rag_data = json.loads(rag_result)

                    assert rag_data["success"] is True
                    assert len(rag_data["results"]) > 0

    async def test_searxng_special_characters(self, searxng_url, searxng_health_check):
        """Test search with special characters and encoding."""
        with patch.dict(os.environ, {"SEARXNG_URL": searxng_url}):
            # Test with special characters
            queries = [
                "C++ programming",
                "Python & machine learning",
                "JavaScript (ES6)",
                "email@example.com search",
                "price: $100-$200",
            ]

            for query in queries:
                ctx = MockContext()
                result = await search(ctx, query)
                data = json.loads(result)

                # Should handle special characters properly
                assert "results" in data
                # Don't assert on result count as it may vary

    async def test_searxng_pagination(self, searxng_url, searxng_health_check):
        """Test search pagination parameters."""
        with patch.dict(os.environ, {"SEARXNG_URL": searxng_url}):
            # Note: SearXNG pagination support varies by engine
            # This test verifies the parameter is accepted
            ctx = MockContext()
            result = await search(ctx, "Python", num_results=20)
            data = json.loads(result)

            assert "results" in data
            # Results count may be limited by SearXNG configuration
            assert isinstance(data["results"], list)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-m", "searxng"])
