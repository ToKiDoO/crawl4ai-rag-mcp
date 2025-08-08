#!/usr/bin/env python3
"""Test the JSON string parsing fixes for both scrape_urls and smart_crawl_url tools."""

import json
import os
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def parse_url_parameter(url):
    """Replicate the URL parsing logic from scrape_urls function."""
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


def parse_query_parameter(query):
    """Replicate the query parsing logic from smart_crawl_url function."""
    parsed_query = None
    if query is not None:
        if isinstance(query, str):
            # Check if it's a JSON string representation of a list
            if query.strip().startswith("[") and query.strip().endswith("]"):
                try:
                    parsed = json.loads(query)
                    if isinstance(parsed, list):
                        parsed_query = parsed
                    else:
                        parsed_query = [query]  # Single query
                except json.JSONDecodeError:
                    parsed_query = [query]  # Single query, JSON parsing failed
            else:
                parsed_query = [query]  # Single query
        else:
            parsed_query = query  # Assume it's already a list
    return parsed_query


def test_url_parameter_parsing():
    """Test URL parameter parsing for scrape_urls."""
    print("Testing URL parameter parsing (scrape_urls):")
    print("=" * 60)

    test_cases = [
        {
            "input": "https://example.com",
            "expected": ["https://example.com"],
            "description": "Single URL string",
        },
        {
            "input": '["https://example.com", "https://httpbin.org/html"]',
            "expected": ["https://example.com", "https://httpbin.org/html"],
            "description": "JSON string representation of URL list",
        },
        {
            "input": ["https://example.com", "https://httpbin.org/html"],
            "expected": ["https://example.com", "https://httpbin.org/html"],
            "description": "Python list of URLs",
        },
    ]

    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        result = parse_url_parameter(test_case["input"])
        passed = result == test_case["expected"]
        all_passed = all_passed and passed

        print(f"Test {i}: {test_case['description']}")
        print(f"  Input: {test_case['input']}")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Got: {result}")
        print(f"  Status: {'✓ PASS' if passed else '✗ FAIL'}")
        print()

    return all_passed


def test_query_parameter_parsing():
    """Test query parameter parsing for smart_crawl_url."""
    print("Testing query parameter parsing (smart_crawl_url):")
    print("=" * 60)

    test_cases = [
        {
            "input": None,
            "expected": None,
            "description": "None query",
        },
        {
            "input": "single query",
            "expected": ["single query"],
            "description": "Single query string",
        },
        {
            "input": '["query1", "query2", "query3"]',
            "expected": ["query1", "query2", "query3"],
            "description": "JSON string representation of query list",
        },
        {
            "input": ["query1", "query2", "query3"],
            "expected": ["query1", "query2", "query3"],
            "description": "Python list of queries",
        },
        {
            "input": "[invalid json query",
            "expected": ["[invalid json query"],
            "description": "Invalid JSON string (should be treated as single query)",
        },
    ]

    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        result = parse_query_parameter(test_case["input"])
        passed = result == test_case["expected"]
        all_passed = all_passed and passed

        print(f"Test {i}: {test_case['description']}")
        print(f"  Input: {test_case['input']}")
        print(f"  Expected: {test_case['expected']}")
        print(f"  Got: {result}")
        print(f"  Status: {'✓ PASS' if passed else '✗ FAIL'}")
        print()

    return all_passed


def main():
    """Run all tests."""
    print("Testing JSON string parsing fixes for MCP tools")
    print("=" * 80)
    print()

    url_tests_passed = test_url_parameter_parsing()
    print()
    query_tests_passed = test_query_parameter_parsing()

    print("=" * 80)
    overall_result = url_tests_passed and query_tests_passed
    print(
        f"Overall result: {'✓ ALL TESTS PASSED' if overall_result else '✗ SOME TESTS FAILED'}"
    )

    return overall_result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
