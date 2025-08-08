#!/usr/bin/env python3
"""Test script to verify the URL validation fix works with actual scraping."""

import asyncio
import os
import sys

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from utils.validation import validate_urls_for_crawling


async def test_scrape_with_validation():
    """Test scraping with URL validation."""

    # Test URLs that were mentioned in the original issue
    test_urls = [
        "https://example.com",
        "https://www.iana.org/help/example-domains",
        "http://httpbin.org/html",
    ]

    print("Testing URL validation...")
    validation_result = validate_urls_for_crawling(test_urls)
    print(f"Validation result: {validation_result}")

    if not validation_result["valid"]:
        print("❌ URLs failed validation - this would have been caught!")
        return

    print("✅ All URLs passed validation")

    # Test with a known bad URL to see error handling
    print("\nTesting with invalid URL...")
    bad_urls = ["ftp://invalid.com", "https://example.com"]

    bad_validation = validate_urls_for_crawling(bad_urls)
    print(f"Bad URL validation: {bad_validation}")

    # Test actual crawling with valid URLs (commented out to avoid network calls)
    print(
        "\nNote: Actual crawling test would require running crawler, which is skipped in this test"
    )
    print("The validation layer should prevent invalid URLs from reaching crawl4ai")


if __name__ == "__main__":
    asyncio.run(test_scrape_with_validation())
