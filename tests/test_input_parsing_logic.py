#!/usr/bin/env python3
"""
Test the input parsing logic from scrape_urls function without running the full MCP stack.

This isolates the URL parsing logic to verify different input formats work correctly.
"""

import json


def parse_url_input(url_input: str | list[str]) -> tuple[bool, list[str] | str]:
    """
    Parse and validate URL input with security limits and proper validation.

    Returns:
        (success: bool, result: List[str] | error_message: str)
    """
    try:
        # Security limits
        MAX_URLS = 100
        MAX_JSON_SIZE = 10000  # 10KB limit for JSON strings

        urls = []

        if isinstance(url_input, str):
            # Handle string input - could be single URL or JSON array
            url_stripped = url_input.strip()

            if not url_stripped:
                return False, "URL cannot be empty"

            # Security check: limit JSON string size
            if len(url_stripped) > MAX_JSON_SIZE:
                return (
                    False,
                    f"Input too large: {len(url_stripped)} bytes (max: {MAX_JSON_SIZE})",
                )

            # Improved JSON detection - check for array brackets after stripping
            if url_stripped.startswith("[") and url_stripped.endswith("]"):
                try:
                    parsed_urls = json.loads(url_stripped)

                    # Validate it's actually a list
                    if not isinstance(parsed_urls, list):
                        return (
                            False,
                            "JSON input must be an array of URLs, not an object",
                        )

                    # Security check: limit number of URLs
                    if len(parsed_urls) > MAX_URLS:
                        return (
                            False,
                            f"Too many URLs: {len(parsed_urls)} (max: {MAX_URLS})",
                        )

                    # Convert to strings and filter empty ones
                    urls = [str(u).strip() for u in parsed_urls if str(u).strip()]

                except json.JSONDecodeError:
                    # Not valid JSON, treat as single URL
                    urls = [url_stripped]
            else:
                # Single URL string or malformed JSON
                urls = [url_stripped]

        elif isinstance(url_input, list):
            # Handle list input (internal calls)
            if len(url_input) > MAX_URLS:
                return False, f"Too many URLs: {len(url_input)} (max: {MAX_URLS})"

            urls = [str(u).strip() for u in url_input if str(u).strip()]

        else:
            return (
                False,
                f"URL must be a string or list of strings, got {type(url_input).__name__}",
            )

        # Validate we have URLs to process
        if not urls:
            return False, "No valid URLs provided"

        # Validate each URL format
        validated_urls = []
        for url in urls:
            # Basic URL validation
            if not url.startswith(("http://", "https://")):
                return (
                    False,
                    f"Invalid URL format: {url} (must start with http:// or https://)",
                )

            # Additional security: reject obviously invalid URLs
            if any(
                invalid in url.lower() for invalid in ["javascript:", "data:", "file:"]
            ):
                return False, f"Unsafe URL scheme detected: {url}"

            validated_urls.append(url)

        return True, validated_urls

    except Exception as e:
        return False, str(e)


def test_url_parsing():
    """Test URL parsing logic with different input formats."""

    print("🧪 Testing URL input parsing logic...")
    print("=" * 60)

    # Test cases
    test_cases = [
        {
            "name": "1. Single URL string",
            "input": "https://httpbin.org/html",
            "expected_success": True,
            "expected_count": 1,
        },
        {
            "name": "2. List of URLs (internal call format)",
            "input": ["https://httpbin.org/html", "https://example.com"],
            "expected_success": True,
            "expected_count": 2,
        },
        {
            "name": "3. JSON array string",
            "input": '["https://httpbin.org/html", "https://example.com"]',
            "expected_success": True,
            "expected_count": 2,
        },
        {
            "name": "4a. Invalid input - empty string",
            "input": "",
            "expected_success": False,
            "expected_count": 0,
        },
        {
            "name": "4b. Invalid input - empty list",
            "input": [],
            "expected_success": False,
            "expected_count": 0,
        },
        {
            "name": "4c. Invalid input - malformed JSON",
            "input": '["https://example.com", "malformed',
            "expected_success": False,  # Should fail validation as invalid URL
            "expected_count": 0,
        },
        {
            "name": "4d. Invalid input - wrong type",
            "input": 12345,
            "expected_success": False,
            "expected_count": 0,
        },
        {
            "name": "5. JSON array with empty strings",
            "input": '["https://httpbin.org/html", "", "https://example.com"]',
            "expected_success": True,  # Should filter out empty strings
            "expected_count": 2,
        },
        {
            "name": "6. Single URL in JSON array",
            "input": '["https://httpbin.org/html"]',
            "expected_success": True,
            "expected_count": 1,
        },
        {
            "name": "7. JSON array with non-string values",
            "input": '["https://httpbin.org/html", 123, null, "https://example.com"]',
            "expected_success": False,  # Should reject invalid URLs like "123", "None"
            "expected_count": 0,
        },
        {
            "name": "8. Whitespace handling",
            "input": '["  https://httpbin.org/html  ", "  ", " https://example.com "]',
            "expected_success": True,  # Should strip whitespace
            "expected_count": 2,
        },
        {
            "name": "9. Non-JSON object in JSON string",
            "input": '{"url": "https://example.com"}',
            "expected_success": False,  # Should fail as it's not an array
            "expected_count": 0,
        },
        {
            "name": "10. Security test - invalid URL schemes",
            "input": '["https://example.com", "javascript:alert(1)", "data:text/html,<script>"]',
            "expected_success": False,  # Should reject dangerous schemes
            "expected_count": 0,
        },
        {
            "name": "11. Security test - too many URLs",
            "input": json.dumps([f"https://example{i}.com" for i in range(101)]),
            "expected_success": False,  # Should reject >100 URLs
            "expected_count": 0,
        },
        {
            "name": "12. Invalid URLs without schemes",
            "input": '["https://example.com", "example.com", "ftp://example.com"]',
            "expected_success": False,  # Should reject non-http(s) URLs
            "expected_count": 0,
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases):
        print(f"🧪 Test {i + 1}: {test_case['name']}")
        print(f"   Input: {test_case['input']!r}")

        try:
            success, result = parse_url_input(test_case["input"])

            # Check if result matches expectation
            test_passed = success == test_case["expected_success"]

            if success:
                actual_count = len(result) if isinstance(result, list) else 0
                count_correct = actual_count == test_case["expected_count"]
                test_passed = test_passed and count_correct

                print(f"   Result: {'✅ PASS' if test_passed else '❌ FAIL'}")
                print(f"   Success: {success}")
                print(
                    f"   URLs parsed: {actual_count} (expected: {test_case['expected_count']})"
                )
                print(f"   URLs: {result}")
            else:
                print(f"   Result: {'✅ PASS' if test_passed else '❌ FAIL'}")
                print(f"   Success: {success}")
                print(f"   Error: {result}")

            results.append(
                {
                    "test": test_case["name"],
                    "passed": test_passed,
                    "success": success,
                    "expected": test_case["expected_success"],
                    "result": result,
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
            elif isinstance(test["result"], list):
                print(f"     URLs found: {test['result']}")
    else:
        print("🎉 ALL TESTS PASSED!")

    return results


if __name__ == "__main__":
    results = test_url_parsing()

    # Exit with appropriate code
    failed_count = sum(1 for r in results if not r["passed"])
    exit(0 if failed_count == 0 else 1)
