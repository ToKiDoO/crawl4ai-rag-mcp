# Exercise 2 Solutions: Advanced Async Testing with FastMCP Patterns

This document provides comprehensive solutions for Exercise 2, demonstrating advanced async testing patterns specifically for FastMCP servers.

## Complete Solution Code

### simple_mcp_server.py (Reference Implementation)

The implementation provided in the exercise is complete. Key patterns it demonstrates:

1. **MCP Tool Patterns**: Simulated `@mcp.tool()` decorator usage
2. **Context Management**: Proper context handling with shared resources
3. **Async Generators**: Streaming results pattern
4. **Concurrency Control**: Semaphore-based rate limiting
5. **Error Handling**: Custom exceptions with proper error codes

### test_exercise_2.py (Complete Solutions)

```python
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from simple_mcp_server import SimpleMCPServer, Context, ServerContext, MCPToolError

class TestSimpleMCPServer:
    """Test MCP server tool functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create server context with mocked dependencies
        self.server_context = ServerContext()
        self.server_context.crawler = AsyncMock()
        self.server_context.database = AsyncMock()
        self.server_context.cache = {}
        
        # Create MCP server instance
        self.server = SimpleMCPServer(self.server_context)
        
        # Create test context
        self.ctx = Context(lifespan_context=self.server_context)
    
    @pytest.mark.asyncio
    async def test_crawl_url_success(self):
        """Test successful URL crawling"""
        # Arrange
        url = "https://example.com/test"
        expected_content = "Sample page content"
        expected_title = "Sample Page"
        
        # Configure crawler mock to return realistic data
        self.server_context.crawler.crawl.return_value = {
            'content': expected_content,
            'title': expected_title
        }
        
        # Act
        result = await self.server.crawl_url(self.ctx, url)
        
        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['status'] == 'success'
        assert result['url'] == url
        assert result['content'] == expected_content
        assert result['title'] == expected_title
        assert 'id' in result
        assert 'timestamp' in result
        
        # Verify crawler was called with correct parameters
        self.server_context.crawler.crawl.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_crawl_url_invalid_input(self):
        """Test crawl_url with invalid inputs"""
        # Test cases with invalid inputs
        invalid_inputs = [
            ("", "URL must be a non-empty string"),
            (None, "URL must be a non-empty string"),
            (123, "URL must be a non-empty string"),
            ("ftp://example.com", "Only HTTP/HTTPS URLs supported"),
            ("not-a-url", "Only HTTP/HTTPS URLs supported"),
        ]
        
        for invalid_input, expected_message in invalid_inputs:
            with pytest.raises(MCPToolError) as exc_info:
                await self.server.crawl_url(self.ctx, invalid_input)
            
            # Verify error details
            assert exc_info.value.code == -32602
            assert expected_message in exc_info.value.message
            
            # Verify crawler was not called
            self.server_context.crawler.crawl.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_crawl_url_timeout(self):
        """Test timeout handling in crawl_url"""
        # Arrange
        url = "https://slow-server.com"
        timeout = 1
        
        # Configure crawler mock to raise asyncio.TimeoutError
        self.server_context.crawler.crawl.side_effect = asyncio.TimeoutError()
        
        # Act & Assert
        with pytest.raises(MCPToolError) as exc_info:
            await self.server.crawl_url(self.ctx, url, timeout=timeout)
        
        # Verify error details
        assert exc_info.value.code == -32603
        assert f"Crawling timeout after {timeout}s" in exc_info.value.message
        
        # Verify crawler was called
        self.server_context.crawler.crawl.assert_called_once_with(url)
    
    @pytest.mark.asyncio
    async def test_crawl_url_crawler_exception(self):
        """Test handling of crawler exceptions"""
        # Arrange
        url = "https://error-prone.com"
        error_message = "Network connection failed"
        
        # Configure crawler mock to raise generic Exception
        self.server_context.crawler.crawl.side_effect = Exception(error_message)
        
        # Act & Assert
        with pytest.raises(MCPToolError) as exc_info:
            await self.server.crawl_url(self.ctx, url)
        
        # Verify error details
        assert exc_info.value.code == -32603
        assert f"Crawling failed: {error_message}" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_batch_crawl_success(self):
        """Test successful batch crawling"""
        # Arrange
        urls = [
            "https://example.com/1",
            "https://test.org/2", 
            "https://sample.net/3"
        ]
        
        # Configure crawler mock to return different data for each URL
        def mock_crawl(url):
            return {
                'content': f'Content for {url}',
                'title': f'Title for {url}'
            }
        
        self.server_context.crawler.crawl.side_effect = mock_crawl
        
        # Act
        results = await self.server.batch_crawl(self.ctx, urls)
        
        # Assert
        assert len(results) == 3
        
        # Verify all URLs were processed successfully
        for i, result in enumerate(results):
            assert result['status'] == 'success'
            assert result['url'] == urls[i]
            assert f'Content for {urls[i]}' in result['content']
            assert f'Title for {urls[i]}' in result['title']
        
        # Verify crawler was called for each URL
        assert self.server_context.crawler.crawl.call_count == 3
        
        # Verify concurrency was respected (calls should be concurrent, not sequential)
        # This is verified by timing in a separate test
    
    @pytest.mark.asyncio  
    async def test_batch_crawl_concurrency_control(self):
        """Test that concurrency limits are respected"""
        # Arrange
        urls = [f"https://site{i}.com" for i in range(10)]  # 10 URLs
        concurrency = 3
        
        # Track concurrent calls
        active_calls = 0
        max_concurrent = 0
        
        async def mock_crawl_with_tracking(url):
            nonlocal active_calls, max_concurrent
            active_calls += 1
            max_concurrent = max(max_concurrent, active_calls)
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            active_calls -= 1
            return {'content': f'Content for {url}', 'title': f'Title for {url}'}
        
        self.server_context.crawler.crawl.side_effect = mock_crawl_with_tracking
        
        # Act
        results = await self.server.batch_crawl(self.ctx, urls, concurrency=concurrency)
        
        # Assert
        assert len(results) == 10
        assert all(result['status'] == 'success' for result in results)
        
        # Verify concurrency was respected
        assert max_concurrent <= concurrency
        
        # With proper concurrency control, max should be close to limit
        assert max_concurrent >= concurrency - 1  # Allow for timing variations
    
    @pytest.mark.asyncio
    async def test_batch_crawl_partial_failures(self):
        """Test batch crawling with some failures"""
        # Arrange
        urls = [
            "https://good1.com",     # Should succeed
            "https://bad.com",       # Should fail  
            "https://good2.com",     # Should succeed
        ]
        
        # Configure crawler to fail for "bad.com"
        def mock_crawl_with_failures(url):
            if "bad.com" in url:
                raise Exception("Server error")
            return {'content': f'Content for {url}', 'title': f'Title for {url}'}
        
        self.server_context.crawler.crawl.side_effect = mock_crawl_with_failures
        
        # Act
        results = await self.server.batch_crawl(self.ctx, urls)
        
        # Assert
        assert len(results) == 3  # All URLs processed, even failed ones
        
        # Verify successful URLs return success results
        success_results = [r for r in results if r['status'] == 'success']
        assert len(success_results) == 2
        
        success_urls = [r['url'] for r in success_results]
        assert "https://good1.com" in success_urls
        assert "https://good2.com" in success_urls
        
        # Verify failed URLs return error results (not exceptions)
        error_results = [r for r in results if r['status'] == 'error']
        assert len(error_results) == 1
        assert error_results[0]['url'] == "https://bad.com"
        assert "Failed to crawl" in error_results[0]['error']
    
    @pytest.mark.asyncio
    async def test_batch_crawl_invalid_concurrency(self):
        """Test batch crawl with invalid concurrency values"""
        # Arrange
        urls = ["https://example.com"]
        invalid_concurrency_values = [0, -1, 25]
        
        # Act & Assert
        for invalid_concurrency in invalid_concurrency_values:
            with pytest.raises(MCPToolError) as exc_info:
                await self.server.batch_crawl(self.ctx, urls, concurrency=invalid_concurrency)
            
            assert exc_info.value.code == -32602
            assert "Concurrency must be between 1 and 20" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_stream_crawl_results_success(self):
        """Test streaming crawl results"""
        # Arrange
        urls = [
            "https://fast.com",    # Should complete quickly
            "https://slow.com",    # Should complete slowly  
            "https://medium.com"   # Should complete at medium speed
        ]
        
        # Configure crawler mock with different delays for each URL
        async def mock_crawl_with_delays(url):
            if "fast.com" in url:
                await asyncio.sleep(0.05)  # Fast
            elif "slow.com" in url:
                await asyncio.sleep(0.15)  # Slow  
            else:
                await asyncio.sleep(0.10)  # Medium
            
            return {'content': f'Content for {url}', 'title': f'Title for {url}'}
        
        self.server_context.crawler.crawl.side_effect = mock_crawl_with_delays
        
        # Act - Collect results as they're yielded
        results = []
        async for result in self.server.stream_crawl_results(self.ctx, urls):
            results.append(result)
        
        # Assert
        assert len(results) == 3
        
        # Verify results arrive in completion order (not input order)
        # Fast should be first, slow should be last
        assert "fast.com" in results[0]['url']
        assert "slow.com" in results[-1]['url']
        
        # Verify all URLs are eventually processed
        result_urls = [result['url'] for result in results]
        for url in urls:
            assert url in result_urls
    
    @pytest.mark.asyncio
    async def test_stream_crawl_results_with_errors(self):
        """Test streaming with some URL failures"""
        # Arrange
        urls = [
            "https://good.com",
            "invalid-url",       # Should produce error result
            "https://another.com" 
        ]
        
        # Configure appropriate mock behaviors
        async def mock_crawl_with_some_errors(url):
            if url == "invalid-url":
                # This will be caught by crawl_url validation
                raise Exception("Invalid URL")
            return {'content': f'Content for {url}', 'title': f'Title for {url}'}
        
        self.server_context.crawler.crawl.side_effect = mock_crawl_with_some_errors
        
        # Act - Stream results and collect them
        results = []
        async for result in self.server.stream_crawl_results(self.ctx, urls):
            results.append(result)
        
        # Assert
        assert len(results) == 3
        
        # Verify error URLs produce error results (not exceptions)
        error_results = [r for r in results if r['status'] == 'error']
        assert len(error_results) == 1
        assert error_results[0]['url'] == "invalid-url"
        
        # Verify good URLs produce success results
        success_results = [r for r in results if r['status'] == 'success']
        assert len(success_results) == 2
        
        success_urls = [r['url'] for r in success_results]
        assert "https://good.com" in success_urls
        assert "https://another.com" in success_urls
    
    @pytest.mark.asyncio
    async def test_stream_crawl_results_empty_list(self):
        """Test streaming with empty URL list"""
        # Act
        results = []
        async for result in self.server.stream_crawl_results(self.ctx, []):
            results.append(result)
        
        # Assert
        assert len(results) == 0
        
        # Verify no calls were made to crawler
        self.server_context.crawler.crawl.assert_not_called()
    
    # Helper for testing async generators
    async def collect_async_generator(self, agen):
        """Helper to collect all items from async generator"""
        results = []
        async for item in agen:
            results.append(item)
        return results
    
    @pytest.mark.asyncio
    async def test_search_cached_results_success(self):
        """Test searching cached results"""
        # Arrange
        query = "test query"
        cached_results = [
            {'content': 'This contains test query information', 'title': 'Test Result 1'},
            {'content': 'Another document with test data', 'title': 'Test Result 2'},
            {'content': 'Unrelated content', 'title': 'Other Document'},
        ]
        
        # Set up cache with sample crawl results
        self.server_context.cache['crawl_results'] = cached_results
        
        # Act
        results = await self.server.search_cached_results(self.ctx, query)
        
        # Assert
        assert isinstance(results, list)
        assert len(results) == 2  # Only 2 results match "test"
        
        # Verify correct results are returned (contain query term)
        for result in results:
            content_match = query.lower() in result.get('content', '').lower()
            title_match = query.lower() in result.get('title', '').lower()
            assert content_match or title_match
    
    @pytest.mark.asyncio
    async def test_search_cached_results_no_matches(self):
        """Test search with no matching results"""
        # Arrange
        query = "nonexistent"
        cached_results = [
            {'content': 'Some content', 'title': 'Some Title'},
            {'content': 'Other content', 'title': 'Other Title'},
        ]
        
        # Set up cache with results that won't match query
        self.server_context.cache['crawl_results'] = cached_results
        
        # Act
        results = await self.server.search_cached_results(self.ctx, query)
        
        # Assert
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_cached_results_invalid_input(self):
        """Test search with invalid input"""
        # Test cases with invalid inputs
        invalid_inputs = [
            ("", "Query must be a non-empty string"),
            (None, "Query must be a non-empty string"),
            (123, "Query must be a non-empty string"),
        ]
        
        for invalid_input, expected_message in invalid_inputs:
            with pytest.raises(MCPToolError) as exc_info:
                await self.server.search_cached_results(self.ctx, invalid_input)
            
            assert exc_info.value.code == -32602
            assert expected_message in exc_info.value.message
    
    @pytest.mark.asyncio 
    async def test_end_to_end_workflow(self):
        """Test complete workflow: crawl -> cache -> search"""
        # Arrange
        url = "https://example.com/article"
        content = "This is an article about machine learning algorithms"
        title = "ML Article"
        
        # Configure crawler
        self.server_context.crawler.crawl.return_value = {
            'content': content,
            'title': title
        }
        
        # Act 1: Crawl a URL and get result
        crawl_result = await self.server.crawl_url(self.ctx, url)
        
        # Act 2: Store result in cache (simulate caching)
        if 'crawl_results' not in self.server_context.cache:
            self.server_context.cache['crawl_results'] = []
        self.server_context.cache['crawl_results'].append({
            'content': crawl_result['content'],
            'title': crawl_result['title'],
            'url': crawl_result['url']
        })
        
        # Act 3: Search for content from crawled results
        search_results = await self.server.search_cached_results(self.ctx, "machine learning")
        
        # Assert - Verify the complete workflow works
        assert crawl_result['status'] == 'success'
        assert crawl_result['content'] == content
        
        assert len(search_results) == 1
        assert search_results[0]['content'] == content
        assert search_results[0]['url'] == url
    
    @pytest.mark.asyncio
    async def test_concurrent_execution_timing(self):
        """Test that operations actually run concurrently"""
        # Configure crawler with realistic delays
        async def mock_crawl_with_delay(url):
            await asyncio.sleep(0.2)  # 200ms delay
            return {'content': f'Content for {url}', 'title': f'Title for {url}'}
        
        self.server_context.crawler.crawl.side_effect = mock_crawl_with_delay
        
        urls = ["https://site1.com", "https://site2.com", "https://site3.com"]
        
        # Measure time for batch_crawl
        start_time = time.time()
        results = await self.server.batch_crawl(self.ctx, urls)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Assert
        assert len(results) == 3
        
        # Verify time is closer to 200ms (concurrent) than 600ms (sequential)
        # Allow some overhead but verify concurrency
        assert duration < 0.4, f"Duration {duration:.3f}s suggests sequential execution"
        assert duration > 0.15, f"Duration {duration:.3f}s is too fast to be realistic"
    
    @pytest.mark.asyncio
    async def test_timeout_behavior_realistic(self):
        """Test timeout with realistic delay simulation"""
        # Arrange
        url = "https://very-slow-server.com"
        timeout = 1  # 1 second timeout
        
        async def slow_mock_crawl(url):
            await asyncio.sleep(2.0)  # 2 second delay (longer than timeout)
            return {'content': 'content'}
        
        self.server_context.crawler.crawl.side_effect = slow_mock_crawl
        
        # Act & Assert
        with pytest.raises(MCPToolError) as exc_info:
            await self.server.crawl_url(self.ctx, url, timeout=timeout)
        
        # Verify it times out (raises MCPToolError)
        assert exc_info.value.code == -32603
        assert f"Crawling timeout after {timeout}s" in exc_info.value.message
    
    @pytest.mark.asyncio
    async def test_resource_cleanup_on_cancellation(self):
        """Test proper cleanup when operations are cancelled"""
        # Arrange
        url = "https://long-running.com"
        cleanup_called = False
        
        # Create a long-running mock operation
        async def long_running_crawl(url):
            nonlocal cleanup_called
            try:
                await asyncio.sleep(5.0)  # Long operation
                return {'content': 'content'}
            except asyncio.CancelledError:
                # Simulate cleanup
                cleanup_called = True
                raise
        
        self.server_context.crawler.crawl.side_effect = long_running_crawl
        
        # Act - Start crawl_url operation and cancel it
        task = asyncio.create_task(self.server.crawl_url(self.ctx, url))
        
        # Let it start, then cancel
        await asyncio.sleep(0.1)
        task.cancel()
        
        # Wait for cancellation to complete
        with pytest.raises(asyncio.CancelledError):
            await task
        
        # Assert - Verify cleanup code ran
        assert cleanup_called, "Cleanup code should have been called on cancellation"
    
    @pytest.mark.asyncio
    async def test_mock_call_tracking(self):
        """Test detailed mock call tracking and verification"""
        # Arrange
        urls = ["https://site1.com", "https://site2.com"]
        
        # Configure crawler mock with side_effect for different URLs
        def mock_crawl_side_effect(url):
            if "site1" in url:
                return {'content': 'Content 1', 'title': 'Title 1'}
            elif "site2" in url:
                return {'content': 'Content 2', 'title': 'Title 2'}
            else:
                return {'content': 'Default content', 'title': 'Default title'}
        
        self.server_context.crawler.crawl.side_effect = mock_crawl_side_effect
        
        # Act
        results = await self.server.batch_crawl(self.ctx, urls)
        
        # Assert - Verify exact calls made to crawler
        assert self.server_context.crawler.crawl.call_count == 2
        
        # Verify arguments for each call
        call_args_list = self.server_context.crawler.crawl.call_args_list
        called_urls = [call[0][0] for call in call_args_list]  # Extract first argument
        
        assert "https://site1.com" in called_urls
        assert "https://site2.com" in called_urls
        
        # Verify results match expected content
        assert len(results) == 2
        for result in results:
            if "site1" in result['url']:
                assert result['content'] == 'Content 1'
            elif "site2" in result['url']:
                assert result['content'] == 'Content 2'
    
    @pytest.mark.asyncio  
    async def test_stateful_mock_behavior(self):
        """Test mock that changes behavior based on state"""
        # Arrange
        call_count = 0
        
        async def stateful_mock_crawl(url):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call succeeds
                return {'content': 'first content', 'title': 'First Title'}
            elif call_count == 2:
                # Second call fails
                raise Exception("Network error")
            else:
                # Subsequent calls succeed
                return {'content': f'content {call_count}', 'title': f'Title {call_count}'}
        
        self.server_context.crawler.crawl.side_effect = stateful_mock_crawl
        
        # Act & Assert
        # First call succeeds
        result1 = await self.server.crawl_url(self.ctx, "https://first.com")
        assert result1['status'] == 'success'
        assert result1['content'] == 'first content'
        
        # Second call fails appropriately  
        with pytest.raises(MCPToolError) as exc_info:
            await self.server.crawl_url(self.ctx, "https://second.com")
        assert "Network error" in exc_info.value.message
        
        # Third call succeeds again
        result3 = await self.server.crawl_url(self.ctx, "https://third.com")
        assert result3['status'] == 'success'
        assert result3['content'] == 'content 3'
```

## Key Learning Points and Explanations

### 1. FastMCP Testing Patterns

**Context Management:**

```python
def setup_method(self):
    # Create server context with mocked dependencies
    self.server_context = ServerContext()
    self.server_context.crawler = AsyncMock()
    
    # Create test context
    self.ctx = Context(lifespan_context=self.server_context)
```

**Tool Function Testing:**

```python
# Test MCP tools directly (they're just async functions)
result = await self.server.crawl_url(self.ctx, url)

# Verify MCP error patterns
with pytest.raises(MCPToolError) as exc_info:
    await self.server.crawl_url(self.ctx, invalid_url)
assert exc_info.value.code == -32602  # Invalid params
```

### 2. Advanced Async Patterns

**Async Generator Testing:**

```python
async def test_streaming(self):
    results = []
    async for result in self.server.stream_crawl_results(self.ctx, urls):
        results.append(result)
    
    assert len(results) == expected_count
```

**Concurrency Testing:**

```python
async def test_concurrency(self):
    # Track concurrent calls
    active_calls = 0
    max_concurrent = 0
    
    async def mock_with_tracking(url):
        nonlocal active_calls, max_concurrent
        active_calls += 1
        max_concurrent = max(max_concurrent, active_calls)
        await asyncio.sleep(0.1)
        active_calls -= 1
        return result
    
    # Verify concurrency limits
    assert max_concurrent <= expected_limit
```

### 3. Complex Mock Patterns

**Stateful Mocks:**

```python
call_count = 0

async def stateful_mock(url):
    nonlocal call_count
    call_count += 1
    
    if call_count == 1:
        return success_result
    else:
        raise Exception("Simulated failure")
```

**Side Effects with Different Behaviors:**

```python
def mock_side_effect(url):
    if "fast" in url:
        return fast_result
    elif "slow" in url:
        raise TimeoutError()
    else:
        return default_result

mock.side_effect = mock_side_effect
```

### 4. Timing and Performance Testing

**Concurrent vs Sequential Timing:**

```python
start_time = time.time()
results = await batch_operation()
duration = time.time() - start_time

# Verify concurrent execution
assert duration < sequential_time * 0.8
```

**Timeout Testing:**

```python
async def slow_mock():
    await asyncio.sleep(timeout * 2)  # Longer than timeout
    return result

with pytest.raises(TimeoutError):
    await asyncio.wait_for(operation(), timeout=1.0)
```

### 5. Resource Management Testing

**Cancellation Handling:**

```python
task = asyncio.create_task(long_operation())
await asyncio.sleep(0.1)  # Let it start
task.cancel()

with pytest.raises(asyncio.CancelledError):
    await task

# Verify cleanup occurred
assert cleanup_was_called
```

## Advanced Testing Strategies

### 1. Error Propagation Testing

Test how errors flow through the system:

```python
# Test that errors are properly wrapped
with pytest.raises(MCPToolError) as exc_info:
    await mcp_tool()
assert exc_info.value.code == expected_error_code
```

### 2. Batch Operation Testing

Test partial failures don't crash entire batches:

```python
def mock_with_some_failures(item):
    if should_fail(item):
        raise Exception("Simulated failure")
    return success_result

results = await batch_process(items)

# Verify partial success
success_count = len([r for r in results if r['status'] == 'success'])
error_count = len([r for r in results if r['status'] == 'error'])
assert success_count + error_count == len(items)
```

### 3. Stream Processing Testing

Test async generators properly:

```python
# Collect all results
results = []
async for item in async_generator():
    results.append(item)

# Test early termination
async for item in async_generator():
    if condition:
        break
# Verify generator cleanup
```

## Common Pitfalls and Solutions

### 1. Async Generator Issues

**Problem**: Not properly consuming async generators
**Solution**: Use proper `async for` loops and collection helpers

### 2. Mock Configuration

**Problem**: Complex mock setups become unreadable
**Solution**: Use helper methods and clear naming

### 3. Timing Sensitivity

**Problem**: Tests failing due to timing assumptions
**Solution**: Use relative timing checks with reasonable margins

### 4. Resource Cleanup

**Problem**: Tests leaving resources in inconsistent state
**Solution**: Proper setup/teardown and context managers

## Integration with Real MCP Servers

When applying to actual FastMCP servers:

1. **Tool Extraction**: Get actual functions from FastMCP decorators
2. **Context Realism**: Create realistic context objects with proper dependencies
3. **Error Handling**: Test MCP-specific error codes and messages
4. **Lifecycle Testing**: Test server startup/shutdown sequences
5. **Performance**: Verify concurrent request handling

## Next Steps

After mastering these patterns:

1. Move to Exercise 3 for complex dependency mocking
2. Practice with real FastMCP servers
3. Experiment with different async patterns
4. Add performance benchmarking to tests
