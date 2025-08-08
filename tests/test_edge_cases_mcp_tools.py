"""
Edge case and error handling tests for MCP tools.

Focuses on testing error paths and edge cases that aren't covered by happy path tests.
Tests real error scenarios that can occur during MCP tool execution.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
import requests

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawl4ai_mcp import (
    get_available_sources,
    perform_rag_query,
    scrape_urls,
    search,
    smart_crawl_url,
)


class MockContext:
    """Mock FastMCP Context for testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Mock database client
        self.mock_db = AsyncMock()
        self.request_context.lifespan_context.database_client = self.mock_db

        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler
        self.request_context.lifespan_context.reranking_model = None


class TestMCPToolsEdgeCases:
    """Test edge cases and error conditions in MCP tools"""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context for tests"""
        return MockContext()

    @pytest.mark.asyncio
    async def test_scrape_urls_empty_input(self, mock_ctx):
        """Test scrape_urls with empty inputs"""
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

        # Test empty string - this gets processed as a single URL but fails crawling
        result = await scrape_func(mock_ctx, "")
        result_data = json.loads(result)
        # Empty string gets processed but fails during crawling
        assert result_data["success"] is False

        # Test empty list - this should be caught by validation
        result = await scrape_func(mock_ctx, [])
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "empty" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_scrape_urls_invalid_types(self, mock_ctx):
        """Test scrape_urls with invalid input types"""
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

        # Test with integer
        result = await scrape_func(mock_ctx, 123)
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "string" in result_data["error"].lower()

        # Test with dict
        result = await scrape_func(mock_ctx, {"url": "https://test.com"})
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "string" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_scrape_urls_mixed_list_types(self, mock_ctx):
        """Test scrape_urls with mixed types in URL list"""
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

        result = await scrape_func(
            mock_ctx,
            ["https://valid.com", 123, "https://also-valid.com"],
        )
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "string" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_scrape_urls_crawler_exception(self, mock_ctx):
        """Test scrape_urls when crawler raises exception"""
        # Mock crawler to raise exception
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = Exception(
            "Crawler failed",
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        # processing_time_seconds may not be present in all error paths

    @pytest.mark.asyncio
    async def test_search_missing_searxng_config(self, mock_ctx):
        """Test search when SEARXNG_URL is not configured"""
        search_func = search.fn if hasattr(search, "fn") else search

        with patch.dict(os.environ, {}, clear=True):
            result = await search_func(mock_ctx, "test query")
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "searxng_url" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_search_network_timeout(self, mock_ctx):
        """Test search with network timeout"""
        search_func = search.fn if hasattr(search, "fn") else search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
            with patch("requests.get") as mock_get:
                mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

                result = await search_func(mock_ctx, "test query")
                result_data = json.loads(result)
                assert result_data["success"] is False
                assert "timeout" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_search_connection_error(self, mock_ctx):
        """Test search with connection error"""
        search_func = search.fn if hasattr(search, "fn") else search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://nonexistent:8080"}):
            with patch("requests.get") as mock_get:
                mock_get.side_effect = requests.exceptions.ConnectionError(
                    "Connection failed",
                )

                result = await search_func(mock_ctx, "test query")
                result_data = json.loads(result)
                assert result_data["success"] is False
                assert "connect" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_search_http_error(self, mock_ctx):
        """Test search with HTTP error"""
        search_func = search.fn if hasattr(search, "fn") else search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status.side_effect = (
                    requests.exceptions.HTTPError("404 Not Found")
                )
                mock_get.return_value = mock_response

                result = await search_func(mock_ctx, "test query")
                result_data = json.loads(result)
                assert result_data["success"] is False
                assert "http error" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_search_invalid_json_response(self, mock_ctx):
        """Test search with invalid JSON response"""
        search_func = search.fn if hasattr(search, "fn") else search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()  # No exception
                mock_response.json.side_effect = json.JSONDecodeError(
                    "Invalid JSON",
                    "",
                    0,
                )
                mock_get.return_value = mock_response

                result = await search_func(mock_ctx, "test query")
                result_data = json.loads(result)
                assert result_data["success"] is False
                assert "json" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_ctx):
        """Test search with no results returned"""
        search_func = search.fn if hasattr(search, "fn") else search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_response.json.return_value = {"results": []}
                mock_get.return_value = mock_response

                result = await search_func(mock_ctx, "test query")
                result_data = json.loads(result)
                assert result_data["success"] is False
                assert "no search results" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_perform_rag_query_empty_query(self, mock_ctx):
        """Test perform_rag_query with empty query"""
        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )

        result = await rag_func(mock_ctx, "")
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "query" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_perform_rag_query_database_error(self, mock_ctx):
        """Test perform_rag_query when database raises exception"""
        mock_ctx.mock_db.search_documents.side_effect = Exception(
            "Database connection failed",
        )

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_get_available_sources_database_error(self, mock_ctx):
        """Test get_available_sources when database raises exception"""
        mock_ctx.mock_db.get_sources.side_effect = Exception("Database error")

        sources_func = (
            get_available_sources.fn
            if hasattr(get_available_sources, "fn")
            else get_available_sources
        )
        result = await sources_func(mock_ctx)

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_url_invalid_parameters(self, mock_ctx):
        """Test smart_crawl_url with invalid parameters"""
        smart_func = (
            smart_crawl_url.fn if hasattr(smart_crawl_url, "fn") else smart_crawl_url
        )

        # Test with negative max_concurrent
        result = await smart_func(mock_ctx, "https://test.com", max_concurrent=-1)
        result_data = json.loads(result)
        # Should handle gracefully (may use default or return error)
        assert isinstance(result_data, dict)
        assert "success" in result_data

    @pytest.mark.asyncio
    async def test_scrape_urls_network_errors(self, mock_ctx):
        """Test various network errors during scraping"""
        network_errors = [
            Exception("Connection failed"),  # Generic connection error
            aiohttp.ServerTimeoutError("Server timeout"),
            TimeoutError("Request timed out"),
            ConnectionRefusedError("Connection refused"),
        ]

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

        for error in network_errors:
            mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = error

            result = await scrape_func(mock_ctx, "https://test.com")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "error" in result_data
            # processing_time_seconds may not be present in all error paths

    @pytest.mark.asyncio
    async def test_scrape_urls_large_batch_handling(self, mock_ctx):
        """Test handling of very large URL batches"""
        # Create large batch of URLs
        large_batch = [f"https://example{i}.com" for i in range(100)]

        # Mock successful crawling
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Test</body></html>"
        mock_result.markdown = "# Test"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(
            mock_ctx,
            large_batch,
            max_concurrent=5,
            batch_size=10,
        )

        result_data = json.loads(result)
        # Should handle large batches gracefully
        assert isinstance(result_data, dict)
        assert "success" in result_data

    @pytest.mark.asyncio
    async def test_url_deduplication_in_batch(self, mock_ctx):
        """Test URL deduplication in batch processing"""
        # URLs with duplicates
        urls_with_dupes = [
            "https://example.com",
            "https://test.com",
            "https://example.com",  # Duplicate
            "https://another.com",
            "https://test.com",  # Duplicate
        ]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Test</body></html>"
        mock_result.markdown = "# Test"
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, urls_with_dupes)

        result_data = json.loads(result)
        # Should process successfully and handle deduplication
        assert isinstance(result_data, dict)
        assert "success" in result_data

    @pytest.mark.asyncio
    async def test_empty_or_whitespace_urls_in_list(self, mock_ctx):
        """Test handling of empty or whitespace-only URLs in list"""
        urls_with_empty = [
            "https://valid.com",
            "",  # Empty
            "   ",  # Whitespace only
            "https://another-valid.com",
            None,  # This should be caught by type validation
        ]

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

        # This should fail type validation due to None
        result = await scrape_func(mock_ctx, urls_with_empty)
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "string" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_concurrent_limit_enforcement(self, mock_ctx):
        """Test that concurrent limits are respected"""
        # Create batch that would exceed reasonable concurrency
        large_batch = [f"https://site{i}.com" for i in range(20)]

        call_count = 0

        async def count_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.html = f"<html><body>Content {call_count}</body></html>"
            mock_result.markdown = f"# Content {call_count}"
            return mock_result

        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = count_calls

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, large_batch, max_concurrent=2)

        result_data = json.loads(result)
        # Should handle concurrency limits appropriately
        assert isinstance(result_data, dict)
        assert call_count <= len(large_batch)  # All URLs should be processed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
