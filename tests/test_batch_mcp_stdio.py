#!/usr/bin/env python3
"""
Test batch URL scraping via MCP stdio protocol
"""

import asyncio
import json
import subprocess
import time
from typing import Any


async def test_mcp_tool_call(
    tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Test a tool call via MCP stdio protocol"""

    # Create MCP request
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    # Start MCP server process
    process = subprocess.Popen(
        ["docker", "exec", "-i", "mcp-crawl4ai-dev", "python", "src/crawl4ai_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Send initialization handshake first
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0",
                },
            },
        }

        # Send init request
        init_json = json.dumps(init_request) + "\n"
        print(f"Sending init: {init_json.strip()}")
        process.stdin.write(init_json)
        process.stdin.flush()

        # Read init response
        init_response_line = process.stdout.readline()
        print(f"Init response: {init_response_line.strip()}")

        # Send the actual tool call
        request_json = json.dumps(request) + "\n"
        print(f"Sending request: {request_json.strip()}")
        process.stdin.write(request_json)
        process.stdin.flush()

        # Close stdin to signal end of input
        process.stdin.close()

        # Read response
        response_line = process.stdout.readline()
        print(f"Tool response: {response_line.strip()}")

        if response_line:
            return json.loads(response_line)
        stderr_output = process.stderr.read()
        raise Exception(f"No response received. Stderr: {stderr_output}")

    finally:
        # Clean up process
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


async def test_batch_url_scraping():
    """Test batch URL scraping functionality"""
    print("Testing batch URL scraping via MCP stdio...")

    # Test URLs - using reliable test sites
    test_urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/html",
    ]

    print(f"Test URLs: {test_urls}")

    try:
        start_time = time.time()

        # Call scrape_urls tool with array of URLs
        response = await test_mcp_tool_call(
            "scrape_urls",
            {
                "url": test_urls,
                "return_raw_markdown": True,
                "max_concurrent": 2,
            },
        )

        elapsed = time.time() - start_time
        print(f"Request completed in {elapsed:.2f}s")

        # Process response
        if "result" in response:
            result = (
                json.loads(response["result"])
                if isinstance(response["result"], str)
                else response["result"]
            )

            print("\nBatch scraping result:")
            print(f"- Success: {result.get('success', 'unknown')}")
            print(f"- Mode: {result.get('mode', 'unknown')}")

            if result.get("success") and "results" in result:
                results = result["results"]
                print(f"- URLs processed: {len(results)}")

                for url, content in results.items():
                    if content == "No content retrieved":
                        print(f"  ❌ {url}: No content retrieved")
                    else:
                        print(f"  ✅ {url}: {len(content)} chars retrieved")
                        print(
                            f"    Preview: {content[:100]}..."
                            if len(content) > 100
                            else f"    Content: {content}"
                        )

                # Check if all URLs were successful
                successful_urls = [
                    url
                    for url, content in results.items()
                    if content != "No content retrieved"
                ]
                if len(successful_urls) == len(test_urls):
                    print(f"\n✅ All {len(test_urls)} URLs were scraped successfully!")
                    return True
                print(
                    f"\n⚠️ Only {len(successful_urls)}/{len(test_urls)} URLs were scraped successfully"
                )
                return False
            print(f"❌ Scraping failed: {result.get('error', 'unknown error')}")
            return False
        print(f"❌ Unexpected response format: {response}")
        return False

    except Exception as e:
        print(f"❌ Error during batch test: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_single_url_for_comparison():
    """Test single URL scraping for comparison"""
    print("\n" + "=" * 50)
    print("Testing single URL for comparison...")

    test_url = "https://httpbin.org/json"

    try:
        start_time = time.time()

        response = await test_mcp_tool_call(
            "scrape_urls",
            {
                "url": test_url,  # Single URL as string
                "return_raw_markdown": True,
            },
        )

        elapsed = time.time() - start_time
        print(f"Single URL request completed in {elapsed:.2f}s")

        if "result" in response:
            result = (
                json.loads(response["result"])
                if isinstance(response["result"], str)
                else response["result"]
            )

            print("Single URL result:")
            print(f"- Success: {result.get('success', 'unknown')}")

            if result.get("success"):
                content_length = result.get("content_length", 0)
                print(f"- Content length: {content_length} chars")
                return True
            print(f"- Error: {result.get('error', 'unknown')}")
            return False
        print(f"❌ Unexpected response format: {response}")
        return False

    except Exception as e:
        print(f"❌ Error during single URL test: {e}")
        return False


if __name__ == "__main__":
    print("Starting MCP batch URL scraping tests...")

    async def run_tests():
        # Test batch scraping
        batch_success = await test_batch_url_scraping()

        # Test single URL for comparison
        single_success = await test_single_url_for_comparison()

        print("\n" + "=" * 50)
        print("Test Results Summary:")
        print(f"- Batch URL scraping: {'✅ PASS' if batch_success else '❌ FAIL'}")
        print(f"- Single URL scraping: {'✅ PASS' if single_success else '❌ FAIL'}")

        if batch_success:
            print("\n🎉 Batch URL scraping is working correctly!")
        else:
            print("\n🚨 Batch URL scraping has issues that need investigation")

    asyncio.run(run_tests())
