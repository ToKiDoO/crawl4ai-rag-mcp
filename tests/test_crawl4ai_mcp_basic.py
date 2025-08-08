"""Basic unit tests for crawl4ai_mcp.py to improve coverage."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawl4ai_mcp import (
    format_neo4j_error,
    is_sitemap,
    is_txt,
    rerank_results,
    track_request,
    validate_github_url,
    validate_neo4j_connection,
    validate_script_path,
)


class TestBasicFunctions:
    """Test basic helper functions."""

    def test_track_request(self):
        """Test request tracking function."""
        # Simply call it to ensure it works
        track_request("test_tool")
        # Function has no return value, just ensure no errors

    def test_is_sitemap(self):
        """Test sitemap URL detection."""
        assert is_sitemap("https://example.com/sitemap.xml") is True
        assert is_sitemap("https://example.com/sitemap_index.xml") is True
        assert is_sitemap("https://example.com/page.html") is False
        assert is_sitemap("https://example.com/") is False

    def test_is_txt(self):
        """Test text file URL detection."""
        assert is_txt("https://example.com/file.txt") is True
        assert is_txt("https://example.com/robots.txt") is True
        assert is_txt("https://example.com/file.html") is False
        assert is_txt("https://example.com/") is False

    def test_validate_script_path(self):
        """Test script path validation."""
        # Test with non-existent file
        result = validate_script_path("/non/existent/path.py")
        assert result["valid"] is False
        assert "not found" in result["error"]

        # Test with empty path
        result = validate_script_path("")
        assert result["valid"] is False
        assert "required" in result["error"]

        # Test with non-python file (create it first)
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_txt = f.name

        try:
            result = validate_script_path(temp_txt)
            assert result["valid"] is False
            assert "Python" in result["error"]
        finally:
            os.unlink(temp_txt)

        # Test with existing Python file (this test file)
        test_file = __file__
        result = validate_script_path(test_file)
        assert result["valid"] is True

    def test_validate_github_url(self):
        """Test GitHub URL validation."""
        # Valid GitHub URLs
        result = validate_github_url("https://github.com/owner/repo")
        assert result["valid"] is True
        assert result["repo_name"] == "repo"

        result = validate_github_url("https://github.com/owner/repo.git")
        assert result["valid"] is True
        assert result["repo_name"] == "repo"

        # Invalid URLs
        result = validate_github_url("https://example.com/not/github")
        assert result["valid"] is False
        assert "GitHub" in result["error"]

        result = validate_github_url("not-a-url")
        assert result["valid"] is False

        # Empty URL
        result = validate_github_url("")
        assert result["valid"] is False
        assert "required" in result["error"]

    def test_rerank_results(self):
        """Test result reranking."""
        # Mock CrossEncoder
        mock_model = Mock()
        mock_model.predict.return_value = [0.9, 0.5, 0.7]

        results = [
            {"id": "1", "content": "First result"},
            {"id": "2", "content": "Second result"},
            {"id": "3", "content": "Third result"},
        ]

        reranked = rerank_results(mock_model, "query", results)

        # Should be sorted by score descending
        assert len(reranked) == 3
        assert reranked[0]["id"] == "1"  # Highest score 0.9
        assert reranked[1]["id"] == "3"  # Score 0.7
        assert reranked[2]["id"] == "2"  # Lowest score 0.5

        # Test empty results
        reranked_empty = rerank_results(mock_model, "query", [])
        assert reranked_empty == []

    def test_format_neo4j_error(self):
        """Test Neo4j error formatting."""
        # Test with various error messages
        error = Exception("Unable to connect to localhost:7687")
        formatted = format_neo4j_error(error)
        assert "connect" in formatted.lower()

        auth_error = Exception(
            "The client is unauthorized due to authentication failure",
        )
        formatted = format_neo4j_error(auth_error)
        assert "authentication" in formatted.lower()

        database_error = Exception("Database 'neo4j' not found")
        formatted = format_neo4j_error(database_error)
        assert "database" in formatted.lower()

        generic_error = Exception("Something went wrong")
        formatted = format_neo4j_error(generic_error)
        assert "Something went wrong" in formatted


class TestNeo4jValidation:
    """Test Neo4j connection validation."""

    def test_validate_neo4j_connection_no_env(self):
        """Test Neo4j connection validation without env vars."""
        with patch.dict("os.environ", {}, clear=True):
            result = validate_neo4j_connection()
            assert result is False

    @patch("neo4j.GraphDatabase.driver")
    def test_validate_neo4j_connection_success(self, mock_driver):
        """Test successful Neo4j connection validation."""
        # Mock successful connection
        mock_session = Mock()
        mock_session.run.return_value = Mock()
        mock_driver_instance = Mock()
        mock_driver_instance.session.return_value.__enter__ = Mock(
            return_value=mock_session,
        )
        mock_driver_instance.session.return_value.__exit__ = Mock(return_value=None)
        mock_driver_instance.close = Mock()
        mock_driver.return_value = mock_driver_instance

        with patch.dict(
            "os.environ",
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            result = validate_neo4j_connection()
            assert result is True

    def test_validate_neo4j_connection_with_partial_env(self):
        """Test Neo4j connection validation with partial env vars."""
        # Missing password
        with patch.dict(
            "os.environ",
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                # Missing NEO4J_PASSWORD
            },
            clear=True,
        ):
            result = validate_neo4j_connection()
            assert result is False

        # Missing user
        with patch.dict(
            "os.environ",
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_PASSWORD": "password",
                # Missing NEO4J_USER
            },
            clear=True,
        ):
            result = validate_neo4j_connection()
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
