#!/usr/bin/env python3
"""Test script to verify the URL validation fix works with the MCP server."""

import asyncio
import json
import sys

import aiohttp


async def test_mcp_scrape_urls():
    """Test the MCP scrape_urls tool with various URL scenarios."""

    mcp_url = "http://localhost:8051/mcp/"

    # Test case 1: Valid URLs that should work
    valid_urls_payload = {
        "jsonrpc": "2.0",
        "id": "test-valid-urls",
        "method": "tools/call",
        "params": {
            "name": "mcp__crawl4ai-docker__scrape_urls",
            "arguments": {
                "url": [
                    "https://example.com",
                    "https://www.iana.org/help/example-domains",
                ],
                "max_concurrent": 2,
                "return_raw_markdown": True,
            },
        },
    }

    # Test case 2: Invalid URLs that should be caught by validation
    invalid_urls_payload = {
        "jsonrpc": "2.0",
        "id": "test-invalid-urls",
        "method": "tools/call",
        "params": {
            "name": "mcp__crawl4ai-docker__scrape_urls",
            "arguments": {
                "url": [
                    "ftp://invalid.com",  # Should be caught by validation
                    "https://example.com",
                ],
                "max_concurrent": 2,
                "return_raw_markdown": True,
            },
        },
    }

    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        print("Testing with valid URLs...")
        try:
            async with session.post(
                mcp_url, json=valid_urls_payload, headers=headers
            ) as resp:
                result = await resp.json()
                print("Valid URLs test result:")
                if "result" in result and "content" in result["result"]:
                    content = json.loads(result["result"]["content"])
                    if content.get("success"):
                        print("✅ Valid URLs processed successfully!")
                        print(f"Total URLs: {content.get('total_urls', 'unknown')}")
                    else:
                        print(
                            f"❌ Processing failed: {content.get('error', 'unknown error')}"
                        )
                else:
                    print(f"❌ Unexpected response format: {result}")

        except Exception as e:
            print(f"❌ Error testing valid URLs: {e}")

        print("\n" + "=" * 50)
        print("Testing with invalid URLs (should fail gracefully)...")

        try:
            async with session.post(
                mcp_url, json=invalid_urls_payload, headers=headers
            ) as resp:
                result = await resp.json()
                print("Invalid URLs test result:")
                if "error" in result:
                    print("✅ Invalid URLs correctly rejected by MCP layer!")
                    print(f"Error: {result['error']}")
                elif "result" in result and "content" in result["result"]:
                    content = json.loads(result["result"]["content"])
                    if not content.get("success"):
                        print("✅ Invalid URLs correctly rejected by validation layer!")
                        print(f"Error: {content.get('error', 'unknown error')}")
                    else:
                        print(
                            "❌ Invalid URLs were NOT rejected - this indicates a problem!"
                        )
                else:
                    print(f"❌ Unexpected response format: {result}")

        except Exception as e:
            print(f"❌ Error testing invalid URLs: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_scrape_urls())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
