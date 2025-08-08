#!/usr/bin/env python3
"""
Test batch URL scraping via HTTP MCP interface
"""

import asyncio
import json
import time

import aiohttp


async def test_batch_scraping_http():
    """Test batch URL scraping via HTTP API"""

    # Test URLs - using httpbin for reliable testing
    test_urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/html",
    ]

    print("Testing batch URL scraping via HTTP MCP API...")
    print(f"URLs to test: {test_urls}")

    # MCP server HTTP endpoint
    mcp_url = "http://localhost:8051"

    try:
        async with aiohttp.ClientSession() as session:
            # Test MCP server health first
            try:
                async with session.get(f"{mcp_url}/health") as resp:
                    if resp.status == 200:
                        print("✅ MCP server is healthy")
                    else:
                        print(f"⚠️ MCP server health check returned {resp.status}")
            except Exception as e:
                print(f"❌ Could not reach MCP server: {e}")
                return

            # Prepare MCP request payload
            mcp_payload = {
                "method": "tools/call",
                "params": {
                    "name": "scrape_urls",
                    "arguments": {
                        "url": test_urls,
                        "return_raw_markdown": True,
                        "max_concurrent": 2,
                    },
                },
            }

            print("Sending batch scraping request...")
            start_time = time.time()

            # Send request to MCP server
            async with session.post(
                mcp_url,
                json=mcp_payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Request failed with status {resp.status}: {error_text}")
                    return

                result = await resp.json()
                elapsed = time.time() - start_time

                print(f"✅ Request completed in {elapsed:.2f}s")
                print("Response structure:")
                print(
                    json.dumps(result, indent=2)[:1000] + "..."
                    if len(json.dumps(result, indent=2)) > 1000
                    else json.dumps(result, indent=2)
                )

                # Parse and validate the response
                if "result" in result:
                    scrape_result = json.loads(result["result"])
                    print("\nScrape result summary:")
                    print(f"- Success: {scrape_result.get('success', 'unknown')}")
                    print(f"- Mode: {scrape_result.get('mode', 'unknown')}")

                    if scrape_result.get("success") and "results" in scrape_result:
                        results = scrape_result["results"]
                        print(f"- URLs processed: {len(results)}")

                        for url, content in results.items():
                            content_preview = (
                                content[:100] + "..." if len(content) > 100 else content
                            )
                            print(
                                f"  - {url}: {len(content)} chars - '{content_preview}'"
                            )

                            if content == "No content retrieved":
                                print(f"    ⚠️ No content retrieved for {url}")
                            else:
                                print(f"    ✅ Content retrieved for {url}")
                    else:
                        print(
                            f"❌ Scraping failed: {scrape_result.get('error', 'unknown error')}"
                        )
                else:
                    print("❌ Unexpected response format")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()


async def test_single_url_for_comparison():
    """Test single URL scraping for comparison"""
    print("\n" + "=" * 50)
    print("Testing single URL for comparison...")

    test_url = "https://httpbin.org/json"
    mcp_url = "http://localhost:8051"

    try:
        async with aiohttp.ClientSession() as session:
            mcp_payload = {
                "method": "tools/call",
                "params": {
                    "name": "scrape_urls",
                    "arguments": {
                        "url": test_url,  # Single URL as string
                        "return_raw_markdown": True,
                    },
                },
            }

            print(f"Scraping single URL: {test_url}")
            start_time = time.time()

            async with session.post(
                mcp_url,
                json=mcp_payload,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    elapsed = time.time() - start_time

                    print(f"✅ Single URL request completed in {elapsed:.2f}s")

                    if "result" in result:
                        scrape_result = json.loads(result["result"])
                        print(
                            f"Single URL result: Success={scrape_result.get('success')}"
                        )
                        if scrape_result.get("success"):
                            if "content_length" in scrape_result:
                                print(
                                    f"Content length: {scrape_result['content_length']} chars"
                                )
                        else:
                            print(f"Error: {scrape_result.get('error')}")
                else:
                    error_text = await resp.text()
                    print(f"❌ Single URL request failed: {resp.status} - {error_text}")

    except Exception as e:
        print(f"❌ Error during single URL test: {e}")


if __name__ == "__main__":
    print("Starting batch URL scraping tests...")
    asyncio.run(test_batch_scraping_http())
    asyncio.run(test_single_url_for_comparison())
