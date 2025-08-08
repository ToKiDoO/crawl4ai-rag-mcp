#!/usr/bin/env python3
"""
Test script to debug batch URL scraping issues.
"""

import asyncio
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


from crawl4ai_mcp import scrape_urls


class MockContext:
    """Mock context for testing"""

    def __init__(self):
        self.request_context = MockRequestContext()


class MockRequestContext:
    """Mock request context"""

    def __init__(self):
        self.lifespan_context = MockLifespanContext()


class MockLifespanContext:
    """Mock lifespan context - we'll need to import the actual classes"""

    def __init__(self):
        self.crawler = None
        self.database_client = None


async def test_batch_scraping():
    """Test batch URL scraping with mock context"""

    # Test URLs - using simple, reliable sites
    test_urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/html",
        "https://httpbin.org/robots.txt",
    ]

    print("Testing batch URL scraping...")
    print(f"URLs to test: {test_urls}")

    try:
        # Create mock context
        ctx = MockContext()

        # Test with return_raw_markdown=True to avoid database operations
        result = await scrape_urls(
            ctx=ctx,
            url=test_urls,
            max_concurrent=2,
            batch_size=10,
            return_raw_markdown=True,
        )

        print("Result:")
        print(result)

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_batch_scraping())
