#!/usr/bin/env python3
"""Test the batch URL processing fix."""

import json
import os
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_url_parsing_logic():
    """Test the URL parsing logic that's now in tools.py."""

    def parse_url_parameter(url):
        """Replicate the logic from the fixed scrape_urls function."""
        if isinstance(url, str):
            # Check if it's a JSON string representation of a list
            if url.strip().startswith("[") and url.strip().endswith("]"):
                try:
                    parsed = json.loads(url)
                    if isinstance(parsed, list):
                        urls = parsed
                    else:
                        urls = [url]  # Single URL
                except json.JSONDecodeError:
                    urls = [url]  # Single URL, JSON parsing failed
            else:
                urls = [url]  # Single URL
        else:
            urls = url  # Assume it's already a list
        return urls

    # Test cases
    test_cases = [
        # Single URL string
        {
            "input": "https://example.com",
            "expected": ["https://example.com"],
            "description": "Single URL string",
        },
        # JSON string list (the problematic case from MCP)
        {
            "input": '["https://example.com", "https://httpbin.org/html"]',
            "expected": ["https://example.com", "https://httpbin.org/html"],
            "description": "JSON string representation of URL list",
        },
        # Python list (should still work)
        {
            "input": ["https://example.com", "https://httpbin.org/html"],
            "expected": ["https://example.com", "https://httpbin.org/html"],
            "description": "Python list of URLs",
        },
        # Edge case: string that looks like JSON but isn't
        {
            "input": "[not valid json",
            "expected": ["[not valid json"],
            "description": "Invalid JSON string (should be treated as single URL)",
        },
        # Edge case: single URL that looks like a list but isn't JSON
        {
            "input": "https://example.com/path[with]brackets",
            "expected": ["https://example.com/path[with]brackets"],
            "description": "URL with brackets (not JSON)",
        },
    ]

    print("Testing URL parameter parsing logic:")
    print("=" * 60)

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        result = parse_url_parameter(test_case["input"])
        passed = result == test_case["expected"]
        all_passed = all_passed and passed

        print(f"\nTest {i}: {test_case['description']}")
        print(
            f"Input: {test_case['input']} (type: {type(test_case['input']).__name__})"
        )
        print(f"Expected: {test_case['expected']}")
        print(f"Got: {result}")
        print(f"Status: {'✓ PASS' if passed else '✗ FAIL'}")

    print("\n" + "=" * 60)
    print(
        f"Overall result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}"
    )

    return all_passed


if __name__ == "__main__":
    success = test_url_parsing_logic()
    sys.exit(0 if success else 1)
