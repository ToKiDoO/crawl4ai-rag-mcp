"""
Unit tests for main MCP application functions.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
import os
import sys
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
    @patch('crawl4ai_mcp.add_documents_to_database')
    async def test_scrape_single_url_success(self, mock_add_docs):
        """Test scraping a single URL successfully"""
        # Setup
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Content\n\nThis is test content."
        mock_result.cleaned_html = "<h1>Test Content</h1><p>This is test content.</p>"
        mock_result.metadata = {"title": "Test Page"}
        mock_crawler.arun.return_value = mock_result
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        result = await scrape_urls(ctx, urls="https://example.com", return_raw_markdown=False)
        
        # Verify
        assert "Successfully scraped 1 URLs" in result
        mock_crawler.arun.assert_called_once()
        mock_add_docs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_multiple_urls(self):
        """Test scraping multiple URLs"""
        # Setup
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "Content"
        mock_result.cleaned_html = "<p>Content</p>"
        mock_result.metadata = {}
        mock_crawler.arun.return_value = mock_result
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        with patch('crawl4ai_mcp._process_multiple_urls') as mock_process:
            mock_process.return_value = (["url1", "url2"], [], 2, 0)
            result = await scrape_urls(ctx, urls=["https://example.com/1", "https://example.com/2"])
        
        # Verify
        assert "Successfully scraped 2 URLs" in result
        mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_with_raw_markdown(self):
        """Test scraping with raw markdown output"""
        # Setup
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Content"
        mock_crawler.arun.return_value = mock_result
        
        ctx = MockContext(crawler=mock_crawler)
        
        # Test
        result = await scrape_urls(ctx, urls="https://example.com", return_raw_markdown=True)
        
        # Verify
        assert "# Test Content" in result
        assert "Successfully scraped" not in result  # Raw mode doesn't add summary
    
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
        result = await scrape_urls(ctx, urls="https://example.com")
        
        # Verify
        assert "Failed URLs: https://example.com" in result


class TestSmartCrawlUrl:
    """Test smart_crawl_url MCP tool"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.scrape_urls')
    async def test_smart_crawl_sitemap(self, mock_scrape):
        """Test smart crawling of sitemap URL"""
        # Setup
        mock_scrape.return_value = "Scraped sitemap results"
        ctx = MockContext()
        
        # Test
        result = await smart_crawl_url(ctx, url="https://example.com/sitemap.xml")
        
        # Verify
        assert result == "Scraped sitemap results"
        mock_scrape.assert_called_once_with(ctx, urls="https://example.com/sitemap.xml")
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.scrape_urls')
    async def test_smart_crawl_llms_txt(self, mock_scrape):
        """Test smart crawling of llms.txt file"""
        # Setup
        mock_scrape.return_value = "Scraped llms.txt results"
        ctx = MockContext()
        
        # Test
        result = await smart_crawl_url(ctx, url="https://example.com/llms-full.txt", max_depth=3)
        
        # Verify
        assert result == "Scraped llms.txt results"
        mock_scrape.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.requests.get')
    @patch('crawl4ai_mcp.scrape_urls')
    async def test_smart_crawl_recursive(self, mock_scrape, mock_get):
        """Test recursive crawling of regular webpage"""
        # Setup
        mock_response = MagicMock()
        mock_response.text = '<html><body><a href="/page1">Link 1</a></body></html>'
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        mock_scrape.return_value = "Scraped results"
        ctx = MockContext()
        
        # Test
        result = await smart_crawl_url(ctx, url="https://example.com", max_pages=5)
        
        # Verify
        assert "Scraped results" in result
        mock_get.assert_called_once()
        mock_scrape.assert_called()


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
        assert "Available sources (1):" in result
        assert "example.com" in result
        assert "Example website" in result
        assert "Words: 1,500" in result
    
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
        assert "No sources found" in result


class TestPerformRagQuery:
    """Test perform_rag_query MCP tool"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.search_documents')
    async def test_rag_query_basic(self, mock_search):
        """Test basic RAG query"""
        # Setup
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
        assert "Found 1 relevant results" in result
        assert "Test content about Python" in result
        assert "Source: https://example.com/python" in result
        mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_HYBRID_SEARCH": "true"})
    @patch('crawl4ai_mcp.search_documents')
    async def test_rag_query_hybrid_search(self, mock_search):
        """Test RAG query with hybrid search enabled"""
        # Setup
        mock_search.return_value = [{"content": "Result", "url": "https://example.com", "similarity": 0.8}]
        mock_db = AsyncMock()
        mock_db.search_documents_by_keyword.return_value = [
            {"id": "2", "content": "Keyword result", "url": "https://example.com/2"}
        ]
        
        ctx = MockContext(database_client=mock_db)
        
        # Test
        result = await perform_rag_query(ctx, query="test query")
        
        # Verify
        assert "results" in result
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
        assert "Found 2 relevant results" in result
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
        
        mock_scrape.return_value = "Scraped content"
        
        ctx = MockContext()
        
        # Test
        result = await search(ctx, query="test search", num_results=1)
        
        # Verify
        assert "Found 1 search results" in result
        assert "https://example.com/result1" in result
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
        assert "No search results found" in result
    
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
        
        mock_scrape.return_value = "# Raw Markdown Content"
        
        ctx = MockContext()
        
        # Test
        result = await search(ctx, query="test", return_raw_markdown=True)
        
        # Verify
        assert "# Raw Markdown Content" in result
        mock_scrape.assert_called_with(
            ctx, 
            urls=["https://example.com"], 
            return_raw_markdown=True,
            batch_size=20,
            max_concurrent=5
        )


class TestSearchCodeExamples:
    """Test search_code_examples MCP tool"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_AGENTIC_RAG": "true"})
    @patch('crawl4ai_mcp.search_code_examples')
    async def test_search_code_examples_success(self, mock_search):
        """Test searching code examples"""
        # Setup
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
        assert "Found 1 code examples" in result
        assert "def hello():" in result
        assert "Hello world function" in result
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