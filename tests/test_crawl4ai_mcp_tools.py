"""Comprehensive unit tests for MCP tools in crawl4ai_mcp.py."""
import pytest
import json
import os
import aiohttp
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import necessary components
from fastmcp import Context


class TestMCPTools:
    """Test MCP tool functions."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock context with crawl4ai context."""
        ctx = Mock(spec=Context)
        ctx.crawl4ai = Mock()
        ctx.crawl4ai.crawler = AsyncMock()
        ctx.crawl4ai.db_adapter = AsyncMock()
        ctx.crawl4ai.embedding_service = Mock()
        ctx.crawl4ai.cross_encoder = Mock()
        ctx.crawl4ai.searxng_client = AsyncMock()
        return ctx
    
    @pytest.mark.asyncio
    async def test_search_tool_success(self, mock_context):
        """Test successful search operation."""
        from src.crawl4ai_mcp import search
        
        # Mock environment variable
        with patch.dict(os.environ, {'SEARXNG_URL': 'http://localhost:8080'}):
            # Mock aiohttp session and response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='''
            <div class="results">
                <article class="result">
                    <h3><a href="https://example.com/1">Result 1</a></h3>
                    <p class="content">Content 1</p>
                </article>
                <article class="result">
                    <h3><a href="https://example.com/2">Result 2</a></h3>
                    <p class="content">Content 2</p>
                </article>
            </div>
            ''')
            
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            with patch('aiohttp.ClientSession', return_value=mock_session):
                # Mock crawling
                mock_crawl_result = Mock()
                mock_crawl_result.success = True
                mock_crawl_result.markdown = "# Test Content\nThis is test content."
                mock_crawl_result.cleaned_html = "<h1>Test Content</h1><p>This is test content.</p>"
                mock_crawl_result.media = {"images": [], "videos": []}
                mock_crawl_result.links = {"internal": [], "external": []}
                mock_crawl_result.screenshot = None
                mock_crawl_result.pdf = None
                
                # Setup context mocks properly
                mock_context.request_context = Mock()
                mock_context.request_context.lifespan_context = Mock()
                mock_context.request_context.lifespan_context.crawler = AsyncMock()
                mock_context.request_context.lifespan_context.crawler.arun.return_value = mock_crawl_result
                mock_context.request_context.lifespan_context.database_client = AsyncMock()
                
                # Mock database operations
                with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
                    mock_store.return_value = None
                    
                    # Test basic search
                    result = await search(mock_context, "test query", return_raw_markdown=False, num_results=2)
                    result_data = json.loads(result)
                    
                    assert result_data["success"] is True
                    assert "results" in result_data
                    assert "summary" in result_data
                    
    @pytest.mark.asyncio
    async def test_search_tool_no_searxng_url(self, mock_context):
        """Test search when SEARXNG_URL is not configured."""
        from src.crawl4ai_mcp import search
        
        # Remove SEARXNG_URL from environment
        with patch.dict(os.environ, {}, clear=True):
            result = await search(mock_context, "test query")
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert "SEARXNG_URL environment variable is not configured" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_search_tool_network_error(self, mock_context):
        """Test search with network errors."""
        from src.crawl4ai_mcp import search
        
        with patch.dict(os.environ, {'SEARXNG_URL': 'http://localhost:8080'}):
            # Mock network error
            with patch('aiohttp.ClientSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session.get.side_effect = aiohttp.ClientError("Connection failed")
                mock_session_class.return_value = mock_session
                
                result = await search(mock_context, "test query")
                result_data = json.loads(result)
                
                assert result_data["success"] is False
                assert "error" in result_data
    
    @pytest.mark.asyncio
    async def test_search_tool_raw_markdown(self, mock_context):
        """Test search with raw markdown return."""
        from src.crawl4ai_mcp import search
        
        with patch.dict(os.environ, {'SEARXNG_URL': 'http://localhost:8080'}):
            # Mock response with URLs
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='''
            <div class="results">
                <article class="result">
                    <h3><a href="https://example.com/1">Result 1</a></h3>
                </article>
            </div>
            ''')
            
            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            
            with patch('aiohttp.ClientSession', return_value=mock_session):
                # Mock crawling for raw markdown
                mock_crawl_result = Mock()
                mock_crawl_result.success = True
                mock_crawl_result.markdown = "# Raw Markdown Content"
                
                mock_context.request_context = Mock()
                mock_context.request_context.lifespan_context = Mock()
                mock_context.request_context.lifespan_context.crawler = AsyncMock()
                mock_context.request_context.lifespan_context.crawler.arun.return_value = mock_crawl_result
                
                result = await search(mock_context, "test query", return_raw_markdown=True, num_results=1)
                result_data = json.loads(result)
                
                assert result_data["success"] is True
                assert "# Raw Markdown Content" in result_data["markdown"]
    
    @pytest.mark.asyncio
    async def test_scrape_urls_single_success(self, mock_context):
        """Test successful scraping of a single URL."""
        from src.crawl4ai_mcp import scrape_urls
        
        # Setup context properly
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock crawl result
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "# Page Title\nPage content here."
        mock_result.cleaned_html = "<h1>Page Title</h1><p>Page content here.</p>"
        mock_result.media = {"images": ["image1.jpg"], "videos": []}
        mock_result.links = {"internal": ["/page2"], "external": ["https://external.com"]}
        mock_result.screenshot = None
        mock_result.pdf = None
        mock_crawler.arun.return_value = mock_result
        
        # Test single URL scraping
        result = await scrape_urls(mock_context, "https://example.com", return_raw_markdown=True)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert result_data["markdown"] == "# Page Title\nPage content here."
        assert len(result_data["media"]["images"]) == 1
        mock_crawler.arun.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrape_urls_single_failure(self, mock_context):
        """Test scraping failure for a single URL."""
        from src.crawl4ai_mcp import scrape_urls
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock failed crawl result
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Failed to load page"
        mock_crawler.arun.return_value = mock_result
        
        # Test single URL scraping failure
        result = await scrape_urls(mock_context, "https://invalid-url.com")
        result_data = json.loads(result)
        
        assert result_data["success"] is True  # Overall success even if individual URL fails
        assert result_data["summary"]["failed"] == 1
        assert result_data["summary"]["successful"] == 0
    
    @pytest.mark.asyncio
    async def test_scrape_urls_network_timeout(self, mock_context):
        """Test scraping with network timeout."""
        from src.crawl4ai_mcp import scrape_urls
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock timeout exception
        import asyncio
        mock_crawler.arun.side_effect = asyncio.TimeoutError("Request timed out")
        
        result = await scrape_urls(mock_context, "https://slow-site.com")
        result_data = json.loads(result)
        
        assert result_data["success"] is True  # Overall operation succeeds
        assert result_data["summary"]["failed"] == 1
    
    @pytest.mark.asyncio
    async def test_scrape_urls_invalid_input(self, mock_context):
        """Test scraping with invalid input."""
        from src.crawl4ai_mcp import scrape_urls
        
        # Test with empty URL
        result = await scrape_urls(mock_context, "")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "error" in result_data
        
        # Test with None URL
        result = await scrape_urls(mock_context, None)
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "error" in result_data
    
    @pytest.mark.asyncio
    async def test_scrape_urls_multiple_success(self, mock_context):
        """Test successful scraping of multiple URLs."""
        from src.crawl4ai_mcp import scrape_urls
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock crawl results
        mock_result1 = Mock()
        mock_result1.success = True
        mock_result1.markdown = "Content 1"
        mock_result1.cleaned_html = "<p>Content 1</p>"
        mock_result1.media = {"images": [], "videos": []}
        mock_result1.links = {"internal": [], "external": []}
        mock_result1.screenshot = None
        mock_result1.pdf = None
        
        mock_result2 = Mock()
        mock_result2.success = True
        mock_result2.markdown = "Content 2"
        mock_result2.cleaned_html = "<p>Content 2</p>"
        mock_result2.media = {"images": [], "videos": []}
        mock_result2.links = {"internal": [], "external": []}
        mock_result2.screenshot = None
        mock_result2.pdf = None
        
        # Configure mock to return different results
        mock_crawler.arun.side_effect = [mock_result1, mock_result2]
        
        # Mock database operations
        with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
            mock_store.return_value = None
            
            # Test multiple URLs
            urls = ["https://example.com/1", "https://example.com/2"]
            result = await scrape_urls(mock_context, urls, return_raw_markdown=False)
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["summary"]["total_urls"] == 2
            assert result_data["summary"]["successful"] == 2
            assert mock_crawler.arun.call_count == 2
    
    @pytest.mark.asyncio
    async def test_scrape_urls_mixed_results(self, mock_context):
        """Test scraping multiple URLs with mixed success/failure."""
        from src.crawl4ai_mcp import scrape_urls
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock mixed results
        mock_result_success = Mock()
        mock_result_success.success = True
        mock_result_success.markdown = "Success content"
        mock_result_success.cleaned_html = "<p>Success content</p>"
        mock_result_success.media = {"images": [], "videos": []}
        mock_result_success.links = {"internal": [], "external": []}
        mock_result_success.screenshot = None
        mock_result_success.pdf = None
        
        mock_result_failure = Mock()
        mock_result_failure.success = False
        mock_result_failure.error_message = "Failed to load"
        
        mock_crawler.arun.side_effect = [mock_result_success, mock_result_failure]
        
        # Mock database operations
        with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
            mock_store.return_value = None
            
            urls = ["https://good-site.com", "https://bad-site.com"]
            result = await scrape_urls(mock_context, urls)
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["summary"]["total_urls"] == 2
            assert result_data["summary"]["successful"] == 1
            assert result_data["summary"]["failed"] == 1
    
    @pytest.mark.asyncio
    async def test_get_available_sources(self, mock_context):
        """Test getting available sources."""
        from src.crawl4ai_mcp import get_available_sources
        
        # Mock database response
        mock_context.crawl4ai.db_adapter.get_unique_sources.return_value = [
            {"url": "https://example.com", "count": 10},
            {"url": "https://another.com", "count": 5}
        ]
        
        result = await get_available_sources(mock_context)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert len(result_data["sources"]) == 2
        assert result_data["sources"][0]["url"] == "https://example.com"
        assert result_data["sources"][0]["count"] == 10
    
    @pytest.mark.asyncio
    async def test_perform_rag_query_success(self, mock_context):
        """Test successful RAG query."""
        from src.crawl4ai_mcp import perform_rag_query
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock search_documents function
        mock_search_results = [
            {
                "id": "1",
                "score": 0.9,
                "content": "Relevant content here",
                "url": "https://example.com/page1",
                "metadata": {"title": "Page 1"},
                "chunk_number": 1,
                "source_id": "example.com"
            }
        ]
        
        with patch('src.crawl4ai_mcp.search_documents', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_search_results
            
            result = await perform_rag_query(mock_context, "test query", match_count=1)
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["content"] == "Relevant content here"
            mock_search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_perform_rag_query_with_source_filter(self, mock_context):
        """Test RAG query with source filter."""
        from src.crawl4ai_mcp import perform_rag_query
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock search results with source filtering
        mock_search_results = [
            {
                "id": "1",
                "score": 0.9,
                "content": "Filtered content",
                "url": "https://specific-source.com/page1",
                "metadata": {"title": "Filtered Page"},
                "chunk_number": 1,
                "source_id": "specific-source.com"
            }
        ]
        
        with patch('src.crawl4ai_mcp.search_documents', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_search_results
            
            result = await perform_rag_query(
                mock_context, 
                "test query", 
                source="specific-source.com", 
                match_count=1
            )
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["results"][0]["source_id"] == "specific-source.com"
            # Verify search was called with source filter
            call_args = mock_search.call_args
            assert "source_filter" in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_perform_rag_query_hybrid_search(self, mock_context):
        """Test RAG query with hybrid search enabled."""
        from src.crawl4ai_mcp import perform_rag_query
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        with patch.dict(os.environ, {'USE_HYBRID_SEARCH': 'true'}):
            mock_search_results = [
                {
                    "id": "1",
                    "score": 0.95,
                    "content": "Hybrid search result",
                    "url": "https://example.com/hybrid",
                    "metadata": {"title": "Hybrid Result"},
                    "chunk_number": 1,
                    "source_id": "example.com"
                }
            ]
            
            with patch('src.crawl4ai_mcp.search_documents', new_callable=AsyncMock) as mock_search:
                with patch('src.crawl4ai_mcp.keyword_search_documents', new_callable=AsyncMock) as mock_keyword:
                    mock_search.return_value = mock_search_results
                    mock_keyword.return_value = mock_search_results
                    
                    result = await perform_rag_query(mock_context, "test query")
                    result_data = json.loads(result)
                    
                    assert result_data["success"] is True
                    # Both vector and keyword search should be called
                    mock_search.assert_called()
                    mock_keyword.assert_called()
    
    @pytest.mark.asyncio
    async def test_perform_rag_query_no_results(self, mock_context):
        """Test RAG query with no results."""
        from src.crawl4ai_mcp import perform_rag_query
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        with patch('src.crawl4ai_mcp.search_documents', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []  # No results
            
            result = await perform_rag_query(mock_context, "nonexistent query")
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert len(result_data["results"]) == 0
            assert "No relevant documents found" in result_data["message"]
    
    @pytest.mark.asyncio
    async def test_perform_rag_query_error_handling(self, mock_context):
        """Test RAG query error handling."""
        from src.crawl4ai_mcp import perform_rag_query
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        with patch('src.crawl4ai_mcp.search_documents', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Database error")
            
            result = await perform_rag_query(mock_context, "test query")
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert "error" in result_data
            assert "Database error" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_search_code_examples(self, mock_context):
        """Test searching code examples."""
        from src.crawl4ai_mcp import search_code_examples
        
        # Test when feature is disabled
        with patch.dict('os.environ', {'ENABLE_AGENTIC_RAG': 'false'}):
            result = await search_code_examples(mock_context, "python function")
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "not enabled" in result_data["error"]
        
        # Test when feature is enabled
        with patch.dict('os.environ', {'ENABLE_AGENTIC_RAG': 'true'}):
            # Mock embedding creation
            mock_context.crawl4ai.embedding_service.create_embedding.return_value = [0.1] * 1536
            
            # Mock search results
            mock_results = [
                {
                    "id": "1",
                    "score": 0.85,
                    "language": "python",
                    "code": "def hello(): return 'world'",
                    "description": "Hello function",
                    "url": "https://example.com"
                }
            ]
            mock_context.crawl4ai.db_adapter.search_code_examples.return_value = mock_results
            
            result = await search_code_examples(mock_context, "python function", match_count=1)
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["language"] == "python"
    
    @pytest.mark.asyncio
    async def test_smart_crawl_url_txt_file_success(self, mock_context):
        """Test smart crawl for text files."""
        from src.crawl4ai_mcp import smart_crawl_url
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock crawl result for txt file
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "Line 1\nLine 2\nLine 3\n" * 100  # Long text
        mock_result.cleaned_html = ""
        mock_result.media = {"images": [], "videos": []}
        mock_result.links = {"internal": [], "external": []}
        mock_result.screenshot = None
        mock_result.pdf = None
        mock_crawler.arun.return_value = mock_result
        
        # Mock database operations
        with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
            mock_store.return_value = None
            
            result = await smart_crawl_url(
                mock_context, 
                "https://example.com/file.txt",
                chunk_size=100,
                return_raw_markdown=False
            )
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["type"] == "txt"
            assert result_data["chunks_created"] > 1  # Should create multiple chunks
    
    @pytest.mark.asyncio
    async def test_smart_crawl_url_sitemap_success(self, mock_context):
        """Test smart crawl for sitemap files."""
        from src.crawl4ai_mcp import smart_crawl_url
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock sitemap parsing
        with patch('src.crawl4ai_mcp.parse_sitemap') as mock_parse:
            mock_parse.return_value = [
                "https://example.com/page1",
                "https://example.com/page2"
            ]
            
            # Mock crawl results
            mock_result = Mock()
            mock_result.success = True
            mock_result.markdown = "Page content"
            mock_result.cleaned_html = "<p>Page content</p>"
            mock_result.media = {"images": [], "videos": []}
            mock_result.links = {"internal": [], "external": []}
            mock_result.screenshot = None
            mock_result.pdf = None
            mock_crawler.arun.return_value = mock_result
            
            # Mock database operations
            with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
                mock_store.return_value = None
                
                result = await smart_crawl_url(
                    mock_context,
                    "https://example.com/sitemap.xml",
                    max_depth=1,
                    return_raw_markdown=False
                )
                result_data = json.loads(result)
                
                assert result_data["success"] is True
                assert result_data["type"] == "sitemap"
                assert "urls_found" in result_data
                mock_parse.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_smart_crawl_url_regular_webpage(self, mock_context):
        """Test smart crawl for regular webpages."""
        from src.crawl4ai_mcp import smart_crawl_url
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock regular webpage crawling with internal links
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "Main page content"
        mock_result.cleaned_html = "<p>Main page content</p>"
        mock_result.media = {"images": [], "videos": []}
        mock_result.links = {
            "internal": ["https://example.com/page2", "https://example.com/page3"],
            "external": ["https://external.com"]
        }
        mock_result.screenshot = None
        mock_result.pdf = None
        mock_crawler.arun.return_value = mock_result
        
        with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
            mock_store.return_value = None
            
            result = await smart_crawl_url(
                mock_context,
                "https://example.com/main",
                max_depth=1,
                return_raw_markdown=False
            )
            result_data = json.loads(result)
            
            assert result_data["success"] is True
            assert result_data["type"] == "webpage"
            assert result_data["pages_crawled"] >= 1
    
    @pytest.mark.asyncio
    async def test_smart_crawl_url_with_rag_query(self, mock_context):
        """Test smart crawl with RAG query functionality."""
        from src.crawl4ai_mcp import smart_crawl_url
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock crawl result
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "Content with specific information about Python programming"
        mock_result.cleaned_html = "<p>Python content</p>"
        mock_result.media = {"images": [], "videos": []}
        mock_result.links = {"internal": [], "external": []}
        mock_result.screenshot = None
        mock_result.pdf = None
        mock_crawler.arun.return_value = mock_result
        
        # Mock RAG query results
        with patch('src.crawl4ai_mcp.store_crawled_page', new_callable=AsyncMock) as mock_store:
            with patch('src.crawl4ai_mcp.search_documents', new_callable=AsyncMock) as mock_search:
                mock_store.return_value = None
                mock_search.return_value = [
                    {
                        "content": "Python is a programming language",
                        "url": "https://example.com",
                        "score": 0.95
                    }
                ]
                
                result = await smart_crawl_url(
                    mock_context,
                    "https://example.com/python-guide",
                    query=["Python programming"],
                    return_raw_markdown=False
                )
                result_data = json.loads(result)
                
                assert result_data["success"] is True
                assert "rag_results" in result_data
                assert len(result_data["rag_results"]) > 0
    
    @pytest.mark.asyncio
    async def test_smart_crawl_url_error_handling(self, mock_context):
        """Test smart crawl error handling."""
        from src.crawl4ai_mcp import smart_crawl_url
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_crawler = AsyncMock()
        mock_context.request_context.lifespan_context.crawler = mock_crawler
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock crawl failure
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Failed to load page"
        mock_crawler.arun.return_value = mock_result
        
        result = await smart_crawl_url(mock_context, "https://invalid-url.com")
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "error" in result_data
    
    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_success(self, mock_context):
        """Test AI script hallucination checking."""
        from src.crawl4ai_mcp import check_ai_script_hallucinations
        
        # Mock environment variable for Neo4j
        with patch.dict(os.environ, {'ENABLE_KNOWLEDGE_GRAPH': 'true', 'NEO4J_URI': 'bolt://localhost:7687'}):
            # Setup context
            mock_context.request_context = Mock()
            mock_context.request_context.lifespan_context = Mock()
            mock_context.request_context.lifespan_context.database_client = AsyncMock()
            
            # Mock file reading
            test_script_content = '''
            import requests
            
            def fetch_data():
                response = requests.get("https://api.example.com/data")
                return response.json()
            '''
            
            # Mock graph verification
            with patch('src.crawl4ai_mcp.verify_with_knowledge_graph', new_callable=AsyncMock) as mock_verify:
                mock_verify.return_value = {
                    "verification_results": [
                        {
                            "entity": "requests library",
                            "confidence": 0.95,
                            "verified": True,
                            "sources": ["https://docs.python-requests.org/"]
                        }
                    ],
                    "overall_confidence": 0.95,
                    "hallucination_risk": "low"
                }
                
                with patch('builtins.open', mock_open(read_data=test_script_content)):
                    result = await check_ai_script_hallucinations(mock_context, "/path/to/script.py")
                    result_data = json.loads(result)
                    
                    assert result_data["success"] is True
                    assert result_data["hallucination_risk"] == "low"
                    assert result_data["overall_confidence"] == 0.95
                    assert len(result_data["verification_results"]) > 0
    
    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_disabled(self, mock_context):
        """Test AI script hallucination checking when feature is disabled."""
        from src.crawl4ai_mcp import check_ai_script_hallucinations
        
        # Mock environment without knowledge graph enabled
        with patch.dict(os.environ, {'ENABLE_KNOWLEDGE_GRAPH': 'false'}):
            result = await check_ai_script_hallucinations(mock_context, "/path/to/script.py")
            result_data = json.loads(result)
            
            assert result_data["success"] is False
            assert "not enabled" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_file_not_found(self, mock_context):
        """Test AI script hallucination checking with non-existent file."""
        from src.crawl4ai_mcp import check_ai_script_hallucinations
        
        with patch.dict(os.environ, {'ENABLE_KNOWLEDGE_GRAPH': 'true', 'NEO4J_URI': 'bolt://localhost:7687'}):
            # Mock file not found
            with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
                result = await check_ai_script_hallucinations(mock_context, "/nonexistent/script.py")
                result_data = json.loads(result)
                
                assert result_data["success"] is False
                assert "File not found" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_get_available_sources_success(self, mock_context):
        """Test getting available sources successfully."""
        from src.crawl4ai_mcp import get_available_sources
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Mock database adapter with get_sources method
        mock_adapter = AsyncMock()
        mock_adapter.get_sources.return_value = [
            {"source_id": "example.com", "summary": "Example website", "total_word_count": 5000},
            {"source_id": "docs.python.org", "summary": "Python documentation", "total_word_count": 15000}
        ]
        mock_context.request_context.lifespan_context.database_client = mock_adapter
        
        result = await get_available_sources(mock_context)
        result_data = json.loads(result)
        
        assert result_data["success"] is True
        assert len(result_data["sources"]) == 2
        assert result_data["sources"][0]["source_id"] == "example.com"
        assert result_data["total_sources"] == 2
    
    @pytest.mark.asyncio
    async def test_get_available_sources_error(self, mock_context):
        """Test getting available sources with database error."""
        from src.crawl4ai_mcp import get_available_sources
        
        # Setup context with failing database
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_adapter = AsyncMock()
        mock_adapter.get_sources.side_effect = Exception("Database connection failed")
        mock_context.request_context.lifespan_context.database_client = mock_adapter
        
        result = await get_available_sources(mock_context)
        result_data = json.loads(result)
        
        assert result_data["success"] is False
        assert "error" in result_data
        assert "Database connection failed" in result_data["error"]
    
    @pytest.mark.asyncio
    async def test_search_code_examples_enabled(self, mock_context):
        """Test searching code examples when feature is enabled."""
        from src.crawl4ai_mcp import search_code_examples
        
        # Setup context
        mock_context.request_context = Mock()
        mock_context.request_context.lifespan_context = Mock()
        mock_context.request_context.lifespan_context.database_client = AsyncMock()
        
        # Test when feature is enabled
        with patch.dict(os.environ, {'ENABLE_AGENTIC_RAG': 'true'}):
            # Mock search results
            with patch('src.crawl4ai_mcp.search_code_examples_db', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = [
                    {
                        "id": "1",
                        "score": 0.85,
                        "language": "python",
                        "code": "def hello(): return 'world'",
                        "description": "Hello function",
                        "url": "https://example.com",
                        "metadata": {"framework": "basic"}
                    }
                ]
                
                result = await search_code_examples(mock_context, "python function", match_count=1)
                result_data = json.loads(result)
                
                assert result_data["success"] is True
                assert len(result_data["results"]) == 1
                assert result_data["results"][0]["language"] == "python"
                mock_search.assert_called_once()


# Import mock_open for file mocking
from unittest.mock import mock_open


if __name__ == "__main__":
    pytest.main([__file__, "-v"])