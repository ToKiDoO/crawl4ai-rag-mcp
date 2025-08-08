#!/usr/bin/env python3
"""Test script to reproduce the batch crawling URL validation error."""

import asyncio
import os
import sys

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from crawl4ai import AsyncWebCrawler

from services.crawling import crawl_batch


async def test_batch_crawling():
    """Test batch crawling with the exact URLs that were failing."""

    # The URLs from the original error report
    test_urls = [
        "https://example.com",
        "https://www.iana.org/help/example-domains",
    ]

    print("Testing batch crawling with problematic URLs...")
    print(f"URLs: {test_urls}")

    crawler = AsyncWebCrawler()

    try:
        print("Calling crawl_batch function...")
        results = await crawl_batch(crawler, test_urls, max_concurrent=2)

        print("✅ Batch crawling succeeded!")
        print(f"Results count: {len(results)}")

        for result in results:
            url = result.get("url", "unknown")
            markdown_length = len(result.get("markdown", ""))
            print(f"  {url}: {markdown_length} chars")

    except Exception as e:
        print(f"❌ Batch crawling failed: {e}")
        print(f"Exception type: {type(e)}")

        # Check if the error message contains the truncated URL
        error_str = str(e)
        if ".../help/example-domains" in error_str:
            print("🔍 Found the truncated URL in error message!")
            print(f"Full error: {error_str}")
        else:
            print("Error does not contain the truncated URL pattern")

    finally:
        # Note: Using proper async context manager would be better
        pass


async def test_malformed_urls():
    """Test with intentionally malformed URLs to see error handling."""

    print("\nTesting with malformed URLs to trigger validation errors...")

    malformed_urls = [
        "https://example.com",
        ".../help/example-domains",  # This should trigger the validation error
    ]

    crawler = AsyncWebCrawler()

    try:
        print(f"Testing with: {malformed_urls}")
        results = await crawl_batch(crawler, malformed_urls, max_concurrent=2)
        print("❌ Expected validation error but got success!")

    except Exception as e:
        print(f"✅ Caught expected validation error: {e}")
        print(f"Exception type: {type(e)}")


if __name__ == "__main__":
    asyncio.run(test_batch_crawling())
    asyncio.run(test_malformed_urls())
