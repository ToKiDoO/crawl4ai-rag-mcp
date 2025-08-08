"""
Unit tests for advanced features: Neo4j knowledge graph and GitHub repository parsing.

This module tests:
- Neo4j connection validation and operations
- GitHub URL parsing and validation
- Knowledge graph integration with MCP tools
- AI script hallucination detection
- Repository parsing and analysis
"""

import json
import os
import sys
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import crawl4ai_mcp
from crawl4ai_mcp import (
    format_neo4j_error,
    validate_github_url,
    validate_neo4j_connection,
    validate_script_path,
)


def get_tool_function(tool_name: str):
    """Extract the actual function from FastMCP tool wrapper."""
    tool_attr = getattr(crawl4ai_mcp, tool_name, None)
    if hasattr(tool_attr, "fn"):
        return tool_attr.fn
    if callable(tool_attr):
        return tool_attr
    raise AttributeError(f"Cannot find callable function for {tool_name}")


class MockContext:
    """Mock context object for MCP tools."""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Neo4j related mocks
        self.request_context.lifespan_context.repo_extractor = Mock()
        self.request_context.lifespan_context.knowledge_validator = Mock()

        # Mock Neo4j driver and session with proper async context manager
        self.neo4j_driver = AsyncMock()
        self.neo4j_session = AsyncMock()
        self.request_context.lifespan_context.repo_extractor.driver = self.neo4j_driver

        # Create a proper async context manager mock
        async_cm = AsyncMock()
        async_cm.__aenter__ = AsyncMock(return_value=self.neo4j_session)
        async_cm.__aexit__ = AsyncMock(return_value=None)
        self.neo4j_driver.session.return_value = async_cm


@pytest.fixture
def mock_context():
    """Provide mock context for tests."""
    return MockContext()


@pytest.fixture
def mock_neo4j_environment():
    """Mock Neo4j environment variables."""
    with patch.dict(
        os.environ,
        {
            "USE_KNOWLEDGE_GRAPH": "true",
            "NEO4J_URI": "neo4j://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
        },
    ):
        yield


@pytest.fixture
def mock_github_environment():
    """Mock GitHub-related environment variables."""
    with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token"}):
        yield


class TestNeo4jConnectionValidation:
    """Test Neo4j connection validation functions."""

    def test_validate_neo4j_connection_all_vars_present(self):
        """Test validation when all environment variables are present."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "neo4j://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            result = validate_neo4j_connection()
            assert result is True

    def test_validate_neo4j_connection_missing_uri(self):
        """Test validation when NEO4J_URI is missing."""
        with patch.dict(
            os.environ,
            {"NEO4J_USER": "neo4j", "NEO4J_PASSWORD": "password"},
            clear=True,
        ):
            result = validate_neo4j_connection()
            assert result is False

    def test_validate_neo4j_connection_missing_user(self):
        """Test validation when NEO4J_USER is missing."""
        with patch.dict(
            os.environ,
            {"NEO4J_URI": "neo4j://localhost:7687", "NEO4J_PASSWORD": "password"},
            clear=True,
        ):
            result = validate_neo4j_connection()
            assert result is False

    def test_validate_neo4j_connection_missing_password(self):
        """Test validation when NEO4J_PASSWORD is missing."""
        with patch.dict(
            os.environ,
            {"NEO4J_URI": "neo4j://localhost:7687", "NEO4J_USER": "neo4j"},
            clear=True,
        ):
            result = validate_neo4j_connection()
            assert result is False

    def test_validate_neo4j_connection_all_missing(self):
        """Test validation when all environment variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            result = validate_neo4j_connection()
            assert result is False

    def test_validate_neo4j_connection_empty_values(self):
        """Test validation when environment variables are empty."""
        with patch.dict(
            os.environ,
            {"NEO4J_URI": "", "NEO4J_USER": "", "NEO4J_PASSWORD": ""},
        ):
            result = validate_neo4j_connection()
            assert result is False


class TestGitHubUrlValidation:
    """Test GitHub URL parsing and validation functions."""

    def test_validate_github_url_valid_https(self):
        """Test validation of valid HTTPS GitHub URL."""
        url = "https://github.com/owner/repository"
        result = validate_github_url(url)

        assert result["valid"] is True
        assert result["repo_name"] == "repository"

    def test_validate_github_url_valid_https_with_git(self):
        """Test validation of HTTPS GitHub URL with .git suffix."""
        url = "https://github.com/owner/repository.git"
        result = validate_github_url(url)

        assert result["valid"] is True
        assert result["repo_name"] == "repository"

    def test_validate_github_url_valid_ssh(self):
        """Test validation of SSH GitHub URL."""
        url = "git@github.com:owner/repository.git"
        result = validate_github_url(url)

        assert result["valid"] is True
        assert result["repo_name"] == "repository"

    def test_validate_github_url_empty_string(self):
        """Test validation of empty URL."""
        result = validate_github_url("")

        assert result["valid"] is False
        assert "Repository URL is required" in result["error"]

    def test_validate_github_url_none(self):
        """Test validation of None URL."""
        result = validate_github_url(None)

        assert result["valid"] is False
        assert "Repository URL is required" in result["error"]

    def test_validate_github_url_not_string(self):
        """Test validation of non-string URL."""
        result = validate_github_url(123)

        assert result["valid"] is False
        assert "Repository URL is required" in result["error"]

    def test_validate_github_url_not_github(self):
        """Test validation of non-GitHub URL."""
        url = "https://gitlab.com/owner/repository"
        result = validate_github_url(url)

        assert result["valid"] is False
        assert "valid GitHub repository URL" in result["error"]

    def test_validate_github_url_invalid_protocol(self):
        """Test validation of URL with invalid protocol."""
        url = "ftp://github.com/owner/repository"
        result = validate_github_url(url)

        assert result["valid"] is False
        assert "must start with https:// or git@" in result["error"]

    def test_validate_github_url_with_whitespace(self):
        """Test validation handles whitespace properly."""
        url = "  https://github.com/owner/repository  "
        result = validate_github_url(url)

        assert result["valid"] is True
        assert result["repo_name"] == "repository"

    def test_validate_github_url_case_insensitive(self):
        """Test that validation is case insensitive for github.com."""
        url = "https://GITHUB.COM/owner/repository"
        result = validate_github_url(url)

        assert result["valid"] is True
        assert result["repo_name"] == "repository"


class TestScriptPathValidation:
    """Test script path validation functions."""

    @patch("builtins.open", mock_open(read_data="print('hello')"))
    @patch("os.path.exists")
    def test_validate_script_path_valid(self, mock_exists):
        """Test validation of valid script path."""
        mock_exists.return_value = True
        script_path = "/path/to/script.py"

        result = validate_script_path(script_path)

        assert result["valid"] is True
        mock_exists.assert_called_once_with(script_path)

    @patch("os.path.exists")
    def test_validate_script_path_file_not_exists(self, mock_exists):
        """Test validation when file doesn't exist."""
        mock_exists.return_value = False
        script_path = "/path/to/nonexistent.py"

        result = validate_script_path(script_path)

        assert result["valid"] is False
        assert "Script not found: /path/to/nonexistent.py" in result["error"]

    def test_validate_script_path_empty(self):
        """Test validation of empty script path."""
        result = validate_script_path("")

        assert result["valid"] is False
        assert "Script path is required" in result["error"]

    def test_validate_script_path_none(self):
        """Test validation of None script path."""
        result = validate_script_path(None)

        assert result["valid"] is False
        assert "Script path is required" in result["error"]

    @patch("os.path.exists")
    def test_validate_script_path_not_python(self, mock_exists):
        """Test validation of non-Python file."""
        mock_exists.return_value = True
        script_path = "/path/to/script.txt"

        result = validate_script_path(script_path)

        assert result["valid"] is False
        assert "Only Python (.py) files are supported" in result["error"]


class TestNeo4jErrorFormatting:
    """Test Neo4j error formatting functions."""

    def test_format_neo4j_error_connection_failed(self):
        """Test formatting of connection failed error."""
        error = Exception("Connection failed")
        result = format_neo4j_error(error)

        assert (
            result
            == "Cannot connect to Neo4j. Check NEO4J_URI and ensure Neo4j is running."
        )

    def test_format_neo4j_error_with_database_exception(self):
        """Test formatting of database-specific exception."""
        error = Exception("Database unavailable")
        result = format_neo4j_error(error)

        assert (
            result
            == "Neo4j database error. Check if the database exists and is accessible."
        )

    def test_format_neo4j_error_generic(self):
        """Test formatting of generic Neo4j error."""
        error = Exception("Some other error")
        result = format_neo4j_error(error)

        assert result == "Neo4j error: Some other error"


class TestCheckAiScriptHallucinationsTool:
    """Test AI script hallucination detection MCP tool."""

    @pytest.mark.asyncio
    async def test_knowledge_graph_disabled(self, mock_context):
        """Test when knowledge graph functionality is disabled."""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "false"}):
            check_hallucinations = get_tool_function("check_ai_script_hallucinations")

            result = await check_hallucinations(mock_context, "/path/to/script.py")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Knowledge graph functionality is disabled" in result_data["error"]

    @pytest.mark.asyncio
    async def test_knowledge_validator_not_available(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test when knowledge validator is not available."""
        mock_context.request_context.lifespan_context.knowledge_validator = None

        check_hallucinations = get_tool_function("check_ai_script_hallucinations")

        result = await check_hallucinations(mock_context, "/path/to/script.py")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Knowledge graph validator not available" in result_data["error"]

    @pytest.mark.asyncio
    async def test_invalid_script_path(self, mock_context, mock_neo4j_environment):
        """Test with invalid script path."""
        with patch("crawl4ai_mcp.validate_script_path") as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "error": "Script file not found",
            }

            check_hallucinations = get_tool_function("check_ai_script_hallucinations")

            result = await check_hallucinations(mock_context, "/path/to/nonexistent.py")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert result_data["script_path"] == "/path/to/nonexistent.py"
            assert "Script file not found" in result_data["error"]

    @pytest.mark.asyncio
    async def test_successful_analysis(self, mock_context, mock_neo4j_environment):
        """Test successful script analysis."""
        # Mock script validation
        with patch("crawl4ai_mcp.validate_script_path") as mock_validate:
            mock_validate.return_value = {"valid": True}

            # Mock analysis components
            with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
                mock_analyzer = Mock()
                mock_analysis_result = Mock()
                mock_analysis_result.errors = []
                mock_analyzer.analyze_script.return_value = mock_analysis_result
                mock_analyzer_class.return_value = mock_analyzer

                # Mock validation result
                mock_validation_result = Mock()
                mock_validation_result.overall_confidence = 0.85
                mock_context.request_context.lifespan_context.knowledge_validator.validate_script = AsyncMock(
                    return_value=mock_validation_result,
                )

                # Mock report generation
                with patch("crawl4ai_mcp.HallucinationReporter") as mock_reporter_class:
                    mock_reporter = Mock()
                    mock_report = {
                        "validation_summary": {
                            "total_validations": 10,
                            "valid_count": 8,
                            "invalid_count": 1,
                            "uncertain_count": 1,
                            "not_found_count": 0,
                            "hallucination_rate": 0.1,
                        },
                        "hallucinations_detected": [],
                        "recommendations": ["Review uncertain validations"],
                        "analysis_metadata": {
                            "total_imports": 5,
                            "total_classes": 2,
                            "total_methods": 8,
                            "total_attributes": 3,
                            "total_functions": 1,
                        },
                        "libraries_analyzed": ["numpy", "pandas"],
                    }
                    mock_reporter.generate_comprehensive_report.return_value = (
                        mock_report
                    )
                    mock_reporter_class.return_value = mock_reporter

                    check_hallucinations = get_tool_function(
                        "check_ai_script_hallucinations",
                    )

                    result = await check_hallucinations(
                        mock_context,
                        "/path/to/script.py",
                    )
                    result_data = json.loads(result)

                    assert result_data["success"] is True
                    assert result_data["script_path"] == "/path/to/script.py"
                    assert result_data["overall_confidence"] == 0.85
                    assert result_data["validation_summary"]["total_validations"] == 10
                    assert (
                        result_data["validation_summary"]["hallucination_rate"] == 0.1
                    )
                    assert result_data["libraries_analyzed"] == ["numpy", "pandas"]

    @pytest.mark.asyncio
    async def test_analysis_exception(self, mock_context, mock_neo4j_environment):
        """Test handling of analysis exception."""
        with patch("crawl4ai_mcp.validate_script_path") as mock_validate:
            mock_validate.return_value = {"valid": True}

            with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
                mock_analyzer_class.side_effect = Exception("Analysis failed")

                check_hallucinations = get_tool_function(
                    "check_ai_script_hallucinations",
                )

                result = await check_hallucinations(mock_context, "/path/to/script.py")
                result_data = json.loads(result)

                assert result_data["success"] is False
                assert result_data["script_path"] == "/path/to/script.py"
                assert "Analysis failed" in result_data["error"]


class TestQueryKnowledgeGraphTool:
    """Test knowledge graph querying MCP tool."""

    @pytest.mark.asyncio
    async def test_knowledge_graph_disabled(self, mock_context):
        """Test when knowledge graph functionality is disabled."""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "false"}):
            query_kg = get_tool_function("query_knowledge_graph")

            result = await query_kg(mock_context, "repos")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Knowledge graph functionality is disabled" in result_data["error"]

    @pytest.mark.asyncio
    async def test_neo4j_not_available(self, mock_context, mock_neo4j_environment):
        """Test when Neo4j connection is not available."""
        mock_context.request_context.lifespan_context.repo_extractor = None

        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "repos")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Neo4j connection not available" in result_data["error"]

    @pytest.mark.asyncio
    async def test_empty_command(self, mock_context, mock_neo4j_environment):
        """Test with empty command."""
        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert result_data["command"] == ""
        assert "Command cannot be empty" in result_data["error"]

    @pytest.mark.asyncio
    async def test_repos_command(self, mock_context, mock_neo4j_environment):
        """Test repos command execution."""
        # Mock the Neo4j query result for repos command
        mock_result = AsyncMock()
        mock_result.__aiter__ = AsyncMock(
            return_value=iter([{"name": "repo1"}, {"name": "repo2"}]),
        )
        mock_context.neo4j_session.run.return_value = mock_result

        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "repos")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["command"] == "repos"
        assert result_data["data"]["repositories"] == ["repo1", "repo2"]

    @pytest.mark.asyncio
    async def test_explore_command_no_args(self, mock_context, mock_neo4j_environment):
        """Test explore command without repository name."""
        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "explore")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert result_data["command"] == "explore"
        assert "Repository name required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_explore_command_with_args(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test explore command with repository name."""
        # Mock multiple Neo4j queries for explore command
        repo_check_result = AsyncMock()
        repo_check_result.single = AsyncMock(return_value={"name": "pydantic-ai"})

        stats_results = [
            AsyncMock(),  # files query
            AsyncMock(),  # classes query
            AsyncMock(),  # functions query
            AsyncMock(),  # methods query
        ]
        stats_results[0].single = AsyncMock(return_value={"file_count": 10})
        stats_results[1].single = AsyncMock(return_value={"class_count": 5})
        stats_results[2].single = AsyncMock(return_value={"function_count": 8})
        stats_results[3].single = AsyncMock(return_value={"method_count": 20})

        mock_context.neo4j_session.run.side_effect = [repo_check_result] + stats_results

        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "explore pydantic-ai")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["data"]["repository"] == "pydantic-ai"
        assert result_data["data"]["statistics"]["files"] == 10
        assert result_data["data"]["statistics"]["classes"] == 5

    @pytest.mark.asyncio
    async def test_unknown_command(self, mock_context, mock_neo4j_environment):
        """Test with unknown command."""
        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "unknown_command")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert result_data["command"] == "unknown_command"
        assert "Unknown command 'unknown_command'" in result_data["error"]

    @pytest.mark.asyncio
    async def test_query_command_no_args(self, mock_context, mock_neo4j_environment):
        """Test query command without Cypher query."""
        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "query")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert result_data["command"] == "query"
        assert "Cypher query required" in result_data["error"]

    @pytest.mark.asyncio
    async def test_query_execution_exception(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test handling of query execution exception."""
        # Mock session.run to raise an exception
        mock_context.neo4j_session.run.side_effect = Exception(
            "Database connection failed",
        )

        query_kg = get_tool_function("query_knowledge_graph")

        result = await query_kg(mock_context, "repos")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert result_data["command"] == "repos"
        assert "Query execution failed" in result_data["error"]
        assert "Database connection failed" in result_data["error"]


class TestParseGithubRepositoryTool:
    """Test GitHub repository parsing MCP tool."""

    @pytest.mark.asyncio
    async def test_knowledge_graph_disabled(self, mock_context):
        """Test when knowledge graph functionality is disabled."""
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "false"}):
            parse_repo = get_tool_function("parse_github_repository")

            result = await parse_repo(mock_context, "https://github.com/owner/repo")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert "Knowledge graph functionality is disabled" in result_data["error"]

    @pytest.mark.asyncio
    async def test_repo_extractor_not_available(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test when repository extractor is not available."""
        mock_context.request_context.lifespan_context.repo_extractor = None

        parse_repo = get_tool_function("parse_github_repository")

        result = await parse_repo(mock_context, "https://github.com/owner/repo")
        result_data = json.loads(result)

        assert result_data["success"] is False
        assert "Repository extractor not available" in result_data["error"]

    @pytest.mark.asyncio
    async def test_invalid_repository_url(self, mock_context, mock_neo4j_environment):
        """Test with invalid repository URL."""
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Invalid GitHub URL"}

            parse_repo = get_tool_function("parse_github_repository")

            result = await parse_repo(mock_context, "invalid://url")
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert result_data["repo_url"] == "invalid://url"
            assert "Invalid GitHub URL" in result_data["error"]

    @pytest.mark.asyncio
    async def test_successful_repository_parsing(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test successful repository parsing."""
        # Mock URL validation
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.return_value = {"valid": True, "repo_name": "test-repo"}

            # Mock repository analysis
            mock_context.request_context.lifespan_context.repo_extractor.analyze_repository = AsyncMock()

            # Mock Neo4j query result
            mock_result = AsyncMock()
            mock_record = {
                "repo_name": "test-repo",
                "files_count": 15,
                "classes_count": 8,
                "methods_count": 25,
                "functions_count": 12,
                "attributes_count": 18,
                "sample_modules": ["module1", "module2", "module3"],
            }
            mock_result.single.return_value = mock_record
            mock_context.neo4j_session.run.return_value = mock_result

            parse_repo = get_tool_function("parse_github_repository")

            result = await parse_repo(
                mock_context,
                "https://github.com/owner/test-repo",
            )
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["repo_url"] == "https://github.com/owner/test-repo"
            assert result_data["repo_name"] == "test-repo"
            assert result_data["ready_for_validation"] is True

            stats = result_data["statistics"]
            assert stats["repository"] == "test-repo"
            assert stats["files_processed"] == 15
            assert stats["classes_created"] == 8
            assert stats["methods_created"] == 25
            assert stats["functions_created"] == 12
            assert stats["attributes_created"] == 18
            assert stats["sample_modules"] == ["module1", "module2", "module3"]

    @pytest.mark.asyncio
    async def test_repository_not_found_after_parsing(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test when repository is not found in database after parsing."""
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.return_value = {"valid": True, "repo_name": "test-repo"}

            # Mock repository analysis
            mock_context.request_context.lifespan_context.repo_extractor.analyze_repository = AsyncMock()

            # Mock Neo4j query returning no results
            mock_result = AsyncMock()
            mock_result.single.return_value = None
            mock_context.neo4j_session.run.return_value = mock_result

            parse_repo = get_tool_function("parse_github_repository")

            result = await parse_repo(
                mock_context,
                "https://github.com/owner/test-repo",
            )
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert result_data["repo_url"] == "https://github.com/owner/test-repo"
            assert (
                "Repository 'test-repo' not found in database after parsing"
                in result_data["error"]
            )

    @pytest.mark.asyncio
    async def test_repository_parsing_exception(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test handling of repository parsing exception."""
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.return_value = {"valid": True, "repo_name": "test-repo"}

            # Mock repository analysis to raise exception
            mock_context.request_context.lifespan_context.repo_extractor.analyze_repository = AsyncMock(
                side_effect=Exception("Git clone failed"),
            )

            parse_repo = get_tool_function("parse_github_repository")

            result = await parse_repo(
                mock_context,
                "https://github.com/owner/test-repo",
            )
            result_data = json.loads(result)

            assert result_data["success"] is False
            assert result_data["repo_url"] == "https://github.com/owner/test-repo"
            assert "Repository parsing failed" in result_data["error"]
            assert "Git clone failed" in result_data["error"]


class TestNeo4jIntegration:
    """Test Neo4j integration patterns and workflows."""

    @pytest.mark.asyncio
    async def test_neo4j_session_context_manager(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test that Neo4j session is properly used as async context manager."""
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.return_value = {"valid": True, "repo_name": "test-repo"}

            mock_context.request_context.lifespan_context.repo_extractor.analyze_repository = AsyncMock()

            # Mock successful query result
            mock_result = AsyncMock()
            mock_record = {
                "repo_name": "test-repo",
                "files_count": 5,
                "classes_count": 2,
                "methods_count": 8,
                "functions_count": 3,
                "attributes_count": 4,
                "sample_modules": ["test_module"],
            }
            mock_result.single.return_value = mock_record
            mock_context.neo4j_session.run.return_value = mock_result

            parse_repo = get_tool_function("parse_github_repository")
            await parse_repo(mock_context, "https://github.com/owner/test-repo")

            # Verify session context manager was used
            mock_context.neo4j_driver.session.assert_called()
            mock_context.neo4j_session.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_neo4j_query_parameters(self, mock_context, mock_neo4j_environment):
        """Test that Neo4j queries use proper parameters."""
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.return_value = {"valid": True, "repo_name": "test-repo"}

            mock_context.request_context.lifespan_context.repo_extractor.analyze_repository = AsyncMock()

            mock_result = AsyncMock()
            mock_record = {
                "repo_name": "test-repo",
                "files_count": 5,
                "classes_count": 2,
                "methods_count": 8,
                "functions_count": 3,
                "attributes_count": 4,
                "sample_modules": ["test_module"],
            }
            mock_result.single.return_value = mock_record
            mock_context.neo4j_session.run.return_value = mock_result

            parse_repo = get_tool_function("parse_github_repository")
            await parse_repo(mock_context, "https://github.com/owner/test-repo")

            # Verify query was called with proper parameters
            call_args = mock_context.neo4j_session.run.call_args
            assert call_args is not None
            assert "repo_name" in call_args[1]  # Check parameters
            assert call_args[1]["repo_name"] == "test-repo"

    def test_environment_variable_integration(self):
        """Test that environment variables are properly integrated."""
        # Test when all variables are present
        with patch.dict(
            os.environ,
            {
                "USE_KNOWLEDGE_GRAPH": "true",
                "NEO4J_URI": "neo4j://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            assert os.getenv("USE_KNOWLEDGE_GRAPH") == "true"
            assert validate_neo4j_connection() is True

        # Test when knowledge graph is disabled
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "false"}):
            assert os.getenv("USE_KNOWLEDGE_GRAPH") == "false"


class TestErrorHandlingPatterns:
    """Test error handling patterns across advanced features."""

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_neo4j(self, mock_context):
        """Test graceful degradation when Neo4j is not available."""
        tools = [
            "check_ai_script_hallucinations",
            "query_knowledge_graph",
            "parse_github_repository",
        ]

        # Test each tool handles missing Neo4j gracefully
        for tool_name in tools:
            with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "false"}):
                tool_func = get_tool_function(tool_name)
                result = await tool_func(mock_context, "test_input")
                result_data = json.loads(result)

                assert result_data["success"] is False
                assert (
                    "Knowledge graph functionality is disabled" in result_data["error"]
                )

    @pytest.mark.asyncio
    async def test_exception_handling_consistency(
        self,
        mock_context,
        mock_neo4j_environment,
    ):
        """Test that all tools handle exceptions consistently."""
        with patch("crawl4ai_mcp.validate_github_url") as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            parse_repo = get_tool_function("parse_github_repository")
            result = await parse_repo(mock_context, "https://github.com/owner/repo")
            result_data = json.loads(result)

            # Check error response format consistency
            assert result_data["success"] is False
            assert "error" in result_data
            assert "repo_url" in result_data
            assert isinstance(result_data["error"], str)

    def test_input_validation_consistency(self):
        """Test that input validation is consistent across functions."""
        # Test empty/None inputs
        test_cases = [
            (validate_github_url, None),
            (validate_github_url, ""),
            (validate_script_path, None),
            (validate_script_path, ""),
        ]

        for func, invalid_input in test_cases:
            result = func(invalid_input)
            assert result["valid"] is False
            assert "error" in result
            assert isinstance(result["error"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
