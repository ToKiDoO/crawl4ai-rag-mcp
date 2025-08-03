"""Test network error handling and resilience."""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
import aiohttp

from tests.test_helpers import TestDataBuilder

class TestNetworkErrors:
    """Test network error scenarios."""
    
    @pytest.mark.parametrize("error_type", [
        aiohttp.ClientError("Connection failed"),
        asyncio.TimeoutError("Request timed out"),
        ConnectionRefusedError("Connection refused"),
        aiohttp.ServerTimeoutError("Server timeout"),
    ])
    async def test_network_error_handling(self, error_type):
        """Test handling of various network errors."""
        from src.crawl4ai_mcp import scrape_urls
        
        with patch('crawl4ai.AsyncWebCrawler') as mock_crawler:
            # Make crawler.arun raise network error
            mock_instance = MagicMock()
            mock_instance.arun.side_effect = error_type
            mock_crawler.return_value.__aenter__.return_value = mock_instance
            
            result = await scrape_urls("https://test.com")
            
            # Should return error response, not crash
            assert isinstance(result, dict)
            assert result.get("success") is False
            assert "error" in result
    
    async def test_partial_batch_failure(self):
        """Test handling when some URLs in batch fail."""
        from src.crawl4ai_mcp import scrape_urls
        
        urls = [
            "https://success1.com",
            "https://fail.com", 
            "https://success2.com"
        ]
        
        with patch('crawl4ai.AsyncWebCrawler') as mock_crawler:
            mock_instance = MagicMock()
            
            # Make second URL fail
            async def mock_arun(url, **kwargs):
                if "fail" in url:
                    raise aiohttp.ClientError("Failed to connect")
                return MagicMock(
                    success=True,
                    html="<html>Success</html>",
                    markdown="Success"
                )
            
            mock_instance.arun = mock_arun
            mock_crawler.return_value.__aenter__.return_value = mock_instance
            
            # Process all URLs
            results = []
            for url in urls:
                result = await scrape_urls(url)
                results.append(result)
            
            # Verify mixed results
            assert results[0]["success"] is True
            assert results[1]["success"] is False
            assert results[2]["success"] is True
    
    async def test_retry_logic(self):
        """Test retry behavior on transient failures."""
        from src.utils_refactored import crawl_url
        
        call_count = 0
        
        with patch('crawl4ai.AsyncWebCrawler') as mock_crawler:
            mock_instance = MagicMock()
            
            async def mock_arun(url, **kwargs):
                nonlocal call_count
                call_count += 1
                
                # Fail first 2 times, succeed on 3rd
                if call_count < 3:
                    raise aiohttp.ClientError("Temporary failure")
                
                return MagicMock(
                    success=True,
                    html="<html>Success after retry</html>",
                    markdown="Success after retry"
                )
            
            mock_instance.arun = mock_arun
            mock_crawler.return_value.__aenter__.return_value = mock_instance
            
            # Should retry and eventually succeed
            result = await crawl_url("https://test.com", max_retries=3)
            
            assert call_count == 3
            assert result is not None
            assert "Success after retry" in result.markdown

if __name__ == "__main__":
    pytest.main([__file__, "-v"])