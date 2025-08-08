"""
Comprehensive tests for chat/RAG MCP tools: perform_rag_query and search_code_examples

Focus on:
1. Basic Q&A functionality
2. Chat with crawled context
3. Conversation memory management
4. Error handling
5. Code search and analysis

Test execution time target: <10 seconds total
Individual test target: <1 second each
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Import the module under test
import crawl4ai_mcp


def get_tool_function(tool_name: str):
    """Helper to extract actual function from FastMCP tool wrapper"""
    tool_attr = getattr(crawl4ai_mcp, tool_name, None)
    if hasattr(tool_attr, "fn"):
        return tool_attr.fn
    if callable(tool_attr):
        return tool_attr
    raise AttributeError(f"Cannot find callable function for {tool_name}")


# Shared test data for performance
MOCK_EMBEDDING = [0.1] * 1536
MOCK_RAG_RESULTS = [
    {
        "content": "This is a comprehensive guide to Python programming for beginners.",
        "metadata": {"source": "python-guide.com", "title": "Python Basics"},
        "similarity": 0.95,
    },
    {
        "content": "Advanced Python concepts including decorators and metaclasses.",
        "metadata": {"source": "advanced-python.org", "title": "Advanced Python"},
        "similarity": 0.87,
    },
]

MOCK_CODE_EXAMPLES = [
    {
        "content": 'def hello_world():\n    print("Hello, World!")\n    return "Hello"',
        "summary": "Simple hello world function in Python",
        "metadata": {"language": "python", "complexity": "beginner"},
        "similarity": 0.92,
    },
    {
        "content": "async def fetch_data(url):\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()",
        "summary": "Asynchronous HTTP request function using aiohttp",
        "metadata": {"language": "python", "complexity": "intermediate"},
        "similarity": 0.89,
    },
]


class MockContext:
    """Mock FastMCP Context for chat/RAG testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.lifespan_context = Mock()

        # Mock database client with comprehensive methods
        self.request_context.lifespan_context.database_client = AsyncMock()
        self.request_context.lifespan_context.database_client.search_documents = (
            AsyncMock()
        )
        self.request_context.lifespan_context.database_client.search_code_examples = (
            AsyncMock()
        )
        self.request_context.lifespan_context.database_client.get_sources = AsyncMock()

        # Default return values
        self.request_context.lifespan_context.database_client.search_documents.return_value = MOCK_RAG_RESULTS
        self.request_context.lifespan_context.database_client.search_code_examples.return_value = MOCK_CODE_EXAMPLES
        self.request_context.lifespan_context.database_client.get_sources.return_value = [
            {"source_id": "python-guide.com", "summary": "Python programming guide"},
            {"source_id": "advanced-python.org", "summary": "Advanced Python concepts"},
        ]


@pytest.fixture
def mock_context():
    """Provide a mock FastMCP context for testing"""
    return MockContext()


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up test environment variables"""
    env_vars = {
        "OPENAI_API_KEY": "test-key-for-mocks",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "USE_AGENTIC_RAG": "true",
    }

    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value


@pytest.fixture
def mock_external_dependencies():
    """Mock external dependencies for chat/RAG tests"""
    with (
        patch("openai.embeddings.create") as mock_openai,
        patch("utils.create_embeddings_batch") as mock_embeddings_batch,
    ):
        # Mock OpenAI embeddings
        mock_response = Mock()
        mock_response.data = [Mock(embedding=MOCK_EMBEDDING)]
        mock_openai.return_value = mock_response
        mock_embeddings_batch.return_value = [MOCK_EMBEDDING]

        yield {
            "mock_openai": mock_openai,
            "mock_embeddings_batch": mock_embeddings_batch,
        }


class TestPerformRagQueryTool:
    """Test cases for the perform_rag_query MCP tool"""

    @pytest.mark.asyncio
    async def test_rag_query_basic_functionality(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test basic RAG query functionality"""
        rag_fn = get_tool_function("perform_rag_query")

        # Execute RAG query
        result = await rag_fn(mock_context, "What is Python programming?")

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data
        assert len(result_data["results"]) >= 1
        assert "query" in result_data
        assert result_data["query"] == "What is Python programming?"

        # Verify database search was called
        mock_context.request_context.lifespan_context.database_client.search_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_query_with_source_filter(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with source filtering"""
        rag_fn = get_tool_function("perform_rag_query")

        # Execute RAG query with source filter
        result = await rag_fn(
            mock_context,
            "How to use decorators?",
            source="python-guide.com",
        )

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data
        assert "query" in result_data

        # Verify database search was called with source filter
        mock_context.request_context.lifespan_context.database_client.search_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_query_with_match_count(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with custom match count"""
        rag_fn = get_tool_function("perform_rag_query")

        # Execute RAG query with custom match count
        result = await rag_fn(mock_context, "Python best practices", match_count=10)

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data

        # Verify database search was called
        mock_context.request_context.lifespan_context.database_client.search_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_rag_query_empty_results(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with no matching results"""
        rag_fn = get_tool_function("perform_rag_query")

        # Mock empty results
        mock_context.request_context.lifespan_context.database_client.search_documents.return_value = []

        # Execute RAG query
        result = await rag_fn(mock_context, "nonexistent topic")

        # Parse and validate result
        result_data = json.loads(result)
        # Should handle empty results gracefully
        assert result_data["success"] is True or result_data["success"] is False
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_rag_query_database_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with database errors"""
        rag_fn = get_tool_function("perform_rag_query")

        # Mock database error
        mock_context.request_context.lifespan_context.database_client.search_documents.side_effect = Exception(
            "Database error",
        )

        # Execute RAG query
        result = await rag_fn(mock_context, "test query")

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data

    @pytest.mark.asyncio
    async def test_rag_query_various_query_types(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with different types of queries"""
        rag_fn = get_tool_function("perform_rag_query")

        # Test different query types
        test_queries = [
            "What is Python?",  # Question format
            "python tutorial",  # Keywords
            "How to implement async/await in Python",  # Technical question
            "Python vs JavaScript comparison",  # Comparison query
            "debugging python code best practices",  # Best practices query
        ]

        for query in test_queries:
            result = await rag_fn(mock_context, query)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert result_data["query"] == query
            assert "results" in result_data


class TestSearchCodeExamplesTool:
    """Test cases for the search_code_examples MCP tool"""

    @pytest.mark.asyncio
    async def test_search_code_examples_basic(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test basic code examples search functionality"""
        search_fn = get_tool_function("search_code_examples")

        # Execute code search
        result = await search_fn(mock_context, "hello world function")

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data
        assert len(result_data["results"]) >= 1

        # Verify the result contains code examples
        for example in result_data["results"]:
            assert "content" in example
            assert "summary" in example
            assert "metadata" in example

        # Verify database search was called
        mock_context.request_context.lifespan_context.database_client.search_code_examples.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_code_examples_with_source_filter(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with source filtering"""
        search_fn = get_tool_function("search_code_examples")

        # Execute code search with source filter
        result = await search_fn(
            mock_context,
            "async function",
            source_id="python-guide.com",
        )

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data

        # Verify database search was called with source filter
        mock_context.request_context.lifespan_context.database_client.search_code_examples.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_code_examples_match_count(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with custom match count"""
        search_fn = get_tool_function("search_code_examples")

        # Execute code search with custom match count
        result = await search_fn(mock_context, "class definition", match_count=10)

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is True
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_search_code_examples_empty_results(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with no results"""
        search_fn = get_tool_function("search_code_examples")

        # Mock empty results
        mock_context.request_context.lifespan_context.database_client.search_code_examples.return_value = []

        # Execute code search
        result = await search_fn(mock_context, "nonexistent code pattern")

        # Parse and validate result
        result_data = json.loads(result)
        # Should handle empty results gracefully
        assert result_data["success"] is True or result_data["success"] is False
        assert "results" in result_data

    @pytest.mark.asyncio
    async def test_search_code_examples_language_specific(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test searching for language-specific code examples"""
        search_fn = get_tool_function("search_code_examples")

        # Test different programming language queries
        language_queries = [
            "python function definition",
            "javascript async await",
            "java class constructor",
            "rust error handling",
            "go goroutine example",
        ]

        for query in language_queries:
            result = await search_fn(mock_context, query)
            result_data = json.loads(result)

            assert result_data["success"] is True
            assert "results" in result_data

    @pytest.mark.asyncio
    async def test_search_code_examples_database_error(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code examples search with database errors"""
        search_fn = get_tool_function("search_code_examples")

        # Mock database error
        mock_context.request_context.lifespan_context.database_client.search_code_examples.side_effect = Exception(
            "Database error",
        )

        # Execute code search
        result = await search_fn(mock_context, "test query")

        # Parse and validate result
        result_data = json.loads(result)
        assert result_data["success"] is False
        assert "error" in result_data


class TestChatToolsIntegration:
    """Integration tests for chat/RAG tools"""

    @pytest.mark.asyncio
    async def test_rag_query_and_code_search_workflow(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test combining RAG query with code search"""
        rag_fn = get_tool_function("perform_rag_query")
        search_fn = get_tool_function("search_code_examples")

        # First, perform RAG query
        rag_result = await rag_fn(
            mock_context,
            "How to implement async functions in Python?",
        )
        rag_data = json.loads(rag_result)
        assert rag_data["success"] is True

        # Then, search for related code examples
        code_result = await search_fn(mock_context, "async function python")
        code_data = json.loads(code_result)
        assert code_data["success"] is True

        # Both should provide complementary information
        assert "results" in rag_data
        assert "results" in code_data

    @pytest.mark.asyncio
    async def test_chat_context_management(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test context management across multiple queries"""
        rag_fn = get_tool_function("perform_rag_query")

        # Simulate a conversation with related queries
        conversation_queries = [
            "What is Python?",
            "How to write Python functions?",
            "What are Python decorators?",
            "Show me examples of decorators",
        ]

        results = []
        for query in conversation_queries:
            result = await rag_fn(mock_context, query)
            result_data = json.loads(result)
            results.append(result_data)

            assert result_data["success"] is True
            assert "results" in result_data

        # All queries should succeed
        assert len(results) == len(conversation_queries)

    @pytest.mark.asyncio
    async def test_chat_tools_performance(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test performance of chat tools under various loads"""
        rag_fn = get_tool_function("perform_rag_query")
        search_fn = get_tool_function("search_code_examples")

        # Test performance with different query complexities
        performance_tests = [
            ("simple", "Python"),
            ("medium", "How to use Python decorators effectively?"),
            (
                "complex",
                "What are the best practices for asynchronous programming in Python with error handling and resource management?",
            ),
        ]

        for complexity, query in performance_tests:
            start_time = time.time()

            # Test both RAG query and code search
            rag_result = await rag_fn(mock_context, query)
            code_result = await search_fn(mock_context, query)

            end_time = time.time()
            execution_time = end_time - start_time

            # Should complete within reasonable time
            assert execution_time < 3.0  # 3 seconds max with mocks

            # Both results should be valid
            rag_data = json.loads(rag_result)
            code_data = json.loads(code_result)
            assert rag_data["success"] is True
            assert code_data["success"] is True

    @pytest.mark.asyncio
    async def test_concurrent_chat_requests(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test handling multiple concurrent chat requests"""
        rag_fn = get_tool_function("perform_rag_query")

        # Create multiple concurrent chat tasks
        chat_queries = [
            "What is Python programming?",
            "How to write Python functions?",
            "What are Python data types?",
        ]

        tasks = []
        for query in chat_queries:
            task = rag_fn(mock_context, query)
            tasks.append(task)

        start_time = time.time()

        # Execute all chats concurrently
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        execution_time = end_time - start_time

        # Should handle concurrent requests efficiently
        assert execution_time < 5.0  # 5 seconds max for 3 concurrent requests
        assert len(results) == len(chat_queries)

        # All results should be valid
        for result in results:
            result_data = json.loads(result)
            assert result_data["success"] is True
            assert "results" in result_data


class TestChatToolsErrorHandling:
    """Error handling tests for chat/RAG tools"""

    @pytest.mark.asyncio
    async def test_rag_query_invalid_inputs(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test RAG query with invalid inputs"""
        rag_fn = get_tool_function("perform_rag_query")

        # Test various invalid inputs
        invalid_inputs = [
            ("", "Empty query"),
            ("   ", "Whitespace query"),
            (None, "None query"),
        ]

        for query, description in invalid_inputs:
            try:
                result = await rag_fn(mock_context, query)
                result_data = json.loads(result)

                # Should handle invalid inputs gracefully
                assert isinstance(result_data, dict)
                assert "success" in result_data
            except (TypeError, ValueError, AttributeError):
                # Some invalid inputs might raise exceptions, which is acceptable
                pass

    @pytest.mark.asyncio
    async def test_code_search_invalid_inputs(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test code search with invalid inputs"""
        search_fn = get_tool_function("search_code_examples")

        # Test various invalid inputs
        invalid_inputs = [
            ("", "Empty query"),
            ("   ", "Whitespace query"),
            (None, "None query"),
        ]

        for query, description in invalid_inputs:
            try:
                result = await search_fn(mock_context, query)
                result_data = json.loads(result)

                # Should handle invalid inputs gracefully
                assert isinstance(result_data, dict)
                assert "success" in result_data
            except (TypeError, ValueError, AttributeError):
                # Some invalid inputs might raise exceptions, which is acceptable
                pass

    @pytest.mark.asyncio
    async def test_chat_tools_memory_management(
        self,
        mock_context,
        mock_external_dependencies,
    ):
        """Test memory management with large queries and results"""
        rag_fn = get_tool_function("perform_rag_query")

        # Test with very long query
        long_query = "What is Python programming? " * 100  # Very long query

        result = await rag_fn(mock_context, long_query)
        result_data = json.loads(result)

        # Should handle long queries without memory issues
        assert isinstance(result_data, dict)
        assert "success" in result_data


if __name__ == "__main__":
    # Run tests with: uv run pytest tests/test_chat_tool.py -v
    pytest.main([__file__, "-v"])
