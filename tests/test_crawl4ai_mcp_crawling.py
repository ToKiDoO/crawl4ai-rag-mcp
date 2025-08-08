"""Unit tests for crawling functions in crawl4ai_mcp.py."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawl4ai_mcp import (
    _process_multiple_urls,
    crawl_batch,
    crawl_markdown_file,
    crawl_recursive_internal_links,
)


class TestCrawlingFunctions:
    """Test crawling-related functions."""

    @pytest.fixture
    def mock_crawler(self):
        """Create a mock crawler."""
        return AsyncMock()

    @pytest.fixture
    def mock_crawl_result(self):
        """Create a mock crawl result."""
        result = Mock()
        result.success = True
        result.markdown = "# Test Page\nThis is test content."
        result.cleaned_html = "<h1>Test Page</h1><p>This is test content.</p>"
        result.media = {"images": ["test.jpg"], "videos": []}
        result.links = {
            "internal": ["/page1", "/page2"],
            "external": ["https://external.com"],
        }
        result.screenshot = None
        result.pdf = None
        result.failed_before = False
        return result

    @pytest.mark.asyncio
    async def test_crawl_markdown_file_success(self, mock_crawler, mock_crawl_result):
        """Test successful markdown file crawling."""
        mock_crawler.arun.return_value = mock_crawl_result

        results = await crawl_markdown_file(mock_crawler, "https://example.com/page")

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/page"
        assert results[0]["markdown"] == "# Test Page\nThis is test content."
        assert results[0]["success"] is True
        assert len(results[0]["media"]["images"]) == 1
        mock_crawler.arun.assert_called_once()

    @pytest.mark.asyncio
    async def test_crawl_markdown_file_failure(self, mock_crawler):
        """Test failed markdown file crawling."""
        mock_crawler.arun.side_effect = Exception("Network error")

        results = await crawl_markdown_file(mock_crawler, "https://example.com/page")

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/page"
        assert results[0]["success"] is False
        assert "Network error" in results[0]["error"]

    @pytest.mark.asyncio
    async def test_crawl_batch(self, mock_crawler, mock_crawl_result):
        """Test batch crawling."""
        # Create different results for different URLs
        result1 = Mock()
        result1.success = True
        result1.markdown = "Content 1"
        result1.cleaned_html = "<p>Content 1</p>"
        result1.media = {"images": [], "videos": []}
        result1.links = {"internal": [], "external": []}
        result1.screenshot = None
        result1.pdf = None
        result1.failed_before = False

        result2 = Mock()
        result2.success = True
        result2.markdown = "Content 2"
        result2.cleaned_html = "<p>Content 2</p>"
        result2.media = {"images": [], "videos": []}
        result2.links = {"internal": [], "external": []}
        result2.screenshot = None
        result2.pdf = None
        result2.failed_before = False

        mock_crawler.arun.side_effect = [result1, result2]

        urls = ["https://example.com/1", "https://example.com/2"]
        results = await crawl_batch(mock_crawler, urls, max_concurrent=2)

        assert len(results) == 2
        assert results[0]["markdown"] == "Content 1"
        assert results[1]["markdown"] == "Content 2"
        assert all(r["success"] for r in results)
        assert mock_crawler.arun.call_count == 2

    @pytest.mark.asyncio
    async def test_crawl_batch_with_failures(self, mock_crawler):
        """Test batch crawling with some failures."""
        # First URL succeeds
        result1 = Mock()
        result1.success = True
        result1.markdown = "Success"
        result1.cleaned_html = "<p>Success</p>"
        result1.media = {"images": [], "videos": []}
        result1.links = {"internal": [], "external": []}
        result1.screenshot = None
        result1.pdf = None
        result1.failed_before = False

        # Second URL fails
        mock_crawler.arun.side_effect = [result1, Exception("Failed to crawl")]

        urls = ["https://example.com/1", "https://example.com/2"]
        results = await crawl_batch(mock_crawler, urls, max_concurrent=1)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "Failed to crawl" in results[1]["error"]

    @pytest.mark.asyncio
    async def test_crawl_recursive_internal_links(self, mock_crawler):
        """Test recursive crawling of internal links."""
        # Mock results for different pages
        home_result = Mock()
        home_result.success = True
        home_result.markdown = "Home page"
        home_result.cleaned_html = "<p>Home page</p>"
        home_result.media = {"images": [], "videos": []}
        home_result.links = {
            "internal": ["/about", "/contact"],
            "external": ["https://external.com"],
        }
        home_result.screenshot = None
        home_result.pdf = None
        home_result.failed_before = False

        about_result = Mock()
        about_result.success = True
        about_result.markdown = "About page"
        about_result.cleaned_html = "<p>About page</p>"
        about_result.media = {"images": [], "videos": []}
        about_result.links = {
            "internal": ["/team"],  # New link found
            "external": [],
        }
        about_result.screenshot = None
        about_result.pdf = None
        about_result.failed_before = False

        contact_result = Mock()
        contact_result.success = True
        contact_result.markdown = "Contact page"
        contact_result.cleaned_html = "<p>Contact page</p>"
        contact_result.media = {"images": [], "videos": []}
        contact_result.links = {
            "internal": ["/about"],  # Already crawled
            "external": [],
        }
        contact_result.screenshot = None
        contact_result.pdf = None
        contact_result.failed_before = False

        team_result = Mock()
        team_result.success = True
        team_result.markdown = "Team page"
        team_result.cleaned_html = "<p>Team page</p>"
        team_result.media = {"images": [], "videos": []}
        team_result.links = {"internal": [], "external": []}
        team_result.screenshot = None
        team_result.pdf = None
        team_result.failed_before = False

        # Configure mock to return appropriate results
        mock_crawler.arun.side_effect = [
            home_result,  # First crawl of home
            about_result,  # Crawl /about (depth 1)
            contact_result,  # Crawl /contact (depth 1)
            team_result,  # Crawl /team (depth 2)
        ]

        results = await crawl_recursive_internal_links(
            mock_crawler,
            ["https://example.com"],
            max_depth=2,
            max_concurrent=2,
        )

        # Should have crawled 4 pages total
        assert len(results) >= 3  # At least home, about, contact
        assert any(r["url"] == "https://example.com" for r in results)
        assert any("about" in r["url"] for r in results)
        assert any("contact" in r["url"] for r in results)

        # Check that internal links were discovered
        home_result_data = next(r for r in results if r["url"] == "https://example.com")
        assert len(home_result_data["links"]["internal"]) == 2

    @pytest.mark.asyncio
    async def test_crawl_recursive_max_depth(self, mock_crawler):
        """Test that recursive crawling respects max depth."""
        # Create a chain of pages
        result = Mock()
        result.success = True
        result.markdown = "Page content"
        result.cleaned_html = "<p>Page content</p>"
        result.media = {"images": [], "videos": []}
        result.links = {
            "internal": ["/next"],  # Always has a next page
            "external": [],
        }
        result.screenshot = None
        result.pdf = None
        result.failed_before = False

        # Return the same result for all crawls
        mock_crawler.arun.return_value = result

        results = await crawl_recursive_internal_links(
            mock_crawler,
            ["https://example.com"],
            max_depth=1,  # Only crawl 1 level deep
            max_concurrent=1,
        )

        # With max_depth=1, should crawl:
        # - Initial page (depth 0)
        # - One level of internal links (depth 1)
        # Should not crawl beyond that
        assert mock_crawler.arun.call_count <= 3  # Initial + maybe a few at depth 1

    @pytest.mark.asyncio
    async def test_process_multiple_urls(self):
        """Test the _process_multiple_urls helper function."""
        from fastmcp import Context

        # Create mock context
        ctx = Mock(spec=Context)
        ctx.crawl4ai = Mock()
        ctx.crawl4ai.crawler = AsyncMock()
        ctx.crawl4ai.db_adapter = AsyncMock()
        ctx.crawl4ai.embedding_service = Mock()

        # Mock crawler results
        result1 = Mock()
        result1.success = True
        result1.markdown = "Page 1"
        result1.cleaned_html = "<p>Page 1</p>"
        result1.media = {"images": [], "videos": []}
        result1.links = {"internal": [], "external": []}
        result1.screenshot = None
        result1.pdf = None

        result2 = Mock()
        result2.success = False
        result2.markdown = ""

        ctx.crawl4ai.crawler.arun.side_effect = [result1, Exception("Failed")]

        # Mock database operations
        ctx.crawl4ai.db_adapter.add_documents.return_value = {"success": True}

        # Test processing multiple URLs
        urls = ["https://example.com/1", "https://example.com/2"]
        results = await _process_multiple_urls(
            ctx,
            urls,
            max_concurrent=2,
            batch_size=10,
            return_raw_markdown=False,
        )

        assert results["total_urls"] == 2
        assert results["successful"] == 1
        assert results["failed"] == 1
        assert len(results["failed_urls"]) == 1
        assert results["failed_urls"][0] == "https://example.com/2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
