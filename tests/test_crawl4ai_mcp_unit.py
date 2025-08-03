"""Unit tests for crawl4ai_mcp.py focused on improving coverage."""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawl4ai_mcp import (
    track_request, validate_neo4j_connection, format_neo4j_error,
    validate_script_path, validate_github_url, rerank_results,
    is_sitemap, is_txt, parse_sitemap, smart_chunk_markdown,
    extract_section_info, process_code_example
)


class TestHelperFunctions:
    """Test helper functions in crawl4ai_mcp.py"""
    
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
    
    def test_smart_chunk_markdown(self):
        """Test markdown chunking."""
        # Test basic chunking
        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        chunks = smart_chunk_markdown(text, chunk_size=20)
        assert len(chunks) > 0
        assert all(len(chunk) <= 20 for chunk in chunks)
        
        # Test with headers
        text_with_headers = "# Header 1\nContent 1\n## Header 2\nContent 2"
        chunks = smart_chunk_markdown(text_with_headers, chunk_size=30)
        assert len(chunks) > 0
        
        # Test empty text
        chunks = smart_chunk_markdown("", chunk_size=100)
        assert chunks == [""]
    
    def test_extract_section_info(self):
        """Test section info extraction."""
        # Test with headers
        chunk_with_header = "# Main Title\nSome content here"
        info = extract_section_info(chunk_with_header)
        assert "main_headers" in info
        assert "Main Title" in info["main_headers"]
        
        # Test without headers
        chunk_no_header = "Just some plain text content"
        info = extract_section_info(chunk_no_header)
        assert info["main_headers"] == []
        
        # Test with multiple headers
        chunk_multi = "# Header 1\n## Header 2\n### Header 3\nContent"
        info = extract_section_info(chunk_multi)
        assert len(info["main_headers"]) >= 2
    
    @patch('src.utils_refactored.create_embedding')
    def test_process_code_example(self, mock_create_embedding):
        """Test code example processing."""
        mock_create_embedding.return_value = [0.1] * 1536
        
        args = (
            "python",  # language
            "def hello(): return 'world'",  # code
            "https://example.com",  # url
            "Example description"  # description
        )
        
        result = process_code_example(args)
        
        assert result is not None
        assert result["language"] == "python"
        assert result["code"] == "def hello(): return 'world'"
        assert result["url"] == "https://example.com"
        assert "embedding" in result
        mock_create_embedding.assert_called_once()
    
    def test_validate_script_path(self):
        """Test script path validation."""
        # Test with non-existent file
        result = validate_script_path("/non/existent/path.py")
        assert result["valid"] is False
        assert "error" in result
        
        # Test with existing file (this test file)
        test_file = __file__
        result = validate_script_path(test_file)
        assert result["valid"] is True
        assert result["path"] == test_file
    
    def test_validate_github_url(self):
        """Test GitHub URL validation."""
        # Valid GitHub URLs
        result = validate_github_url("https://github.com/owner/repo")
        assert result["valid"] is True
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        
        result = validate_github_url("https://github.com/owner/repo.git")
        assert result["valid"] is True
        assert result["owner"] == "owner"
        assert result["repo"] == "repo"
        
        # Invalid URLs
        result = validate_github_url("https://example.com/not/github")
        assert result["valid"] is False
        assert "error" in result
        
        result = validate_github_url("not-a-url")
        assert result["valid"] is False
        assert "error" in result
    
    @patch('requests.get')
    def test_parse_sitemap(self, mock_get):
        """Test sitemap parsing."""
        # Mock sitemap XML response
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page1</loc>
            </url>
            <url>
                <loc>https://example.com/page2</loc>
            </url>
        </urlset>"""
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        urls = parse_sitemap("https://example.com/sitemap.xml")
        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls
        
        # Test error handling
        mock_get.side_effect = Exception("Network error")
        urls = parse_sitemap("https://example.com/sitemap.xml")
        assert urls == []
    
    def test_rerank_results(self):
        """Test result reranking."""
        # Mock CrossEncoder
        mock_model = Mock()
        mock_model.predict.return_value = [0.9, 0.5, 0.7]
        
        results = [
            {"id": "1", "content": "First result"},
            {"id": "2", "content": "Second result"},
            {"id": "3", "content": "Third result"}
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


class TestNeo4jFunctions:
    """Test Neo4j-related functions."""
    
    @patch('neo4j.GraphDatabase.driver')
    def test_validate_neo4j_connection_success(self, mock_driver):
        """Test successful Neo4j connection validation."""
        mock_session = Mock()
        mock_session.run.return_value = Mock()
        mock_driver_instance = Mock()
        mock_driver_instance.session.return_value.__enter__ = Mock(return_value=mock_session)
        mock_driver_instance.session.return_value.__exit__ = Mock(return_value=None)
        mock_driver.return_value = mock_driver_instance
        
        with patch.dict('os.environ', {
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USER': 'neo4j',
            'NEO4J_PASSWORD': 'password'
        }):
            result = validate_neo4j_connection()
            assert result is True
    
    def test_validate_neo4j_connection_no_env(self):
        """Test Neo4j connection validation without env vars."""
        with patch.dict('os.environ', {}, clear=True):
            result = validate_neo4j_connection()
            assert result is False
    
    @patch('neo4j.GraphDatabase.driver')
    def test_validate_neo4j_connection_error(self, mock_driver):
        """Test Neo4j connection validation with error."""
        mock_driver.side_effect = Exception("Connection failed")
        
        with patch.dict('os.environ', {
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USER': 'neo4j',
            'NEO4J_PASSWORD': 'password'
        }):
            result = validate_neo4j_connection()
            assert result is False
    
    def test_format_neo4j_error(self):
        """Test Neo4j error formatting."""
        # Test with Neo4j ServiceUnavailable error
        error = Exception("Unable to connect to localhost:7687")
        formatted = format_neo4j_error(error)
        assert "localhost:7687" in formatted
        
        # Test with authentication error
        auth_error = Exception("authentication failed")
        formatted = format_neo4j_error(auth_error)
        assert "authentication" in formatted.lower()
        
        # Test with generic error
        generic_error = Exception("Something went wrong")
        formatted = format_neo4j_error(generic_error)
        assert "Something went wrong" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])