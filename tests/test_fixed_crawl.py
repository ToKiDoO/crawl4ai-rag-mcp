#!/usr/bin/env python3
"""
Test that the smart_crawl_url tool is now working with the fix.
This uses the OpenAI SDK to make an HTTP call to the MCP server.
"""

import asyncio
import json

import aiohttp


async def test_smart_crawl_url():
    """Test smart_crawl_url via the actual running MCP server."""
    url = "http://localhost:8051"

    async with aiohttp.ClientSession() as session:
        # First, get list of tools to see if server is responding
        list_tools_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer test-token",
        }

        try:
            async with session.post(
                f"{url}/v1/tools/list", headers=headers, json=list_tools_payload
            ) as response:
                print(f"List tools response: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(
                        f"Available tools: {[tool.get('name', 'unknown') for tool in data.get('tools', [])]}"
                    )

                    # Now test smart_crawl_url
                    crawl_payload = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "smart_crawl_url",
                            "arguments": {
                                "url": "https://example.com",
                                "max_depth": 1,
                                "return_raw_markdown": True,
                            },
                        },
                    }

                    async with session.post(
                        f"{url}/v1/tools/call", headers=headers, json=crawl_payload
                    ) as crawl_response:
                        print(f"Smart crawl response: {crawl_response.status}")
                        crawl_data = await crawl_response.json()
                        print(f"Result: {json.dumps(crawl_data, indent=2)}")
                else:
                    response_text = await response.text()
                    print(f"Error: {response_text}")

        except Exception as e:
            print(f"Error testing: {e}")

            # Try direct FastMCP format instead
            print("\nTrying direct FastMCP format...")
            mcp_url = "http://localhost:8051/mcp/tools/call"
            mcp_headers = {
                "Content-Type": "application/json",
            }

            mcp_payload = {
                "name": "smart_crawl_url",
                "arguments": {
                    "url": "https://example.com",
                    "max_depth": 1,
                    "return_raw_markdown": True,
                },
            }

            try:
                async with session.post(
                    mcp_url, headers=mcp_headers, json=mcp_payload
                ) as mcp_response:
                    print(f"FastMCP response: {mcp_response.status}")
                    mcp_data = await mcp_response.text()
                    print(f"FastMCP result: {mcp_data}")
            except Exception as mcp_e:
                print(f"FastMCP error: {mcp_e}")


if __name__ == "__main__":
    asyncio.run(test_smart_crawl_url())
