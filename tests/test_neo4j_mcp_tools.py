"""
Comprehensive tests for Neo4j MCP tools integration.

This module tests the MCP tool integration for Neo4j knowledge graph functionality:
- check_ai_script_hallucinations MCP tool
- query_knowledge_graph MCP tool
- parse_github_repository MCP tool
- Integration with lifespan context
- Environment variable handling
- Error handling and validation
- Tool response formatting
- Performance and reliability
"""

import asyncio
import json
import os

# Add src to path for imports
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import fixtures

# Mock all Neo4j and knowledge graph dependencies
with patch.dict(
    "sys.modules",
    {
        "neo4j": MagicMock(),
        "neo4j.AsyncGraphDatabase": MagicMock(),
        "knowledge_graphs.ai_script_analyzer": MagicMock(),
        "knowledge_graphs.knowledge_graph_validator": MagicMock(),
        "knowledge_graphs.hallucination_reporter": MagicMock(),
        "knowledge_graphs.parse_repo_into_neo4j": MagicMock(),
    },
):
    # Now import the MCP module
    from crawl4ai_mcp import (
        check_ai_script_hallucinations,
        parse_github_repository,
        query_knowledge_graph,
    )


class MockContext:
    """Mock MCP Context for testing"""

    def __init__(self):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = MagicMock()
        self.request_context.lifespan_context.knowledge_validator = None


class TestMCPToolEnvironmentSetup:
    """Test environment setup and configuration for MCP tools"""

    @pytest.fixture
    def clean_environment(self):
        """Fixture to provide clean environment for each test"""
        # Store original environment
        original_env = {}
        test_keys = ["USE_KNOWLEDGE_GRAPH", "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]

        for key in test_keys:
            original_env[key] = os.environ.get(key)
            # Clear the key
            if key in os.environ:
                del os.environ[key]

        yield

        # Restore original environment
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]

    @pytest.mark.asyncio
    async def test_knowledge_graph_disabled(self, clean_environment):
        """Test MCP tools when knowledge graph is disabled"""
        # Set knowledge graph as disabled
        os.environ["USE_KNOWLEDGE_GRAPH"] = "false"

        ctx = MockContext()
        script_path = "/path/to/test_script.py"

        result = await check_ai_script_hallucinations(ctx, script_path)

        # Should return error about disabled functionality
        response = json.loads(result)
        assert response["success"] is False
        assert "disabled" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_knowledge_graph_enabled_no_validator(self, clean_environment):
        """Test MCP tools when knowledge graph is enabled but validator not available"""
        # Set knowledge graph as enabled
        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        ctx = MockContext()
        ctx.request_context.lifespan_context.knowledge_validator = None

        script_path = "/path/to/test_script.py"

        result = await check_ai_script_hallucinations(ctx, script_path)

        # Should return error about validator not available
        response = json.loads(result)
        assert response["success"] is False
        assert "not available" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_knowledge_graph_environment_variables(self, clean_environment):
        """Test that all required environment variables are checked"""
        # Set partial environment
        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"
        os.environ["NEO4J_URI"] = "bolt://localhost:7687"
        # Missing NEO4J_USER and NEO4J_PASSWORD

        ctx = MockContext()

        # The actual implementation should validate environment variables
        # This test verifies the importance of complete configuration


class TestCheckAIScriptHallucinationsTool:
    """Test the check_ai_script_hallucinations MCP tool"""

    @pytest.fixture
    def mock_knowledge_context(self):
        """Mock context with knowledge validator"""
        ctx = MockContext()

        # Mock knowledge validator
        mock_validator = MagicMock()
        mock_validator.validate_script = AsyncMock()

        ctx.request_context.lifespan_context.knowledge_validator = mock_validator

        return ctx, mock_validator

    @pytest.fixture
    def enabled_environment(self):
        """Environment with knowledge graph enabled"""
        original_env = os.environ.get("USE_KNOWLEDGE_GRAPH")
        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        yield

        if original_env is not None:
            os.environ["USE_KNOWLEDGE_GRAPH"] = original_env
        else:
            os.environ.pop("USE_KNOWLEDGE_GRAPH", None)

    @pytest.mark.asyncio
    async def test_valid_script_path(
        self,
        mock_knowledge_context,
        enabled_environment,
        sample_script_file,
    ):
        """Test hallucination check with valid script path"""
        ctx, mock_validator = mock_knowledge_context

        # Mock successful validation
        mock_validation_result = MagicMock()
        mock_validation_result.overall_confidence = 0.95
        mock_validator.validate_script.return_value = mock_validation_result

        with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analysis_result = MagicMock()
            mock_analysis_result.errors = []
            mock_analyzer.analyze_script.return_value = mock_analysis_result
            mock_analyzer_class.return_value = mock_analyzer

            with patch("crawl4ai_mcp.HallucinationReporter") as mock_reporter_class:
                mock_reporter = MagicMock()
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
                    "recommendations": ["Use verified imports"],
                    "analysis_metadata": {
                        "total_imports": 3,
                        "total_classes": 1,
                        "total_methods": 2,
                        "total_attributes": 1,
                        "total_functions": 1,
                    },
                    "libraries_analyzed": ["main"],
                }
                mock_reporter.generate_comprehensive_report.return_value = mock_report
                mock_reporter_class.return_value = mock_reporter

                result = await check_ai_script_hallucinations(ctx, sample_script_file)

                # Verify successful response
                response = json.loads(result)
                assert response["success"] is True
                assert response["overall_confidence"] == 0.95
                assert "validation_summary" in response
                assert response["validation_summary"]["total_validations"] == 10

    @pytest.mark.asyncio
    async def test_invalid_script_path(
        self,
        mock_knowledge_context,
        enabled_environment,
    ):
        """Test hallucination check with invalid script path"""
        ctx, mock_validator = mock_knowledge_context

        invalid_path = "/nonexistent/script.py"

        result = await check_ai_script_hallucinations(ctx, invalid_path)

        # Should return error for invalid path
        response = json.loads(result)
        assert response["success"] is False
        assert "error" in response

    @pytest.mark.asyncio
    async def test_script_analysis_error(
        self,
        mock_knowledge_context,
        enabled_environment,
        sample_script_file,
    ):
        """Test handling of script analysis errors"""
        ctx, mock_validator = mock_knowledge_context

        with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_script.side_effect = Exception("Analysis failed")
            mock_analyzer_class.return_value = mock_analyzer

            result = await check_ai_script_hallucinations(ctx, sample_script_file)

            # Should return error for analysis failure
            response = json.loads(result)
            assert response["success"] is False
            assert "Analysis failed" in response["error"]

    @pytest.mark.asyncio
    async def test_validation_error(
        self,
        mock_knowledge_context,
        enabled_environment,
        sample_script_file,
    ):
        """Test handling of validation errors"""
        ctx, mock_validator = mock_knowledge_context

        # Mock validation error
        mock_validator.validate_script.side_effect = Exception("Validation failed")

        with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analysis_result = MagicMock()
            mock_analysis_result.errors = []
            mock_analyzer.analyze_script.return_value = mock_analysis_result
            mock_analyzer_class.return_value = mock_analyzer

            result = await check_ai_script_hallucinations(ctx, sample_script_file)

            # Should return error for validation failure
            response = json.loads(result)
            assert response["success"] is False
            assert "Validation failed" in response["error"]

    @pytest.mark.asyncio
    async def test_script_with_warnings(
        self,
        mock_knowledge_context,
        enabled_environment,
        sample_script_file,
    ):
        """Test handling of script analysis with warnings"""
        ctx, mock_validator = mock_knowledge_context

        # Mock validation with warnings
        mock_validation_result = MagicMock()
        mock_validation_result.overall_confidence = 0.7
        mock_validator.validate_script.return_value = mock_validation_result

        with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analysis_result = MagicMock()
            mock_analysis_result.errors = ["Warning: Potential issue found"]
            mock_analyzer.analyze_script.return_value = mock_analysis_result
            mock_analyzer_class.return_value = mock_analyzer

            with patch("crawl4ai_mcp.HallucinationReporter") as mock_reporter_class:
                mock_reporter = MagicMock()
                mock_report = {
                    "validation_summary": {
                        "total_validations": 5,
                        "valid_count": 3,
                        "invalid_count": 1,
                        "uncertain_count": 1,
                        "not_found_count": 0,
                        "hallucination_rate": 0.2,
                    },
                    "hallucinations_detected": ["Potential hallucination"],
                    "recommendations": ["Review imports"],
                    "analysis_metadata": {
                        "total_imports": 2,
                        "total_classes": 0,
                        "total_methods": 0,
                        "total_attributes": 0,
                        "total_functions": 1,
                    },
                    "libraries_analyzed": [],
                }
                mock_reporter.generate_comprehensive_report.return_value = mock_report
                mock_reporter_class.return_value = mock_reporter

                result = await check_ai_script_hallucinations(ctx, sample_script_file)

                # Should handle warnings gracefully
                response = json.loads(result)
                assert response["success"] is True
                assert response["overall_confidence"] == 0.7
                assert len(response["hallucinations_detected"]) > 0


class TestQueryKnowledgeGraphTool:
    """Test the query_knowledge_graph MCP tool"""

    @pytest.fixture
    def mock_extractor_context(self):
        """Mock context for knowledge graph queries"""
        ctx = MockContext()

        # Mock extractor
        mock_extractor = MagicMock()
        mock_extractor.search_graph = AsyncMock()

        ctx.request_context.lifespan_context.knowledge_extractor = mock_extractor

        return ctx, mock_extractor

    @pytest.mark.asyncio
    async def test_basic_query(self, mock_extractor_context):
        """Test basic knowledge graph query"""
        ctx, mock_extractor = mock_extractor_context

        # Mock query result
        mock_result = [
            {"class": {"name": "TestClass", "full_name": "main.TestClass"}},
            {"class": {"name": "UtilClass", "full_name": "utils.UtilClass"}},
        ]
        mock_extractor.search_graph.return_value = mock_result

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        query_command = "MATCH (c:Class) RETURN c LIMIT 10"

        result = await query_knowledge_graph(ctx, query_command)

        # Verify successful query
        response = json.loads(result)
        assert response["success"] is True
        assert "results" in response
        assert len(response["results"]) == 2

    @pytest.mark.asyncio
    async def test_complex_query_with_relationships(self, mock_extractor_context):
        """Test complex query with relationships"""
        ctx, mock_extractor = mock_extractor_context

        # Mock complex query result
        mock_result = [
            {
                "method": {"name": "test_method"},
                "class": {"name": "TestClass"},
                "relationship": {"type": "BELONGS_TO"},
            },
        ]
        mock_extractor.search_graph.return_value = mock_result

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        query_command = "MATCH (m:Method)-[:BELONGS_TO]->(c:Class) RETURN m, c"

        result = await query_knowledge_graph(ctx, query_command)

        # Verify complex query result
        response = json.loads(result)
        assert response["success"] is True
        assert len(response["results"]) == 1

    @pytest.mark.asyncio
    async def test_empty_query_result(self, mock_extractor_context):
        """Test query with no results"""
        ctx, mock_extractor = mock_extractor_context

        # Mock empty result
        mock_extractor.search_graph.return_value = []

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        query_command = "MATCH (n:NonexistentType) RETURN n"

        result = await query_knowledge_graph(ctx, query_command)

        # Should handle empty results gracefully
        response = json.loads(result)
        assert response["success"] is True
        assert response["results"] == []
        assert response["result_count"] == 0

    @pytest.mark.asyncio
    async def test_invalid_query_syntax(self, mock_extractor_context):
        """Test handling of invalid query syntax"""
        ctx, mock_extractor = mock_extractor_context

        # Mock query error
        from neo4j.exceptions import CypherSyntaxError

        mock_extractor.search_graph.side_effect = CypherSyntaxError("Invalid syntax")

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        invalid_query = "INVALID CYPHER SYNTAX"

        result = await query_knowledge_graph(ctx, invalid_query)

        # Should return error for invalid syntax
        response = json.loads(result)
        assert response["success"] is False
        assert "syntax" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_query_timeout(self, mock_extractor_context):
        """Test handling of query timeouts"""
        ctx, mock_extractor = mock_extractor_context

        # Mock timeout error
        mock_extractor.search_graph.side_effect = TimeoutError("Query timeout")

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        slow_query = "MATCH (n) RETURN n"  # Potentially slow query

        result = await query_knowledge_graph(ctx, slow_query)

        # Should handle timeout gracefully
        response = json.loads(result)
        assert response["success"] is False
        assert "timeout" in response["error"].lower()


class TestParseGitHubRepositoryTool:
    """Test the parse_github_repository MCP tool"""

    @pytest.fixture
    def mock_extractor_context(self):
        """Mock context for repository parsing"""
        ctx = MockContext()

        # Mock extractor
        mock_extractor = MagicMock()
        mock_extractor.analyze_repository = AsyncMock()
        mock_extractor.clear_repository_data = AsyncMock()

        ctx.request_context.lifespan_context.knowledge_extractor = mock_extractor

        return ctx, mock_extractor

    @pytest.mark.asyncio
    async def test_successful_repository_parsing(self, mock_extractor_context):
        """Test successful GitHub repository parsing"""
        ctx, mock_extractor = mock_extractor_context

        # Mock successful parsing
        mock_result = {
            "repository": "test-repo",
            "files_processed": 10,
            "classes_found": 5,
            "methods_found": 20,
            "functions_found": 15,
        }
        mock_extractor.analyze_repository.return_value = mock_result
        mock_extractor.clear_repository_data.return_value = {
            "nodes_deleted": 0,
            "relationships_deleted": 0,
        }

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        repo_url = "https://github.com/test/test-repo.git"

        result = await parse_github_repository(ctx, repo_url)

        # Verify successful parsing
        response = json.loads(result)
        assert response["success"] is True
        assert "test-repo" in response["message"]
        assert "files_processed" in response["analysis_results"]
        assert response["analysis_results"]["files_processed"] == 10

    @pytest.mark.asyncio
    async def test_invalid_repository_url(self, mock_extractor_context):
        """Test handling of invalid repository URLs"""
        ctx, mock_extractor = mock_extractor_context

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        invalid_urls = [
            "not-a-url",
            "https://invalid-domain.com/repo.git",
            "https://github.com/user",  # Missing repo name
            "",
        ]

        for invalid_url in invalid_urls:
            result = await parse_github_repository(ctx, invalid_url)

            response = json.loads(result)
            assert response["success"] is False
            assert "invalid" in response["error"].lower() or "error" in response

    @pytest.mark.asyncio
    async def test_repository_not_found(self, mock_extractor_context):
        """Test handling of non-existent repositories"""
        ctx, mock_extractor = mock_extractor_context

        # Mock repository not found error
        mock_extractor.analyze_repository.side_effect = Exception(
            "Repository not found",
        )

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        repo_url = "https://github.com/nonexistent/repo.git"

        result = await parse_github_repository(ctx, repo_url)

        # Should handle repository not found
        response = json.loads(result)
        assert response["success"] is False
        assert "not found" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_repository_access_denied(self, mock_extractor_context):
        """Test handling of private/restricted repositories"""
        ctx, mock_extractor = mock_extractor_context

        # Mock access denied error
        mock_extractor.analyze_repository.side_effect = Exception("Access denied")

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        repo_url = "https://github.com/private/repo.git"

        result = await parse_github_repository(ctx, repo_url)

        # Should handle access denied
        response = json.loads(result)
        assert response["success"] is False
        assert "access denied" in response["error"].lower()

    @pytest.mark.asyncio
    async def test_repository_parsing_with_cleanup(self, mock_extractor_context):
        """Test repository parsing with existing data cleanup"""
        ctx, mock_extractor = mock_extractor_context

        # Mock existing data cleanup
        mock_extractor.clear_repository_data.return_value = {
            "nodes_deleted": 50,
            "relationships_deleted": 100,
        }

        # Mock successful parsing
        mock_result = {
            "repository": "existing-repo",
            "files_processed": 15,
            "classes_found": 8,
            "methods_found": 30,
            "functions_found": 20,
        }
        mock_extractor.analyze_repository.return_value = mock_result

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        repo_url = "https://github.com/test/existing-repo.git"

        result = await parse_github_repository(ctx, repo_url)

        # Verify cleanup and parsing
        response = json.loads(result)
        assert response["success"] is True
        assert "existing-repo" in response["message"]
        assert response["cleanup_results"]["nodes_deleted"] == 50
        assert response["cleanup_results"]["relationships_deleted"] == 100

    @pytest.mark.asyncio
    async def test_large_repository_handling(self, mock_extractor_context):
        """Test handling of large repositories"""
        ctx, mock_extractor = mock_extractor_context

        # Mock large repository results
        mock_result = {
            "repository": "large-repo",
            "files_processed": 1000,
            "classes_found": 500,
            "methods_found": 2000,
            "functions_found": 1500,
        }
        mock_extractor.analyze_repository.return_value = mock_result
        mock_extractor.clear_repository_data.return_value = {
            "nodes_deleted": 0,
            "relationships_deleted": 0,
        }

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        repo_url = "https://github.com/test/large-repo.git"

        result = await parse_github_repository(ctx, repo_url)

        # Should handle large repositories
        response = json.loads(result)
        assert response["success"] is True
        assert response["analysis_results"]["files_processed"] == 1000
        assert (
            "performance" in response
            or "files_processed" in response["analysis_results"]
        )


class TestMCPToolsIntegration:
    """Test integration aspects of MCP tools"""

    @pytest.mark.asyncio
    async def test_tool_chaining_workflow(self):
        """Test chaining multiple MCP tools in a workflow"""
        # Test workflow: parse repository -> query graph -> check script

        # Mock context
        ctx = MockContext()

        # Mock extractor and validator
        mock_extractor = MagicMock()
        mock_validator = MagicMock()

        ctx.request_context.lifespan_context.knowledge_extractor = mock_extractor
        ctx.request_context.lifespan_context.knowledge_validator = mock_validator

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        # Step 1: Parse repository
        mock_extractor.analyze_repository = AsyncMock(
            return_value={
                "repository": "test-repo",
                "files_processed": 5,
                "classes_found": 3,
                "methods_found": 10,
                "functions_found": 8,
            },
        )
        mock_extractor.clear_repository_data = AsyncMock(
            return_value={"nodes_deleted": 0, "relationships_deleted": 0},
        )

        parse_result = await parse_github_repository(
            ctx,
            "https://github.com/test/repo.git",
        )
        parse_response = json.loads(parse_result)
        assert parse_response["success"] is True

        # Step 2: Query the parsed data
        mock_extractor.search_graph = AsyncMock(
            return_value=[
                {"class": {"name": "TestClass", "full_name": "main.TestClass"}},
            ],
        )

        query_result = await query_knowledge_graph(ctx, "MATCH (c:Class) RETURN c")
        query_response = json.loads(query_result)
        assert query_response["success"] is True
        assert len(query_response["results"]) == 1

        # Step 3: Check script against parsed knowledge
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write("from main import TestClass\nobj = TestClass()")
            tmp_path = tmp.name

        try:
            mock_validator.validate_script = AsyncMock()
            mock_validation_result = MagicMock()
            mock_validation_result.overall_confidence = 0.95
            mock_validator.validate_script.return_value = mock_validation_result

            with patch("crawl4ai_mcp.AIScriptAnalyzer") as mock_analyzer_class:
                mock_analyzer = MagicMock()
                mock_analysis_result = MagicMock()
                mock_analysis_result.errors = []
                mock_analyzer.analyze_script.return_value = mock_analysis_result
                mock_analyzer_class.return_value = mock_analyzer

                with patch("crawl4ai_mcp.HallucinationReporter") as mock_reporter_class:
                    mock_reporter = MagicMock()
                    mock_report = {
                        "validation_summary": {
                            "total_validations": 2,
                            "valid_count": 2,
                            "invalid_count": 0,
                            "uncertain_count": 0,
                            "not_found_count": 0,
                            "hallucination_rate": 0.0,
                        },
                        "hallucinations_detected": [],
                        "recommendations": [],
                        "analysis_metadata": {
                            "total_imports": 1,
                            "total_classes": 1,
                            "total_methods": 0,
                            "total_attributes": 0,
                            "total_functions": 0,
                        },
                        "libraries_analyzed": ["main"],
                    }
                    mock_reporter.generate_comprehensive_report.return_value = (
                        mock_report
                    )
                    mock_reporter_class.return_value = mock_reporter

                    check_result = await check_ai_script_hallucinations(ctx, tmp_path)
                    check_response = json.loads(check_result)
                    assert check_response["success"] is True
                    assert check_response["overall_confidence"] == 0.95

        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_concurrent_tool_usage(self):
        """Test concurrent usage of multiple MCP tools"""
        # Test that tools can be used concurrently without conflicts

        ctx1 = MockContext()
        ctx2 = MockContext()
        ctx3 = MockContext()

        # Set up mocks for all contexts
        for ctx in [ctx1, ctx2, ctx3]:
            mock_extractor = MagicMock()
            mock_validator = MagicMock()

            ctx.request_context.lifespan_context.knowledge_extractor = mock_extractor
            ctx.request_context.lifespan_context.knowledge_validator = mock_validator

            # Mock successful operations
            mock_extractor.search_graph = AsyncMock(
                return_value=[{"result": "success"}],
            )
            mock_extractor.analyze_repository = AsyncMock(
                return_value={"repository": "concurrent-test", "files_processed": 1},
            )
            mock_extractor.clear_repository_data = AsyncMock(
                return_value={"nodes_deleted": 0, "relationships_deleted": 0},
            )

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        # Run tools concurrently
        tasks = [
            query_knowledge_graph(ctx1, "MATCH (n) RETURN count(n)"),
            parse_github_repository(ctx2, "https://github.com/test/repo1.git"),
            query_knowledge_graph(ctx3, "MATCH (c:Class) RETURN c"),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            response = json.loads(result)
            assert response["success"] is True

    @pytest.mark.asyncio
    async def test_tool_performance_monitoring(self, mock_extractor_context):
        """Test performance characteristics of MCP tools"""
        ctx, mock_extractor = mock_extractor_context

        # Mock slow operations
        async def slow_search(query):
            await asyncio.sleep(0.1)  # Simulate processing time
            return [{"result": "data"}]

        mock_extractor.search_graph = slow_search

        os.environ["USE_KNOWLEDGE_GRAPH"] = "true"

        import time

        start_time = time.time()

        result = await query_knowledge_graph(ctx, "MATCH (n) RETURN n")

        end_time = time.time()
        execution_time = end_time - start_time

        # Verify result and performance
        response = json.loads(result)
        assert response["success"] is True

        # Should complete within reasonable time (including mock delay)
        assert execution_time < 1.0  # Should be much faster than 1 second

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test that all MCP tools handle errors consistently"""
        ctx = MockContext()

        # Test disabled functionality error format
        os.environ["USE_KNOWLEDGE_GRAPH"] = "false"

        results = []

        # Test check_ai_script_hallucinations
        result1 = await check_ai_script_hallucinations(ctx, "/fake/path.py")
        results.append(json.loads(result1))

        # Test query_knowledge_graph
        result2 = await query_knowledge_graph(ctx, "MATCH (n) RETURN n")
        results.append(json.loads(result2))

        # Test parse_github_repository
        result3 = await parse_github_repository(ctx, "https://github.com/test/repo.git")
        results.append(json.loads(result3))

        # All should have consistent error format
        for response in results:
            assert response["success"] is False
            assert "error" in response
            assert isinstance(response["error"], str)
            assert len(response["error"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
