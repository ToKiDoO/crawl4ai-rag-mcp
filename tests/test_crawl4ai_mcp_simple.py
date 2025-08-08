"""
Simple tests for crawl4ai_mcp.py to improve coverage.
Focus on testing individual functions without complex mocking.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import functions to test
from crawl4ai_mcp import (
    extract_section_info,
    format_neo4j_error,
    is_sitemap,
    is_txt,
    parse_sitemap,
    rerank_results,
    smart_chunk_markdown,
    track_request,
    validate_github_url,
    validate_neo4j_connection,
    validate_script_path,
)


class TestHelperFunctions:
    """Test simple helper functions"""

    def test_track_request(self):
        """Test request tracking decorator"""

        # Create a simple function to decorate
        @track_request("test_tool")
        def test_func():
            return "result"

        # Call the function
        result = test_func()
        assert result == "result"

    def test_is_sitemap(self):
        """Test sitemap URL detection"""
        assert is_sitemap("https://example.com/sitemap.xml")
        assert is_sitemap("https://example.com/sitemap_index.xml")
        assert is_sitemap("https://example.com/path/sitemap.xml")
        assert not is_sitemap("https://example.com/page.html")
        assert not is_sitemap("https://example.com/robots.txt")

    def test_is_txt(self):
        """Test text file URL detection"""
        assert is_txt("https://example.com/robots.txt")
        assert is_txt("https://example.com/llms.txt")
        assert is_txt("https://example.com/path/file.txt")
        assert not is_txt("https://example.com/page.html")
        assert not is_txt("https://example.com/sitemap.xml")

    def test_validate_github_url(self):
        """Test GitHub URL validation"""
        # Valid URLs
        result = validate_github_url("https://github.com/user/repo")
        assert result["valid"] is True
        assert result["owner"] == "user"
        assert result["repo"] == "repo"

        result = validate_github_url("https://github.com/org-name/repo-name")
        assert result["valid"] is True
        assert result["owner"] == "org-name"
        assert result["repo"] == "repo-name"

        # Invalid URLs
        result = validate_github_url("https://gitlab.com/user/repo")
        assert result["valid"] is False
        assert "Invalid GitHub URL" in result["error"]

        result = validate_github_url("not-a-url")
        assert result["valid"] is False
        assert "Invalid GitHub URL" in result["error"]

        result = validate_github_url("https://github.com/user")
        assert result["valid"] is False
        assert "Invalid GitHub URL" in result["error"]

    def test_validate_script_path(self):
        """Test script path validation"""
        # Test with existing file
        with patch("os.path.exists", return_value=True):
            with patch("os.path.isfile", return_value=True):
                result = validate_script_path("/path/to/script.py")
                assert result["valid"] is True

        # Test with non-existent file
        with patch("os.path.exists", return_value=False):
            result = validate_script_path("/path/to/nonexistent.py")
            assert result["valid"] is False
            assert "does not exist" in result["error"]

        # Test with directory instead of file
        with patch("os.path.exists", return_value=True):
            with patch("os.path.isfile", return_value=False):
                result = validate_script_path("/path/to/directory")
                assert result["valid"] is False
                assert "not a file" in result["error"]

        # Test with non-Python file
        with patch("os.path.exists", return_value=True):
            with patch("os.path.isfile", return_value=True):
                result = validate_script_path("/path/to/script.txt")
                assert result["valid"] is False
                assert "Python file" in result["error"]

    def test_smart_chunk_markdown(self):
        """Test markdown chunking"""
        # Test simple text
        text = "This is a simple text that should not be chunked."
        chunks = smart_chunk_markdown(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

        # Test text that needs chunking
        text = "A" * 150  # 150 characters
        chunks = smart_chunk_markdown(text, chunk_size=100)
        assert len(chunks) == 2
        assert len(chunks[0]) <= 100
        assert len(chunks[1]) <= 100

        # Test with markdown headers
        text = (
            "# Header 1\nContent 1\n\n## Header 2\nContent 2\n\n### Header 3\nContent 3"
        )
        chunks = smart_chunk_markdown(text, chunk_size=50)
        assert len(chunks) > 1
        # Each chunk should be within size limit
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_extract_section_info(self):
        """Test section info extraction"""
        # Test with header
        chunk = "# Main Title\nThis is the content of the section."
        info = extract_section_info(chunk)
        assert info["header"] == "Main Title"
        assert info["level"] == 1
        assert "Main Title" in info["summary"]

        # Test with subheader
        chunk = "## Subsection\nMore detailed content here."
        info = extract_section_info(chunk)
        assert info["header"] == "Subsection"
        assert info["level"] == 2

        # Test without header
        chunk = "Just plain text without any header."
        info = extract_section_info(chunk)
        assert info["header"] == ""
        assert info["level"] == 0
        assert info["summary"] == "Content without header"

    def test_format_neo4j_error(self):
        """Test Neo4j error formatting"""
        # Test with generic exception
        error = Exception("Connection failed")
        result = format_neo4j_error(error)
        assert "Neo4j connection error" in result
        assert "Connection failed" in result

        # Test with specific error message
        error = Exception("Unable to connect to localhost:7687")
        result = format_neo4j_error(error)
        assert "localhost:7687" in result

    @patch("neo4j.GraphDatabase.driver")
    def test_validate_neo4j_connection(self, mock_driver):
        """Test Neo4j connection validation"""
        # Test successful connection
        mock_session = MagicMock()
        mock_driver.return_value.session.return_value = mock_session
        mock_session.run.return_value.single.return_value = [1]

        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USERNAME": "neo4j",
                "NEO4J_PASSWORD": "password",
            },
        ):
            result = validate_neo4j_connection()
            assert result is True

        # Test failed connection
        mock_driver.side_effect = Exception("Connection failed")
        result = validate_neo4j_connection()
        assert result is False

    def test_rerank_results(self):
        """Test result reranking"""
        # Mock cross encoder model
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.5, 0.7]

        # Test data
        query = "test query"
        results = [
            {"content": "very relevant content", "id": 1},
            {"content": "not so relevant", "id": 2},
            {"content": "somewhat relevant", "id": 3},
        ]

        # Rerank
        reranked = rerank_results(mock_model, query, results)

        # Verify order (highest score first)
        assert reranked[0]["id"] == 1  # 0.9 score
        assert reranked[1]["id"] == 3  # 0.7 score
        assert reranked[2]["id"] == 2  # 0.5 score

        # Verify rerank scores are added
        assert "rerank_score" in reranked[0]
        assert reranked[0]["rerank_score"] == 0.9

    @patch("requests.get")
    def test_parse_sitemap(self, mock_get):
        """Test sitemap parsing"""
        # Mock sitemap response
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page1</loc>
            </url>
            <url>
                <loc>https://example.com/page2</loc>
            </url>
        </urlset>"""
        mock_get.return_value = mock_response

        # Parse sitemap
        urls = parse_sitemap("https://example.com/sitemap.xml")

        # Verify
        assert len(urls) == 2
        assert "https://example.com/page1" in urls
        assert "https://example.com/page2" in urls

        # Test error handling
        mock_get.side_effect = Exception("Network error")
        urls = parse_sitemap("https://example.com/sitemap.xml")
        assert urls == []


class TestSearchFunction:
    """Test the search function"""

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_search_with_results(self, mock_httpx):
        """Test search with successful results"""
        # Mock context
        from dataclasses import dataclass

        @dataclass
        class MockLifespanContext:
            database_client: object = None
            embedding_service: object = None
            crawler: object = None
            reranking_model: object = None

        @dataclass
        class MockRequestContext:
            lifespan_context: MockLifespanContext = MockLifespanContext()

        @dataclass
        class MockContext:
            request_context: MockRequestContext = MockRequestContext()

        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "results": [
                {"url": "https://example.com/page1", "title": "Page 1"},
                {"url": "https://example.com/page2", "title": "Page 2"},
            ],
        }
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        # Mock crawler and database
        mock_crawler = AsyncMock()
        mock_db = AsyncMock()

        ctx = MockContext()
        ctx.request_context.lifespan_context.crawler = mock_crawler
        ctx.request_context.lifespan_context.database_client = mock_db

        # Import and test
        from crawl4ai_mcp import search

        with patch("crawl4ai_mcp.scrape_urls", new_callable=AsyncMock) as mock_scrape:
            mock_scrape.return_value = json.dumps(
                {
                    "success": True,
                    "results": [
                        {"url": "https://example.com/page1", "content": "Content 1"},
                        {"url": "https://example.com/page2", "content": "Content 2"},
                    ],
                },
            )

            result = await search(ctx, query="test query", num_results=2)

        # Verify
        result_json = json.loads(result)
        assert result_json["success"] is True
        assert result_json["query"] == "test query"
        assert len(result_json["results"]) == 2
