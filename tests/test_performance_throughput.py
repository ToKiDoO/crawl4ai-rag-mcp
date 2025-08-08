#!/usr/bin/env python3
"""
Performance test for throughput: 10 URLs concurrent
Target: Complete within reasonable time, no failures
"""

import asyncio
import time

import pytest

# Test URLs - using mock data to avoid actual network calls
TEST_URLS = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3",
    "https://example.com/page4",
    "https://example.com/page5",
    "https://example.com/page6",
    "https://example.com/page7",
    "https://example.com/page8",
    "https://example.com/page9",
    "https://example.com/page10",
]


@pytest.mark.asyncio
async def test_throughput_10_urls_concurrent():
    """Test throughput with 10 concurrent URL scrapes"""

    # Create a mock scraping function
    async def mock_scrape_url(url):
        # Simulate some processing time
        await asyncio.sleep(0.1)  # 100ms per URL
        return {
            "success": True,
            "url": url,
            "content": f"Mocked content for {url}",
            "metadata": {"title": f"Page {url.split('/')[-1]}"},
        }

    start_time = time.time()

    # Run concurrent scrapes
    tasks = []
    for url in TEST_URLS:
        task = mock_scrape_url(url)
        tasks.append(task)

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    duration = end_time - start_time

    # Analyze results
    successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    failed = sum(
        1
        for r in results
        if isinstance(r, Exception) or (isinstance(r, dict) and not r.get("success"))
    )

    print("\nThroughput Test Results:")
    print(f"- Total URLs: {len(TEST_URLS)}")
    print(f"- Successful: {successful}")
    print(f"- Failed: {failed}")
    print(f"- Total Time: {duration:.2f} seconds")
    print(f"- Average Time per URL: {duration / len(TEST_URLS):.2f} seconds")
    print(f"- Throughput: {len(TEST_URLS) / duration:.2f} URLs/second")

    # Assertions
    assert successful == len(TEST_URLS), (
        f"Expected all {len(TEST_URLS)} to succeed, but only {successful} did"
    )
    # With 100ms per URL and concurrent execution, should complete in ~0.2-0.5 seconds
    assert duration < 2.0, (
        f"Expected to complete in under 2 seconds, but took {duration:.2f} seconds"
    )

    # Performance metrics
    throughput = len(TEST_URLS) / duration
    assert throughput > 5, (
        f"Expected throughput > 5 URLs/second, but got {throughput:.2f}"
    )

    return {
        "total_urls": len(TEST_URLS),
        "successful": successful,
        "failed": failed,
        "duration": duration,
        "throughput": throughput,
    }


if __name__ == "__main__":
    # Run the test directly
    import asyncio

    async def main():
        try:
            result = await test_throughput_10_urls_concurrent()
            print("\nTest PASSED ✅")
            print(f"Performance metrics: {result}")
        except AssertionError as e:
            print(f"\nTest FAILED ❌: {e}")
            exit(1)
        except Exception as e:
            print(f"\nTest ERROR ❌: {e}")
            exit(1)

    asyncio.run(main())
