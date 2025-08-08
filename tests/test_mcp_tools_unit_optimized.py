"""
Optimized version of test_mcp_tools_unit.py with performance improvements

Key optimizations:
1. Mock OpenAI embeddings to avoid real API calls
2. Use shared fixtures with caching
3. Simplified mock setups
4. Batch test data creation
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

# Shared test data
MOCK_EMBEDDING = [0.1] * 1536
MOCK_SEARCH_RESULTS = [
    {"url": "https://example.com/page1"},
    {"url": "https://example.com/page2"},
]


# Mock the FastMCP Context before importing the main module
class MockContext:
    """Mock FastMCP Context for testing - optimized version"""

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


# Fast mock for OpenAI embeddings
def mock_openai_embeddings():
    """Fast mock for OpenAI embeddings - avoid real API calls"""
    mock_response = Mock()
    mock_response.data = [Mock(embedding=MOCK_EMBEDDING)]
    return mock_response


# Mock all external dependencies before importing
@pytest.fixture(autouse=True, scope="module")
def mock_external_dependencies():
    """Mock all external dependencies used by MCP tools - module scoped for performance"""
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

    # Mock OpenAI to avoid real API calls
    with (
        patch.dict(os.environ, env_vars),
        patch(
            "openai.embeddings.create",
            side_effect=lambda **kwargs: mock_openai_embeddings(),
        ),
        patch("openai.OpenAI") as mock_openai_client,
    ):
        # Configure OpenAI mock
        mock_client_instance = Mock()
        mock_client_instance.embeddings = Mock()
        mock_client_instance.embeddings.create = Mock(
            side_effect=lambda **kwargs: mock_openai_embeddings(),
        )
        mock_openai_client.return_value = mock_client_instance

        with patch.dict(
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
        ):
            # Mock specific classes and functions
            with (
                patch("crawl4ai.AsyncWebCrawler") as mock_crawler,
                patch("crawl4ai.BrowserConfig") as mock_browser_config,
                patch("crawl4ai.CrawlerRunConfig") as mock_crawler_config,
                patch("requests.get") as mock_requests_get,
                patch(
                    "database.factory.create_and_initialize_database",
                ) as mock_db_factory,
                patch("utils.add_documents_to_database") as mock_add_docs,
                patch("utils.search_documents") as mock_search_docs,
                patch("utils.extract_code_blocks") as mock_extract_code,
                patch(
                    "utils.generate_code_example_summary",
                ) as mock_code_summary,
                patch(
                    "knowledge_graph_validator.KnowledgeGraphValidator",
                ) as mock_kg_validator,
                patch(
                    "parse_repo_into_neo4j.DirectNeo4jExtractor",
                ) as mock_neo4j_extractor,
                patch("ai_script_analyzer.AIScriptAnalyzer") as mock_ai_analyzer,
                patch(
                    "hallucination_reporter.HallucinationReporter",
                ) as mock_hallucination_reporter,
                patch("os.path.exists", return_value=True) as mock_path_exists,
                patch(
                    "builtins.open",
                    mock_open(read_data="script content"),
                ) as mock_file_open,
            ):
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
    """Test the search() MCP tool - optimized with shared fixtures"""

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
        mock_response.json.return_value = {"results": MOCK_SEARCH_RESULTS}
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error_type,error_msg,expected_msg",
        [
            (
                requests.exceptions.Timeout,
                "Request timed out",
                "SearXNG request timed out",
            ),
            (
                requests.exceptions.ConnectionError,
                "Connection failed",
                "Cannot connect to SearXNG",
            ),
        ],
    )
    async def test_search_errors(
        self,
        mock_context,
        mock_external_dependencies,
        error_type,
        error_msg,
        expected_msg,
    ):
        """Test search failure scenarios - parameterized for efficiency"""
        mock_requests = mock_external_dependencies["mock_requests_get"]
        mock_requests.side_effect = error_type(error_msg)

        result = await search(mock_context, query="test query")

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert expected_msg in result_data["error"]

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
    """Test the scrape_urls() MCP tool - optimized"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "urls,expected_count",
        [
            ("https://example.com", 1),
            (["https://example.com/page1", "https://example.com/page2"], 2),
        ],
    )
    async def test_scrape_urls_success(
        self,
        mock_context,
        mock_external_dependencies,
        urls,
        expected_count,
    ):
        """Test successful URL scraping - parameterized"""
        # Mock the crawl_batch function directly
        with patch(
            "crawl4ai_mcp.crawl_batch",
            new_callable=AsyncMock,
        ) as mock_crawl_batch:
            if isinstance(urls, str):
                mock_crawl_batch.return_value = [
                    {
                        "url": urls,
                        "markdown": "# Test Content",
                        "links": {"internal": [], "external": []},
                    },
                ]
            else:
                mock_crawl_batch.return_value = [
                    {"url": url, "markdown": f"# Page {i}", "links": {}}
                    for i, url in enumerate(urls)
                ]
            mock_external_dependencies["mock_add_docs"].return_value = True

            # Execute test
            result = await scrape_urls(mock_context, url=urls)

            # Verify result
            result_data = json.loads(result)
            assert result_data["success"] is True
            if isinstance(urls, list):
                assert result_data["summary"]["successful_urls"] == expected_count
            else:
                assert result_data["url"] == urls


class TestPerformRagQueryTool:
    """Test the perform_rag_query() MCP tool - optimized with mocked embeddings"""

    @pytest.mark.asyncio
    async def test_rag_query_success(self, mock_context, mock_external_dependencies):
        """Test successful RAG query with mocked embeddings"""
        # Mock search_documents to return results without calling OpenAI
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

            # Mock the embedding creation to avoid OpenAI calls
            with patch(
                "crawl4ai_mcp.create_embeddings",
                new_callable=AsyncMock,
            ) as mock_embed:
                mock_embed.return_value = [MOCK_EMBEDDING]

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


class TestMCPToolsPerformance:
    """Performance tests for MCP tools"""

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test that tools can handle concurrent requests efficiently"""
        # Mock search_documents with minimal overhead
        with patch(
            "crawl4ai_mcp.search_documents",
            new_callable=AsyncMock,
        ) as mock_search:
            mock_search.return_value = [
                {"content": "Test", "similarity": 0.9, "metadata": {}},
            ]

            # Mock embeddings to avoid OpenAI calls
            with patch(
                "crawl4ai_mcp.create_embeddings",
                new_callable=AsyncMock,
            ) as mock_embed:
                mock_embed.return_value = [MOCK_EMBEDDING]

                # Create multiple concurrent requests
                tasks = [
                    perform_rag_query(mock_context, query=f"test query {i}")
                    for i in range(5)
                ]

                # Execute concurrently
                start_time = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                execution_time = time.time() - start_time

                # Verify all succeeded and performance
                for result in results:
                    assert not isinstance(result, Exception)
                    result_data = json.loads(result)
                    assert result_data["success"] is True

                # Should complete quickly with mocked dependencies
                assert execution_time < 1.0  # Should complete in under 1 second
