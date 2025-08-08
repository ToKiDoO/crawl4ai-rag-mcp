#!/usr/bin/env python3
"""Test script to verify URL validation fix for crawl4ai compatibility."""

import os
import sys

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from utils.validation import validate_crawl_url, validate_urls_for_crawling


def test_url_validation():
    """Test URL validation functions."""

    print("Testing individual URL validation...")

    # Test valid URLs
    valid_urls = [
        "https://example.com",
        "https://www.iana.org/help/example-domains",
        "http://httpbin.org/html",
        "file:///path/to/local/file.html",
        "raw:some-raw-content",
    ]

    for url in valid_urls:
        result = validate_crawl_url(url)
        print(f"✓ {url} -> Valid: {result['valid']}")
        if result["valid"]:
            print(f"  Normalized: {result['normalized_url']}")
        else:
            print(f"  Error: {result['error']}")

    print("\nTesting invalid URLs...")

    # Test invalid URLs
    invalid_urls = [
        "ftp://example.com",  # Unsupported protocol
        "www.example.com",  # Missing protocol
        "https://",  # Missing domain
        "https:///path",  # Missing domain
        "",  # Empty URL
        None,  # None URL
        "javascript:alert(1)",  # Unsupported protocol
    ]

    for url in invalid_urls:
        result = validate_crawl_url(url)
        print(f"✗ {url} -> Valid: {result['valid']}")
        if not result["valid"]:
            print(f"  Error: {result['error']}")

    print("\nTesting batch URL validation...")

    # Test batch validation with mixed valid/invalid URLs
    test_batch = [
        "https://example.com",
        "ftp://invalid.com",  # This should fail
        "https://www.iana.org/help/example-domains",
    ]

    batch_result = validate_urls_for_crawling(test_batch)
    print(f"Batch validation result: {batch_result}")

    # Test with all valid URLs
    valid_batch = [
        "https://example.com",
        "https://www.iana.org/help/example-domains",
        "http://httpbin.org/html",
    ]

    valid_batch_result = validate_urls_for_crawling(valid_batch)
    print(f"Valid batch result: {valid_batch_result}")


if __name__ == "__main__":
    test_url_validation()
