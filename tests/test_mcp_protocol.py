"""
MCP Protocol compliance tests.
Tests tool discovery, parameter validation, and error handling.
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest
from crawl4ai_mcp import Crawl4AIContext, mcp
from mcp.server.fastmcp import FastMCP


class MockMCPContext:
    """Mock MCP context for testing"""

    def __init__(self):
        self.request_context = Mock()
        self.request_context.session_id = "test-session"
        self.request_context.meta = {}


class TestMCPProtocol:
    """Test MCP protocol compliance"""

    def test_server_initialization(self):
        """Test that MCP server initializes correctly"""
        assert mcp is not None, "MCP server should be initialized"
        assert isinstance(mcp, FastMCP), "MCP should be FastMCP instance"
        assert mcp.name == "mcp-crawl4ai-rag", "Server name should match"

    def test_tool_discovery(self):
        """Test that all tools are discoverable"""
        # Access internal tools registry
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # Expected tools
        expected_tools = [
            "search",
            "scrape_urls",
            "smart_crawl_url",
            "get_available_sources",
            "perform_rag_query",
            "search_code_examples",
        ]

        # Check all expected tools are registered
        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool '{tool_name}' should be registered"

        # Validate tool structure - FastMCP uses Tool objects, not dicts
        for tool_name, tool_obj in tools.items():
            assert hasattr(tool_obj, "fn"), (
                f"Tool '{tool_name}' should have fn attribute"
            )
            assert hasattr(tool_obj, "name"), (
                f"Tool '{tool_name}' should have name attribute"
            )
            assert hasattr(tool_obj, "description"), (
                f"Tool '{tool_name}' should have description attribute"
            )
            assert hasattr(tool_obj, "parameters"), (
                f"Tool '{tool_name}' should have parameters attribute"
            )

    def test_tool_parameters(self):
        """Test tool parameter schemas"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # Test search tool parameters
        search_tool = tools["search"]
        search_schema = search_tool.parameters
        assert "properties" in search_schema
        assert "query" in search_schema["properties"]
        assert search_schema["properties"]["query"]["type"] == "string"
        assert "required" in search_schema
        assert "query" in search_schema["required"]

        # Optional parameters
        assert "return_raw_markdown" in search_schema["properties"]
        assert search_schema["properties"]["return_raw_markdown"]["type"] == "boolean"
        assert "num_results" in search_schema["properties"]
        assert search_schema["properties"]["num_results"]["type"] == "integer"

    def test_parameter_validation_types(self):
        """Test parameter type validation"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # Check various parameter types
        test_cases = [
            ("search", "query", "string"),
            ("search", "num_results", "integer"),
            ("search", "return_raw_markdown", "boolean"),
            ("scrape_urls", "url", ["string", "array"]),  # Union type
            ("smart_crawl_url", "max_depth", "integer"),
            ("perform_rag_query", "match_count", "integer"),
        ]

        for tool_name, param_name, expected_type in test_cases:
            tool_obj = tools[tool_name]
            schema = tool_obj.parameters
            param_schema = schema["properties"].get(param_name, {})

            if isinstance(expected_type, list):
                # Union type - check oneOf or anyOf
                assert (
                    "oneOf" in param_schema
                    or "anyOf" in param_schema
                    or "type" in param_schema
                )
            else:
                assert param_schema.get("type") == expected_type, (
                    f"{tool_name}.{param_name} should be {expected_type}"
                )

    def test_default_parameter_values(self):
        """Test default parameter values"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # Test defaults
        test_defaults = [
            ("search", "return_raw_markdown", False),
            ("search", "num_results", 6),
            ("search", "batch_size", 20),
            ("scrape_urls", "max_concurrent", 10),
            ("smart_crawl_url", "max_depth", 3),
            ("perform_rag_query", "match_count", 5),
        ]

        for tool_name, param_name, expected_default in test_defaults:
            # Get the tool handler function
            tool_obj = tools[tool_name]
            handler = tool_obj.fn

            # Check function signature for defaults
            import inspect

            sig = inspect.signature(handler)
            param = sig.parameters.get(param_name)

            if param and param.default != inspect.Parameter.empty:
                assert param.default == expected_default, (
                    f"{tool_name}.{param_name} default should be {expected_default}"
                )

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test error handling for missing required parameters"""
        # Mock context
        ctx = MockMCPContext()

        # Get search tool handler
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        search_tool = tools["search"]
        search_handler = search_tool.fn

        # Test calling without required 'query' parameter
        with pytest.raises(TypeError) as exc_info:
            await search_handler(ctx)

        assert "query" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_invalid_parameter_types(self):
        """Test error handling for invalid parameter types"""
        ctx = MockMCPContext()

        # Mock the context properly
        ctx.request_context.lifespan_context = Crawl4AIContext(
            crawler=AsyncMock(),
            database_client=AsyncMock(),
            reranking_model=None,
            knowledge_validator=None,
            repo_extractor=None,
        )

        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        search_tool = tools["search"]
        search_handler = search_tool.fn

        # Test with invalid parameter type
        # Note: Python type hints don't enforce runtime validation
        # MCP servers should validate types if strict validation is needed
        try:
            # This might not raise an error in Python
            result = await search_handler(
                ctx,
                query=123,  # Should be string
                num_results="invalid",  # Should be int
            )
        except Exception as e:
            # If validation is implemented, check error
            assert "type" in str(e).lower() or "invalid" in str(e).lower()

    def test_tool_descriptions(self):
        """Test that all tools have meaningful descriptions"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        for tool_name, tool_obj in tools.items():
            desc = tool_obj.description if hasattr(tool_obj, "description") else ""

            # Check description exists and is meaningful
            assert desc, f"Tool '{tool_name}' should have a description"
            assert len(desc) > 20, f"Tool '{tool_name}' description too short"
            assert not desc.startswith("TODO"), (
                f"Tool '{tool_name}' has placeholder description"
            )

            # Check description mentions key functionality
            if tool_name == "search":
                assert "search" in desc.lower() or "searxng" in desc.lower()
            elif tool_name == "scrape_urls":
                assert "scrape" in desc.lower() or "url" in desc.lower()

    def test_enum_parameters(self):
        """Test enum parameter validation"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # Check if any tools have enum parameters
        for tool_name, tool_obj in tools.items():
            schema = tool_obj.parameters
            properties = schema.get("properties", {})

            for param_name, param_schema in properties.items():
                if "enum" in param_schema:
                    # Validate enum values
                    enum_values = param_schema["enum"]
                    assert isinstance(enum_values, list), (
                        f"{tool_name}.{param_name} enum should be list"
                    )
                    assert len(enum_values) > 0, (
                        f"{tool_name}.{param_name} enum should not be empty"
                    )

    def test_array_parameters(self):
        """Test array parameter handling"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # scrape_urls accepts both string and array
        scrape_tool = tools["scrape_urls"]
        scrape_schema = scrape_tool.parameters
        url_schema = scrape_schema["properties"]["url"]

        # Should handle both single and array
        assert (
            "oneOf" in url_schema
            or "anyOf" in url_schema
            or url_schema.get("type") == "array"
        )

    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """Test that errors follow JSON-RPC format"""
        ctx = MockMCPContext()

        # This would be tested at the transport layer
        # Here we just ensure exceptions are raised properly
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        search_tool = tools["search"]
        handler = search_tool.fn

        with pytest.raises(Exception):
            await handler(ctx)  # Missing required parameter

    def test_tool_naming_conventions(self):
        """Test that tool names follow conventions"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        for tool_name in tools:
            # Check naming conventions
            assert tool_name.islower() or "_" in tool_name, (
                f"Tool '{tool_name}' should use lowercase/underscore naming"
            )
            assert not tool_name.startswith("_"), (
                f"Tool '{tool_name}' should not start with underscore"
            )
            assert not tool_name.endswith("_"), (
                f"Tool '{tool_name}' should not end with underscore"
            )
            assert "__" not in tool_name, (
                f"Tool '{tool_name}' should not have double underscores"
            )

    def test_response_types(self):
        """Test that tools specify return types"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        for tool_name, tool_obj in tools.items():
            handler = tool_obj.fn

            # Check if handler has return type annotation
            import inspect

            sig = inspect.signature(handler)

            # Most tools should return strings for MCP
            # This is more of a convention check
            assert sig.return_annotation != inspect.Parameter.empty, (
                f"Tool '{tool_name}' should have return type annotation"
            )


class TestMCPEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_empty_array_parameter(self):
        """Test handling of empty arrays"""
        ctx = MockMCPContext()
        ctx.request_context.lifespan_context = Crawl4AIContext(
            crawler=AsyncMock(),
            database_client=AsyncMock(),
            reranking_model=None,
            knowledge_validator=None,
            repo_extractor=None,
        )

        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        scrape_tool = tools["scrape_urls"]
        handler = scrape_tool.fn

        # Test with empty URL array
        result = await handler(ctx, url=[])

        # Should return error response as JSON
        response = json.loads(result)
        assert response["success"] is False
        assert (
            "empty" in response["error"].lower() or "url" in response["error"].lower()
        )

    def test_unknown_tool_handling(self):
        """Test that unknown tools are handled properly"""
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        # Verify unknown tool doesn't exist
        assert "unknown_tool_xyz" not in tools

        # In actual MCP, this would return proper JSON-RPC error
        # Here we just verify the tool doesn't exist

    def test_tool_timeout_handling(self):
        """Test that tools can handle timeouts gracefully"""
        # This would be tested with actual timeout scenarios
        # Here we verify tools are async and can be cancelled
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}

        for tool_name, tool_obj in tools.items():
            handler = tool_obj.fn

            # Verify handler is async
            import inspect

            assert inspect.iscoroutinefunction(handler), (
                f"Tool '{tool_name}' handler should be async"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
