#!/usr/bin/env python3
"""Test the MCP server tool directly via HTTP."""

import json
import time

import requests

# MCP server endpoint
MCP_URL = "http://localhost:8051/mcp/"


def test_scrape_urls_tool():
    """Test the scrape_urls tool with various URL formats."""
    print("Testing scrape_urls MCP tool...")
    print("=" * 50)

    # Test cases
    test_cases = [
        {
            "name": "Valid URL",
            "params": {
                "url": "https://example.com",
                "return_raw_markdown": True,
            },
        },
        {
            "name": "URL without protocol (should fail with helpful message)",
            "params": {
                "url": "example.com",
                "return_raw_markdown": True,
            },
        },
        {
            "name": "Truncated URL (should fail with helpful message)",
            "params": {
                "url": ".../help/example-domains",
                "return_raw_markdown": True,
            },
        },
        {
            "name": "Multiple URLs with mixed validity",
            "params": {
                "url": ["https://example.com", ".../help/example-domains"],
                "return_raw_markdown": True,
            },
        },
    ]

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {test['params']['url']}")

        # Prepare MCP request
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "scrape_urls",
                "arguments": test["params"],
            },
            "id": int(time.time()),
        }

        try:
            # Send request to MCP server
            response = requests.post(
                MCP_URL,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()

                if "result" in result:
                    # Parse the content (it's a JSON string within the result)
                    try:
                        content = json.loads(result["result"]["content"][0]["text"])
                        if content.get("success"):
                            print(
                                f"✓ Success - {content.get('message', 'Processed successfully')}"
                            )
                            if content.get("total_urls"):
                                print(f"  Processed {content['total_urls']} URLs")
                        else:
                            print(f"✗ Failed - {content.get('error', 'Unknown error')}")
                    except:
                        # If not JSON, print raw result
                        print(f"Result: {result['result']}")

                elif "error" in result:
                    error = result["error"]
                    print(f"✗ MCP Error: {error.get('message', 'Unknown error')}")
                    if error.get("data"):
                        print(f"  Details: {error['data']}")
            else:
                print(f"✗ HTTP Error {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            print("✗ Request timed out")
        except requests.exceptions.ConnectionError:
            print("✗ Could not connect to MCP server at", MCP_URL)
        except Exception as e:
            print(f"✗ Exception: {e}")

    print("\n" + "=" * 50)
    print("MCP tool testing complete!")


if __name__ == "__main__":
    test_scrape_urls_tool()
