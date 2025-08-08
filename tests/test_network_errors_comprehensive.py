"""
Comprehensive network error handling tests for Crawl4AI MCP.

Tests various network failure scenarios:
- Connection timeouts and failures
- DNS resolution errors
- HTTP status codes (4xx, 5xx)
- Partial response handling
- Retry logic validation
- Network interruptions during operations
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawl4ai_mcp import (
    scrape_urls,
    search,
)


class MockContext:
    """Mock FastMCP Context for testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Mock database client
        self.request_context.lifespan_context.database_client = AsyncMock()

        # Mock crawler with async context manager support
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun = AsyncMock()
        mock_crawler.arun_many = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler
        self.request_context.lifespan_context.reranking_model = None


class TestNetworkErrorHandling:
    """Test network error scenarios comprehensively"""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context for tests"""
        return MockContext()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error_type,expected_error_msg",
        [
            (
                aiohttp.ClientConnectorError(None, OSError("Connection failed")),
                "Connection failed",
            ),
            (aiohttp.ServerTimeoutError("Server timeout"), "Server timeout"),
            (TimeoutError("Request timed out"), "Request timed out"),
            (ConnectionRefusedError("Connection refused"), "Connection refused"),
            (aiohttp.ClientResponseError(None, None, status=500), "status=500"),
            (aiohttp.ClientPayloadError("Payload error"), "Payload error"),
        ],
    )
    async def test_crawl_network_errors(self, mock_ctx, error_type, expected_error_msg):
        """Test various network errors during crawling"""
        # Mock crawler to raise network error
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = error_type

        # Extract the actual function from the FastMCP tool
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            # Get the actual function that was decorated
            scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

            result = await scrape_func(mock_ctx, "https://test.com")

            # Verify error response structure
            assert isinstance(result, str)
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "error" in result_data
            assert expected_error_msg.lower() in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, mock_ctx):
        """Test handling of connection timeout scenarios"""

        # Mock timeout after 2 seconds
        async def timeout_after_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # Short delay to simulate timeout
            raise TimeoutError("Connection timed out after 30 seconds")

        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = (
            timeout_after_delay
        )

        start_time = time.time()
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://slow-site.com")
        processing_time = time.time() - start_time

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "timeout" in result_data["error"].lower()
        assert processing_time < 5  # Should fail quickly, not hang

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self, mock_ctx):
        """Test handling of DNS resolution failures"""
        dns_error = aiohttp.ClientConnectorError(
            "Cannot connect to host nonexistent-domain.com:443 ssl:default",
            None,
        )
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = dns_error

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://nonexistent-domain.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "connect" in result_data["error"].lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "status_code,expected_type",
        [
            (400, "client error"),
            (401, "unauthorized"),
            (403, "forbidden"),
            (404, "not found"),
            (429, "rate limit"),
            (500, "server error"),
            (502, "bad gateway"),
            (503, "service unavailable"),
        ],
    )
    async def test_http_status_code_handling(
        self,
        mock_ctx,
        status_code,
        expected_type,
    ):
        """Test handling of various HTTP status codes"""
        http_error = aiohttp.ClientResponseError(
            None,
            None,
            status=status_code,
            message=f"HTTP {status_code}",
        )
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = http_error

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, f"https://httpstat.us/{status_code}")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert str(status_code) in result_data["error"]

    @pytest.mark.asyncio
    async def test_partial_response_handling(self, mock_ctx):
        """Test handling of partial/incomplete responses"""
        # Mock successful crawl but with incomplete content
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = "<html><body>Partial content"  # Incomplete HTML
        mock_result.markdown = "# Partial"

        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://partial-site.com")

        result_data = json.loads(result)
        # Should still succeed but with partial content
        assert result_data["success"] is True
        assert "Partial" in str(result_data)

    @pytest.mark.asyncio
    async def test_batch_crawl_mixed_failures(self, mock_ctx):
        """Test batch crawling with mixed success/failure scenarios"""
        urls = [
            "https://success1.com",
            "https://timeout.com",
            "https://success2.com",
            "https://error.com",
        ]

        # Mock different responses for different URLs
        async def mock_arun(url, **kwargs):
            if "success" in url:
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.html = f"<html><body>Content from {url}</body></html>"
                mock_result.markdown = f"# Content from {url}"
                return mock_result
            if "timeout" in url:
                raise TimeoutError("Request timed out")
            if "error" in url:
                raise aiohttp.ClientError("Connection failed")

        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = mock_arun

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, urls)

        result_data = json.loads(result)

        # Should process successfully crawled URLs
        assert result_data["success"] is True
        assert "successful_urls" in result_data or "summary" in result_data

    @pytest.mark.asyncio
    async def test_network_interruption_during_batch(self, mock_ctx):
        """Test handling of network interruption during batch operations"""
        urls = [f"https://site{i}.com" for i in range(5)]

        call_count = 0

        async def failing_arun(url, **kwargs):
            nonlocal call_count
            call_count += 1

            # First 2 calls succeed, then network fails
            if call_count <= 2:
                mock_result = MagicMock()
                mock_result.success = True
                mock_result.html = f"<html><body>Content {call_count}</body></html>"
                mock_result.markdown = f"# Content {call_count}"
                return mock_result
            raise ConnectionError("Network connection lost")

        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = (
            failing_arun
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, urls)

        result_data = json.loads(result)

        # Should handle partial success gracefully
        assert (
            result_data["success"] is True
            or "partial" in result_data.get("error", "").lower()
        )

    @pytest.mark.asyncio
    async def test_retry_logic_validation(self, mock_ctx):
        """Test retry behavior on transient failures"""
        call_count = 0

        async def transient_failure(url, **kwargs):
            nonlocal call_count
            call_count += 1

            # Fail first 2 attempts, succeed on 3rd
            if call_count <= 2:
                raise aiohttp.ClientConnectorError("Temporary connection failure", None)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.html = "<html><body>Success after retry</body></html>"
            mock_result.markdown = "# Success after retry"
            return mock_result

        # Note: Current implementation may not have built-in retry logic
        # This test validates that the system handles transient failures appropriately
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = (
            transient_failure
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://flaky-site.com")

        # Should fail on first attempt (current behavior)
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert call_count == 1  # No retry in current implementation

    @pytest.mark.asyncio
    async def test_concurrent_connection_limits(self, mock_ctx):
        """Test behavior when hitting concurrent connection limits"""
        # Mock connection pool exhaustion
        connection_error = aiohttp.ClientConnectorError("Connector is closed", None)
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = (
            connection_error
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(
            mock_ctx,
            ["https://site1.com"] * 50,
            max_concurrent=100,
        )

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "connector" in result_data["error"].lower()
            or "connection" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_memory_pressure_during_large_batch(self, mock_ctx):
        """Test handling of memory pressure during large batch operations"""
        # Mock memory error during large batch processing
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = (
            MemoryError("Out of memory")
        )

        # Create large batch of URLs
        large_url_batch = [f"https://site{i}.com" for i in range(1000)]

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, large_url_batch)

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "memory" in result_data["error"].lower()

    @pytest.mark.asyncio
    async def test_search_network_errors(self, mock_ctx):
        """Test network error handling in search operations"""
        with patch("requests.get") as mock_get:
            # Mock network timeout in search
            mock_get.side_effect = aiohttp.ClientTimeout("Search request timed out")

            search_func = search.fn if hasattr(search, "fn") else search
            result = await search_func(mock_ctx, "test query")

            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "error" in result_data

    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, mock_ctx):
        """Test handling of malformed or corrupted responses"""
        # Mock crawler returning malformed data
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.html = None  # Malformed response
        mock_result.markdown = None

        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://malformed-site.com")

        result_data = json.loads(result)
        # Should handle gracefully, possibly with empty content
        assert isinstance(result_data, dict)
        assert "success" in result_data

    @pytest.mark.asyncio
    async def test_ssl_certificate_errors(self, mock_ctx):
        """Test handling of SSL certificate errors"""
        ssl_error = aiohttp.ClientConnectorCertificateError(
            "SSL: CERTIFICATE_VERIFY_FAILED",
            None,
        )
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = ssl_error

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://invalid-cert.com")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "ssl" in result_data["error"].lower()
            or "certificate" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    async def test_error_message_sanitization(self, mock_ctx):
        """Test that error messages don't leak sensitive information"""
        # Mock error with potentially sensitive info
        sensitive_error = Exception(
            "Database connection failed: user=admin, password=secret123",
        )
        mock_ctx.request_context.lifespan_context.crawler.arun.side_effect = (
            sensitive_error
        )

        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, "https://test.com")

        result_data = json.loads(result)
        assert result_data["success"] is False

        # Check that sensitive information is not exposed
        error_msg = result_data["error"].lower()
        assert "password" not in error_msg
        assert "secret" not in error_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
