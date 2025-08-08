#!/usr/bin/env python3
"""Test script to validate URL handling in the MCP server."""

import asyncio
import json

# Test the validation function directly
from src.utils.validation import validate_urls_for_crawling


def test_url_validation():
    """Test URL validation function with various inputs."""
    print("Testing URL validation function...")
    print("=" * 50)

    # Test cases
    test_cases = [
        (["https://example.com"], "Valid HTTPS URL"),
        (["http://example.org"], "Valid HTTP URL"),
        (["example.com"], "URL without protocol"),
        ([".../help/example-domains"], "Truncated URL"),
        (["https://example.com", ".../invalid"], "Mixed valid and invalid"),
        (["https://example.com", "example.org"], "Mixed with auto-fixable"),
        (["ftp://example.com"], "Invalid protocol"),
        ([""], "Empty URL"),
        (["https://"], "Incomplete URL"),
    ]

    for urls, description in test_cases:
        print(f"\nTest: {description}")
        print(f"Input: {urls}")

        try:
            result = validate_urls_for_crawling(urls)
            if result["valid"]:
                print(f"✓ Valid - Output URLs: {result['urls']}")
                if result.get("warnings"):
                    print(f"  Warnings: {result['warnings']}")
            else:
                print(f"✗ Invalid - Error: {result['error']}")
                if result.get("invalid_urls"):
                    print(f"  Invalid URLs: {result['invalid_urls']}")
                if result.get("valid_urls"):
                    print(f"  Valid URLs: {result['valid_urls']}")
        except Exception as e:
            print(f"✗ Exception: {e}")

    print("\n" + "=" * 50)
    print("URL validation testing complete!")


async def test_mcp_scrape_urls():
    """Test the actual MCP scrape_urls function if running locally."""
    print("\nTesting MCP scrape_urls function...")
    print("=" * 50)

    try:
        # Import the MCP context and tools
        from crawl4ai import AsyncWebCrawler
        from fastmcp import Context

        from src.core.context import Crawl4AIContext, get_app_context, set_app_context
        from src.services.crawling import process_urls_for_mcp

        # Create a mock context for testing
        print("Setting up test context...")

        # Initialize crawler
        crawler = AsyncWebCrawler()
        await crawler.start()

        # Create mock database client (we'll use return_raw_markdown=True to skip DB)
        class MockDatabase:
            pass

        # Create Crawl4AI context
        crawl4ai_ctx = Crawl4AIContext(
            crawler=crawler,
            database_client=MockDatabase(),
            repo_extractor=None,
        )

        # Set global context
        set_app_context(crawl4ai_ctx)

        # Create mock FastMCP context
        mock_ctx = Context()
        mock_ctx.crawl4ai_context = crawl4ai_ctx

        # Test cases for actual crawling
        test_urls = [
            ["https://example.com"],  # Valid URL
            ["example.com"],  # Should be auto-fixed to https://example.com
            [".../help/example-domains"],  # Should be rejected
        ]

        for urls in test_urls:
            print(f"\nTesting URLs: {urls}")
            try:
                result = await process_urls_for_mcp(
                    ctx=mock_ctx,
                    urls=urls,
                    return_raw_markdown=True,
                )
                result_data = json.loads(result)
                if result_data.get("success"):
                    print(
                        f"✓ Success - Crawled {len(result_data.get('results', []))} URLs"
                    )
                else:
                    print(f"✗ Failed - Error: {result_data.get('error')}")
            except Exception as e:
                print(f"✗ Exception during crawl: {e}")

        # Clean up
        await crawler.close()

    except ImportError as e:
        print(f"Cannot test MCP functions directly - missing imports: {e}")
        print("This is expected if not running in the proper environment")
    except Exception as e:
        print(f"Error during MCP testing: {e}")

    print("\n" + "=" * 50)
    print("MCP testing complete!")


if __name__ == "__main__":
    # Test validation function
    test_url_validation()

    # Test MCP scrape_urls if possible
    print("\nAttempting to test MCP scrape_urls function...")
    try:
        asyncio.run(test_mcp_scrape_urls())
    except Exception as e:
        print(f"Could not test MCP function: {e}")
