"""
Comprehensive tests for crawl4ai_mcp.py to improve coverage.
Focus on untested MCP tools and edge cases.
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from crawl4ai_mcp import (
    Crawl4AIContext,
    check_ai_script_hallucinations,
    parse_github_repository,
    query_knowledge_graph,
)

from tests.test_doubles import FakeCrawler


class MockContext:
    """Mock context for testing MCP tools"""

    def __init__(
        self,
        crawler=None,
        database_client=None,
        reranking_model=None,
        knowledge_validator=None,
        repo_extractor=None,
    ):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = Crawl4AIContext(
            crawler=crawler or AsyncMock(),
            database_client=database_client or AsyncMock(),
            reranking_model=reranking_model,
            knowledge_validator=knowledge_validator,
            repo_extractor=repo_extractor,
        )


@pytest.mark.skipif(
    os.getenv("USE_KNOWLEDGE_GRAPH", "false") != "true",
    reason="Knowledge graph functionality is disabled",
)
class TestKnowledgeGraphTools:
    """Test knowledge graph related MCP tools"""

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_success(self):
        """Test successful hallucination check"""

        # Setup
        mock_validator = AsyncMock()
        mock_validator.validate_script.return_value = {
            "has_hallucinations": False,
            "violations": [],
            "analysis": {
                "imports": ["pandas", "numpy"],
                "function_calls": ["pd.DataFrame", "np.array"],
                "class_instantiations": [],
                "method_calls": [],
            },
            "summary": "No hallucinations detected",
        }

        ctx = MockContext(knowledge_validator=mock_validator)

        # Test
        result = await check_ai_script_hallucinations(ctx, script_path="test_script.py")

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["has_hallucinations"] is False
        assert len(result_json["violations"]) == 0
        mock_validator.validate_script.assert_called_once_with("test_script.py")

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_with_violations(self):
        """Test hallucination check with violations found"""
        # Setup
        mock_validator = AsyncMock()
        mock_validator.validate_script.return_value = {
            "has_hallucinations": True,
            "violations": [
                {
                    "type": "import",
                    "line": 3,
                    "content": "import fake_library",
                    "reason": "Library 'fake_library' not found in knowledge graph",
                },
            ],
            "analysis": {
                "imports": ["fake_library"],
                "function_calls": [],
                "class_instantiations": [],
                "method_calls": [],
            },
            "summary": "1 hallucination detected",
        }

        ctx = MockContext(knowledge_validator=mock_validator)

        # Test
        result = await check_ai_script_hallucinations(ctx, script_path="test_script.py")

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["has_hallucinations"] is True
        assert len(result_json["violations"]) == 1
        assert result_json["violations"][0]["type"] == "import"

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_no_validator(self):
        """Test hallucination check when validator is not available"""
        # Setup
        ctx = MockContext(knowledge_validator=None)

        # Test
        result = await check_ai_script_hallucinations(ctx, script_path="test_script.py")

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "not available" in result_json["error"]

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_repos_command(self):
        """Test querying knowledge graph for repositories"""
        # Setup
        mock_validator = AsyncMock()
        mock_validator.get_all_repositories.return_value = [
            {"name": "repo1", "url": "https://github.com/user/repo1"},
            {"name": "repo2", "url": "https://github.com/user/repo2"},
        ]

        ctx = MockContext(knowledge_validator=mock_validator)

        # Test
        result = await query_knowledge_graph(ctx, command="repos")

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["command"] == "repos"
        assert len(result_json["repositories"]) == 2
        mock_validator.get_all_repositories.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_classes_command(self):
        """Test querying knowledge graph for classes"""
        # Setup
        mock_validator = AsyncMock()
        mock_validator.get_all_classes.return_value = [
            {"name": "TestClass", "repo": "repo1", "module": "test_module"},
            {"name": "AnotherClass", "repo": "repo1", "module": "another_module"},
        ]

        ctx = MockContext(knowledge_validator=mock_validator)

        # Test
        result = await query_knowledge_graph(ctx, command="classes repo1")

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["command"] == "classes"
        assert result_json["repo"] == "repo1"
        assert len(result_json["classes"]) == 2
        mock_validator.get_all_classes.assert_called_once_with("repo1")

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_invalid_command(self):
        """Test querying knowledge graph with invalid command"""
        # Setup
        mock_validator = AsyncMock()
        ctx = MockContext(knowledge_validator=mock_validator)

        # Test
        result = await query_knowledge_graph(ctx, command="invalid_command")

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "Unknown command" in result_json["error"]

    @pytest.mark.asyncio
    async def test_parse_github_repository_success(self):
        """Test parsing GitHub repository successfully"""
        # Setup
        mock_extractor = AsyncMock()
        mock_extractor.parse_repository.return_value = {
            "repo_name": "test-repo",
            "files_parsed": 10,
            "classes_found": 5,
            "functions_found": 20,
            "methods_found": 15,
        }

        ctx = MockContext(repo_extractor=mock_extractor)

        # Test
        result = await parse_github_repository(
            ctx,
            repo_url="https://github.com/user/test-repo",
        )

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["repo_name"] == "test-repo"
        assert result_json["files_parsed"] == 10
        mock_extractor.parse_repository.assert_called_once_with(
            "https://github.com/user/test-repo",
        )

    @pytest.mark.asyncio
    async def test_parse_github_repository_no_extractor(self):
        """Test parsing repository when extractor is not available"""
        # Setup
        ctx = MockContext(repo_extractor=None)

        # Test
        result = await parse_github_repository(
            ctx,
            repo_url="https://github.com/user/test-repo",
        )

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "not available" in result_json["error"]


class TestErrorHandling:
    """Test error handling in MCP tools"""

    @pytest.mark.asyncio
    async def test_scrape_urls_database_error(self):
        """Test handling database errors during scraping"""
        # Setup
        mock_crawler = FakeCrawler()
        mock_db_client = AsyncMock()
        mock_db_client.add_documents_batch.side_effect = Exception(
            "Database connection failed",
        )

        ctx = MockContext(crawler=mock_crawler, database_client=mock_db_client)

        with patch("crawl4ai_mcp.crawl_batch") as mock_crawl_batch:
            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com",
                    "success": True,
                    "markdown": "Test content",
                    "cleaned_html": "<p>Test</p>",
                    "metadata": {},
                },
            ]

            # Test - should handle error gracefully
            from crawl4ai_mcp import scrape_urls

            result = await scrape_urls(ctx, url="https://example.com")

            # Verify
            result_json = json.loads(result)
            # Should still return success for crawl even if database fails
            assert "url" in result_json or "error" in result_json

    @pytest.mark.asyncio
    async def test_perform_rag_query_no_results(self):
        """Test RAG query with no results"""
        # Setup
        mock_db_client = AsyncMock()
        mock_db_client.search_documents.return_value = []

        ctx = MockContext(database_client=mock_db_client)

        # Import the function we need to test
        from crawl4ai_mcp import perform_rag_query

        # Patch search_documents to return empty list
        with patch("crawl4ai_mcp.search_documents", return_value=[]):
            # Test
            result = await perform_rag_query(
                ctx,
                query="non-existent content",
                match_count=5,
            )

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["count"] == 0
        assert len(result_json["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_code_examples_feature_disabled(self):
        """Test searching code examples when feature is disabled"""
        # Setup
        ctx = MockContext()

        with patch.dict(os.environ, {"USE_AGENTIC_RAG": "false"}):
            from crawl4ai_mcp import search_code_examples

            # Test
            result = await search_code_examples(ctx, query="test code", match_count=5)

            # Verify
            result_json = json.loads(result)
            assert result_json["success"] is False
            assert "disabled" in result_json["error"]


class TestSmartCrawlUrl:
    """Test smart_crawl_url MCP tool"""

    @pytest.mark.asyncio
    async def test_smart_crawl_sitemap(self):
        """Test crawling a sitemap URL"""
        # Setup
        mock_crawler = AsyncMock()
        mock_db_client = AsyncMock()

        # Mock sitemap response
        sitemap_result = MagicMock()
        sitemap_result.success = True
        sitemap_result.text = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>"""

        mock_crawler.arun.return_value = sitemap_result

        ctx = MockContext(crawler=mock_crawler, database_client=mock_db_client)

        with patch("crawl4ai_mcp.crawl_batch") as mock_crawl_batch:
            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com/page1",
                    "success": True,
                    "markdown": "Page 1",
                    "metadata": {},
                },
                {
                    "url": "https://example.com/page2",
                    "success": True,
                    "markdown": "Page 2",
                    "metadata": {},
                },
            ]

            from crawl4ai_mcp import smart_crawl_url

            result = await smart_crawl_url(
                ctx,
                url="https://example.com/sitemap.xml",
                max_depth=1,
            )

            # Verify
            result_json = json.loads(result)
            assert result_json["success"] is True
            assert result_json["crawl_type"] == "sitemap"
            assert result_json["total_pages"] == 2

    @pytest.mark.asyncio
    async def test_smart_crawl_llms_txt(self):
        """Test crawling llms.txt file"""
        # Setup
        mock_crawler = AsyncMock()
        mock_db_client = AsyncMock()

        # Mock llms.txt response
        llms_result = MagicMock()
        llms_result.success = True
        llms_result.text = """# LLMs.txt
        
        ## About
        This is a test llms.txt file
        
        ## Links
        - https://example.com/docs
        - https://example.com/api
        """

        mock_crawler.arun.return_value = llms_result

        ctx = MockContext(crawler=mock_crawler, database_client=mock_db_client)

        from crawl4ai_mcp import smart_crawl_url

        result = await smart_crawl_url(
            ctx,
            url="https://example.com/llms.txt",
            return_raw_markdown=True,
        )

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["crawl_type"] == "llms_txt"
        assert "raw_markdown" in result_json
        assert "LLMs.txt" in result_json["raw_markdown"]

    @pytest.mark.asyncio
    @patch("crawl4ai_mcp.get_available_sources")
    async def test_get_available_sources_error(self):
        """Test get_available_sources with database error"""
        # Setup
        mock_db_client = AsyncMock()
        mock_db_client.get_all_sources.side_effect = Exception("Database error")

        ctx = MockContext(database_client=mock_db_client)

        from crawl4ai_mcp import get_available_sources

        result = await get_available_sources(ctx)

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "error" in result_json


class TestSearchIntegration:
    """Test search MCP tool with various scenarios"""

    @pytest.mark.asyncio
    @patch("crawl4ai_mcp.searxng_search")
    @patch("crawl4ai_mcp.crawl_batch")
    async def test_search_with_searxng_error(self, mock_crawl, mock_searxng):
        """Test search when SearXNG fails"""
        # Setup
        mock_searxng.side_effect = Exception("SearXNG connection failed")
        mock_db_client = AsyncMock()

        ctx = MockContext(database_client=mock_db_client)

        from crawl4ai_mcp import search

        result = await search(ctx, query="test query", num_results=3)

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "SearXNG connection failed" in result_json["error"]
        mock_crawl.assert_not_called()

    @pytest.mark.asyncio
    @patch("crawl4ai_mcp.searxng_search")
    @patch("crawl4ai_mcp.crawl_batch")
    async def test_search_return_raw_markdown(self, mock_crawl, mock_searxng):
        """Test search with raw markdown return"""
        # Setup
        mock_searxng.return_value = {
            "results": [
                {
                    "url": "https://example.com/1",
                    "title": "Test 1",
                    "content": "Preview 1",
                },
            ],
        }

        mock_crawl.return_value = [
            {
                "url": "https://example.com/1",
                "success": True,
                "markdown": "# Test Page\n\nRaw markdown content",
                "metadata": {"title": "Test 1"},
            },
        ]

        mock_db_client = AsyncMock()
        ctx = MockContext(database_client=mock_db_client)

        from crawl4ai_mcp import search

        result = await search(
            ctx,
            query="test",
            return_raw_markdown=True,
            num_results=1,
        )

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert len(result_json["results"]) == 1
        assert "raw_markdown" in result_json["results"][0]
        assert "Raw markdown content" in result_json["results"][0]["raw_markdown"]


class TestPerformRagQuery:
    """Test perform_rag_query with various scenarios"""

    @pytest.mark.asyncio
    async def test_rag_query_with_reranking(self):
        """Test RAG query with reranking enabled"""
        # Setup
        mock_db_client = AsyncMock()
        mock_db_client.search_documents.return_value = [
            {"content": "Test doc 1", "url": "https://example.com/1", "score": 0.8},
            {"content": "Test doc 2", "url": "https://example.com/2", "score": 0.7},
        ]

        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            {"content": "Test doc 2", "url": "https://example.com/2", "score": 0.9},
            {"content": "Test doc 1", "url": "https://example.com/1", "score": 0.6},
        ]

        ctx = MockContext(database_client=mock_db_client, reranking_model=mock_reranker)

        with patch.dict(os.environ, {"USE_RERANKING": "true"}):
            from crawl4ai_mcp import perform_rag_query

            result = await perform_rag_query(ctx, query="test query", match_count=2)

            # Verify
            result_json = json.loads(result)
            assert result_json["success"] is True
            assert result_json["match_count"] == 2
            assert result_json["reranking_applied"] is True
            # First result should be doc 2 after reranking
            assert result_json["results"][0]["url"] == "https://example.com/2"

    @pytest.mark.asyncio
    async def test_rag_query_database_error(self):
        """Test RAG query with database error"""
        # Setup
        mock_db_client = AsyncMock()
        mock_db_client.search_documents.side_effect = Exception("Search failed")

        ctx = MockContext(database_client=mock_db_client)

        from crawl4ai_mcp import perform_rag_query

        result = await perform_rag_query(ctx, query="test", match_count=5)

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is False
        assert "Search failed" in result_json["error"]


class TestCodeExamples:
    """Test code example search functionality"""

    @pytest.mark.asyncio
    async def test_search_code_examples_success(self):
        """Test successful code example search"""
        # Setup
        mock_db_client = AsyncMock()
        mock_db_client.search_code_examples.return_value = [
            {
                "code": "def hello():\n    print('Hello')",
                "language": "python",
                "url": "https://example.com/code",
                "summary": "Hello function",
                "score": 0.9,
            },
        ]

        ctx = MockContext(database_client=mock_db_client)

        with patch.dict(os.environ, {"USE_AGENTIC_RAG": "true"}):
            from crawl4ai_mcp import search_code_examples

            result = await search_code_examples(
                ctx,
                query="hello function",
                match_count=5,
            )

            # Verify
            result_json = json.loads(result)
            assert result_json["success"] is True
            assert result_json["match_count"] == 1
            assert result_json["results"][0]["language"] == "python"

    @pytest.mark.asyncio
    async def test_search_code_examples_with_source_filter(self):
        """Test code example search with source filter"""
        # Setup
        mock_db_client = AsyncMock()
        mock_db_client.search_code_examples.return_value = []

        ctx = MockContext(database_client=mock_db_client)

        with patch.dict(os.environ, {"USE_AGENTIC_RAG": "true"}):
            from crawl4ai_mcp import search_code_examples

            result = await search_code_examples(
                ctx,
                query="test",
                source_id="github.com",
                match_count=5,
            )

            # Verify
            result_json = json.loads(result)
            assert result_json["success"] is True
            assert result_json["source_filter"] == "github.com"
            mock_db_client.search_code_examples.assert_called_once_with(
                query_text="test",
                source_id="github.com",
                match_count=5,
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
