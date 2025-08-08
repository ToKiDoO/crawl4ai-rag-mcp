"""
Unit tests for MCP tool context wrappers in Neo4j-Qdrant integration.

Tests the wrapper functions that provide context-aware integration between
MCP tools, validated search service, and the underlying database operations.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tools import (
    perform_rag_query_wrapper,
    search_code_examples_wrapper,
)


class TestMCPToolWrappers:
    """Test MCP tool wrapper functions for Neo4j-Qdrant integration."""

    @pytest.fixture
    def mock_database_factory(self):
        """Mock database factory with Qdrant adapter."""
        with patch("tools.get_database_adapter") as mock_factory:
            mock_adapter = AsyncMock()
            mock_adapter.search_crawled_pages = AsyncMock()
            mock_adapter.search_code_examples = AsyncMock()
            mock_factory.return_value = mock_adapter
            yield mock_adapter

    @pytest.fixture
    def mock_validated_search_service(self):
        """Mock ValidatedCodeSearchService."""
        with patch("tools.ValidatedCodeSearchService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search_and_validate_code = AsyncMock()
            mock_service_class.return_value = mock_service
            yield mock_service

    @pytest.mark.asyncio
    async def test_perform_rag_query_wrapper_basic(self, mock_database_factory):
        """Test basic RAG query wrapper functionality."""
        # Mock successful database response
        mock_database_factory.search_crawled_pages.return_value = [
            {
                "content": "Example Python function definition",
                "metadata": {"source": "example.py", "type": "function"},
                "similarity": 0.95,
            },
        ]

        result = await perform_rag_query_wrapper(
            query="Python function example",
            source=None,
            match_count=5,
        )

        # Verify database was called correctly
        mock_database_factory.search_crawled_pages.assert_called_once()
        call_args = mock_database_factory.search_crawled_pages.call_args
        assert call_args[1]["match_count"] == 5

        # Verify result structure
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert "results" in result_data
        assert len(result_data["results"]) == 1
        assert result_data["results"][0]["similarity"] == 0.95

    @pytest.mark.asyncio
    async def test_perform_rag_query_wrapper_with_source_filter(
        self, mock_database_factory
    ):
        """Test RAG query wrapper with source filtering."""
        mock_database_factory.search_crawled_pages.return_value = []

        result = await perform_rag_query_wrapper(
            query="Django models",
            source="django-docs",
            match_count=10,
        )

        # Verify source filter was applied
        call_args = mock_database_factory.search_crawled_pages.call_args
        assert call_args[1]["source_filter"] == "django-docs"
        assert call_args[1]["match_count"] == 10

        result_data = json.loads(result)
        assert result_data["results"] == []

    @pytest.mark.asyncio
    async def test_perform_rag_query_wrapper_error_handling(
        self, mock_database_factory
    ):
        """Test RAG query wrapper error handling."""
        # Mock database error
        mock_database_factory.search_crawled_pages.side_effect = Exception(
            "Database connection failed"
        )

        result = await perform_rag_query_wrapper(
            query="test query",
            source=None,
            match_count=5,
        )

        result_data = json.loads(result)
        assert "error" in result_data
        assert "Database connection failed" in result_data["error"]

    @pytest.mark.asyncio
    async def test_search_code_examples_wrapper_basic(self, mock_database_factory):
        """Test basic code examples search wrapper."""
        # Mock successful database response
        mock_database_factory.search_code_examples.return_value = [
            {
                "content": "class ExampleClass:\n    def __init__(self):\n        pass",
                "metadata": {
                    "code_type": "class",
                    "class_name": "ExampleClass",
                    "repository_name": "example-repo",
                },
                "similarity": 0.88,
            },
        ]

        result = await search_code_examples_wrapper(
            query="Python class example",
            source_id=None,
            match_count=3,
        )

        # Verify database was called correctly
        mock_database_factory.search_code_examples.assert_called_once()
        call_args = mock_database_factory.search_code_examples.call_args
        assert call_args[1]["match_count"] == 3

        # Verify result structure
        result_data = json.loads(result)
        assert "results" in result_data
        assert len(result_data["results"]) == 1
        assert result_data["results"][0]["metadata"]["code_type"] == "class"

    @pytest.mark.asyncio
    async def test_search_code_examples_wrapper_with_validated_search(
        self, mock_validated_search_service, mock_database_factory
    ):
        """Test code examples wrapper with Neo4j validation enabled."""
        # Mock Neo4j environment variables
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_PASSWORD": "test_password",
            },
        ):
            # Mock validated search response
            mock_validated_search_service.search_and_validate_code.return_value = {
                "success": True,
                "query": "authenticated method",
                "results": [
                    {
                        "content": "def authenticate(self, username, password):\n    return True",
                        "metadata": {
                            "code_type": "method",
                            "method_name": "authenticate",
                            "class_name": "AuthService",
                        },
                        "similarity": 0.92,
                        "validation": {
                            "is_valid": True,
                            "confidence_score": 0.85,
                            "validation_checks": [
                                {
                                    "check": "method_exists",
                                    "passed": True,
                                    "weight": 0.7,
                                },
                            ],
                            "neo4j_validated": True,
                        },
                    },
                ],
                "validation_summary": {
                    "total_found": 5,
                    "validated": 1,
                    "high_confidence": 1,
                    "neo4j_available": True,
                },
            }

            result = await search_code_examples_wrapper(
                query="authenticated method",
                source_id="auth-service-repo",
                match_count=5,
            )

            # Verify validated search was used
            mock_validated_search_service.search_and_validate_code.assert_called_once()
            call_args = mock_validated_search_service.search_and_validate_code.call_args
            assert call_args[1]["query"] == "authenticated method"
            assert call_args[1]["source_filter"] == "auth-service-repo"
            assert call_args[1]["match_count"] == 5

            # Verify validated result structure
            result_data = json.loads(result)
            assert "validation_summary" in result_data
            assert result_data["validation_summary"]["neo4j_available"] is True
            assert len(result_data["results"]) == 1
            assert result_data["results"][0]["validation"]["is_valid"] is True

    @pytest.mark.asyncio
    async def test_search_code_examples_wrapper_neo4j_unavailable(
        self, mock_database_factory
    ):
        """Test code examples wrapper fallback when Neo4j is unavailable."""
        # Mock no Neo4j environment
        with patch.dict(os.environ, {}, clear=True):
            mock_database_factory.search_code_examples.return_value = [
                {
                    "content": "def example_function():\n    pass",
                    "metadata": {"code_type": "function"},
                    "similarity": 0.75,
                },
            ]

            result = await search_code_examples_wrapper(
                query="example function",
                source_id=None,
                match_count=5,
            )

            # Should fall back to regular database search
            mock_database_factory.search_code_examples.assert_called_once()

            result_data = json.loads(result)
            assert (
                "validation_summary" not in result_data
            )  # No validation when Neo4j unavailable
            assert len(result_data["results"]) == 1

    @pytest.mark.asyncio
    async def test_search_code_examples_wrapper_validation_error(
        self, mock_validated_search_service
    ):
        """Test code examples wrapper handling validation service errors."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_PASSWORD": "test_password",
            },
        ):
            # Mock validation service error
            mock_validated_search_service.search_and_validate_code.side_effect = (
                Exception("Neo4j connection failed")
            )

            result = await search_code_examples_wrapper(
                query="test query",
                source_id=None,
                match_count=5,
            )

            result_data = json.loads(result)
            assert "error" in result_data
            assert "Neo4j connection failed" in result_data["error"]

    @pytest.mark.asyncio
    async def test_wrapper_performance_monitoring(self, mock_database_factory):
        """Test that wrapper functions include performance monitoring."""
        mock_database_factory.search_crawled_pages.return_value = []

        # Mock performance tracking
        with patch("tools.track_request") as mock_track:
            # The decorator should be applied to wrapper functions
            result = await perform_rag_query_wrapper(
                query="performance test",
                source=None,
                match_count=1,
            )

            # Verify operation completed successfully
            result_data = json.loads(result)
            assert "results" in result_data

    @pytest.mark.asyncio
    async def test_wrapper_input_validation(self, mock_database_factory):
        """Test wrapper input validation and sanitization."""
        mock_database_factory.search_crawled_pages.return_value = []

        # Test empty query handling
        result = await perform_rag_query_wrapper(
            query="",
            source=None,
            match_count=5,
        )

        result_data = json.loads(result)
        # Should handle empty query gracefully
        assert "results" in result_data

        # Test invalid match_count
        result = await perform_rag_query_wrapper(
            query="test",
            source=None,
            match_count=0,
        )

        result_data = json.loads(result)
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_wrapper_concurrent_requests(self, mock_database_factory):
        """Test wrapper handling of concurrent requests."""
        mock_database_factory.search_crawled_pages.return_value = [
            {"content": "result", "similarity": 0.8},
        ]

        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            task = perform_rag_query_wrapper(
                query=f"concurrent query {i}",
                source=None,
                match_count=1,
            )
            tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks)

        # All requests should complete successfully
        assert len(results) == 5
        for result in results:
            result_data = json.loads(result)
            assert "results" in result_data
            assert len(result_data["results"]) == 1

        # Database should have been called 5 times
        assert mock_database_factory.search_crawled_pages.call_count == 5


class TestWrapperIntegration:
    """Test integration aspects of wrapper functions."""

    @pytest.fixture
    def integration_environment(self):
        """Set up integration test environment."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "test_password",
                "QDRANT_HOST": "localhost",
                "QDRANT_PORT": "6333",
            },
        ):
            yield

    @pytest.mark.asyncio
    async def test_end_to_end_code_search_flow(self, integration_environment):
        """Test complete code search flow through wrappers."""
        with (
            patch("tools.get_database_adapter") as mock_db,
            patch("tools.ValidatedCodeSearchService") as mock_service_class,
        ):
            # Mock database adapter
            mock_adapter = AsyncMock()
            mock_db.return_value = mock_adapter

            # Mock validated search service
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # Mock validated search response
            mock_service.search_and_validate_code.return_value = {
                "success": True,
                "query": "JWT authentication",
                "results": [
                    {
                        "content": "def verify_jwt(token: str) -> bool:\n    return jwt.decode(token, key)",
                        "metadata": {
                            "code_type": "function",
                            "function_name": "verify_jwt",
                            "repository_name": "auth-lib",
                        },
                        "similarity": 0.94,
                        "validation": {
                            "is_valid": True,
                            "confidence_score": 0.91,
                            "validation_checks": [
                                {
                                    "check": "repository_exists",
                                    "passed": True,
                                    "weight": 0.3,
                                },
                                {
                                    "check": "function_exists",
                                    "passed": True,
                                    "weight": 0.7,
                                },
                            ],
                            "neo4j_validated": True,
                        },
                    },
                ],
                "validation_summary": {
                    "total_found": 3,
                    "validated": 1,
                    "high_confidence": 1,
                    "neo4j_available": True,
                },
            }

            # Execute search
            result = await search_code_examples_wrapper(
                query="JWT authentication",
                source_id="auth-lib",
                match_count=5,
            )

            # Verify complete flow
            result_data = json.loads(result)

            # Check that validated search was used
            mock_service.search_and_validate_code.assert_called_once()

            # Verify result structure includes validation
            assert "validation_summary" in result_data
            assert result_data["validation_summary"]["neo4j_available"] is True
            assert result_data["results"][0]["validation"]["confidence_score"] == 0.91
            assert result_data["results"][0]["validation"]["neo4j_validated"] is True

    @pytest.mark.asyncio
    async def test_wrapper_fallback_mechanism(self, integration_environment):
        """Test wrapper fallback when Neo4j validation fails."""
        with (
            patch("tools.get_database_adapter") as mock_db,
            patch("tools.ValidatedCodeSearchService") as mock_service_class,
        ):
            mock_adapter = AsyncMock()
            mock_db.return_value = mock_adapter

            # Mock validation service that fails
            mock_service_class.side_effect = Exception("Neo4j unavailable")

            # Mock fallback to regular search
            mock_adapter.search_code_examples.return_value = [
                {
                    "content": "def fallback_function():\n    pass",
                    "metadata": {"code_type": "function"},
                    "similarity": 0.72,
                },
            ]

            result = await search_code_examples_wrapper(
                query="fallback test",
                source_id=None,
                match_count=3,
            )

            # Should fall back to regular database search
            mock_adapter.search_code_examples.assert_called_once()

            result_data = json.loads(result)
            assert len(result_data["results"]) == 1
            assert (
                "validation_summary" not in result_data
            )  # No validation in fallback mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
