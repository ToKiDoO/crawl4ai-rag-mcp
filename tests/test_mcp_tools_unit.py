"""
Comprehensive unit tests for MCP tools in crawl4ai_mcp.py

This module tests all @mcp.tool decorated functions with proper mocking
of external dependencies including Crawl4AI, databases, and Neo4j.

Target coverage: >90% for all MCP tool functions
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest
import requests

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
# Add tests to path for test helpers
tests_path = Path(__file__).parent
sys.path.insert(0, str(tests_path))


# Mock the FastMCP Context before importing the main module
class MockContext:
    """Mock FastMCP Context for testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()
        self.request_context.lifespan_context.database_client = AsyncMock()

        # Create a properly mocked AsyncWebCrawler that supports async context manager
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)

        # Mock both single and batch crawling methods
        mock_crawler.arun = AsyncMock()
        mock_crawler.arun_many = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler

        # Create a properly mocked Neo4j repository extractor with session context manager
        mock_repo_extractor = Mock()
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock session methods for Neo4j operations
        mock_session.run = AsyncMock()
        mock_session.single = AsyncMock()

        # Mock the driver and session creation
        mock_driver = Mock()
        mock_driver.session = Mock(return_value=mock_session)
        mock_repo_extractor.driver = mock_driver
        mock_repo_extractor.analyze_repository = AsyncMock()

        self.request_context.lifespan_context.repo_extractor = mock_repo_extractor

        # Add knowledge validator for hallucination testing
        mock_knowledge_validator = AsyncMock()
        mock_knowledge_validator.validate_script = AsyncMock()
        self.request_context.lifespan_context.knowledge_validator = (
            mock_knowledge_validator
        )


@pytest.fixture
def mock_context():
    """Provide a mock FastMCP context for testing"""
    return MockContext()


# Import mock helper
from mock_openai_helper import patch_openai_embeddings


# Mock all external dependencies before importing
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """Mock all external dependencies used by MCP tools"""
    # Set up environment variables for all tests
    env_vars = {
        # Search and Web Scraping
        "SEARXNG_URL": "http://localhost:8888",
        "SEARXNG_USER_AGENT": "MCP-Crawl4AI-RAG-Server/1.0",
        "SEARXNG_TIMEOUT": "30",
        "SEARXNG_DEFAULT_ENGINES": "",
        # Knowledge Graph / Neo4j
        "USE_KNOWLEDGE_GRAPH": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
        # RAG Features
        "USE_AGENTIC_RAG": "true",
        "USE_RERANKING": "true",
        "USE_HYBRID_SEARCH": "true",
        # Vector Database
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "test-key",
        # API Keys
        "OPENAI_API_KEY": "test-openai-key",
        # General Configuration
        "MCP_DEBUG": "false",
        "USE_TEST_ENV": "true",
        "HOST": "0.0.0.0",
        "PORT": "8051",
        "TRANSPORT": "http",
    }

    # Get OpenAI patches
    openai_patches = patch_openai_embeddings()

    # Create a context manager list
    context_managers = (
        [patch.dict(os.environ, env_vars)]
        + openai_patches
        + [
            patch.dict(
                "sys.modules",
                {
                    "crawl4ai": Mock(),
                    "fastmcp": Mock(),
                    "sentence_transformers": Mock(),
                    "database.factory": Mock(),
                    "utils": Mock(),
                    "knowledge_graph_validator": Mock(),
                    "parse_repo_into_neo4j": Mock(),
                    "ai_script_analyzer": Mock(),
                    "hallucination_reporter": Mock(),
                },
            ),
        ]
    )

    # Apply all context managers using ExitStack
    from contextlib import ExitStack

    with ExitStack() as stack:
        for cm in context_managers:
            stack.enter_context(cm)

        # Mock specific classes and functions
        mock_crawler = stack.enter_context(patch("crawl4ai.AsyncWebCrawler"))
        mock_browser_config = stack.enter_context(patch("crawl4ai.BrowserConfig"))
        mock_crawler_config = stack.enter_context(patch("crawl4ai.CrawlerRunConfig"))
        mock_requests_get = stack.enter_context(patch("requests.get"))
        mock_db_factory = stack.enter_context(
            patch("database.factory.create_and_initialize_database"),
        )
        mock_add_docs = stack.enter_context(
            patch("utils.add_documents_to_database"),
        )
        mock_search_docs = stack.enter_context(
            patch("utils.search_documents"),
        )
        mock_extract_code = stack.enter_context(
            patch("utils.extract_code_blocks"),
        )
        mock_code_summary = stack.enter_context(
            patch("utils.generate_code_example_summary"),
        )
        mock_kg_validator = stack.enter_context(
            patch("knowledge_graph_validator.KnowledgeGraphValidator"),
        )
        mock_neo4j_extractor = stack.enter_context(
            patch("parse_repo_into_neo4j.DirectNeo4jExtractor"),
        )
        mock_ai_analyzer = stack.enter_context(
            patch("ai_script_analyzer.AIScriptAnalyzer"),
        )
        mock_hallucination_reporter = stack.enter_context(
            patch("hallucination_reporter.HallucinationReporter"),
        )
        mock_path_exists = stack.enter_context(
            patch("os.path.exists", return_value=True),
        )
        mock_file_open = stack.enter_context(
            patch("builtins.open", mock_open(read_data="script content")),
        )

        yield {
            "mock_crawler": mock_crawler,
            "mock_requests_get": mock_requests_get,
            "mock_db_factory": mock_db_factory,
            "mock_add_docs": mock_add_docs,
            "mock_search_docs": mock_search_docs,
            "mock_extract_code": mock_extract_code,
            "mock_code_summary": mock_code_summary,
            "mock_kg_validator": mock_kg_validator,
            "mock_neo4j_extractor": mock_neo4j_extractor,
            "mock_ai_analyzer": mock_ai_analyzer,
            "mock_hallucination_reporter": mock_hallucination_reporter,
            "mock_path_exists": mock_path_exists,
            "mock_file_open": mock_file_open,
        }


# Import the module under test after mocking
# Instead of importing wrapped functions, import the module and access the underlying functions
import crawl4ai_mcp


# Access the underlying functions from the FastMCP tool wrappers
def get_tool_function(tool_name: str):
    """Get the underlying function from FastMCP tool wrapper"""
    tool_attr = getattr(crawl4ai_mcp, tool_name, None)
    if hasattr(tool_attr, "fn"):
        return tool_attr.fn
    if callable(tool_attr):
        return tool_attr
    raise AttributeError(f"Cannot find callable function for {tool_name}")


# Get the actual functions
search = get_tool_function("search")
scrape_urls = get_tool_function("scrape_urls")
smart_crawl_url = get_tool_function("smart_crawl_url")
get_available_sources = get_tool_function("get_available_sources")
perform_rag_query = get_tool_function("perform_rag_query")
search_code_examples = get_tool_function("search_code_examples")
check_ai_script_hallucinations = get_tool_function("check_ai_script_hallucinations")
query_knowledge_graph = get_tool_function("query_knowledge_graph")
parse_github_repository = get_tool_function("parse_github_repository")


class TestSearchTool:
    """Test the search() MCP tool"""

    @pytest.mark.asyncio
    async def test_search_success_with_rag(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful search with RAG processing"""
        # Setup mocks
        mock_requests = mock_external_dependencies["mock_requests_get"]

        # Mock SearXNG response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"url": "https://example.com/page1"},
                {"url": "https://example.com/page2"},
            ],
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls function - it's an async function so needs AsyncMock
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {"success": True, "results": {"scraped": 2}},
            )

            # Mock perform_rag_query function - also async
            with patch(
                "crawl4ai_mcp.perform_rag_query",
                new_callable=AsyncMock,
            ) as mock_rag:
                mock_rag.return_value = json.dumps(
                    {
                        "success": True,
                        "results": [
                            {
                                "content": "Test content",
                                "similarity": 0.9,
                                "metadata": {},
                            },
                        ],
                    },
                )

                # Execute test
                result = await search(
                    mock_context,
                    query="test query",
                    return_raw_markdown=False,
                    num_results=2,
                )

                # Verify result
                result_data = json.loads(result)
                assert result_data["success"] is True
                assert result_data["query"] == "test query"
                assert result_data["mode"] == "rag_query"
                assert len(result_data["searxng_results"]) == 2

                # Verify function calls
                mock_requests.assert_called_once()
                mock_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_success_with_raw_markdown(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful search with raw markdown return"""
        # Setup mocks
        mock_requests = mock_external_dependencies["mock_requests_get"]

        # Mock SearXNG response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com/page1"}],
        }
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock database client
        mock_context.request_context.lifespan_context.database_client.get_documents_by_url.return_value = [
            {"content": "Raw markdown content"},
        ]

        # Mock scrape_urls function
        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps({"success": True})

            # Execute test
            result = await search(
                mock_context,
                query="test query",
                return_raw_markdown=True,
            )

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["mode"] == "raw_markdown"
            assert "https://example.com/page1" in result_data["results"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=False)  # Remove SEARXNG_URL for this test
    async def test_search_missing_searxng_url(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search failure when SEARXNG_URL is not configured"""
        # Temporarily remove SEARXNG_URL from environment
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):  # Clear all environment variables for this test
            # Execute test
            result = await search(mock_context, query="test query")

            # Verify error result
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert (
                "SEARXNG_URL environment variable is not configured"
                in result_data["error"]
            )

    @pytest.mark.asyncio
    async def test_search_http_timeout(self, mock_context, mock_external_dependencies):
        """Test search failure due to HTTP timeout"""
        # Setup timeout mock
        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_requests.side_effect = requests.exceptions.Timeout("Request timed out")

        # Execute test
        result = await search(mock_context, query="test query")

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "SearXNG request timed out" in result_data["error"]

    @pytest.mark.asyncio
    async def test_search_connection_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test search failure due to connection error"""
        # Setup connection error mock
        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_requests.side_effect = requests.exceptions.ConnectionError(
            "Connection failed",
        )

        # Execute test
        result = await search(mock_context, query="test query")

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Cannot connect to SearXNG" in result_data["error"]

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_context, mock_external_dependencies):
        """Test search with no results from SearXNG"""
        # Mock empty response
        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Execute test
        result = await search(mock_context, query="test query")

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "No search results returned from SearXNG" in result_data["error"]


class TestScrapeUrlsTool:
    """Test the scrape_urls() MCP tool"""

    @pytest.mark.asyncio
    async def test_scrape_single_url_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful scraping of a single URL"""
        # Mock the crawl_batch function directly since it's called by _process_multiple_urls
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com",
                    "markdown": "# Test Content\nThis is test content",
                    "links": {"internal": [], "external": []},
                },
            ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test
            result = await scrape_urls(mock_context, url="https://example.com")

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_scrape_multiple_urls_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful scraping of multiple URLs"""
        urls = ["https://example.com/page1", "https://example.com/page2"]

        # Mock the crawl_batch function directly since it's called by _process_multiple_urls
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com/page1",
                    "markdown": "# Page 1",
                    "links": {},
                },
                {
                    "url": "https://example.com/page2",
                    "markdown": "# Page 2",
                    "links": {},
                },
            ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test
            result = await scrape_urls(mock_context, url=urls)

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["summary"]["successful_urls"] == 2

    @pytest.mark.asyncio
    async def test_scrape_invalid_url(self, mock_context, mock_external_dependencies):
        """Test scraping with invalid URL"""
        # Mock the crawl_batch function to return empty results for invalid URL
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            mock_crawl_batch.return_value = []  # No successful results for invalid URL

            # Execute test with invalid URL
            result = await scrape_urls(mock_context, url="not-a-url")

            # Verify error result
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "No content retrieved" in result_data["error"]

    @pytest.mark.asyncio
    async def test_scrape_crawler_failure(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test scraping when crawler fails"""
        # Mock the crawl_batch function to return empty results (simulating failure)
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            mock_crawl_batch.return_value = []  # No successful results

            # Execute test
            result = await scrape_urls(mock_context, url="https://example.com/404")

            # Verify result shows failure
            result_data = json.loads(result)
            assert result_data["success"] is False
            assert "No content retrieved" in result_data["error"]

    @pytest.mark.asyncio
    async def test_scrape_with_raw_markdown(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test scraping with raw markdown return (no database storage)"""
        # Mock the crawl_batch function directly
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com",
                    "markdown": "# Raw Content",
                    "links": {},
                },
            ]

            # Execute test with raw markdown flag
            result = await scrape_urls(
                mock_context,
                url="https://example.com",
                return_raw_markdown=True,
            )

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["mode"] == "raw_markdown"
            assert "# Raw Content" in result_data["results"]["https://example.com"]

            # Verify database functions were NOT called
            mock_external_dependencies["mock_add_docs"].assert_not_called()


class TestSmartCrawlUrlTool:
    """Test the smart_crawl_url() MCP tool"""

    @pytest.mark.asyncio
    async def test_smart_crawl_regular_url(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with regular URL (should use crawl_recursive_internal_links)"""
        # Mock crawl_recursive_internal_links function which is actually called for regular URLs
        with patch(
            "crawl4ai_mcp.crawl_recursive_internal_links",
            new_callable=AsyncMock,
        ) as mock_crawl_recursive:
            mock_crawl_recursive.return_value = [
                {
                    "url": "https://example.com",
                    "markdown": "# Test Content",
                    "links": {},
                },
            ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test
            result = await smart_crawl_url(mock_context, url="https://example.com")

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["crawl_type"] == "webpage"
            mock_crawl_recursive.assert_called_once()

    @pytest.mark.asyncio
    async def test_smart_crawl_sitemap_url(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with sitemap URL"""
        # Mock sitemap content
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>"""

        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_response = Mock()
        mock_response.text = sitemap_xml
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock parse_sitemap and crawl_batch functions
        with (
            patch("crawl4ai_mcp.parse_sitemap") as mock_parse_sitemap,
            patch(
                "crawl4ai_mcp.crawl_batch",
                new_callable=AsyncMock,
            ) as mock_crawl_batch,
        ):
            # Mock parse_sitemap to return the URLs from the sitemap
            mock_parse_sitemap.return_value = [
                "https://example.com/page1",
                "https://example.com/page2",
            ]

            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com/page1",
                    "markdown": "# Page 1",
                    "links": {},
                },
                {
                    "url": "https://example.com/page2",
                    "markdown": "# Page 2",
                    "links": {},
                },
            ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test
            result = await smart_crawl_url(
                mock_context,
                url="https://example.com/sitemap.xml",
            )

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["crawl_type"] == "sitemap"
            assert result_data["pages_crawled"] == 2

    @pytest.mark.asyncio
    async def test_smart_crawl_robots_txt(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with robots.txt URL"""
        # Mock crawl_markdown_file function which is actually called for .txt files
        with patch(
            "crawl4ai_mcp.crawl_markdown_file",
            new_callable=AsyncMock,
        ) as mock_crawl_markdown:
            mock_crawl_markdown.return_value = [
                {
                    "url": "https://example.com/robots.txt",
                    "markdown": "User-agent: *\nSitemap: https://example.com/sitemap.xml",
                    "links": {},
                },
            ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test
            result = await smart_crawl_url(
                mock_context,
                url="https://example.com/robots.txt",
            )

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["crawl_type"] == "text_file"
            mock_crawl_markdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_smart_crawl_invalid_sitemap(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl with invalid sitemap XML"""
        # Mock invalid XML
        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_response = Mock()
        mock_response.text = "Invalid XML content"
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Execute test
        result = await smart_crawl_url(
            mock_context,
            url="https://example.com/sitemap.xml",
        )

        # Verify error handling - should return "No URLs found in sitemap" for invalid XML
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "No URLs found in sitemap" in result_data["error"]

    @pytest.mark.asyncio
    async def test_smart_crawl_max_depth_limit(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test smart crawl respects max_depth parameter"""
        # Mock sitemap with many URLs
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
            <url><loc>https://example.com/page3</loc></url>
            <url><loc>https://example.com/page4</loc></url>
            <url><loc>https://example.com/page5</loc></url>
        </urlset>"""

        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_response = Mock()
        mock_response.text = sitemap_xml
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock parse_sitemap and crawl_batch functions
        with (
            patch("crawl4ai_mcp.parse_sitemap") as mock_parse_sitemap,
            patch(
                "crawl4ai_mcp.crawl_batch",
                new_callable=AsyncMock,
            ) as mock_crawl_batch,
        ):
            # Mock parse_sitemap to return the URLs from the sitemap
            mock_parse_sitemap.return_value = [
                "https://example.com/page1",
                "https://example.com/page2",
                "https://example.com/page3",
                "https://example.com/page4",
                "https://example.com/page5",
            ]

            mock_crawl_batch.return_value = [
                {
                    "url": "https://example.com/page1",
                    "markdown": "# Page 1",
                    "links": {},
                },
                {
                    "url": "https://example.com/page2",
                    "markdown": "# Page 2",
                    "links": {},
                },
                {
                    "url": "https://example.com/page3",
                    "markdown": "# Page 3",
                    "links": {},
                },
                {
                    "url": "https://example.com/page4",
                    "markdown": "# Page 4",
                    "links": {},
                },
                {
                    "url": "https://example.com/page5",
                    "markdown": "# Page 5",
                    "links": {},
                },
            ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test with max_depth=3 (note: max_depth doesn't apply to sitemaps, they crawl all URLs)
            result = await smart_crawl_url(
                mock_context,
                url="https://example.com/sitemap.xml",
                max_depth=3,
            )

            # Verify sitemap was processed (max_depth doesn't limit sitemap processing)
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert result_data["crawl_type"] == "sitemap"
            assert result_data["pages_crawled"] == 5


class TestGetAvailableSourcesTool:
    """Test the get_available_sources() MCP tool"""

    @pytest.mark.asyncio
    async def test_get_available_sources_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful retrieval of available sources"""
        # Mock database client - use get_sources() method which is actually called
        mock_context.request_context.lifespan_context.database_client.get_sources.return_value = [
            {
                "source_id": "example.com",
                "summary": "Example website",
                "total_word_count": 1000,
            },
            {
                "source_id": "test.org",
                "summary": "Test website",
                "total_word_count": 2000,
            },
            {
                "source_id": "docs.python.org",
                "summary": "Python documentation",
                "total_word_count": 5000,
            },
        ]

        # Execute test
        result = await get_available_sources(mock_context)

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["sources"]) == 3
        # Check that specific source exists in the list of source dictionaries
        source_ids = [source["source_id"] for source in result_data["sources"]]
        assert "example.com" in source_ids

    @pytest.mark.asyncio
    async def test_get_available_sources_empty(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test get available sources when database is empty"""
        # Mock empty database
        mock_context.request_context.lifespan_context.database_client.get_unique_sources.return_value = []

        # Execute test
        result = await get_available_sources(mock_context)

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["sources"]) == 0

    @pytest.mark.asyncio
    async def test_get_available_sources_database_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test get available sources when database throws error"""
        # Mock database error - use get_sources() method which is actually called
        mock_context.request_context.lifespan_context.database_client.get_sources.side_effect = Exception(
            "Database connection failed",
        )

        # Execute test
        result = await get_available_sources(mock_context)

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Database connection failed" in result_data["error"]


class TestPerformRagQueryTool:
    """Test the perform_rag_query() MCP tool"""

    @pytest.mark.asyncio
    async def test_rag_query_success(self, mock_context, mock_external_dependencies):
        """Test successful RAG query"""
        # Mock search_documents function directly
        with patch(
            "crawl4ai_mcp.search_documents",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = [
                {
                    "content": "Test content about Python",
                    "similarity": 0.95,
                    "metadata": {"source": "example.com", "title": "Python Guide"},
                },
            ]

            # Execute test
            result = await perform_rag_query(
                mock_context,
                query="Python programming",
                source="example.com",
                match_count=5,
            )

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["similarity"] == 0.95

    @pytest.mark.asyncio
    async def test_rag_query_no_results(self, mock_context, mock_external_dependencies):
        """Test RAG query with no matching results"""
        # Mock empty search results
        mock_external_dependencies["mock_search_docs"].return_value = []

        # Execute test
        result = await perform_rag_query(mock_context, query="nonexistent topic")

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_rag_query_with_source_filter(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with source filtering"""
        # Mock search results
        mock_external_dependencies["mock_search_docs"].return_value = [
            {"content": "Filtered content", "similarity": 0.8, "metadata": {}},
        ]

        # Execute test
        result = await perform_rag_query(
            mock_context,
            query="test query",
            source="specific.com",
        )

        # Verify result and that search_documents was called with source filter
        result_data = json.loads(result)
        assert result_data["success"] is True
        mock_external_dependencies["mock_search_docs"].assert_called_once()
        call_args = mock_external_dependencies["mock_search_docs"].call_args
        assert call_args[1]["source"] == "specific.com"

    @pytest.mark.asyncio
    async def test_rag_query_database_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query when database search fails"""
        # Mock database error
        mock_external_dependencies["mock_search_docs"].side_effect = Exception(
            "Search failed",
        )

        # Execute test
        result = await perform_rag_query(mock_context, query="test query")

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Search failed" in result_data["error"]


class TestSearchCodeExamplesTool:
    """Test the search_code_examples() MCP tool"""

    @pytest.mark.asyncio
    async def test_search_code_examples_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful code examples search"""
        # Mock code search results
        mock_external_dependencies["mock_extract_code"].return_value = [
            {
                "code": "def example(): pass",
                "language": "python",
                "similarity": 0.9,
                "metadata": {"source": "example.com"},
            },
        ]

        # Execute test
        result = await search_code_examples(
            mock_context,
            query="Python function example",
        )

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["results"]) == 1
        assert "def example()" in result_data["results"][0]["code"]

    @pytest.mark.asyncio
    async def test_search_code_examples_with_source_filter(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with source filtering"""
        # Mock code search results
        mock_external_dependencies["mock_extract_code"].return_value = []

        # Execute test
        result = await search_code_examples(
            mock_context,
            query="test code",
            source_id="github.com",
        )

        # Verify result and function call
        result_data = json.loads(result)
        assert result_data["success"] is True
        mock_external_dependencies["mock_extract_code"].assert_called_once()

    @pytest.mark.asyncio
    async def test_search_code_examples_no_results(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with no results"""
        # Mock empty results
        mock_external_dependencies["mock_extract_code"].return_value = []

        # Execute test
        result = await search_code_examples(mock_context, query="nonexistent code")

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_code_examples_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with database error"""
        # Mock database error
        mock_external_dependencies["mock_extract_code"].side_effect = Exception(
            "Code search failed",
        )

        # Execute test
        result = await search_code_examples(mock_context, query="test")

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Code search failed" in result_data["error"]


class TestCheckAiScriptHallucinationsTool:
    """Test the check_ai_script_hallucinations() MCP tool"""

    @pytest.mark.asyncio
    async def test_check_hallucinations_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful hallucination check"""
        # Mock analyzer results - the analyzer returns a structured result object
        mock_analysis_result = Mock()
        mock_analysis_result.errors = []  # No errors for successful analysis
        mock_analysis_result.hallucinations = [
            {
                "type": "function",
                "name": "nonexistent_function",
                "line": 42,
                "description": "Function does not exist",
            },
        ]

        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_script.return_value = mock_analysis_result
        mock_external_dependencies[
            "mock_ai_analyzer"
        ].return_value = mock_analyzer_instance

        # Mock knowledge validator result
        mock_validation_result = Mock()
        mock_validation_result.overall_confidence = 0.9
        mock_validation_result.hallucinations = [
            {
                "type": "function",
                "name": "nonexistent_function",
                "line": 42,
                "description": "Function does not exist",
            },
        ]

        # Mock the async validate_script method in the context
        mock_context.request_context.lifespan_context.knowledge_validator.validate_script.return_value = mock_validation_result

        # Mock the reporter
        mock_report = {
            "validation_summary": {
                "total_validations": 1,
                "passed_validations": 0,
                "failed_validations": 1,
            },
            "hallucinations_by_category": {"function": 1},
            "confidence_metrics": {"overall_confidence": 0.9},
        }
        mock_reporter_instance = Mock()
        mock_reporter_instance.generate_comprehensive_report.return_value = mock_report
        mock_external_dependencies[
            "mock_hallucination_reporter"
        ].return_value = mock_reporter_instance

        # Execute test
        result = await check_ai_script_hallucinations(
            mock_context,
            script_path="/path/to/script.py",
        )

        # Verify result
        result_data = json.loads(result)
        print(f"Debug - AI hallucination check result: {result}")  # Debug output
        assert result_data["success"] is True
        assert result_data["overall_confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_check_hallucinations_no_issues(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test hallucination check with no issues found"""
        # Mock analyzer with no hallucinations
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_script.return_value = {
            "hallucinations": [],
            "confidence": 0.95,
        }
        mock_external_dependencies[
            "mock_ai_analyzer"
        ].return_value = mock_analyzer_instance

        # Execute test
        result = await check_ai_script_hallucinations(
            mock_context,
            script_path="/path/to/clean_script.py",
        )

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["hallucinations"]) == 0

    @pytest.mark.asyncio
    async def test_check_hallucinations_file_not_found(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test hallucination check with non-existent file"""
        # Mock file not found error
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_script.side_effect = FileNotFoundError(
            "Script file not found",
        )
        mock_external_dependencies[
            "mock_ai_analyzer"
        ].return_value = mock_analyzer_instance

        # Execute test
        result = await check_ai_script_hallucinations(
            mock_context,
            script_path="/nonexistent/script.py",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Script file not found" in result_data["error"]

    @pytest.mark.asyncio
    async def test_check_hallucinations_analyzer_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test hallucination check with analyzer error"""
        # Mock analyzer error
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_script.side_effect = Exception("Analysis failed")
        mock_external_dependencies[
            "mock_ai_analyzer"
        ].return_value = mock_analyzer_instance

        # Execute test
        result = await check_ai_script_hallucinations(
            mock_context,
            script_path="/path/to/script.py",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Analysis failed" in result_data["error"]


class TestQueryKnowledgeGraphTool:
    """Test the query_knowledge_graph() MCP tool"""

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful knowledge graph query"""
        # Mock validator results
        mock_validator_instance = Mock()
        mock_validator_instance.execute_query.return_value = [
            {"name": "function1", "type": "function", "exists": True},
            {"name": "function2", "type": "function", "exists": False},
        ]
        mock_external_dependencies[
            "mock_kg_validator"
        ].return_value = mock_validator_instance

        # Execute test
        result = await query_knowledge_graph(
            mock_context,
            command="MATCH (f:Function) RETURN f.name, f.exists",
        )

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["results"]) == 2
        assert result_data["results"][0]["name"] == "function1"

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_empty_result(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test knowledge graph query with empty result"""
        # Mock empty results
        mock_validator_instance = Mock()
        mock_validator_instance.execute_query.return_value = []
        mock_external_dependencies[
            "mock_kg_validator"
        ].return_value = mock_validator_instance

        # Execute test
        result = await query_knowledge_graph(
            mock_context,
            command="MATCH (n:NonExistent) RETURN n",
        )

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert len(result_data["results"]) == 0

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_connection_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test knowledge graph query with connection error"""
        # Mock connection error
        mock_validator_instance = Mock()
        mock_validator_instance.execute_query.side_effect = Exception(
            "Neo4j connection failed",
        )
        mock_external_dependencies[
            "mock_kg_validator"
        ].return_value = mock_validator_instance

        # Execute test
        result = await query_knowledge_graph(mock_context, command="MATCH (n) RETURN n")

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Neo4j connection failed" in result_data["error"]

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_invalid_query(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test knowledge graph query with invalid Cypher query"""
        # Mock invalid query error
        mock_validator_instance = Mock()
        mock_validator_instance.execute_query.side_effect = Exception(
            "Invalid Cypher syntax",
        )
        mock_external_dependencies[
            "mock_kg_validator"
        ].return_value = mock_validator_instance

        # Execute test
        result = await query_knowledge_graph(
            mock_context,
            command="INVALID CYPHER QUERY",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Invalid Cypher syntax" in result_data["error"]


class TestParseGithubRepositoryTool:
    """Test the parse_github_repository() MCP tool"""

    @pytest.mark.asyncio
    async def test_parse_github_repository_success(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test successful GitHub repository parsing"""
        # Mock extractor results
        mock_extractor_instance = Mock()
        mock_extractor_instance.extract_repo.return_value = {
            "success": True,
            "functions_extracted": 25,
            "classes_extracted": 10,
            "files_processed": 15,
        }
        mock_external_dependencies[
            "mock_neo4j_extractor"
        ].return_value = mock_extractor_instance

        # Execute test
        result = await parse_github_repository(
            mock_context,
            repo_url="https://github.com/example/test-repo",
        )

        # Verify result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["functions_extracted"] == 25
        assert result_data["classes_extracted"] == 10

    @pytest.mark.asyncio
    async def test_parse_github_repository_invalid_url(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test GitHub repository parsing with invalid URL"""
        # Execute test with invalid URL
        result = await parse_github_repository(
            mock_context,
            repo_url="not-a-github-url",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Invalid GitHub repository URL" in result_data["error"]

    @pytest.mark.asyncio
    async def test_parse_github_repository_private_repo(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test GitHub repository parsing with private repo (access denied)"""
        # Mock access denied error
        mock_extractor_instance = Mock()
        mock_extractor_instance.extract_repo.side_effect = Exception(
            "Access denied - repository is private",
        )
        mock_external_dependencies[
            "mock_neo4j_extractor"
        ].return_value = mock_extractor_instance

        # Execute test
        result = await parse_github_repository(
            mock_context,
            repo_url="https://github.com/private/repo",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Access denied" in result_data["error"]

    @pytest.mark.asyncio
    async def test_parse_github_repository_network_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test GitHub repository parsing with network error"""
        # Mock network error
        mock_extractor_instance = Mock()
        mock_extractor_instance.extract_repo.side_effect = Exception("Network timeout")
        mock_external_dependencies[
            "mock_neo4j_extractor"
        ].return_value = mock_extractor_instance

        # Execute test
        result = await parse_github_repository(
            mock_context,
            repo_url="https://github.com/example/repo",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Network timeout" in result_data["error"]

    @pytest.mark.asyncio
    async def test_parse_github_repository_neo4j_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test GitHub repository parsing with Neo4j connection error"""
        # Mock Neo4j connection error
        mock_extractor_instance = Mock()
        mock_extractor_instance.extract_repo.side_effect = Exception(
            "Neo4j connection failed",
        )
        mock_external_dependencies[
            "mock_neo4j_extractor"
        ].return_value = mock_extractor_instance

        # Execute test
        result = await parse_github_repository(
            mock_context,
            repo_url="https://github.com/example/repo",
        )

        # Verify error result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "Neo4j connection failed" in result_data["error"]


class TestMCPToolsIntegration:
    """Integration tests for MCP tools interaction"""

    @pytest.mark.asyncio
    async def test_search_to_rag_query_integration(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test integration between search and RAG query tools"""
        # First mock successful search
        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_response = Mock()
        mock_response.json.return_value = {"results": [{"url": "https://example.com"}]}
        mock_response.raise_for_status.return_value = None
        mock_requests.return_value = mock_response

        # Mock scrape_urls and perform_rag_query
        with (
            patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape,
            patch("crawl4ai_mcp.perform_rag_query", new_callable=AsyncMock) as mock_rag,
        ):
            mock_scrape.return_value = json.dumps({"success": True})
            mock_rag.return_value = json.dumps(
                {
                    "success": True,
                    "results": [{"content": "Test content", "similarity": 0.9}],
                },
            )

            # Execute search (which should call RAG internally)
            search_result = await search(mock_context, query="test")

            # Then execute RAG query directly
            rag_result = await perform_rag_query(mock_context, query="test")

            # Verify both succeeded
            search_data = json.loads(search_result)
            rag_data = json.loads(rag_result)

            assert search_data["success"] is True
            assert rag_data["success"] is True

    @pytest.mark.asyncio
    async def test_error_propagation(self, mock_context, mock_external_dependencies):
        """Test that errors are properly propagated and formatted"""
        # Mock a function to raise an exception
        mock_external_dependencies["mock_search_docs"].side_effect = Exception(
            "Database unavailable",
        )

        # Execute test
        result = await perform_rag_query(mock_context, query="test")

        # Verify error is properly formatted
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data
        assert isinstance(result_data["error"], str)


# Performance and stress tests
class TestMCPToolsPerformance:
    """Performance tests for MCP tools"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test that tools can handle concurrent requests"""
        # Mock successful responses
        mock_external_dependencies["mock_search_docs"].return_value = [
            {"content": "Test", "similarity": 0.9, "metadata": {}},
        ]

        # Create multiple concurrent requests
        tasks = [
            perform_rag_query(mock_context, query=f"test query {i}") for i in range(5)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all succeeded
        for result in results:
            assert not isinstance(result, Exception)
            result_data = json.loads(result)
            assert result_data["success"] is True

    @pytest.mark.asyncio
    async def test_large_batch_processing(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test batch processing with large number of URLs"""
        # Create a large list of URLs
        large_url_list = [f"https://example.com/page{i}" for i in range(100)]

        # Mock the crawl_batch function directly
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            # Generate mock results for the first 10 URLs
            mock_results = [
                {"url": url, "markdown": f"# Test {i}", "links": {}}
                for i, url in enumerate(large_url_list[:10])
            ]
            mock_crawl_batch.return_value = mock_results
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test with large batch
            start_time = time.time()
            result = await scrape_urls(
                mock_context,
                url=large_url_list[:10],  # Limit to 10 for test performance
                max_concurrent=3,
                batch_size=5,
            )
            execution_time = time.time() - start_time

            # Verify result and reasonable execution time
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert (
                execution_time < 30
            )  # Should complete within 30 seconds  # Should complete within 30 seconds  # Should complete within 30 seconds
