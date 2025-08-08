#!/usr/bin/env python3
"""
Test scrape_urls function through MCP tools with different input formats.

This tests the actual MCP tool functionality for handling different input formats.
"""

import asyncio
import json
import sys


# MCP tool testing functions
async def test_scrape_formats():
    """Test scrape_urls with different input formats using MCP tools."""

    print(
        "🧪 Testing scrape_urls function with multiple input formats via MCP tools..."
    )
    print("=" * 60)

    # Test cases
    test_cases = [
        {
            "name": "1. Single URL string",
            "input": "https://httpbin.org/html",
            "expected_success": True,
        },
        {
            "name": "2. JSON array string",
            "input": '["https://httpbin.org/html", "https://example.com"]',
            "expected_success": True,
        },
        {
            "name": "3. Invalid input - empty string",
            "input": "",
            "expected_success": False,
        },
        {
            "name": "4. Invalid input - malformed JSON",
            "input": '["https://example.com", "malformed',
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
            # Test using MCP tool
            from mcp__crawl4ai_docker__scrape_urls import (
                mcp__crawl4ai_docker__scrape_urls,
            )

            result = await mcp__crawl4ai_docker__scrape_urls(
                url=test_case["input"],
                return_raw_markdown=True,
            )

            # Parse result if it's a string
            if isinstance(result, str):
                try:
                    parsed_result = json.loads(result)
                except json.JSONDecodeError:
                    parsed_result = {"raw_result": result}
            else:
                parsed_result = result

            success = parsed_result.get("success", False)
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

    # Test search integration
    print("🔍 Testing search tool integration...")
    try:
        from mcp__crawl4ai_docker__search import mcp__crawl4ai_docker__search

        search_result = await mcp__crawl4ai_docker__search(
            query="python tutorial",
            num_results=2,
            return_raw_markdown=True,
        )

        if isinstance(search_result, str):
            try:
                search_parsed = json.loads(search_result)
            except json.JSONDecodeError:
                search_parsed = {"raw_result": search_result}
        else:
            search_parsed = search_result

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


async def main():
    """Main test runner."""
    try:
        results = await test_scrape_formats()

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
