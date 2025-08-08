"""
Simplified end-to-end workflow integration tests.

Tests core workflows using available MCP tools:
- Basic crawl and store workflow
- Search functionality
- RAG query workflow
- Code example search
"""

import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


from crawl4ai_mcp import (
    perform_rag_query,
    scrape_urls,
    search,
    search_code_examples,
    smart_crawl_url,
)


class MockContext:
    """Mock context for integration testing."""

    def __init__(self, database_adapter=None):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = MagicMock()

        # Set up database adapter
        self.request_context.lifespan_context.database_client = database_adapter

        # Set up mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun = AsyncMock()
        mock_crawler.arun_many = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler
        self.request_context.lifespan_context.reranking_model = None


@pytest.mark.integration
@pytest.mark.e2e
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_basic_crawl_and_search_workflow(
        self,
        qdrant_client,
        performance_thresholds,
        integration_test_env,
    ):
        """Test basic crawl → search workflow."""

        start_time = time.time()

        # Mock successful crawl result
        mock_crawl_result = {
            "url": "https://example.com/test",
            "extracted_content": "This is a test page about artificial intelligence and machine learning.",
            "markdown": "# Test Page\nThis is a test page about artificial intelligence and machine learning.",
            "success": True,
            "status_code": 200,
        }

        mock_ctx = MockContext(database_adapter=qdrant_client)

        # Mock the crawler to return our test result
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = (
            mock_crawl_result
        )

        # Step 1: Crawl and store a URL
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            # Mock create_embedding for storage
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                crawl_func = (
                    scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
                )

                # Call with store_results=True (this should be parsed from the URL parameter)
                result = await crawl_func(
                    mock_ctx,
                    "https://example.com/test?store_results=true",
                )

        # Verify crawl succeeded
        assert "success" in result.lower() or "stored" in result.lower()

        # Step 2: Search for the stored content
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                search_func = search.fn if hasattr(search, "fn") else search
                search_result = await search_func(
                    mock_ctx,
                    query="artificial intelligence",
                    num_results=5,
                )

        # Verify search found relevant content
        assert (
            "artificial intelligence" in search_result.lower()
            or "machine learning" in search_result.lower()
        )

        # Performance check
        total_time = (time.time() - start_time) * 1000
        assert total_time < performance_thresholds["e2e_workflow_ms"]

        print(f"✅ Basic workflow completed in {total_time:.2f}ms")

    @pytest.mark.asyncio
    async def test_rag_query_workflow(self, qdrant_client, integration_test_env):
        """Test RAG query functionality."""

        # First, populate the database with some test content
        with patch("src.utils.create_embedding", return_value=[0.1] * 1536):
            await qdrant_client.store_crawled_page(
                url="https://example.com/python-guide",
                content="Python is a high-level programming language. It supports object-oriented programming and has extensive libraries.",
                title="Python Programming Guide",
                metadata={"category": "programming", "language": "python"},
            )

            await qdrant_client.store_crawled_page(
                url="https://example.com/ai-intro",
                content="Artificial Intelligence involves creating systems that can perform tasks requiring human intelligence.",
                title="Introduction to AI",
                metadata={"category": "ai", "topic": "introduction"},
            )

        mock_ctx = MockContext(database_adapter=qdrant_client)

        # Test RAG query
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                rag_func = (
                    perform_rag_query.fn
                    if hasattr(perform_rag_query, "fn")
                    else perform_rag_query
                )

                # Query about Python
                python_result = await rag_func(
                    mock_ctx,
                    query="What is Python programming language?",
                    match_count=3,
                )

                # Query about AI
                ai_result = await rag_func(
                    mock_ctx,
                    query="What is artificial intelligence?",
                    match_count=3,
                )

        # Verify RAG results contain relevant information
        assert (
            "python" in python_result.lower() or "programming" in python_result.lower()
        )
        assert "artificial" in ai_result.lower() or "intelligence" in ai_result.lower()

        print("✅ RAG query workflow working correctly")

    @pytest.mark.asyncio
    async def test_code_search_workflow(self, qdrant_client, integration_test_env):
        """Test code example search functionality."""

        # Populate with code examples
        code_content = """
        # Python async example
        ```python
        import asyncio
        
        async def fetch_data():
            await asyncio.sleep(1)
            return "data"
        
        async def main():
            result = await fetch_data()
            print(result)
        ```
        
        # JavaScript example
        ```javascript
        async function fetchData() {
            return new Promise(resolve => {
                setTimeout(() => resolve("data"), 1000);
            });
        }
        ```
        """

        with patch("src.utils.create_embedding", return_value=[0.1] * 1536):
            await qdrant_client.store_crawled_page(
                url="https://example.com/code-examples",
                content=code_content,
                title="Code Examples",
                metadata={"category": "code", "type": "examples"},
            )

        mock_ctx = MockContext(database_adapter=qdrant_client)

        # Test code search
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                code_search_func = (
                    search_code_examples.fn
                    if hasattr(search_code_examples, "fn")
                    else search_code_examples
                )

                # Search for async code examples
                async_result = await code_search_func(
                    mock_ctx,
                    query="async await example",
                    match_count=3,
                )

                # Search for JavaScript examples
                js_result = await code_search_func(
                    mock_ctx,
                    query="javascript function",
                    match_count=3,
                )

        # Verify code search results
        assert "async" in async_result.lower() or "await" in async_result.lower()
        assert "javascript" in js_result.lower() or "function" in js_result.lower()

        print("✅ Code search workflow working correctly")

    @pytest.mark.asyncio
    async def test_smart_crawl_workflow(self, qdrant_client, integration_test_env):
        """Test smart crawling functionality."""

        mock_ctx = MockContext(database_adapter=qdrant_client)

        # Mock multiple crawl results for smart crawling
        mock_results = [
            {
                "url": "https://example.com/page1",
                "extracted_content": "Page 1 content about web development",
                "success": True,
            },
            {
                "url": "https://example.com/page2",
                "extracted_content": "Page 2 content about programming",
                "success": True,
            },
        ]

        mock_ctx.request_context.lifespan_context.crawler.arun_many.return_value = (
            mock_results
        )

        # Test smart crawl
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                smart_crawl_func = (
                    smart_crawl_url.fn
                    if hasattr(smart_crawl_url, "fn")
                    else smart_crawl_url
                )

                result = await smart_crawl_func(
                    mock_ctx,
                    url="https://example.com",
                    max_depth=2,
                    max_concurrent=5,
                )

        # Verify smart crawl worked
        assert "content" in result.lower() or "page" in result.lower()

        print("✅ Smart crawl workflow working correctly")

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, qdrant_client, integration_test_env):
        """Test workflow error handling."""

        mock_ctx = MockContext(database_adapter=qdrant_client)

        # Mock failed crawl result
        mock_ctx.request_context.lifespan_context.crawler.arun.return_value = {
            "url": "https://example.com/nonexistent",
            "extracted_content": "",
            "success": False,
            "status_code": 404,
            "error": "Not Found",
        }

        # Test that failed crawl is handled gracefully
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            crawl_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls

            result = await crawl_func(mock_ctx, "https://example.com/nonexistent")

        # Should return error information, not crash
        assert (
            "error" in result.lower() or "failed" in result.lower() or "404" in result
        )

        # Test search with no results
        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                search_func = search.fn if hasattr(search, "fn") else search

                empty_result = await search_func(
                    mock_ctx,
                    query="nonexistent content that should not be found",
                    num_results=5,
                )

        # Should handle empty results gracefully
        assert isinstance(empty_result, str)  # Should return a string response

        print("✅ Error handling workflow working correctly")

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_performance_workflow(
        self,
        qdrant_client,
        performance_thresholds,
        integration_test_env,
    ):
        """Test workflow performance characteristics."""

        mock_ctx = MockContext(database_adapter=qdrant_client)

        # Populate database with test data
        test_urls = [f"https://example.com/perf/{i}" for i in range(5)]

        for i, url in enumerate(test_urls):
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                await qdrant_client.store_crawled_page(
                    url=url,
                    content=f"Performance test document {i} with searchable content about topic {i}.",
                    title=f"Performance Test {i}",
                    metadata={"test": "performance", "doc_id": i},
                )

        # Test search performance
        search_times = []

        with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
            with patch(
                "src.utils.create_embedding",
                return_value=[0.1] * 1536,
            ):
                search_func = search.fn if hasattr(search, "fn") else search

                for i in range(5):
                    start_time = time.time()

                    result = await search_func(
                        mock_ctx,
                        query=f"performance test topic {i}",
                        num_results=3,
                    )

                    search_time = (time.time() - start_time) * 1000
                    search_times.append(search_time)

                    assert len(result) > 0  # Should find results

        # Performance validation
        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)

        assert avg_search_time < performance_thresholds["search_documents_ms"]
        assert max_search_time < performance_thresholds["search_documents_ms"] * 2

        print(
            f"✅ Performance: avg search {avg_search_time:.1f}ms, max {max_search_time:.1f}ms",
        )
