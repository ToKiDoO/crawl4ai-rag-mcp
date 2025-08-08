#!/usr/bin/env python3
"""Debug script to reproduce the URL validation error."""

import asyncio
import sys
import os
import logging

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from crawl4ai import AsyncWebCrawler
from services.crawling import crawl_batch
from utils.validation import validate_urls_for_crawling, validate_crawl_url

# Set up logging to see all details
logging.basicConfig(level=logging.DEBUG)

async def test_direct_crawl4ai_call():
    """Test calling crawl4ai directly with potentially problematic URLs."""
    
    # The URLs mentioned in the error
    test_urls = [
        "https://example.com",
        "https://www.iana.org/help/example-domains"
    ]
    
    print("Testing individual URL validation...")
    for url in test_urls:
        result = validate_crawl_url(url)
        print(f"URL: {url}")
        print(f"  Valid: {result['valid']}")
        if result['valid']:
            print(f"  Normalized: {result['normalized_url']}")
        else:
            print(f"  Error: {result['error']}")
        print()
    
    print("Testing batch validation...")
    batch_result = validate_urls_for_crawling(test_urls)
    print(f"Batch result: {batch_result}")
    print()
    
    # Test what happens when we pass these directly to crawl4ai
    print("Testing direct crawl4ai call...")
    crawler = AsyncWebCrawler()
    
    try:
        print("Attempting to crawl with crawl4ai...")
        from crawl4ai import CrawlerRunConfig
        
        # Try each URL individually to isolate which one causes the error
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            try:
                result = await crawler.arun(url=url, config=CrawlerRunConfig())
                print(f"  Success: {result.success}")
                if not result.success:
                    print(f"  Error: {result.error_message}")
            except Exception as e:
                print(f"  Exception: {e}")
                print(f"  Exception type: {type(e)}")
    
    except Exception as e:
        print(f"Error during crawl4ai setup: {e}")
        print(f"Exception type: {type(e)}")
    
    finally:
        await crawler.aclose()

if __name__ == "__main__":
    asyncio.run(test_direct_crawl4ai_call())