# Exercise 2: Advanced Async Testing with FastMCP Patterns

**Duration**: 60 minutes  
**Difficulty**: Intermediate  
**Prerequisites**: Completion of Exercise 1, understanding of async/await, basic FastMCP knowledge

## Learning Objectives

After completing this exercise, you will be able to:

- Test FastMCP tool functions with proper context handling
- Handle complex async patterns with proper mocking
- Test async generators and streaming responses
- Manage async context managers and lifecycle events
- Debug async timing and event loop issues

## Exercise Overview

You'll build and test a simplified MCP server that simulates the Crawl4AI patterns. This includes testing tool functions, context management, async generators, and error propagation.

## Part 1: FastMCP Tool Testing Patterns (20 minutes)

### Task 2.1: Create a simplified MCP server

Create `exercises/simple_mcp_server.py`:

```python
import asyncio
import uuid
from typing import Dict, List, Optional, AsyncGenerator
from dataclasses import dataclass
from unittest.mock import AsyncMock

# Simulate FastMCP Context and decorators
class Context:
    """Simplified MCP Context for testing"""
    def __init__(self, lifespan_context=None):
        self.request_context = type('RequestContext', (), {})()
        self.request_context.lifespan_context = lifespan_context or ServerContext()

@dataclass
class ServerContext:
    """Simplified server context holding shared resources"""
    crawler: Optional[AsyncMock] = None
    database: Optional[AsyncMock] = None
    cache: Optional[Dict] = None
    
    def __post_init__(self):
        if self.crawler is None:
            self.crawler = AsyncMock()
        if self.database is None:
            self.database = AsyncMock()
        if self.cache is None:
            self.cache = {}

class MCPToolError(Exception):
    """Custom exception for MCP tool errors"""
    def __init__(self, message: str, code: int = -32000):
        self.message = message
        self.code = code
        super().__init__(message)

# Simulate the @mcp.tool() decorator behavior
def mcp_tool(func):
    """Simplified MCP tool decorator"""
    func._is_mcp_tool = True
    return func

class SimpleMCPServer:
    """Simplified MCP server for testing async patterns"""
    
    def __init__(self, context: ServerContext):
        self.context = context
    
    @mcp_tool
    async def crawl_url(self, ctx: Context, url: str, timeout: int = 30) -> Dict:
        """Simulate URL crawling with async operations"""
        if not url or not isinstance(url, str):
            raise MCPToolError("URL must be a non-empty string", -32602)
        
        if not url.startswith(('http://', 'https://')):
            raise MCPToolError("Only HTTP/HTTPS URLs supported", -32602)
        
        try:
            # Simulate crawling with timeout
            crawler = ctx.request_context.lifespan_context.crawler
            result = await asyncio.wait_for(
                crawler.crawl(url), 
                timeout=timeout
            )
            
            # Simulate processing delay
            await asyncio.sleep(0.1)
            
            return {
                'id': str(uuid.uuid4()),
                'url': url,
                'content': result.get('content', ''),
                'title': result.get('title', ''),
                'status': 'success',
                'timestamp': asyncio.get_event_loop().time()
            }
        
        except asyncio.TimeoutError:
            raise MCPToolError(f"Crawling timeout after {timeout}s", -32603)
        except Exception as e:
            raise MCPToolError(f"Crawling failed: {str(e)}", -32603)
    
    @mcp_tool
    async def batch_crawl(self, ctx: Context, urls: List[str], concurrency: int = 5) -> List[Dict]:
        """Crawl multiple URLs with controlled concurrency"""
        if not urls:
            return []
        
        if concurrency < 1 or concurrency > 20:
            raise MCPToolError("Concurrency must be between 1 and 20", -32602)
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)
        
        async def crawl_with_semaphore(url: str) -> Dict:
            async with semaphore:
                try:
                    return await self.crawl_url(ctx, url)
                except MCPToolError:
                    # Return error info instead of raising
                    return {
                        'id': str(uuid.uuid4()),
                        'url': url,
                        'status': 'error',
                        'error': f'Failed to crawl {url}'
                    }
        
        # Process all URLs concurrently with semaphore
        tasks = [crawl_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        return results
    
    @mcp_tool  
    async def stream_crawl_results(self, ctx: Context, urls: List[str]) -> AsyncGenerator[Dict, None]:
        """Stream crawling results as they complete"""
        if not urls:
            return
        
        async def crawl_and_yield(url: str):
            try:
                result = await self.crawl_url(ctx, url)
                return result
            except MCPToolError as e:
                return {
                    'url': url,
                    'status': 'error', 
                    'error': e.message
                }
        
        # Create tasks for all URLs
        tasks = [crawl_and_yield(url) for url in urls]
        
        # Yield results as they complete
        for coro in asyncio.as_completed(tasks):
            result = await coro
            yield result
    
    @mcp_tool
    async def search_cached_results(self, ctx: Context, query: str, limit: int = 10) -> List[Dict]:
        """Search cached crawling results"""
        if not query or not isinstance(query, str):
            raise MCPToolError("Query must be a non-empty string", -32602)
        
        cache = ctx.request_context.lifespan_context.cache
        
        # Simulate database search with async delay
        await asyncio.sleep(0.05)
        
        # Simple search simulation
        all_results = cache.get('crawl_results', [])
        matching_results = [
            result for result in all_results 
            if query.lower() in result.get('content', '').lower() 
            or query.lower() in result.get('title', '').lower()
        ]
        
        return matching_results[:limit]
```

### Task 2.2: Test MCP tool functions

Create `exercises/test_exercise_2.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from simple_mcp_server import SimpleMCPServer, Context, ServerContext, MCPToolError

class TestSimpleMCPServer:
    """Test MCP server tool functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # TODO: Create server context with mocked dependencies
        # TODO: Create MCP server instance
        # TODO: Create test context
        pass
    
    @pytest.mark.asyncio
    async def test_crawl_url_success(self):
        """Test successful URL crawling"""
        # TODO: 
        # 1. Configure crawler mock to return realistic data
        # 2. Call crawl_url with valid URL
        # 3. Verify result structure and content
        # 4. Verify crawler was called with correct parameters
        pass
    
    @pytest.mark.asyncio
    async def test_crawl_url_invalid_input(self):
        """Test crawl_url with invalid inputs"""
        # TODO: Test with various invalid inputs:
        # - Empty string
        # - Non-string input
        # - Invalid URL format
        # Should raise MCPToolError with appropriate error code
        pass
    
    @pytest.mark.asyncio
    async def test_crawl_url_timeout(self):
        """Test timeout handling in crawl_url"""
        # TODO:
        # 1. Configure crawler mock to raise asyncio.TimeoutError
        # 2. Call crawl_url with short timeout
        # 3. Verify MCPToolError is raised with timeout message
        # 4. Verify error code is -32603
        pass
    
    @pytest.mark.asyncio
    async def test_crawl_url_crawler_exception(self):
        """Test handling of crawler exceptions"""
        # TODO:
        # 1. Configure crawler mock to raise generic Exception
        # 2. Call crawl_url 
        # 3. Verify MCPToolError is raised with generic error message
        pass
```

**Your Tasks:**

1. Implement the setup_method to create proper test fixtures
2. Implement all four test methods
3. Use proper async testing patterns
4. Test both success and error scenarios
5. Verify mock interactions

## Part 2: Async Concurrency and Batching (15 minutes)

### Task 2.3: Test concurrent operations

Add these tests to your test class:

```python
@pytest.mark.asyncio
async def test_batch_crawl_success(self):
    """Test successful batch crawling"""
    urls = [
        "https://example.com",
        "https://test.org", 
        "https://sample.net"
    ]
    
    # TODO:
    # 1. Configure crawler mock to return different data for each URL
    # 2. Call batch_crawl
    # 3. Verify all URLs were processed
    # 4. Verify concurrency was respected (use timing if needed)
    # 5. Verify all results have correct structure
    pass

@pytest.mark.asyncio  
async def test_batch_crawl_concurrency_control(self):
    """Test that concurrency limits are respected"""
    # TODO:
    # 1. Create many URLs (more than default concurrency)
    # 2. Track how many concurrent calls are made
    # 3. Verify concurrency limit is respected
    # 4. Test with custom concurrency parameter
    pass

@pytest.mark.asyncio
async def test_batch_crawl_partial_failures(self):
    """Test batch crawling with some failures"""
    urls = [
        "https://good1.com",     # Should succeed
        "https://bad.com",       # Should fail  
        "https://good2.com",     # Should succeed
    ]
    
    # TODO:
    # 1. Configure crawler to fail for "bad.com"
    # 2. Call batch_crawl
    # 3. Verify successful URLs return success results
    # 4. Verify failed URLs return error results (not exceptions)
    # 5. Verify total result count matches input URL count
    pass

@pytest.mark.asyncio
async def test_batch_crawl_invalid_concurrency(self):
    """Test batch crawl with invalid concurrency values"""
    urls = ["https://example.com"]
    
    # TODO: Test with concurrency values: 0, -1, 25
    # Should raise MCPToolError for invalid values
    pass
```

## Part 3: Async Generators and Streaming (15 minutes)

### Task 2.4: Test async generators

```python
@pytest.mark.asyncio
async def test_stream_crawl_results_success(self):
    """Test streaming crawl results"""
    urls = [
        "https://fast.com",    # Should complete quickly
        "https://slow.com",    # Should complete slowly  
        "https://medium.com"   # Should complete at medium speed
    ]
    
    # TODO:
    # 1. Configure crawler mock with different delays for each URL
    # 2. Call stream_crawl_results (it's an async generator)
    # 3. Collect results as they're yielded
    # 4. Verify results arrive in completion order (not input order)
    # 5. Verify all URLs are eventually processed
    
    # Hint: Use "async for result in server.stream_crawl_results(ctx, urls):"
    pass

@pytest.mark.asyncio
async def test_stream_crawl_results_with_errors(self):
    """Test streaming with some URL failures"""
    urls = [
        "https://good.com",
        "invalid-url",       # Should produce error result
        "https://another.com" 
    ]
    
    # TODO:
    # 1. Configure appropriate mock behaviors
    # 2. Stream results and collect them
    # 3. Verify error URLs produce error results (not exceptions)
    # 4. Verify good URLs produce success results
    pass

@pytest.mark.asyncio
async def test_stream_crawl_results_empty_list(self):
    """Test streaming with empty URL list"""
    # TODO:
    # 1. Call stream_crawl_results with empty list
    # 2. Verify no results are yielded
    # 3. Verify the generator completes without error
    pass

# Helper for testing async generators
async def collect_async_generator(agen):
    """Helper to collect all items from async generator"""
    results = []
    async for item in agen:
        results.append(item)
    return results
```

## Part 4: Complex Async Patterns (10 minutes)

### Task 2.5: Test caching and search functionality

```python
@pytest.mark.asyncio
async def test_search_cached_results_success(self):
    """Test searching cached results"""
    # TODO:
    # 1. Set up cache with sample crawl results
    # 2. Call search_cached_results with query that should match
    # 3. Verify correct results are returned
    # 4. Verify limit parameter works correctly
    pass

@pytest.mark.asyncio
async def test_search_cached_results_no_matches(self):
    """Test search with no matching results"""
    # TODO:
    # 1. Set up cache with results that won't match query
    # 2. Call search_cached_results
    # 3. Verify empty list is returned
    pass

@pytest.mark.asyncio
async def test_search_cached_results_invalid_input(self):
    """Test search with invalid input"""
    # TODO: Test with empty string, None, non-string inputs
    # Should raise MCPToolError
    pass

@pytest.mark.asyncio 
async def test_end_to_end_workflow(self):
    """Test complete workflow: crawl -> cache -> search"""
    # TODO:
    # 1. Crawl some URLs and get results
    # 2. Store results in cache
    # 3. Search for content from crawled results
    # 4. Verify the complete workflow works
    pass
```

## Part 5: Advanced Mock Patterns and Timing (15 minutes)

### Task 2.6: Test timing and performance characteristics

```python
import time

@pytest.mark.asyncio
async def test_concurrent_execution_timing(self):
    """Test that operations actually run concurrently"""
    # Configure crawler with realistic delays
    async def mock_crawl_with_delay(url):
        await asyncio.sleep(0.2)  # 200ms delay
        return {'content': f'Content for {url}', 'title': f'Title for {url}'}
    
    self.server_context.crawler.crawl.side_effect = mock_crawl_with_delay
    
    urls = ["https://site1.com", "https://site2.com", "https://site3.com"]
    
    # TODO:
    # 1. Measure time for batch_crawl
    # 2. Verify time is closer to 200ms (concurrent) than 600ms (sequential)
    # 3. Account for test overhead in timing
    pass

@pytest.mark.asyncio
async def test_timeout_behavior_realistic(self):
    """Test timeout with realistic delay simulation"""
    
    async def slow_mock_crawl(url):
        await asyncio.sleep(2.0)  # 2 second delay
        return {'content': 'content'}
    
    self.server_context.crawler.crawl.side_effect = slow_mock_crawl
    
    # TODO:
    # 1. Call crawl_url with 1 second timeout  
    # 2. Verify it times out (raises MCPToolError)
    # 3. Verify timeout error message and code
    pass

@pytest.mark.asyncio
async def test_resource_cleanup_on_cancellation(self):
    """Test proper cleanup when operations are cancelled"""
    
    # Create a long-running mock operation
    async def long_running_crawl(url):
        try:
            await asyncio.sleep(5.0)  # Long operation
            return {'content': 'content'}
        except asyncio.CancelledError:
            # Simulate cleanup
            print(f"Cleaning up resources for {url}")
            raise
    
    self.server_context.crawler.crawl.side_effect = long_running_crawl
    
    # TODO:
    # 1. Start crawl_url operation
    # 2. Cancel it after short delay
    # 3. Verify it handles cancellation properly
    # 4. Verify cleanup code runs (check mock interactions)
    pass
```

### Task 2.7: Test complex mock interactions

```python
@pytest.mark.asyncio
async def test_mock_call_tracking(self):
    """Test detailed mock call tracking and verification"""
    urls = ["https://site1.com", "https://site2.com"]
    
    # TODO:
    # 1. Configure crawler mock with side_effect for different URLs
    # 2. Call batch_crawl
    # 3. Verify exact calls made to crawler:
    #    - Number of calls
    #    - Arguments for each call
    #    - Order of calls (if relevant)
    pass

@pytest.mark.asyncio  
async def test_stateful_mock_behavior(self):
    """Test mock that changes behavior based on state"""
    
    call_count = 0
    
    async def stateful_mock_crawl(url):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # First call succeeds
            return {'content': 'first content'}
        elif call_count == 2:
            # Second call fails
            raise Exception("Network error")
        else:
            # Subsequent calls succeed
            return {'content': f'content {call_count}'}
    
    self.server_context.crawler.crawl.side_effect = stateful_mock_crawl
    
    # TODO:
    # 1. Make multiple calls to crawl_url
    # 2. Verify first call succeeds
    # 3. Verify second call fails appropriately  
    # 4. Verify third call succeeds again
    pass
```

## Verification and Testing

### Running Your Tests

```bash
# Run all Exercise 2 tests
uv run pytest exercises/test_exercise_2.py -v

# Run with asyncio debug mode
uv run pytest exercises/test_exercise_2.py -v --asyncio-mode=auto

# Run specific test patterns
uv run pytest exercises/test_exercise_2.py -v -k "batch"
uv run pytest exercises/test_exercise_2.py -v -k "stream"
uv run pytest exercises/test_exercise_2.py -v -k "timeout"

# Run with coverage
uv run pytest exercises/test_exercise_2.py --cov=exercises --cov-report=term-missing
```

### Expected Test Behavior

Your tests should demonstrate:

1. **Proper Async Handling**: All async functions tested with `@pytest.mark.asyncio`
2. **Mock Configuration**: Realistic mock behaviors that mirror real systems
3. **Error Propagation**: Proper testing of both success and failure paths
4. **Concurrency Testing**: Verification that concurrent operations work correctly
5. **Timing Verification**: Tests that verify performance characteristics
6. **Resource Management**: Proper handling of timeouts and cancellations

### Debugging Async Tests

Common issues and solutions:

```python
# Issue: Event loop warnings
# Solution: Use proper pytest-asyncio configuration

# Issue: Mocks not being awaited properly
# Solution: Use AsyncMock for async functions

# Issue: Tests hanging indefinitely  
# Solution: Add timeouts to test operations

@pytest.mark.asyncio
@pytest.mark.timeout(5)  # 5 second timeout
async def test_with_timeout(self):
    # Test that should complete quickly
    pass

# Issue: Timing tests are flaky
# Solution: Use relative timing comparisons with margins

def test_timing_with_margin(self):
    start = time.time()
    # ... operation ...
    duration = time.time() - start
    
    # Allow 50% margin for test overhead
    assert duration < expected_duration * 1.5
    assert duration > expected_duration * 0.5
```

## Assessment Criteria

Your implementation will be evaluated on:

1. **Correctness**: Tests properly verify expected behavior
2. **Completeness**: All TODO items implemented with appropriate logic
3. **Async Patterns**: Proper use of async/await and asyncio patterns
4. **Mock Usage**: Effective mocking of dependencies and behaviors
5. **Error Handling**: Comprehensive testing of error scenarios
6. **Code Quality**: Clean, readable test code with good structure

## Common Pitfalls

1. **Forgetting `@pytest.mark.asyncio`**: Async tests must be marked
2. **Using `Mock` instead of `AsyncMock`**: Async functions need async mocks
3. **Not awaiting async generators**: Remember to use `async for`
4. **Timing assumptions**: Don't assume exact timing in tests
5. **Mock configuration**: Ensure mocks return appropriate data types

## Next Steps

After completing this exercise:

1. Compare your solution with the provided solution
2. Experiment with more complex async patterns
3. Try adding new MCP tools and testing them
4. Move on to Exercise 3 for advanced mocking patterns

## Reflection Questions

1. How does testing async generators differ from testing regular async functions?
2. What are the challenges of testing concurrent operations?
3. How would you test real-world timing constraints without making tests flaky?
4. What mock patterns are most effective for complex async dependencies?
5. How do you balance test realism with test speed and reliability?
