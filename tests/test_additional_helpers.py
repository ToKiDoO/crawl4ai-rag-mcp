"""
Additional unit tests for helper functions from crawl4ai_mcp.py that weren't covered in other test files.

Test Coverage:
- rerank_results(): Test result reranking with cross-encoder models
- track_request(): Test request tracking decorator
- Other utility functions that need additional coverage

Testing Approach:
- Mock external dependencies (CrossEncoder, logging)
- Test decorator functionality
- Comprehensive edge case coverage
- Error handling validation
"""

import asyncio
import functools
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import functions to test
from crawl4ai_mcp import rerank_results, track_request


class TestRerankResults:
    """Test rerank_results() function for search result reranking"""

    def test_rerank_results_basic(self):
        """Test basic result reranking functionality"""
        # Mock CrossEncoder model
        mock_model = Mock()
        mock_model.predict.return_value = [0.8, 0.3, 0.9, 0.1]  # Scores for 4 results

        query = "test query"
        results = [
            {"content": "First result", "id": 1},
            {"content": "Second result", "id": 2},
            {"content": "Third result", "id": 3},
            {"content": "Fourth result", "id": 4},
        ]

        reranked = rerank_results(mock_model, query, results)

        # Should be sorted by rerank_score descending
        assert len(reranked) == 4
        assert reranked[0]["id"] == 3  # Score 0.9
        assert reranked[1]["id"] == 1  # Score 0.8
        assert reranked[2]["id"] == 2  # Score 0.3
        assert reranked[3]["id"] == 4  # Score 0.1

        # Check that rerank scores were added
        assert reranked[0]["rerank_score"] == 0.9
        assert reranked[1]["rerank_score"] == 0.8
        assert reranked[2]["rerank_score"] == 0.3
        assert reranked[3]["rerank_score"] == 0.1

    def test_rerank_results_custom_content_key(self):
        """Test reranking with custom content key"""
        mock_model = Mock()
        mock_model.predict.return_value = [0.5, 0.8]

        query = "test query"
        results = [
            {"text": "First result", "id": 1},
            {"text": "Second result", "id": 2},
        ]

        reranked = rerank_results(mock_model, query, results, content_key="text")

        # Verify model was called with correct texts
        mock_model.predict.assert_called_once_with(
            [[query, "First result"], [query, "Second result"]],
        )

        # Should be reordered
        assert reranked[0]["id"] == 2  # Score 0.8
        assert reranked[1]["id"] == 1  # Score 0.5

    def test_rerank_results_no_model(self):
        """Test reranking with no model (should return original results)"""
        query = "test query"
        results = [{"content": "result", "id": 1}]

        # Test with None model
        reranked = rerank_results(None, query, results)
        assert reranked == results

        # Test with falsy model
        reranked = rerank_results(False, query, results)
        assert reranked == results

    def test_rerank_results_empty_results(self):
        """Test reranking with empty results"""
        mock_model = Mock()
        query = "test query"

        # Empty list
        reranked = rerank_results(mock_model, query, [])
        assert reranked == []

        # None results
        reranked = rerank_results(mock_model, query, None)
        assert reranked is None

    def test_rerank_results_missing_content_key(self):
        """Test reranking when content key is missing from some results"""
        mock_model = Mock()
        mock_model.predict.return_value = [0.5, 0.8]

        query = "test query"
        results = [
            {"content": "First result", "id": 1},
            {"other_field": "Second result", "id": 2},  # Missing 'content' key
        ]

        reranked = rerank_results(mock_model, query, results)

        # Should handle missing key gracefully (empty string for missing content)
        mock_model.predict.assert_called_once_with(
            [
                [query, "First result"],
                [query, ""],  # Empty string for missing content
            ],
        )

        assert len(reranked) == 2

    def test_rerank_results_model_error(self):
        """Test reranking when model prediction fails"""
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Model prediction failed")

        query = "test query"
        results = [{"content": "result", "id": 1}]

        with patch("crawl4ai_mcp.logger") as mock_logger:
            reranked = rerank_results(mock_model, query, results)

            # Should return original results on error
            assert reranked == results

            # Should log error
            mock_logger.error.assert_called_once()
            assert "Error during reranking" in str(mock_logger.error.call_args)

    def test_rerank_results_score_conversion(self):
        """Test conversion of scores to float"""
        mock_model = Mock()
        # Return various numeric types
        mock_model.predict.return_value = [
            0.5,
            1,
            0.0,
            -0.1,
        ]  # float, int, zero, negative

        query = "test query"
        results = [
            {"content": "First", "id": 1},
            {"content": "Second", "id": 2},
            {"content": "Third", "id": 3},
            {"content": "Fourth", "id": 4},
        ]

        reranked = rerank_results(mock_model, query, results)

        # All scores should be converted to float
        for result in reranked:
            assert isinstance(result["rerank_score"], float)

        # Should handle negative scores correctly
        assert any(result["rerank_score"] < 0 for result in reranked)

    def test_rerank_results_preserves_original_data(self):
        """Test that reranking preserves all original result data"""
        mock_model = Mock()
        mock_model.predict.return_value = [0.8, 0.2]

        query = "test query"
        results = [
            {
                "content": "First result",
                "id": 1,
                "metadata": {"source": "doc1"},
                "similarity": 0.95,
                "url": "http://example.com/1",
            },
            {
                "content": "Second result",
                "id": 2,
                "metadata": {"source": "doc2"},
                "similarity": 0.87,
                "url": "http://example.com/2",
            },
        ]

        reranked = rerank_results(mock_model, query, results)

        # Should preserve all original fields
        for result in reranked:
            assert "content" in result
            assert "id" in result
            assert "metadata" in result
            assert "similarity" in result
            assert "url" in result
            assert "rerank_score" in result  # Added by reranking

        # Original similarity scores should be preserved
        assert all("similarity" in result for result in reranked)


class TestTrackRequest:
    """Test track_request() decorator for request tracking"""

    def test_track_request_basic_functionality(self):
        """Test basic request tracking functionality"""
        with patch("crawl4ai_mcp.logger") as mock_logger:

            @track_request("test_tool")
            async def test_function(ctx, param1, param2=None):
                return f"result_{param1}"

            # Mock context
            mock_ctx = Mock()

            # Run the decorated function
            result = asyncio.run(test_function(mock_ctx, "value1", param2="value2"))

            assert result == "result_value1"

            # Check logging calls
            assert mock_logger.info.call_count >= 2  # Start and completion
            assert mock_logger.debug.call_count >= 1  # Arguments

            # Check log messages
            info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("Starting test_tool request" in msg for msg in info_calls)
            assert any("Completed test_tool" in msg for msg in info_calls)

    def test_track_request_timing(self):
        """Test request timing functionality"""
        with patch("crawl4ai_mcp.logger") as mock_logger:

            @track_request("timed_tool")
            async def slow_function(ctx):
                await asyncio.sleep(0.1)  # Small delay
                return "done"

            mock_ctx = Mock()

            start_time = datetime.now().timestamp()
            result = asyncio.run(slow_function(mock_ctx))
            end_time = datetime.now().timestamp()

            assert result == "done"

            # Check that timing is logged
            completion_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "Completed" in str(call)
            ]
            assert len(completion_calls) > 0

            # Timing should be reasonable
            duration = end_time - start_time
            assert duration >= 0.1  # At least our sleep time

    def test_track_request_error_handling(self):
        """Test error handling in tracked requests"""
        with patch("crawl4ai_mcp.logger") as mock_logger:

            @track_request("error_tool")
            async def failing_function(ctx):
                raise ValueError("Test error")

            mock_ctx = Mock()

            # Should re-raise the exception
            with pytest.raises(ValueError, match="Test error"):
                asyncio.run(failing_function(mock_ctx))

            # Check error logging
            assert mock_logger.error.call_count >= 1
            assert mock_logger.debug.call_count >= 1  # Traceback

            error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
            assert any("Failed error_tool" in msg for msg in error_calls)

    def test_track_request_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata"""

        @track_request("metadata_tool")
        async def documented_function(ctx, param):
            """This is a test function with documentation."""
            return param * 2

        # Check that metadata is preserved
        assert documented_function.__name__ == "documented_function"
        assert "test function with documentation" in documented_function.__doc__

        # Function should still work
        mock_ctx = Mock()
        result = asyncio.run(documented_function(mock_ctx, 5))
        assert result == 10

    def test_track_request_uuid_generation(self):
        """Test request ID generation"""
        with (
            patch("crawl4ai_mcp.logger") as mock_logger,
            patch("crawl4ai_mcp.uuid.uuid4") as mock_uuid,
        ):
            mock_uuid.return_value.hex = "abcdef123456"

            @track_request("uuid_tool")
            async def test_function(ctx):
                return "test"

            mock_ctx = Mock()
            asyncio.run(test_function(mock_ctx))

            # Check that UUID was generated and used in logs
            info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("abcdef12" in msg for msg in info_calls)  # First 8 chars

    def test_track_request_with_complex_arguments(self):
        """Test tracking with complex argument types"""
        with patch("crawl4ai_mcp.logger") as mock_logger:

            @track_request("complex_tool")
            async def complex_function(ctx, data_dict, data_list, **kwargs):
                return len(data_dict) + len(data_list)

            mock_ctx = Mock()
            test_dict = {"key1": "value1", "key2": "value2"}
            test_list = [1, 2, 3, 4, 5]

            result = asyncio.run(
                complex_function(
                    mock_ctx,
                    test_dict,
                    test_list,
                    extra_param="extra_value",
                ),
            )

            assert result == 7  # 2 dict items + 5 list items

            # Check that arguments are logged (at debug level)
            debug_calls = [call.args[0] for call in mock_logger.debug.call_args_list]
            assert any("Arguments:" in msg for msg in debug_calls)

    def test_track_request_multiple_decorators(self):
        """Test function with multiple decorators including track_request"""

        def another_decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                return f"decorated_{result}"

            return wrapper

        with patch("crawl4ai_mcp.logger") as mock_logger:

            @another_decorator
            @track_request("multi_decorated_tool")
            async def multi_decorated_function(ctx, value):
                return value.upper()

            mock_ctx = Mock()
            result = asyncio.run(multi_decorated_function(mock_ctx, "test"))

            assert result == "decorated_TEST"

            # Should still log properly
            info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("Starting multi_decorated_tool" in msg for msg in info_calls)

    def test_track_request_concurrent_calls(self):
        """Test concurrent calls with different request IDs"""
        with patch("crawl4ai_mcp.logger") as mock_logger:

            @track_request("concurrent_tool")
            async def concurrent_function(ctx, delay, value):
                await asyncio.sleep(delay)
                return value

            mock_ctx = Mock()

            # Run multiple concurrent calls
            async def run_concurrent():
                tasks = [
                    concurrent_function(mock_ctx, 0.05, "task1"),
                    concurrent_function(mock_ctx, 0.03, "task2"),
                    concurrent_function(mock_ctx, 0.02, "task3"),
                ]
                return await asyncio.gather(*tasks)

            results = asyncio.run(run_concurrent())

            assert set(results) == {"task1", "task2", "task3"}

            # Should have logged multiple different request IDs
            info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            start_calls = [
                msg for msg in info_calls if "Starting concurrent_tool" in msg
            ]
            assert len(start_calls) == 3

            # Each should have different request ID (first 8 chars of UUID)
            request_ids = []
            for call in start_calls:
                # Extract request ID from log message like "[abcd1234] Starting..."
                import re

                match = re.search(r"\[([a-f0-9]+)\]", call)
                if match:
                    request_ids.append(match.group(1))

            assert len(set(request_ids)) == 3  # All different


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
