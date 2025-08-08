"""
Comprehensive unit tests for MCP tools in crawl4ai_mcp.py.
Production-ready tests with proper mocking and assertions.
"""

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

# Proper imports without sys.path manipulation
project_root = Path(__file__).parent.parent
os.chdir(project_root)

# Import necessary components
from fastmcp import Context


class TestMCPToolsComprehensive:
    """Comprehensive test class for MCP tool functions."""

    @pytest.fixture
    def mock_context(self):
        """Create properly structured mock context."""
        ctx = Mock(spec=Context)
        ctx.request_context = Mock()
        ctx.request_context.lifespan_context = Mock()
        ctx.request_context.lifespan_context.crawler = AsyncMock()
        ctx.request_context.lifespan_context.database_client = AsyncMock()
        return ctx

    # ===== SEARCH TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_search_no_searxng_url(self, mock_context):
        """Test search when SEARXNG_URL is not configured."""
        from src.crawl4ai_mcp import search

        with patch.dict(os.environ, {}, clear=True):
            result = await search(mock_context, "test query")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "SEARXNG_URL" in result_data["error"]

    @pytest.mark.asyncio
    async def test_search_network_error(self, mock_context):
        """Test search with network errors."""
        from src.crawl4ai_mcp import search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
            with patch("aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session.get.side_effect = Exception("Network error")
                mock_session_class.return_value = mock_session

                result = await search(mock_context, "test query")
                result_data = json.loads(result)

                assert result_data["success"] is False
                assert "error" in result_data

    @pytest.mark.asyncio
    async def test_search_successful_scraping(self, mock_context):
        """Test successful search with basic URL extraction."""
        from src.crawl4ai_mcp import search

        with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
            # Mock successful HTTP response with URLs
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value="""
            <div class="results">
                <article class="result">
                    <h3><a href="https://example.com/page1">Test Page 1</a></h3>
                    <p>Test content 1</p>
                </article>
            </div>
            """,
            )

            mock_session = AsyncMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response

            with patch("aiohttp.ClientSession", return_value=mock_session):
                # Mock successful crawling
                mock_crawl_result = Mock()
                mock_crawl_result.success = True
                mock_crawl_result.markdown = "# Test Content"
                mock_crawl_result.cleaned_html = "<h1>Test Content</h1>"
                mock_crawl_result.media = {"images": [], "videos": []}
                mock_crawl_result.links = {"internal": [], "external": []}
                mock_crawl_result.screenshot = None
                mock_crawl_result.pdf = None

                mock_context.request_context.lifespan_context.crawler.arun.return_value = mock_crawl_result

                # Mock database operations
                with patch(
                    "src.utils.add_documents_to_database",
                    new_callable=AsyncMock,
                ):
                    result = await search(mock_context, "test query", num_results=1)
                    result_data = json.loads(result)

                    assert result_data["success"] is True
                    assert "results" in result_data or "markdown" in result_data

    # ===== SCRAPE_URLS TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_scrape_urls_invalid_input(self, mock_context):
        """Test scraping with invalid input."""
        from src.crawl4ai_mcp import scrape_urls

        # Test with empty URL
        result = await scrape_urls(mock_context, "")
        result_data = json.loads(result)
        assert result_data["success"] is False

        # Test with None URL
        result = await scrape_urls(mock_context, None)
        result_data = json.loads(result)
        assert result_data["success"] is False

    @pytest.mark.asyncio
    async def test_scrape_urls_success(self, mock_context):
        """Test successful URL scraping."""
        from src.crawl4ai_mcp import scrape_urls

        # Mock successful crawl result
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "# Page Title\nContent here"
        mock_result.cleaned_html = "<h1>Page Title</h1><p>Content here</p>"
        mock_result.media = {"images": ["image1.jpg"], "videos": []}
        mock_result.links = {
            "internal": ["/page2"],
            "external": ["https://external.com"],
        }
        mock_result.screenshot = None
        mock_result.pdf = None

        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        with patch(
            "src.crawl4ai_mcp.add_documents_to_database",
            new_callable=AsyncMock,
        ):
            result = await scrape_urls(
                mock_context,
                "https://example.com",
                return_raw_markdown=True,
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            # Check for expected structure
            assert "markdown" in result_data or "summary" in result_data

    @pytest.mark.asyncio
    async def test_scrape_urls_failure(self, mock_context):
        """Test scraping failure handling."""
        from src.crawl4ai_mcp import scrape_urls

        # Mock failed crawl result
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Failed to load page"

        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        result = await scrape_urls(mock_context, "https://invalid-url.com")
        result_data = json.loads(result)

        # Single URL failure should return failure
        assert result_data["success"] is False
        assert "error" in result_data

    # ===== RAG QUERY TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_perform_rag_query_success(self, mock_context):
        """Test successful RAG query."""
        from src.crawl4ai_mcp import perform_rag_query

        mock_search_results = [
            {
                "id": "1",
                "score": 0.9,
                "content": "Relevant content here",
                "url": "https://example.com/page1",
                "metadata": {"title": "Page 1"},
                "chunk_number": 1,
                "source_id": "example.com",
            },
        ]

        with patch(
            "src.utils.search_documents",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = mock_search_results

            result = await perform_rag_query(mock_context, "test query", match_count=1)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["content"] == "Relevant content here"

    @pytest.mark.asyncio
    async def test_perform_rag_query_no_results(self, mock_context):
        """Test RAG query with no results."""
        from src.crawl4ai_mcp import perform_rag_query

        with patch(
            "src.utils.search_documents",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = []

            result = await perform_rag_query(mock_context, "nonexistent query")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert len(result_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_perform_rag_query_error(self, mock_context):
        """Test RAG query error handling."""
        from src.crawl4ai_mcp import perform_rag_query

        with patch(
            "src.utils.search_documents",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.side_effect = Exception("Database error")

            result = await perform_rag_query(mock_context, "test query")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "error" in result_data

    # ===== SMART CRAWL TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_smart_crawl_url_error_handling(self, mock_context):
        """Test smart crawl error handling."""
        from src.crawl4ai_mcp import smart_crawl_url

        # Mock crawl failure
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Failed to load page"

        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        result = await smart_crawl_url(mock_context, "https://invalid-url.com")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_smart_crawl_url_txt_success(self, mock_context):
        """Test smart crawl for text files."""
        from src.crawl4ai_mcp import smart_crawl_url

        # Mock txt file crawl result
        mock_result = Mock()
        mock_result.success = True
        mock_result.markdown = "Line 1\nLine 2\nLine 3\n" * 20  # Long content
        mock_result.cleaned_html = ""
        mock_result.media = {"images": [], "videos": []}
        mock_result.links = {"internal": [], "external": []}
        mock_result.screenshot = None
        mock_result.pdf = None

        mock_context.request_context.lifespan_context.crawler.arun.return_value = (
            mock_result
        )

        with patch(
            "src.crawl4ai_mcp.add_documents_to_database",
            new_callable=AsyncMock,
        ):
            result = await smart_crawl_url(
                mock_context,
                "https://example.com/file.txt",
                chunk_size=100,
                return_raw_markdown=False,
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["crawl_type"] == "text_file"

    # ===== CODE EXAMPLES TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_search_code_examples_disabled(self, mock_context):
        """Test search code examples when feature is disabled."""
        from src.crawl4ai_mcp import search_code_examples

        with patch.dict(os.environ, {"USE_AGENTIC_RAG": "false"}):
            result = await search_code_examples(mock_context, "python function")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "disabled" in result_data["error"]

    @pytest.mark.asyncio
    async def test_search_code_examples_enabled(self, mock_context):
        """Test search code examples when feature is enabled."""
        from src.crawl4ai_mcp import search_code_examples

        with patch.dict(os.environ, {"USE_AGENTIC_RAG": "true"}):
            mock_results = [
                {
                    "id": "1",
                    "score": 0.85,
                    "language": "python",
                    "code": "def hello(): return 'world'",
                    "description": "Hello function",
                    "url": "https://example.com",
                    "metadata": {"framework": "basic"},
                },
            ]

            with patch(
                "src.utils.search_code_examples",
                return_value=mock_results,
            ) as mock_search:
                result = await search_code_examples(
                    mock_context,
                    "python function",
                    match_count=1,
                )
                result_data = json.loads(result)

                assert result_data["success"] is True
                assert len(result_data["results"]) == 1
                assert result_data["results"][0]["language"] == "python"

    # ===== HALLUCINATION CHECK TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_disabled(self, mock_context):
        """Test AI script hallucination checking when feature is disabled."""
        from src.crawl4ai_mcp import check_ai_script_hallucinations

        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "false"}):
            result = await check_ai_script_hallucinations(
                mock_context,
                "/path/to/script.py",
            )
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "disabled" in result_data["error"]

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_enabled(self, mock_context):
        """Test AI script hallucination checking when enabled."""
        from src.crawl4ai_mcp import check_ai_script_hallucinations

        with patch.dict(
            os.environ,
            {"USE_KNOWLEDGE_GRAPH": "true", "NEO4J_URI": "bolt://localhost:7687"},
        ):
            test_script = """
            import requests
            def fetch_data():
                return requests.get("https://api.example.com").json()
            """

            # Mock knowledge validator in context
            mock_knowledge_validator = AsyncMock()
            mock_knowledge_validator.validate_script.return_value = Mock(
                overall_confidence=0.95,
                # Mock other required attributes as needed
            )
            mock_context.request_context.lifespan_context.knowledge_validator = (
                mock_knowledge_validator
            )

            # Mock the analyzer and reporter classes and validation function
            with patch(
                "src.crawl4ai_mcp.validate_script_path",
                return_value={"valid": True},
            ) as mock_validate:
                with patch("src.crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
                    with patch(
                        "src.crawl4ai_mcp.HallucinationReporter",
                    ) as mock_reporter_class:
                        with patch("builtins.open", mock_open(read_data=test_script)):
                            # Mock analyzer
                            mock_analyzer = Mock()
                            mock_analyzer.analyze_script.return_value = Mock(errors=[])
                            mock_analyzer_class.return_value = mock_analyzer

                            # Mock reporter
                            mock_reporter = Mock()
                            mock_reporter.generate_comprehensive_report.return_value = {
                                "validation_summary": {
                                    "total_validations": 1,
                                    "valid_count": 1,
                                    "invalid_count": 0,
                                    "uncertain_count": 0,
                                    "not_found_count": 0,
                                    "hallucination_rate": 0.0,
                                },
                                "hallucinations_detected": [],
                                "recommendations": ["Code appears valid"],
                                "analysis_metadata": {
                                    "total_imports": 1,
                                    "total_classes": 0,
                                    "total_methods": 1,
                                    "total_attributes": 0,
                                    "total_functions": 1,
                                },
                            }
                            mock_reporter_class.return_value = mock_reporter

                            result = await check_ai_script_hallucinations(
                                mock_context,
                                "/path/to/script.py",
                            )
                            result_data = json.loads(result)

                            assert result_data["success"] is True
                            assert result_data["overall_confidence"] == 0.95

    # ===== GET AVAILABLE SOURCES TOOL TESTS =====

    @pytest.mark.asyncio
    async def test_get_available_sources_success(self, mock_context):
        """Test getting available sources successfully."""
        from src.crawl4ai_mcp import get_available_sources

        mock_adapter = AsyncMock()
        mock_adapter.get_sources.return_value = [
            {
                "source_id": "example.com",
                "summary": "Example website",
                "total_word_count": 5000,
            },
            {
                "source_id": "docs.python.org",
                "summary": "Python docs",
                "total_word_count": 15000,
            },
        ]
        mock_context.request_context.lifespan_context.database_client = mock_adapter

        result = await get_available_sources(mock_context)
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["sources"]) == 2
        assert result_data["sources"][0]["source_id"] == "example.com"

    @pytest.mark.asyncio
    async def test_get_available_sources_error(self, mock_context):
        """Test getting available sources with database error."""
        from src.crawl4ai_mcp import get_available_sources

        mock_adapter = AsyncMock()
        mock_adapter.get_sources.side_effect = Exception("Database error")
        mock_context.request_context.lifespan_context.database_client = mock_adapter

        result = await get_available_sources(mock_context)
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "error" in result_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
