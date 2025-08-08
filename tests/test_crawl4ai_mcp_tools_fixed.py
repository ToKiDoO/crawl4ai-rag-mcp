"""Fixed unit tests for MCP tools in src/tools.py with proper modular imports."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import necessary components
from fastmcp import Context

from src.main import create_mcp_server
from src.tools import register_tools


class TestMCPToolsFixed:
    """Test MCP tool functions with proper modular architecture."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server with registered tools."""
        server = create_mcp_server()
        register_tools(server)
        return server

    @pytest.fixture
    def mock_context(self):
        """Create mock context for MCP tools."""
        ctx = Mock(spec=Context)
        return ctx

    @pytest.mark.asyncio
    async def test_search_tool_success(self, mock_context, mcp_server):
        """Test successful search operation."""
        # Get the search tool from registered tools
        search = mcp_server._tools["search"]

        # Mock the services.search_and_process function
        with patch(
            "services.search_and_process", new_callable=AsyncMock
        ) as mock_search_process:
            mock_search_process.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {
                            "url": "https://example.com/1",
                            "content": "Result 1",
                        }
                    ],
                    "summary": {"total_results": 1},
                }
            )

            # Test basic search
            result = await search(
                mock_context,
                "test query",
                return_raw_markdown=False,
                num_results=2,
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert "results" in result_data
            assert "summary" in result_data
            mock_search_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_urls_tool_success(self, mock_context, mcp_server):
        """Test successful scraping operation."""
        # Get the scrape_urls tool from registered tools
        scrape_urls = mcp_server._tools["scrape_urls"]

        # Mock the services.process_urls_for_mcp function
        with patch(
            "services.process_urls_for_mcp", new_callable=AsyncMock
        ) as mock_process_urls:
            mock_process_urls.return_value = json.dumps(
                {
                    "success": True,
                    "markdown": "# Page Title\nPage content here.",
                    "summary": {"total_urls": 1, "successful": 1, "failed": 0},
                }
            )

            # Test single URL scraping
            result = await scrape_urls(
                mock_context,
                "https://example.com",
                return_raw_markdown=True,
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert "markdown" in result_data
            mock_process_urls.assert_called_once()

    @pytest.mark.asyncio
    async def test_smart_crawl_url_success(self, mock_context, mcp_server):
        """Test successful smart crawl operation."""
        # Get the smart_crawl_url tool from registered tools
        smart_crawl_url = mcp_server._tools["smart_crawl_url"]

        # Mock the services.smart_crawl function
        with patch(
            "services.smart_crawl.smart_crawl_url", new_callable=AsyncMock
        ) as mock_smart_crawl:
            mock_smart_crawl.return_value = json.dumps(
                {
                    "success": True,
                    "type": "webpage",
                    "pages_crawled": 1,
                    "chunks_created": 2,
                }
            )

            result = await smart_crawl_url(
                mock_context,
                "https://example.com",
                max_depth=1,
                return_raw_markdown=False,
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["type"] == "webpage"
            mock_smart_crawl.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_available_sources_success(self, mock_context, mcp_server):
        """Test getting available sources successfully."""
        # Get the get_available_sources tool from registered tools
        get_available_sources = mcp_server._tools["get_available_sources"]

        # Mock the get_available_sources_wrapper function
        with patch(
            "src.tools.get_available_sources_wrapper", new_callable=AsyncMock
        ) as mock_get_sources:
            mock_get_sources.return_value = json.dumps(
                {
                    "success": True,
                    "sources": [
                        {
                            "source_id": "example.com",
                            "summary": "Example website",
                            "total_word_count": 5000,
                        },
                    ],
                    "total_sources": 1,
                }
            )

            result = await get_available_sources(mock_context)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert len(result_data["sources"]) == 1
            mock_get_sources.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_rag_query_success(self, mock_context, mcp_server):
        """Test successful RAG query."""
        # Get the perform_rag_query tool from registered tools
        perform_rag_query = mcp_server._tools["perform_rag_query"]

        # Mock the perform_rag_query_wrapper function
        with patch(
            "src.tools.perform_rag_query_wrapper", new_callable=AsyncMock
        ) as mock_rag_query:
            mock_rag_query.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {
                            "id": "1",
                            "score": 0.9,
                            "content": "Relevant content here",
                            "url": "https://example.com/page1",
                        }
                    ],
                    "query": "test query",
                }
            )

            result = await perform_rag_query(mock_context, "test query", match_count=1)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["content"] == "Relevant content here"
            mock_rag_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_code_examples_success(self, mock_context, mcp_server):
        """Test searching code examples successfully."""
        # Get the search_code_examples tool from registered tools
        search_code_examples = mcp_server._tools["search_code_examples"]

        # Mock the search_code_examples_wrapper function
        with patch(
            "src.tools.search_code_examples_wrapper", new_callable=AsyncMock
        ) as mock_search_code:
            mock_search_code.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {
                            "id": "1",
                            "score": 0.85,
                            "language": "python",
                            "code": "def hello(): return 'world'",
                            "description": "Hello function",
                        }
                    ],
                }
            )

            result = await search_code_examples(
                mock_context, "python function", match_count=1
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["language"] == "python"
            mock_search_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_success(
        self, mock_context, mcp_server
    ):
        """Test AI script hallucination checking successfully."""
        # Get the check_ai_script_hallucinations tool from registered tools
        check_ai_script_hallucinations = mcp_server._tools[
            "check_ai_script_hallucinations"
        ]

        # Mock validation and app context
        with patch("utils.validation.validate_script_path") as mock_validate:
            with patch("src.tools.get_app_context") as mock_get_context:
                # Mock successful validation
                mock_validate.return_value = {"valid": True}

                # Mock app context with required components
                mock_app_ctx = Mock()
                mock_app_ctx.repo_extractor = Mock()
                mock_app_ctx.knowledge_validator = Mock()
                mock_app_ctx.script_analyzer = Mock()
                mock_app_ctx.hallucination_reporter = Mock()
                mock_get_context.return_value = mock_app_ctx

                # Mock the actual hallucination check
                with patch(
                    "knowledge_graph.validation.check_ai_script_hallucinations",
                    new_callable=AsyncMock,
                ) as mock_check:
                    mock_check.return_value = json.dumps(
                        {
                            "success": True,
                            "hallucination_risk": "low",
                            "overall_confidence": 0.95,
                            "verification_results": [],
                        }
                    )

                    result = await check_ai_script_hallucinations(
                        mock_context,
                        "/path/to/valid_script.py",
                    )
                    result_data = json.loads(result)

                    assert result_data["success"] is True
                    assert result_data["hallucination_risk"] == "low"
                    assert result_data["overall_confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_check_ai_script_hallucinations_enhanced_success(
        self, mock_context, mcp_server
    ):
        """Test enhanced AI script hallucination checking successfully."""
        # Get the check_ai_script_hallucinations_enhanced tool from registered tools
        check_ai_script_hallucinations_enhanced = mcp_server._tools[
            "check_ai_script_hallucinations_enhanced"
        ]

        # Mock validation and app context
        with patch("utils.validation.validate_script_path") as mock_validate:
            with patch("src.tools.get_app_context") as mock_get_context:
                # Mock successful validation
                mock_validate.return_value = {"valid": True}

                # Mock app context with database client
                mock_app_ctx = Mock()
                mock_app_ctx.database_client = AsyncMock()
                mock_app_ctx.repo_extractor = Mock()
                mock_app_ctx.repo_extractor.driver = Mock()
                mock_get_context.return_value = mock_app_ctx

                # Mock the enhanced hallucination check
                with patch(
                    "knowledge_graph.enhanced_validation.check_ai_script_hallucinations_enhanced",
                    new_callable=AsyncMock,
                ) as mock_enhanced_check:
                    mock_enhanced_check.return_value = json.dumps(
                        {
                            "success": True,
                            "hallucination_risk": "low",
                            "overall_confidence": 0.95,
                            "enhanced_validation": True,
                        }
                    )

                    result = await check_ai_script_hallucinations_enhanced(
                        mock_context,
                        "/path/to/valid_script.py",
                    )
                    result_data = json.loads(result)

                    assert result_data["success"] is True
                    assert result_data["enhanced_validation"] is True

    @pytest.mark.asyncio
    async def test_query_knowledge_graph_success(self, mock_context, mcp_server):
        """Test knowledge graph query successfully."""
        # Get the query_knowledge_graph tool from registered tools
        query_knowledge_graph = mcp_server._tools["query_knowledge_graph"]

        # Mock the query_knowledge_graph_wrapper function
        with patch(
            "src.tools.query_knowledge_graph_wrapper", new_callable=AsyncMock
        ) as mock_kg_query:
            mock_kg_query.return_value = json.dumps(
                {
                    "success": True,
                    "command": "repos",
                    "results": [
                        {"repository": "test-repo", "files": 10, "classes": 5},
                    ],
                }
            )

            result = await query_knowledge_graph(mock_context, "repos")
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["command"] == "repos"
            mock_kg_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_github_repository_success(self, mock_context, mcp_server):
        """Test GitHub repository parsing successfully."""
        # Get the parse_github_repository tool from registered tools
        parse_github_repository = mcp_server._tools["parse_github_repository"]

        # Mock validation and wrapper function
        with patch("utils.validation.validate_github_url") as mock_validate_url:
            with patch(
                "src.tools.parse_github_repository_wrapper", new_callable=AsyncMock
            ) as mock_parse_repo:
                mock_validate_url.return_value = {"valid": True}
                mock_parse_repo.return_value = json.dumps(
                    {
                        "success": True,
                        "repository": "test/repo",
                        "files_parsed": 25,
                        "classes_extracted": 10,
                    }
                )

                result = await parse_github_repository(
                    mock_context,
                    "https://github.com/test/repo.git",
                )
                result_data = json.loads(result)

                assert result_data["success"] is True
                assert result_data["repository"] == "test/repo"
                mock_parse_repo.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mock_context, mcp_server):
        """Test error handling in MCP tools."""
        # Get the search tool from registered tools
        search = mcp_server._tools["search"]

        # Mock the services function to raise an exception
        with patch(
            "services.search_and_process", new_callable=AsyncMock
        ) as mock_search_process:
            mock_search_process.side_effect = Exception("Service error")

            # Test that the tool catches and handles the exception
            with pytest.raises(Exception) as excinfo:
                await search(mock_context, "test query")

            assert "Search failed" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
