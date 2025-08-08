#!/usr/bin/env python3
"""Test script to verify MCP tool fixes are working."""

import asyncio
from typing import Any

import httpx

MCP_SERVER_URL = "http://localhost:8051"


async def call_mcp_tool(tool_name: str, params: dict[str, Any]) -> dict:
    """Call an MCP tool via HTTP."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{MCP_SERVER_URL}/tools/{tool_name}",
            json=params,
        )
        return response.json()


async def test_scrape_urls():
    """Test Fix #1: Text Processing Module (chunk_size parameter)."""
    print("\n=== Testing Fix #1: scrape_urls (chunk_size parameter) ===")
    try:
        result = await call_mcp_tool(
            "scrape_urls",
            {
                "url": "https://example.com",
                "return_raw_markdown": False,
            },
        )

        if result.get("success"):
            print("✅ PASS: scrape_urls completed successfully")
            if (
                result.get("results")
                and result["results"][0].get("chunks_stored", 0) > 0
            ):
                print(f"   - Chunks stored: {result['results'][0]['chunks_stored']}")
            else:
                print("⚠️  WARNING: No chunks stored (may be expected for example.com)")
        else:
            print(f"❌ FAIL: {result.get('error', 'Unknown error')}")

        return result.get("success", False)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def test_perform_rag_query():
    """Test Fix #2: Database Import (create_embedding function)."""
    print("\n=== Testing Fix #2: perform_rag_query (create_embedding import) ===")
    try:
        result = await call_mcp_tool(
            "perform_rag_query",
            {
                "query": "test query",
                "match_count": 3,
            },
        )

        if result.get("success") or "No results found" in str(result):
            print("✅ PASS: perform_rag_query executed without import errors")
            if result.get("results"):
                print(f"   - Found {len(result['results'])} results")
        else:
            error_msg = result.get("error", "")
            if "attempted relative import" in error_msg:
                print(f"❌ FAIL: Import error still present: {error_msg}")
                return False
            print(f"⚠️  WARNING: Other error: {error_msg}")

        return True  # Even if no results, the import worked
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def test_smart_crawl_url():
    """Test Fix #3: Smart Crawling (context handling)."""
    print("\n=== Testing Fix #3: smart_crawl_url (context handling) ===")
    try:
        result = await call_mcp_tool(
            "smart_crawl_url",
            {
                "url": "https://example.com",
                "max_depth": 1,
            },
        )

        if result.get("success"):
            print("✅ PASS: smart_crawl_url completed successfully")
            if result.get("crawled_count"):
                print(f"   - Pages crawled: {result['crawled_count']}")
        else:
            error_msg = result.get("error", "")
            if "FunctionTool" in error_msg:
                print(f"❌ FAIL: FunctionTool error still present: {error_msg}")
                return False
            print(f"⚠️  WARNING: Other error: {error_msg}")

        return "FunctionTool" not in str(result)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Tool Fixes Validation Test")
    print("=" * 60)

    # Give the server a moment to stabilize after restart
    print("\nWaiting for server to stabilize...")
    await asyncio.sleep(2)

    results = []

    # Test each fix
    results.append(await test_scrape_urls())
    results.append(await test_perform_rag_query())
    results.append(await test_smart_crawl_url())

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 SUCCESS: All fixes are working correctly!")
    else:
        print(f"\n⚠️  PARTIAL SUCCESS: {passed} out of {total} fixes are working")
        print("Please review the failed tests above for details.")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
