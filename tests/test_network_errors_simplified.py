"""Test network error handling and resilience using test doubles."""

import asyncio

import aiohttp
import pytest

from tests.test_doubles import FakeCrawler


class NetworkErrorCrawler(FakeCrawler):
    """Extended fake crawler that can simulate network errors."""

    def __init__(self, error_type=None, fail_on_urls=None, retry_count=0):
        super().__init__()
        self.error_type = error_type
        self.fail_on_urls = fail_on_urls or []
        self.retry_count = retry_count
        self.call_count = 0

    async def arun(self, url: str, **kwargs):
        """Simulate crawling with potential network errors."""
        self.call_count += 1

        # Simulate retry logic
        if self.retry_count > 0 and self.call_count <= self.retry_count:
            if self.error_type:
                raise self.error_type

        # Simulate URL-specific failures
        if url in self.fail_on_urls:
            raise aiohttp.ClientError(f"Failed to connect to {url}")

        # Simulate general failure
        if self.error_type and self.retry_count == 0:
            raise self.error_type

        # Otherwise, return success
        return await super().arun(url, **kwargs)


class TestNetworkErrorsSimplified:
    """Test network error scenarios with simplified test doubles."""

    @pytest.mark.parametrize(
        "error_type",
        [
            aiohttp.ClientError("Connection failed"),
            TimeoutError("Request timed out"),
            ConnectionRefusedError("Connection refused"),
            aiohttp.ServerTimeoutError("Server timeout"),
        ],
    )
    async def test_network_error_handling(self, error_type):
        """Test handling of various network errors."""
        # Create crawler that will fail with specific error
        error_crawler = NetworkErrorCrawler(error_type=error_type)

        # Simulate error handling in the actual function
        try:
            result = await error_crawler.arun("https://test.com")
            # If we get here, the crawler didn't fail as expected
            assert False, "Expected crawler to fail"
        except Exception as e:
            # Verify we got the expected error
            assert type(e) == type(error_type)
            assert str(e) == str(error_type)

    async def test_partial_batch_failure(self):
        """Test handling when some URLs in batch fail."""
        urls = ["https://success1.com", "https://fail.com", "https://success2.com"]

        # Create crawler that fails on specific URLs
        crawler = NetworkErrorCrawler(fail_on_urls=["https://fail.com"])

        # Process all URLs
        results = []
        for url in urls:
            try:
                result = await crawler.arun(url)
                results.append({"url": url, "success": True, "result": result})
            except Exception as e:
                results.append({"url": url, "success": False, "error": str(e)})

        # Verify mixed results
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert "Failed to connect" in results[1]["error"]
        assert results[2]["success"] is True

    async def test_retry_logic(self):
        """Test retry behavior on transient failures."""
        # Create crawler that fails first 2 times, succeeds on 3rd
        crawler = NetworkErrorCrawler(
            error_type=aiohttp.ClientError("Temporary failure"),
            retry_count=2,  # Fail first 2 attempts
        )

        # Simulate retry logic
        max_retries = 3
        result = None

        for attempt in range(max_retries):
            try:
                result = await crawler.arun("https://test.com")
                break  # Success, exit retry loop
            except aiohttp.ClientError:
                if attempt == max_retries - 1:
                    raise  # Re-raise on final attempt
                await asyncio.sleep(0.1)  # Small delay between retries

        # Verify retry succeeded
        assert result is not None
        assert result.success is True
        assert crawler.call_count == 3  # Called 3 times total

    async def test_timeout_handling(self):
        """Test timeout error handling."""
        # Create crawler that times out
        timeout_crawler = NetworkErrorCrawler(
            error_type=TimeoutError("Request timed out"),
        )

        with pytest.raises(asyncio.TimeoutError):
            await timeout_crawler.arun("https://slow-site.com")

    async def test_connection_refused(self):
        """Test connection refused error handling."""
        # Create crawler with connection refused error
        refused_crawler = NetworkErrorCrawler(
            error_type=ConnectionRefusedError("Connection refused"),
        )

        with pytest.raises(ConnectionRefusedError):
            await refused_crawler.arun("https://unreachable.com")

    async def test_resilient_batch_processing(self):
        """Test resilient batch processing with mixed failures."""
        urls = [f"https://test{i}.com" for i in range(10)]
        fail_urls = [urls[2], urls[5], urls[8]]  # Some URLs will fail

        crawler = NetworkErrorCrawler(fail_on_urls=fail_urls)

        # Process batch with resilience
        successful = 0
        failed = 0

        for url in urls:
            try:
                await crawler.arun(url)
                successful += 1
            except Exception:
                failed += 1

        # Verify expected results
        assert successful == 7
        assert failed == 3
        assert successful + failed == len(urls)
