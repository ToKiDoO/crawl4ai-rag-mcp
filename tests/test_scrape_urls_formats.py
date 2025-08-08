#!/usr/bin/env python3
"""
Test script for scrape_urls function with multiple input formats.

Tests various input formats:
1. Single URL string
2. List of URLs
3. JSON array string
4. Invalid inputs (empty string, empty list, malformed JSON)
5. Search tool integration with multiple URLs
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from crawl4ai import AsyncWebCrawler
from crawl4ai_mcp import scrape_urls, search

from database import create_database_client


# Mock context for testing
class MockLifespanContext:
    def __init__(self):
        self.crawler = None
        self.database_client = None


class MockRequestContext:
    def __init__(self):
        self.lifespan_context = MockLifespanContext()


class MockContext:
    def __init__(self):
        self.request_context = MockRequestContext()


async def test_scrape_urls_formats():
    """Test scrape_urls function with different input formats."""

    print("🧪 Testing scrape_urls function with multiple input formats...")
    print("=" * 60)

    # Initialize components
    ctx = MockContext()

    try:
        # Initialize crawler and database client
        crawler = AsyncWebCrawler(
            headless=True,
            browser_type="chromium",
        )
        await crawler.__aenter__()
        ctx.request_context.lifespan_context.crawler = crawler

        database_client = create_database_client()
        ctx.request_context.lifespan_context.database_client = database_client

        # Test URLs for different scenarios
        test_urls = [
            "https://httpbin.org/html",
            "https://example.com",
        ]

        print("🔗 Test URLs being used:")
        for url in test_urls:
            print(f"  - {url}")
        print()

        # Test scenarios
        test_cases = [
            {
                "name": "1. Single URL string",
                "input": test_urls[0],
                "expected_success": True,
            },
            {
                "name": "2. List of URLs (internal call format)",
                "input": test_urls,
                "expected_success": True,
            },
            {
                "name": "3. JSON array string",
                "input": json.dumps(test_urls),
                "expected_success": True,
            },
            {
                "name": "4a. Invalid input - empty string",
                "input": "",
                "expected_success": False,
            },
            {
                "name": "4b. Invalid input - empty list",
                "input": [],
                "expected_success": False,
            },
            {
                "name": "4c. Invalid input - malformed JSON",
                "input": '["https://example.com", "malformed',
                "expected_success": False,
            },
            {
                "name": "4d. Invalid input - wrong type",
                "input": 12345,
                "expected_success": False,
            },
            {
                "name": "5. JSON array with empty strings",
                "input": '["https://httpbin.org/html", "", "https://example.com"]',
                "expected_success": True,  # Should filter out empty strings
            },
            {
                "name": "6. Single URL in JSON array",
                "input": '["https://httpbin.org/html"]',
                "expected_success": True,
            },
        ]

        results = []

        for i, test_case in enumerate(test_cases):
            print(f"🧪 Test {i + 1}: {test_case['name']}")
            print(f"   Input: {test_case['input']!r}")

            try:
                # Test with return_raw_markdown=True for faster testing
                result = await scrape_urls(
                    ctx,
                    test_case["input"],
                    max_concurrent=2,
                    batch_size=5,
                    return_raw_markdown=True,
                )

                # Parse result
                parsed_result = json.loads(result)
                success = parsed_result.get("success", False)

                # Check if result matches expectation
                test_passed = success == test_case["expected_success"]

                print(f"   Result: {'✅ PASS' if test_passed else '❌ FAIL'}")
                print(f"   Success: {success}")

                if success:
                    if "results" in parsed_result:
                        # Multi-URL result
                        urls_processed = parsed_result.get("summary", {}).get(
                            "urls_processed", 0
                        )
                        print(f"   URLs processed: {urls_processed}")
                    elif "url" in parsed_result:
                        # Single URL result
                        print(f"   URL: {parsed_result['url']}")
                else:
                    error = parsed_result.get("error", "Unknown error")
                    print(f"   Error: {error}")

                results.append(
                    {
                        "test": test_case["name"],
                        "passed": test_passed,
                        "success": success,
                        "expected": test_case["expected_success"],
                        "result": parsed_result,
                    }
                )

            except Exception as e:
                print(f"   Result: ❌ EXCEPTION - {e!s}")
                results.append(
                    {
                        "test": test_case["name"],
                        "passed": False,
                        "success": False,
                        "expected": test_case["expected_success"],
                        "error": str(e),
                    }
                )

            print()

        # Test search integration with multiple URLs
        print("🔍 Testing search tool integration with multiple URLs...")
        try:
            search_result = await search(
                ctx,
                query="python tutorial",
                num_results=2,
                return_raw_markdown=True,
            )

            search_parsed = json.loads(search_result)
            if search_parsed.get("success"):
                print("   ✅ Search tool successfully handles multiple URLs")
                urls_in_search = len(search_parsed.get("results", {}))
                print(f"   URLs found in search: {urls_in_search}")
            else:
                print("   ❌ Search tool failed")
                print(f"   Error: {search_parsed.get('error', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ Search test exception: {e!s}")

        print()

        # Summary
        passed_tests = sum(1 for r in results if r["passed"])
        total_tests = len(results)

        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success rate: {passed_tests / total_tests * 100:.1f}%")
        print()

        # Detailed results for failed tests
        failed_tests = [r for r in results if not r["passed"]]
        if failed_tests:
            print("❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"   - {test['test']}")
                print(f"     Expected: {test['expected']}, Got: {test['success']}")
                if "error" in test:
                    print(f"     Exception: {test['error']}")
        else:
            print("🎉 ALL TESTS PASSED!")

        return results

    finally:
        # Cleanup
        if (
            hasattr(ctx.request_context.lifespan_context, "crawler")
            and ctx.request_context.lifespan_context.crawler
        ):
            try:
                await ctx.request_context.lifespan_context.crawler.__aexit__(
                    None, None, None
                )
            except:
                pass


async def main():
    """Main test runner."""
    try:
        results = await test_scrape_urls_formats()

        # Exit with appropriate code
        failed_count = sum(1 for r in results if not r["passed"])
        sys.exit(0 if failed_count == 0 else 1)

    except Exception as e:
        print(f"❌ Test runner failed: {e!s}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
