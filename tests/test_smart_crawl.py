#!/usr/bin/env python3
"""
Test script to debug the smart_crawl_url tool error.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastmcp import Context, FastMCP

from tools import register_tools


async def test_smart_crawl():
    """Test the smart_crawl_url tool directly."""
    try:
        # Create a test FastMCP instance
        mcp = FastMCP("Test MCP")

        # Register tools
        register_tools(mcp)

        # Get the smart_crawl_url tool
        tools = await mcp.get_tools()
        print(f"Available tools: {list(tools.keys())}")

        if "smart_crawl_url" in tools:
            tool = tools["smart_crawl_url"]
            print(f"Tool type: {type(tool)}")
            print(f"Tool: {tool}")

            # Create a context
            ctx = Context(mcp)

            # Try to call the tool function directly
            try:
                result = await tool.fn(
                    ctx,
                    url="https://example.com",
                    max_depth=1,
                    return_raw_markdown=True,
                )
                print(f"Result: {result}")
            except Exception as e:
                print(f"Error calling tool: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("smart_crawl_url tool not found")

    except Exception as e:
        print(f"Error in test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_smart_crawl())
