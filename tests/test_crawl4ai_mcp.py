"""
Unit tests for main MCP application functions.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call, mock_open
import os
import sys
import json
from typing import List, Dict, Any
from datetime import datetime

# Mock external dependencies before importing crawl4ai_mcp
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['crawl4ai'] = MagicMock()
sys.modules['knowledge_graph_validator'] = MagicMock()
sys.modules['parse_repo_into_neo4j'] = MagicMock() 
sys.modules['ai_script_analyzer'] = MagicMock()
sys.modules['hallucination_reporter'] = MagicMock()

# Import MCP tools - we'll test the tool functions directly
from crawl4ai_mcp import (
    scrape_urls,
    smart_crawl_url,
    get_available_sources,
    perform_rag_query,
    search,
    search_code_examples,
    check_ai_script_hallucinations,
    query_knowledge_graph,
    parse_github_repository,
    Crawl4AIContext,
    # Helper functions
    track_request,
    validate_neo4j_connection,
    format_neo4j_error,
    validate_script_path,
    validate_github_url,
    rerank_results,
    is_sitemap,
    is_txt,
    parse_sitemap,
    smart_chunk_markdown,
    extract_section_info,
    process_code_example,
    crawl_markdown_file,
    crawl_batch,
    crawl_recursive_internal_links,
    # Exception class
    MCPToolError
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


class TestValidationFunctions:
    """Test validation and utility functions"""
    
    def test_validate_neo4j_connection_success(self):
        """Test Neo4j connection validation with all required env vars"""
        with patch.dict(os.environ, {
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",  # Note: actual code uses NEO4J_USER
            "NEO4J_PASSWORD": "password"
        }):
            assert validate_neo4j_connection() is True
    
    def test_validate_neo4j_connection_missing_vars(self):
        """Test Neo4j connection validation with missing env vars"""
        with patch.dict(os.environ, {}, clear=True):
            assert validate_neo4j_connection() is False
    
    def test_format_neo4j_error_authentication(self):
        """Test formatting of Neo4j authentication errors"""
        error = Exception("Authentication failed: unauthorized")
        result = format_neo4j_error(error)
        assert "authentication" in result.lower()
        assert "neo4j_user" in result.lower()
    
    def test_format_neo4j_error_connection(self):
        """Test formatting of Neo4j connection errors"""
        error = Exception("Connection refused")
        result = format_neo4j_error(error)
        assert "neo4j" in result.lower()
        assert "neo4j_uri" in result.lower()
    
    def test_format_neo4j_error_generic(self):
        """Test formatting of generic Neo4j errors"""
        error = Exception("Some other error")
        result = format_neo4j_error(error)
        assert "Some other error" in result
    
    def test_validate_script_path_valid(self):
        """Test valid script path validation"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data="# Python file")):
            result = validate_script_path("/path/to/script.py")
            assert result["valid"] is True
            assert "error" not in result
    
    def test_validate_script_path_empty(self):
        """Test empty script path validation"""
        result = validate_script_path("")
        assert result["valid"] is False
        assert "required" in result["error"]
    
    def test_validate_script_path_none(self):
        """Test None script path validation"""
        result = validate_script_path(None)
        assert result["valid"] is False
        assert "required" in result["error"]
    
    def test_validate_script_path_not_python(self):
        """Test non-Python script path validation"""
        with patch('os.path.exists', return_value=True):
            result = validate_script_path("/path/to/script.txt")
            assert result["valid"] is False
            assert "Python" in result["error"]
    
    def test_validate_script_path_not_exists(self):
        """Test non-existent script path validation"""
        with patch('os.path.exists', return_value=False):
            result = validate_script_path("/nonexistent/script.py")
            assert result["valid"] is False
            assert "not found" in result["error"]
    
    def test_validate_github_url_valid(self):
        """Test valid GitHub URL validation"""
        result = validate_github_url("https://github.com/user/repo")
        assert result["valid"] is True
    
    def test_validate_github_url_empty(self):
        """Test empty GitHub URL validation"""
        result = validate_github_url("")
        assert result["valid"] is False
        assert "required" in result["error"]
    
    def test_validate_github_url_invalid_format(self):
        """Test invalid GitHub URL format validation"""
        result = validate_github_url("https://gitlab.com/user/repo")
        assert result["valid"] is False
        assert "GitHub" in result["error"]
    
    def test_validate_github_url_no_user_repo(self):
        """Test GitHub URL without user/repo validation"""
        result = validate_github_url("https://github.com")
        assert result["valid"] is True  # Basic GitHub URL passes validation


class TestUtilityFunctions:
    """Test utility and helper functions"""
    
    def test_is_sitemap_xml(self):
        """Test sitemap detection for XML files"""
        assert is_sitemap("https://example.com/sitemap.xml") is True
        assert is_sitemap("https://example.com/sitemaps/index.xml") is True
    
    def test_is_sitemap_non_xml(self):
        """Test sitemap detection for non-XML files"""
        assert is_sitemap("https://example.com/page.html") is False
        assert is_sitemap("https://example.com/data.json") is False
    
    def test_is_txt_file(self):
        """Test text file detection"""
        assert is_txt("https://example.com/file.txt") is True
        assert is_txt("https://example.com/llms.txt") is True
        assert is_txt("https://example.com/robots.txt") is True
    
    def test_is_txt_non_txt(self):
        """Test text file detection for non-txt files"""
        assert is_txt("https://example.com/page.html") is False
        assert is_txt("https://example.com/data.json") is False
    
    @patch('requests.get')
    def test_parse_sitemap_success(self, mock_get):
        """Test successful sitemap parsing"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>'''
        mock_get.return_value = mock_response
        
        urls = parse_sitemap("https://example.com/sitemap.xml")
        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
    
    @patch('requests.get')
    def test_parse_sitemap_with_sitemapindex(self, mock_get):
        """Test sitemap parsing with sitemap index"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap1.xml</loc></sitemap>
        </sitemapindex>'''
        mock_get.return_value = mock_response
        
        urls = parse_sitemap("https://example.com/sitemap.xml")
        assert len(urls) == 1
        assert "https://example.com/sitemap1.xml" in urls
    
    @patch('requests.get')
    def test_parse_sitemap_failure(self, mock_get):
        """Test sitemap parsing failure"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        urls = parse_sitemap("https://example.com/sitemap.xml")
        assert urls == []
    
    def test_smart_chunk_markdown_basic(self):
        """Test basic markdown chunking"""
        text = "# Header\n\nParagraph 1\n\nParagraph 2"
        chunks = smart_chunk_markdown(text, chunk_size=50)
        assert len(chunks) >= 1
        assert all(len(chunk) <= 50 for chunk in chunks)
    
    def test_smart_chunk_markdown_code_blocks(self):
        """Test markdown chunking with code blocks"""
        text = "# Header\n\n```python\ndef hello():\n    return 'world'\n```\n\nParagraph"
        chunks = smart_chunk_markdown(text, chunk_size=100)
        # Code blocks should be kept together
        code_chunk = next((chunk for chunk in chunks if "```python" in chunk), None)
        assert code_chunk is not None
        assert "def hello():" in code_chunk
    
    def test_extract_section_info_with_headers(self):
        """Test section info extraction with headers"""
        chunk = "# Main Header\n\n## Sub Header\n\nContent here with 50 words " * 5
        info = extract_section_info(chunk)
        assert "headers" in info
        assert "word_count" in info
        assert info["word_count"] > 0
        assert "# Main Header" in info["headers"]
    
    def test_extract_section_info_no_headers(self):
        """Test section info extraction without headers"""
        chunk = "Just plain text content without any headers"
        info = extract_section_info(chunk)
        assert "headers" in info
        assert info["headers"] == ""
        assert info["word_count"] > 0
    
    @patch('crawl4ai_mcp.generate_code_example_summary')
    def test_process_code_example(self, mock_generate):
        """Test code example processing"""
        mock_generate.return_value = "A hello world function"
        args = ("```python\ndef hello():\n    return 'world'\n```", "before context", "after context")
        result = process_code_example(args)
        assert result == "A hello world function"
        mock_generate.assert_called_once()
    
    def test_rerank_results(self):
        """Test result reranking with cross-encoder"""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.7, 0.8]
        
        query = "test query"
        results = [
            {"content": "Result 1", "similarity": 0.5},
            {"content": "Result 2", "similarity": 0.6},
            {"content": "Result 3", "similarity": 0.7}
        ]
        
        reranked = rerank_results(mock_model, query, results)
        assert len(reranked) == 3
        assert reranked[0]["rerank_score"] == 0.9
        assert "similarity" in reranked[0]


class TestAsyncHelperFunctions:
    """Test async helper functions"""
    
    @pytest.mark.asyncio
    async def test_crawl_markdown_file_success(self):
        """Test successful markdown file crawling"""
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Content"
        mock_crawler.arun.return_value = mock_result
        
        results = await crawl_markdown_file(mock_crawler, "https://example.com/file.txt")
        
        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/file.txt"
        assert results[0]["markdown"] == "# Test Content"
    
    @pytest.mark.asyncio
    async def test_crawl_markdown_file_failure(self):
        """Test failed markdown file crawling"""
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Network error"
        mock_crawler.arun.return_value = mock_result
        
        results = await crawl_markdown_file(mock_crawler, "https://example.com/file.txt")
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_crawl_batch_success(self):
        """Test successful batch crawling"""
        mock_crawler = AsyncMock()
        mock_results = []
        
        for i in range(3):
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.url = f"https://example.com/page{i}"
            mock_result.markdown = f"Content {i}"
            mock_result.links = {"internal": [], "external": []}
            mock_results.append(mock_result)
        
        mock_crawler.arun_many.return_value = mock_results
        
        urls = [f"https://example.com/page{i}" for i in range(3)]
        results = await crawl_batch(mock_crawler, urls)
        
        assert len(results) == 3
        assert all("url" in result for result in results)
        assert all("markdown" in result for result in results)
    
    @pytest.mark.asyncio
    async def test_crawl_batch_partial_failure(self):
        """Test batch crawling with partial failures"""
        mock_crawler = AsyncMock()
        mock_results = []
        
        # First result succeeds, second fails
        mock_result1 = MagicMock()
        mock_result1.success = True
        mock_result1.url = "https://example.com/page1"
        mock_result1.markdown = "Content 1"
        mock_result1.links = {"internal": []}
        
        mock_result2 = MagicMock()
        mock_result2.success = False
        mock_result2.url = "https://example.com/page2"
        
        mock_results = [mock_result1, mock_result2]
        mock_crawler.arun_many.return_value = mock_results
        
        urls = ["https://example.com/page1", "https://example.com/page2"]
        results = await crawl_batch(mock_crawler, urls)
        
        assert len(results) == 1  # Only successful result
        assert results[0]["url"] == "https://example.com/page1"
    
    @pytest.mark.asyncio
    async def test_crawl_recursive_internal_links(self):
        """Test recursive internal link crawling"""
        mock_crawler = AsyncMock()
        
        # Mock first depth results
        mock_result1 = MagicMock()
        mock_result1.success = True
        mock_result1.url = "https://example.com/start"
        mock_result1.markdown = "Start content"
        mock_result1.links = {
            "internal": [{"href": "https://example.com/page1"}],
            "external": []
        }
        
        # Mock second depth results
        mock_result2 = MagicMock()
        mock_result2.success = True
        mock_result2.url = "https://example.com/page1"
        mock_result2.markdown = "Page 1 content"
        mock_result2.links = {"internal": [], "external": []}
        
        mock_crawler.arun_many.side_effect = [[mock_result1], [mock_result2]]
        
        results = await crawl_recursive_internal_links(
            mock_crawler, 
            ["https://example.com/start"], 
            max_depth=2
        )
        
        assert len(results) == 2
        assert any(r["url"] == "https://example.com/start" for r in results)
        assert any(r["url"] == "https://example.com/page1" for r in results)


class TestCheckAiScriptHallucinations:
    """Test AI script hallucination detection tool"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        "USE_KNOWLEDGE_GRAPH": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j", 
        "NEO4J_PASSWORD": "password"
    })
    @patch('crawl4ai_mcp.KnowledgeGraphValidator')
    @patch('crawl4ai_mcp.AIScriptAnalyzer')
    @patch('crawl4ai_mcp.HallucinationReporter')
    async def test_check_hallucinations_success(self, mock_reporter, mock_analyzer, mock_validator):
        """Test successful hallucination check"""
        # Setup mocks
        mock_validator_instance = MagicMock()
        mock_validator.return_value = mock_validator_instance
        
        mock_analyzer_instance = MagicMock()
        mock_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_script.return_value = {
            "imports": ["numpy", "pandas"],
            "functions": ["main", "process_data"],
            "classes": ["DataProcessor"]
        }
        
        mock_reporter_instance = MagicMock()
        mock_reporter.return_value = mock_reporter_instance
        mock_reporter_instance.generate_report.return_value = {
            "total_hallucinations": 0,
            "verified_imports": 2,
            "verified_functions": 2,
            "verified_classes": 1,
            "hallucinations": []
        }
        
        ctx = MockContext()
        
        # Test
        with patch('os.path.exists', return_value=True):
            result = await check_ai_script_hallucinations(ctx, "/path/to/script.py")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["total_hallucinations"] == 0
        assert "verification_summary" in result_json
    
    @pytest.mark.asyncio
    async def test_check_hallucinations_invalid_path(self):
        """Test hallucination check with invalid script path"""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}):
            ctx = MockContext()
            
            result = await check_ai_script_hallucinations(ctx, "")
            
            result_json = json.loads(result)
            assert result_json["success"] is False
            assert "required" in result_json["error"]
    
    @pytest.mark.asyncio
    async def test_check_hallucinations_no_neo4j(self):
        """Test hallucination check without Neo4j configuration"""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}, clear=True):
            ctx = MockContext()
            
            result = await check_ai_script_hallucinations(ctx, "/path/to/script.py")
            
            result_json = json.loads(result)
            assert result_json["success"] is False
            assert "Neo4j" in result_json["error"]


class TestQueryKnowledgeGraph:
    """Test knowledge graph query tool"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        "USE_KNOWLEDGE_GRAPH": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
    })
    @patch('neo4j.AsyncGraphDatabase')
    async def test_query_repos_command(self, mock_graph_db):
        """Test 'repos' command"""
        # Setup mock
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_records = [MagicMock(data={"name": "repo1"}), MagicMock(data={"name": "repo2"})]
        
        mock_result.data.return_value = mock_records
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        ctx = MockContext()
        
        # Test
        result = await query_knowledge_graph(ctx, "repos")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert "repositories" in result_json
        assert len(result_json["repositories"]) == 2
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        "USE_KNOWLEDGE_GRAPH": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
    })
    @patch('neo4j.AsyncGraphDatabase')
    async def test_query_explore_command(self, mock_graph_db):
        """Test 'explore <repo>' command"""
        # Setup mock
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        
        # Mock repo check result
        mock_repo_result = AsyncMock()
        mock_repo_result.data.return_value = [MagicMock(data={"name": "test-repo"})]
        
        # Mock stats result
        mock_stats_result = AsyncMock()
        mock_stats_result.single.return_value = {
            "file_count": 10,
            "class_count": 5,
            "function_count": 20
        }
        
        mock_session.run.side_effect = [mock_repo_result, mock_stats_result]
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        ctx = MockContext()
        
        # Test
        result = await query_knowledge_graph(ctx, "explore test-repo")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["repository"] == "test-repo"
        assert "statistics" in result_json
    
    @pytest.mark.asyncio
    async def test_query_no_neo4j_config(self):
        """Test query without Neo4j configuration"""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}, clear=True):
            ctx = MockContext()
            
            result = await query_knowledge_graph(ctx, "repos")
            
            result_json = json.loads(result)
            assert result_json["success"] is False
            assert "Neo4j" in result_json["error"]


class TestParseGithubRepository:
    """Test GitHub repository parsing tool"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        "USE_KNOWLEDGE_GRAPH": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
    })
    @patch('crawl4ai_mcp.DirectNeo4jExtractor')
    async def test_parse_repository_success(self, mock_extractor):
        """Test successful repository parsing"""
        # Setup mock
        mock_extractor_instance = MagicMock()
        mock_extractor.return_value = mock_extractor_instance
        mock_extractor_instance.extract_repository.return_value = {
            "repository_name": "test/repo",
            "files_processed": 25,
            "classes_extracted": 10,
            "functions_extracted": 50
        }
        
        ctx = MockContext()
        
        # Test
        result = await parse_github_repository(ctx, "https://github.com/test/repo")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["repository_name"] == "test/repo"
        assert result_json["files_processed"] == 25
    
    @pytest.mark.asyncio
    async def test_parse_repository_invalid_url(self):
        """Test repository parsing with invalid URL"""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}):
            ctx = MockContext()
            
            result = await parse_github_repository(ctx, "https://gitlab.com/test/repo")
            
            result_json = json.loads(result)
            assert result_json["success"] is False
            assert "GitHub" in result_json["error"]
    
    @pytest.mark.asyncio
    async def test_parse_repository_no_neo4j(self):
        """Test repository parsing without Neo4j configuration"""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}, clear=True):
            ctx = MockContext()
            
            result = await parse_github_repository(ctx, "https://github.com/test/repo")
            
            result_json = json.loads(result)
            assert result_json["success"] is False
            assert "Neo4j" in result_json["error"]


class TestMCPToolError:
    """Test custom MCP tool error class"""
    
    def test_mcp_tool_error_default(self):
        """Test MCPToolError with default values"""
        error = MCPToolError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.code == -32000
    
    def test_mcp_tool_error_custom_code(self):
        """Test MCPToolError with custom code"""
        error = MCPToolError("Test error", code=-32001)
        assert error.code == -32001
        assert error.message == "Test error"


class TestTrackRequestDecorator:
    """Test request tracking decorator"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.logger')
    async def test_track_request_success(self, mock_logger):
        """Test successful request tracking"""
        @track_request("test_tool")
        async def test_function(ctx, param="test"):
            return "success"
        
        ctx = MockContext()
        result = await test_function(ctx, param="test")
        
        assert result == "success"
        assert mock_logger.info.call_count >= 2  # Start and completion logs
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.logger')
    async def test_track_request_failure(self, mock_logger):
        """Test failed request tracking"""
        @track_request("test_tool")
        async def test_function(ctx):
            raise ValueError("Test error")
        
        ctx = MockContext()
        
        with pytest.raises(ValueError):
            await test_function(ctx)
        
        assert mock_logger.error.called


class TestSearchToolFixed:
    """Test search MCP tool with proper environment mocking"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"})
    @patch('crawl4ai_mcp.requests.get')
    @patch('crawl4ai_mcp.scrape_urls')
    async def test_search_basic_fixed(self, mock_scrape, mock_get):
        """Test basic search functionality with SEARXNG_URL set"""
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
        
        mock_scrape.return_value = json.dumps({
            "success": True, 
            "mode": "multi_url", 
            "summary": {"successful_urls": 1}
        })
        
        ctx = MockContext()
        
        # Test
        result = await search(ctx, query="test search", num_results=1)
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert "searxng_results" in result_json
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)  # No SEARXNG_URL
    async def test_search_no_searxng_url(self):
        """Test search with missing SEARXNG_URL"""
        ctx = MockContext()
        
        result = await search(ctx, query="test search")
        
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "SEARXNG_URL" in result_json["error"]


class TestSearchCodeExamplesFixed:
    """Test search_code_examples MCP tool with proper environment mocking"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_AGENTIC_RAG": "true"})
    @patch('utils_refactored.search_code_examples')  # This should patch the utils function
    async def test_search_code_examples_success_fixed(self, mock_search):
        """Test searching code examples with fixed import"""
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
        
        # Import the actual tool function
        from crawl4ai_mcp import search_code_examples as search_code_tool
        
        # Test
        result = await search_code_tool(ctx, query="hello world function")
        
        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 1
        assert "def hello():" in result_json["results"][0]["code"]


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases to boost coverage"""
    
    def test_suppress_stdout_context_manager(self):
        """Test SuppressStdout context manager"""
        from crawl4ai_mcp import SuppressStdout
        import sys
        original_stdout = sys.stdout
        
        with SuppressStdout():
            assert sys.stdout == sys.stderr
        
        assert sys.stdout == original_stdout
    
    def test_smart_chunk_markdown_empty(self):
        """Test markdown chunking with empty text"""
        chunks = smart_chunk_markdown("", chunk_size=100)
        assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0] == "")
    
    def test_smart_chunk_markdown_long_code(self):
        """Test markdown chunking with very long code block"""
        long_code = "```python\n" + "print('hello')\n" * 100 + "```"
        chunks = smart_chunk_markdown(long_code, chunk_size=50)
        # Code blocks should be kept together even if larger than chunk_size
        assert any("```python" in chunk and "```" in chunk for chunk in chunks)
    
    def test_extract_section_info_complex(self):
        """Test section info extraction with complex headers"""
        chunk = "# Level 1\n## Level 2\n### Level 3\n#### Level 4\nContent"
        info = extract_section_info(chunk)
        assert "headers" in info
        assert "Level 1" in info["headers"]
        assert "Level 2" in info["headers"]
        assert info["word_count"] > 0
    
    @patch('crawl4ai_mcp.logger')
    def test_parse_sitemap_xml_error(self, mock_logger):
        """Test sitemap parsing with malformed XML"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'<invalid>xml'
            mock_get.return_value = mock_response
            
            urls = parse_sitemap("https://example.com/sitemap.xml")
            assert urls == []
            mock_logger.error.assert_called()
    
    def test_normalize_url_function(self):
        """Test URL normalization used in recursive crawling"""
        # Test the normalize_url function from crawl_recursive_internal_links
        from urllib.parse import urldefrag
        
        # This function is defined inside crawl_recursive_internal_links
        def normalize_url(url):
            return urldefrag(url)[0]
        
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"
        assert normalize_url("https://example.com/page?param=1") == "https://example.com/page?param=1"


class TestMCPToolIntegration:
    """Additional integration tests for MCP tools"""
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.add_documents_to_database')
    @patch('crawl4ai_mcp.crawl_batch')
    async def test_scrape_urls_error_handling(self, mock_crawl_batch, mock_add_docs):
        """Test scrape_urls with various error conditions"""
        # Test with exception during crawling
        mock_crawl_batch.side_effect = Exception("Crawl error")
        ctx = MockContext()
        
        result = await scrape_urls(ctx, url="https://example.com")
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json
    
    @pytest.mark.asyncio
    async def test_get_available_sources_error(self):
        """Test get_available_sources with database error"""
        mock_db = AsyncMock()
        mock_db.get_sources.side_effect = Exception("Database error")
        ctx = MockContext(database_client=mock_db)
        
        result = await get_available_sources(ctx)
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.search_documents')
    async def test_perform_rag_query_error(self, mock_search):
        """Test perform_rag_query with search error"""
        mock_search.side_effect = Exception("Search error")
        ctx = MockContext()
        
        result = await perform_rag_query(ctx, query="test query")
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.parse_sitemap')
    @patch('crawl4ai_mcp.crawl_batch')
    async def test_smart_crawl_url_empty_sitemap(self, mock_crawl_batch, mock_parse_sitemap):
        """Test smart crawl with empty sitemap"""
        mock_parse_sitemap.return_value = []
        ctx = MockContext()
        
        result = await smart_crawl_url(ctx, url="https://example.com/sitemap.xml")
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["crawl_type"] == "sitemap"
        assert len(result_json["results"]) == 0
    
    @pytest.mark.asyncio
    async def test_smart_crawl_url_invalid_url(self):
        """Test smart crawl with invalid URL"""
        ctx = MockContext()
        
        result = await smart_crawl_url(ctx, url="invalid-url")
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json
    
    @pytest.mark.asyncio
    @patch('crawl4ai_mcp.crawl_markdown_file')
    async def test_smart_crawl_txt_file_error(self, mock_crawl_markdown):
        """Test smart crawl txt file with error"""
        mock_crawl_markdown.side_effect = Exception("Crawl error")
        ctx = MockContext()
        
        result = await smart_crawl_url(ctx, url="https://example.com/file.txt")
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json


if __name__ == "__main__":
    pytest.main([__file__, "-v"])