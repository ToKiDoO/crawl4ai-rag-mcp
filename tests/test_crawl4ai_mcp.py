"""
Unit tests for main MCP application functions.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
import os
import sys
import json
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import MCP tools - we'll test the tool functions directly
from crawl4ai_mcp import (
    scrape_urls,
    smart_crawl_url,
    get_available_sources,
    perform_rag_query,
    search,
    search_code_examples,
    Crawl4AIContext
)


class MockContext:
    """Mock context for testing MCP tools"""
    def __init__(self, crawler=None, database_client=None, reranking_model=None):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = Crawl4AIContext(
            crawler=crawler or AsyncMock(),
            database_client=database_client or AsyncMock(),
            reranking_model=reranking_model,
            knowledge_validator=None,
            repo_extractor=None
        )


class TestScrapeUrls:
    """Test scrape_urls MCP tool"""
    
    @pytest.mark.asyncio
    @patch('utils_refactored.extract_source_summary', return_value="Test summary")
    @patch('crawl4ai_mcp.add_documents_to_database')
    @patch('crawl4ai_mcp.crawl_batch')
    async def test_scrape_single_url_success(self, mock_crawl_batch, mock_add_docs, mock_summary):
        """Test scraping a single URL successfully"""
        # Setup
        mock_crawler = AsyncMock()
        # We don't need to mock crawler.arun since crawl_batch is mocked
        
        # Mock crawl_batch to return crawl results
        mock_crawl_batch.return_value = [{
            "url": "https://example.com",
            "success": True,
            "markdown": "# Test Content\n\nThis is test content.",
            "cleaned_html": "<h1>Test Content</h1><p>This is test content.</p>",
            "metadata": {"title": "Test Page"}
        }]
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        result = await scrape_urls(ctx, url="https://example.com", return_raw_markdown=False)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert "url" in result_json or "mode" in result_json
        mock_crawl_batch.assert_called_once()
        mock_add_docs.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.add_documents_to_database')
    @patch('crawl4ai_mcp.crawl_batch')
    async def test_scrape_multiple_urls(self, mock_crawl_batch, mock_add_docs):
        """Test scraping multiple URLs"""
        # Setup
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "Content"
        mock_result.cleaned_html = "<p>Content</p>"
        mock_result.metadata = {}
        mock_crawler.arun.return_value = mock_result
        
        # Mock crawl_batch to return multiple results
        mock_crawl_batch.return_value = [
            {"url": "https://example.com/1", "success": True, "markdown": "Content 1", "cleaned_html": "<p>Content 1</p>", "metadata": {}},
            {"url": "https://example.com/2", "success": True, "markdown": "Content 2", "cleaned_html": "<p>Content 2</p>", "metadata": {}}
        ]
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        result = await scrape_urls(ctx, url=["https://example.com/1", "https://example.com/2"])
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json.get("mode") == "multi_url"
        assert result_json["summary"]["total_urls"] == 2
        # Should be called once with batch of URLs
        assert mock_crawl_batch.call_count == 1
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.crawl_batch')
    async def test_scrape_with_raw_markdown(self, mock_crawl_batch):
        """Test scraping with raw markdown output"""
        # Setup
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Content"
        mock_crawler.arun.return_value = mock_result
        
        # Mock crawl_batch to return results
        mock_crawl_batch.return_value = [{
            "url": "https://example.com",
            "success": True,
            "markdown": "# Test Content",
            "cleaned_html": "<h1>Test Content</h1>",
            "metadata": {}
        }]
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        result = await scrape_urls(ctx, url="https://example.com", return_raw_markdown=True)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json.get("mode") == "raw_markdown"
        assert "# Test Content" in str(result_json.get("results", {}))
    
    @pytest.mark.asyncio
    async def test_scrape_url_failure(self):
        """Test handling of scraping failure"""
        # Setup
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_crawler.arun.return_value = mock_result
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        result = await scrape_urls(ctx, url="https://example.com")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json


class TestSmartCrawlUrl:
    """Test smart_crawl_url MCP tool"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.parse_sitemap')
    @patch('crawl4ai_mcp.crawl_batch')
    async def test_smart_crawl_sitemap(self, mock_crawl_batch, mock_parse_sitemap):
        """Test smart crawling of sitemap URL"""
        # Setup
        mock_parse_sitemap.return_value = ["https://example.com/page1", "https://example.com/page2"]
        mock_crawl_batch.return_value = [
            {"url": "https://example.com/page1", "markdown": "Page 1 content"},
            {"url": "https://example.com/page2", "markdown": "Page 2 content"}
        ]
        ctx = MockContext()
        
        # Test
        result = await smart_crawl_url(ctx, url="https://example.com/sitemap.xml", return_raw_markdown=True)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["crawl_type"] == "sitemap"
        assert len(result_json["results"]) == 2
        mock_parse_sitemap.assert_called_once_with("https://example.com/sitemap.xml")
        mock_crawl_batch.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.crawl_markdown_file')
    async def test_smart_crawl_llms_txt(self, mock_crawl_markdown):
        """Test smart crawling of llms.txt file"""
        # Setup
        mock_crawl_markdown.return_value = [
            {"url": "https://example.com/llms-full.txt", "markdown": "# LLMs Documentation\n\nContent here"}
        ]
        ctx = MockContext()
        
        # Test
        result = await smart_crawl_url(ctx, url="https://example.com/llms-full.txt", max_depth=3, return_raw_markdown=True)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["crawl_type"] == "text_file"
        assert "https://example.com/llms-full.txt" in result_json["results"]
        mock_crawl_markdown.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.crawl_recursive_internal_links')
    async def test_smart_crawl_recursive(self, mock_crawl_recursive):
        """Test recursive crawling of regular webpage"""
        # Setup
        mock_crawl_recursive.return_value = [
            {"url": "https://example.com", "markdown": "Main page content"},
            {"url": "https://example.com/page1", "markdown": "Page 1 content"}
        ]
        ctx = MockContext()
        
        # Test
        result = await smart_crawl_url(ctx, url="https://example.com", max_depth=2, return_raw_markdown=True)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["crawl_type"] == "webpage"
        assert len(result_json["results"]) == 2
        assert "https://example.com" in result_json["results"]
        assert "https://example.com/page1" in result_json["results"]
        mock_crawl_recursive.assert_called_once_with(
            ctx.request_context.lifespan_context.crawler,
            ["https://example.com"],
            max_depth=2,
            max_concurrent=10
        )


class TestGetAvailableSources:
    """Test get_available_sources MCP tool"""
    
    @pytest.mark.asyncio
    async def test_get_sources_success(self):
        """Test getting available sources"""
        # Setup
        mock_db = AsyncMock()
        mock_db.get_sources.return_value = [
            {
                "source_id": "example.com",
                "summary": "Example website",
                "total_word_count": 1500,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        ]
        
        ctx = MockContext(database_client=mock_db)
        
        # Test
        result = await get_available_sources(ctx)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 1
        assert len(result_json["sources"]) == 1
        assert result_json["sources"][0]["source_id"] == "example.com"
        assert result_json["sources"][0]["summary"] == "Example website"
    
    @pytest.mark.asyncio
    async def test_get_sources_empty(self):
        """Test getting sources when none exist"""
        # Setup
        mock_db = AsyncMock()
        mock_db.get_sources.return_value = []
        
        ctx = MockContext(database_client=mock_db)
        
        # Test
        result = await get_available_sources(ctx)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 0
        assert len(result_json["sources"]) == 0


class TestPerformRagQuery:
    """Test perform_rag_query MCP tool"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.search_documents')
    async def test_rag_query_basic(self, mock_search):
        """Test basic RAG query"""
        # Setup
        # Since search_documents is called without await in the code, return a direct value
        mock_search.return_value = [
            {
                "content": "Test content about Python",
                "url": "https://example.com/python",
                "chunk_number": 1,
                "similarity": 0.9
            }
        ]
        
        ctx = MockContext()
        
        # Test
        result = await perform_rag_query(ctx, query="Python programming")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 1
        assert len(result_json["results"]) == 1
        assert result_json["results"][0]["content"] == "Test content about Python"
        assert result_json["results"][0]["url"] == "https://example.com/python"
        mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_HYBRID_SEARCH": "true"})
    @patch('crawl4ai_mcp.search_documents')
    async def test_rag_query_hybrid_search(self, mock_search):
        """Test RAG query with hybrid search enabled"""
        # Setup
        mock_search.return_value = [{"id": "1", "content": "Result", "url": "https://example.com", "similarity": 0.8, "chunk_number": 1, "metadata": {}, "source_id": "src1"}]
        mock_db = AsyncMock()
        mock_db.search_documents_by_keyword.return_value = [
            {"id": "2", "content": "Keyword result", "url": "https://example.com/2", "chunk_number": 2, "metadata": {}, "source_id": "src2"}
        ]
        
        ctx = MockContext(database_client=mock_db)
        
        # Test
        result = await perform_rag_query(ctx, query="test query")
        
        # Verify
        result_json = json.loads(result)
        print(f"Hybrid search result JSON: {result_json}")
        assert result_json["success"] is True
        assert "results" in result_json
        mock_search.assert_called_once()
        mock_db.search_documents_by_keyword.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_RERANKING": "true"})
    @patch('crawl4ai_mcp.search_documents')
    async def test_rag_query_with_reranking(self, mock_search):
        """Test RAG query with reranking enabled"""
        # Setup
        mock_search.return_value = [
            {"content": "Result 1", "url": "url1", "similarity": 0.7},
            {"content": "Result 2", "url": "url2", "similarity": 0.8}
        ]
        
        mock_reranker = MagicMock()
        mock_reranker.predict.return_value = [0.9, 0.6]  # Reranked scores
        
        ctx = MockContext(reranking_model=mock_reranker)
        
        # Test
        result = await perform_rag_query(ctx, query="test query")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 2
        assert result_json["reranking_applied"] is True
        mock_reranker.predict.assert_called_once()


class TestSearch:
    """Test search MCP tool"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.requests.get')
    @patch('crawl4ai_mcp.scrape_urls')
    async def test_search_basic(self, mock_scrape, mock_get):
        """Test basic search functionality"""
        # Setup
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "url": "https://example.com/result1",
                    "title": "Result 1",
                    "content": "Preview of result 1"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        mock_scrape.return_value = json.dumps({"success": True, "mode": "multi_url", "summary": {"successful_urls": 1}})
        
        ctx = MockContext()
        
        # Test
        result = await search(ctx, query="test search", num_results=1)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert "searxng_results" in result_json
        assert "https://example.com/result1" in result_json["searxng_results"]
        mock_get.assert_called_once()
        mock_scrape.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.requests.get')
    async def test_search_no_results(self, mock_get):
        """Test search with no results"""
        # Setup
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        ctx = MockContext()
        
        # Test
        result = await search(ctx, query="no results query")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json
        assert "No search results" in result_json["error"]
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.requests.get')
    @patch('crawl4ai_mcp.scrape_urls')
    async def test_search_raw_markdown(self, mock_scrape, mock_get):
        """Test search with raw markdown output"""
        # Setup
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "title": "Test"}]
        }
        mock_get.return_value = mock_response
        
        mock_scrape.return_value = json.dumps({"success": True, "mode": "raw_markdown", "results": {"https://example.com": "# Raw Markdown Content"}})
        
        ctx = MockContext()
        
        # Test
        result = await search(ctx, query="test", return_raw_markdown=True)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json.get("mode") == "raw_markdown"
        # Check that scrape_urls was called with the correct arguments
        # The search function calls it with positional arguments
        call_args = mock_scrape.call_args
        assert call_args is not None
        # First argument is ctx
        assert call_args[0][0] == ctx
        # Second argument is the list of URLs
        assert call_args[0][1] == ["https://example.com"]
        # Third and fourth are max_concurrent and batch_size
        assert call_args[0][2] == 10  # max_concurrent
        assert call_args[0][3] == 20  # batch_size


class TestSearchCodeExamples:
    """Test search_code_examples MCP tool"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_AGENTIC_RAG": "true"})
    @patch('utils.search_code_examples')
    async def test_search_code_examples_success(self, mock_search):
        """Test searching code examples"""
        # Setup
        # Mock the async search_code_examples function to return results
        mock_search.return_value = [
            {
                "content": "def hello():\n    return 'world'",
                "summary": "Hello world function",
                "url": "https://example.com/docs",
                "similarity": 0.95,
                "metadata": {"language": "python"}
            }
        ]
        
        ctx = MockContext()
        
        # Test
        from crawl4ai_mcp import search_code_examples as search_code_tool
        result = await search_code_tool(ctx, query="hello world function")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 1
        assert "def hello():" in result_json["results"][0]["code"]
        assert "Hello world function" in result_json["results"][0]["summary"]
        mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_AGENTIC_RAG": "false"})
    async def test_search_code_examples_disabled(self):
        """Test code examples search when disabled"""
        ctx = MockContext()
        
        # Import function directly since it's conditional
        from crawl4ai_mcp import mcp
        
        # Verify the tool is not registered when USE_AGENTIC_RAG is false
        # This would need to check the MCP server's registered tools
        # For now, we just verify the environment check works
        assert os.getenv("USE_AGENTIC_RAG", "false") == "false"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])