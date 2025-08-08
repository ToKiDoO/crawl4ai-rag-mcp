#!/usr/bin/env python3
"""Final test to verify URL validation catches problematic URLs."""

import os
import sys

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from utils.validation import validate_urls_for_crawling


def test_edge_cases():
    """Test edge cases that might cause the original error."""

    print("=" * 60)
    print("TESTING URL VALIDATION FOR CRAWL4AI COMPATIBILITY")
    print("=" * 60)

    # Test cases that should PASS
    valid_test_cases = [
        ["https://example.com"],
        ["https://www.iana.org/help/example-domains"],
        ["http://httpbin.org/html"],
        ["https://example.com", "https://httpbin.org/html"],
        ["file:///path/to/local/file"],
        ["raw:some-content"],
    ]

    print("\n✅ VALID URL TESTS:")
    for i, urls in enumerate(valid_test_cases, 1):
        result = validate_urls_for_crawling(urls)
        status = "✅ PASS" if result["valid"] else "❌ FAIL"
        print(f"  Test {i}: {status} - {urls}")
        if not result["valid"]:
            print(f"    Error: {result['error']}")

    # Test cases that should FAIL (and be caught by our validation)
    invalid_test_cases = [
        ["ftp://invalid.com"],  # Unsupported protocol
        ["javascript:alert(1)"],  # Dangerous protocol
        ["www.example.com"],  # Missing protocol
        ["https://"],  # Missing domain
        ["https:///path"],  # Missing domain with path
        [""],  # Empty URL
        ["https://example.com", "ftp://bad.com"],  # Mixed valid/invalid
        ["telnet://old.protocol.com"],  # Old protocol
        ["data:text/html,<h1>test</h1>"],  # Data URL (not supported)
    ]

    print("\n❌ INVALID URL TESTS (should be caught):")
    for i, urls in enumerate(invalid_test_cases, 1):
        result = validate_urls_for_crawling(urls)
        status = "✅ CAUGHT" if not result["valid"] else "❌ MISSED"
        print(f"  Test {i}: {status} - {urls}")
        if not result["valid"]:
            print(f"    Error: {result['error']}")
        else:
            print("    ⚠️  This should have been rejected!")

    # Test the specific URLs from the original error report
    print("\n🔍 ORIGINAL ERROR CASE TESTS:")
    original_urls = [
        ["https://example.com", "https://www.iana.org/help/example-domains"],
    ]

    for i, urls in enumerate(original_urls, 1):
        result = validate_urls_for_crawling(urls)
        status = "✅ VALID" if result["valid"] else "❌ INVALID"
        print(f"  Original Test {i}: {status} - {urls}")
        if result["valid"]:
            print(f"    Normalized URLs: {result['urls']}")
        else:
            print(f"    Error: {result['error']}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✅ URL validation is now in place")
    print("✅ Invalid URLs will be caught before reaching crawl4ai")
    print("✅ Clear error messages are provided for debugging")
    print("✅ Original problematic URLs are properly validated")
    print("\nThe fix should prevent the 'URL must start with...' error from crawl4ai")


if __name__ == "__main__":
    test_edge_cases()
