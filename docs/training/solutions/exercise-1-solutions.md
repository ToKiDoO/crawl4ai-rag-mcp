# Exercise 1 Solutions: Basic Unit Tests with Async/Await Patterns

This document provides comprehensive solutions for Exercise 1, along with detailed explanations of testing patterns and best practices.

## Complete Solution Code

### url_processor.py (Reference Implementation)

The implementation provided in the exercise is complete and correct. Here are the key patterns it demonstrates:

1. **Async/Await Usage**: Proper use of `asyncio.sleep()` for simulation
2. **Error Handling**: Clear exception raising with meaningful messages
3. **State Management**: Tracking processed URLs in instance state
4. **Concurrent Processing**: Using `asyncio.gather()` for parallel execution

### test_exercise_1.py (Complete Solutions)

```python
import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock
from url_processor import URLProcessor

class TestURLProcessor:
    """Test the URLProcessor class"""
    
    def setup_method(self):
        """Set up test fixtures before each test"""
        self.processor = URLProcessor()
    
    def test_validate_url_success(self):
        """Test that valid URLs pass validation"""
        # Arrange
        valid_urls = [
            "https://example.com",
            "http://test.org/path",
            "https://sub.domain.com/long/path?query=1",
            "http://localhost:8080"
        ]
        
        # Act & Assert
        for url in valid_urls:
            # Should not raise any exception
            result = self.processor.validate_url(url)
            assert result is True
    
    def test_validate_url_invalid_format(self):
        """Test that invalid URLs raise ValueError"""
        # Arrange
        invalid_urls = [
            "not-a-url",           # No scheme or netloc
            "ftp://example.com",   # Wrong scheme
            "http://",             # No netloc
            "",                    # Empty string
            None,                  # None value
        ]
        
        # Act & Assert
        for invalid_url in invalid_urls:
            with pytest.raises(ValueError) as exc_info:
                self.processor.validate_url(invalid_url)
            
            # Verify error message is meaningful
            assert "URL" in str(exc_info.value) or "string" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_fetch_url_info_success(self):
        """Test successful URL info fetching"""
        # Arrange
        url = "https://example.com/test-path"
        
        # Act
        result = await self.processor.fetch_url_info(url)
        
        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['url'] == url
        assert result['domain'] == "example.com"
        assert result['path'] == "/test-path"
        assert result['status'] == "success"
        
        # Verify URL was tracked
        assert url in self.processor.processed_urls
        assert self.processor.get_processed_count() == 1
    
    @pytest.mark.asyncio
    async def test_fetch_url_info_invalid_url(self):
        """Test URL info fetching with invalid URL"""
        # Arrange
        invalid_urls = ["not-a-url", "ftp://bad.com", ""]
        
        # Act & Assert
        for invalid_url in invalid_urls:
            with pytest.raises(ValueError):
                await self.processor.fetch_url_info(invalid_url)
            
            # Verify no URLs were added to processed list
            assert invalid_url not in self.processor.processed_urls
    
    @pytest.mark.asyncio
    async def test_process_multiple_urls_success(self):
        """Test processing multiple URLs successfully"""
        # Arrange
        urls = [
            "https://example.com/1",
            "https://test.org/2", 
            "https://sample.net/3"
        ]
        
        # Act
        results = await self.processor.process_multiple_urls(urls)
        
        # Assert
        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 3
        
        # Verify all results are dictionaries with expected structure
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert result['url'] == urls[i]
            assert result['status'] == "success"
            assert 'domain' in result
            assert 'path' in result
        
        # Verify all URLs were processed
        assert self.processor.get_processed_count() == 3
        for url in urls:
            assert url in self.processor.processed_urls
    
    @pytest.mark.asyncio  
    async def test_process_multiple_urls_empty_list(self):
        """Test processing empty URL list"""
        # Arrange
        empty_urls = []
        
        # Act
        results = await self.processor.process_multiple_urls(empty_urls)
        
        # Assert
        assert results == []
        assert self.processor.get_processed_count() == 0
    
    @pytest.mark.asyncio
    async def test_process_multiple_urls_mixed_validity(self):
        """Test processing mix of valid and invalid URLs"""
        # Arrange
        mixed_urls = [
            "https://good1.com",      # Valid
            "invalid-url",            # Invalid
            "https://good2.com",      # Valid
            "ftp://bad.com",          # Invalid scheme
        ]
        
        # Act
        results = await self.processor.process_multiple_urls(mixed_urls)
        
        # Assert - Should return only successful results
        assert isinstance(results, list)
        assert len(results) == 2  # Only 2 valid URLs
        
        # Verify successful results
        success_urls = [result['url'] for result in results]
        assert "https://good1.com" in success_urls
        assert "https://good2.com" in success_urls
        
        # Verify invalid URLs are not in results
        assert "invalid-url" not in success_urls
        assert "ftp://bad.com" not in success_urls
        
        # Verify only valid URLs were processed
        assert self.processor.get_processed_count() == 2
    
    @pytest.mark.asyncio
    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_fetch_url_info_mocked_delay(self, mock_sleep):
        """Test URL fetching with mocked delay"""
        # Arrange
        url = "https://example.com"
        
        # Act
        result = await self.processor.fetch_url_info(url)
        
        # Assert
        assert result['status'] == "success"
        assert result['url'] == url
        
        # Verify sleep was called for delay simulation
        mock_sleep.assert_called_once_with(0.1)
    
    @pytest.mark.asyncio
    async def test_process_multiple_urls_concurrent_execution(self):
        """Test that URLs are processed concurrently, not sequentially"""
        # Arrange
        urls = [
            "https://example.com",
            "https://test.org", 
            "https://sample.net"
        ]
        
        # Act - Measure execution time
        start_time = time.time()
        results = await self.processor.process_multiple_urls(urls)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Assert
        assert len(results) == 3
        
        # With 3 URLs and 0.1s delay each:
        # Sequential would take ~0.3s, concurrent should take ~0.1s
        # Allow some overhead but verify it's closer to concurrent timing
        assert duration < 0.25, f"Duration {duration:.3f}s suggests sequential execution"
        assert duration > 0.05, f"Duration {duration:.3f}s is suspiciously fast"
    
    @pytest.mark.parametrize("url,expected_domain", [
        ("https://example.com", "example.com"),
        ("http://test.org/path", "test.org"),
        ("https://sub.domain.com/long/path", "sub.domain.com"),
    ])
    @pytest.mark.asyncio
    async def test_fetch_url_info_domain_extraction(self, url, expected_domain):
        """Test domain extraction from various URLs"""
        # Act
        result = await self.processor.fetch_url_info(url)
        
        # Assert
        assert result['domain'] == expected_domain
        assert result['url'] == url
        assert result['status'] == "success"
    
    @pytest.mark.parametrize("invalid_url", [
        "",
        "not-a-url", 
        "ftp://example.com",
        None,
        123,
        ["https://example.com"],
    ])
    def test_validate_url_various_invalid_inputs(self, invalid_url):
        """Test validation with various invalid inputs"""
        # Act & Assert
        with pytest.raises((ValueError, TypeError)):
            self.processor.validate_url(invalid_url)
    
    @pytest.mark.asyncio
    async def test_processor_state_tracking(self):
        """Test that processor correctly tracks processed URLs"""
        # Arrange
        urls = ["https://test1.com", "https://test2.com"]
        
        # Assert initial state
        assert self.processor.get_processed_count() == 0
        assert len(self.processor.processed_urls) == 0
        
        # Act - Process some URLs
        await self.processor.fetch_url_info(urls[0])
        assert self.processor.get_processed_count() == 1
        assert urls[0] in self.processor.processed_urls
        
        await self.processor.fetch_url_info(urls[1])
        assert self.processor.get_processed_count() == 2
        assert urls[1] in self.processor.processed_urls
        
        # Act - Reset state
        self.processor.reset()
        
        # Assert state is cleared
        assert self.processor.get_processed_count() == 0
        assert len(self.processor.processed_urls) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_processors_independent_state(self):
        """Test that multiple processor instances have independent state"""
        # Arrange
        processor1 = URLProcessor()
        processor2 = URLProcessor()
        
        # Act - Process different URLs with each processor
        await processor1.fetch_url_info("https://processor1.com")
        await processor2.fetch_url_info("https://processor2.com")
        
        # Assert - States are independent
        assert processor1.get_processed_count() == 1
        assert processor2.get_processed_count() == 1
        
        assert "https://processor1.com" in processor1.processed_urls
        assert "https://processor1.com" not in processor2.processed_urls
        
        assert "https://processor2.com" in processor2.processed_urls
        assert "https://processor2.com" not in processor1.processed_urls
    
    @pytest.mark.asyncio
    async def test_fetch_url_info_exception_handling(self):
        """Test proper exception handling in async context"""
        # Test cases with expected exceptions
        test_cases = [
            ("", ValueError),
            ("invalid-url", ValueError), 
            ("ftp://example.com", ValueError),
            (None, ValueError),
        ]
        
        for invalid_input, expected_exception in test_cases:
            with pytest.raises(expected_exception):
                await self.processor.fetch_url_info(invalid_input)
    
    @pytest.mark.asyncio
    async def test_process_multiple_urls_partial_failures(self):
        """Test handling of partial failures in batch processing"""
        # Arrange
        urls = [
            "https://example.com",    # Valid
            "invalid-url",            # Invalid  
            "https://test.org",       # Valid
            "ftp://bad.com",          # Invalid
        ]
        
        # Act
        results = await self.processor.process_multiple_urls(urls)
        
        # Assert
        # Function should not crash on invalid URLs
        assert isinstance(results, list)
        
        # Only valid URLs should be processed successfully
        assert len(results) == 2
        success_urls = [result['url'] for result in results]
        assert "https://example.com" in success_urls
        assert "https://test.org" in success_urls
        
        # Invalid URLs should not appear in results
        assert "invalid-url" not in success_urls
        assert "ftp://bad.com" not in success_urls
        
        # Only valid URLs should be in processed_urls list
        assert self.processor.get_processed_count() == 2
        assert "https://example.com" in self.processor.processed_urls
        assert "https://test.org" in self.processor.processed_urls
        assert "invalid-url" not in self.processor.processed_urls
        assert "ftp://bad.com" not in self.processor.processed_urls
```

## Key Learning Points and Explanations

### 1. Test Structure and Organization

**Best Practices Demonstrated:**

- **Consistent Setup**: Use `setup_method()` for test fixture initialization
- **Clear Test Names**: Names describe what is being tested and expected outcome
- **Arrange-Act-Assert**: Clear separation of test phases
- **Class Organization**: Group related tests in test classes

### 2. Async Testing Patterns

**Critical Patterns:**

```python
# Always use @pytest.mark.asyncio for async tests
@pytest.mark.asyncio
async def test_async_function(self):
    result = await async_function()
    assert result is not None

# Mock async functions correctly
@patch('asyncio.sleep', new_callable=AsyncMock)
async def test_with_async_mock(self, mock_sleep):
    await function_that_sleeps()
    mock_sleep.assert_called_once_with(0.1)
```

### 3. Exception Testing

**Comprehensive Exception Testing:**

```python
# Test specific exception types
with pytest.raises(ValueError) as exc_info:
    function_that_should_fail()

# Verify exception message
assert "meaningful message" in str(exc_info.value)

# Test multiple invalid inputs
@pytest.mark.parametrize("invalid_input", [None, "", "invalid"])
def test_validation_failures(self, invalid_input):
    with pytest.raises((ValueError, TypeError)):
        validate_function(invalid_input)
```

### 4. State Management Testing

**Testing Object State:**

```python
def test_state_changes(self):
    # Test initial state
    assert object.count == 0
    
    # Perform operations
    object.do_something()
    
    # Verify state changed
    assert object.count == 1
    
    # Test reset functionality
    object.reset()
    assert object.count == 0
```

### 5. Parametrized Testing

**Effective Use of Parameters:**

```python
@pytest.mark.parametrize("url,expected_domain", [
    ("https://example.com", "example.com"),
    ("http://test.org/path", "test.org"),
])
def test_domain_extraction(self, url, expected_domain):
    result = extract_domain(url)
    assert result == expected_domain
```

### 6. Timing and Performance Testing

**Testing Concurrent Behavior:**

```python
async def test_concurrent_execution(self):
    start_time = time.time()
    results = await process_concurrent_operations()
    duration = time.time() - start_time
    
    # Verify timing suggests concurrent execution
    assert duration < sequential_time * 0.8
    assert len(results) == expected_count
```

## Common Issues and Solutions

### Issue 1: Async Tests Not Running

**Problem**: Forgetting `@pytest.mark.asyncio` decorator
**Solution**: Always mark async tests with the decorator

### Issue 2: Mock Not Working

**Problem**: Using `Mock()` instead of `AsyncMock()` for async functions
**Solution**: Use `AsyncMock()` for async functions

### Issue 3: Timing Tests Are Flaky

**Problem**: Hard-coded timing expectations
**Solution**: Use relative comparisons with reasonable margins

### Issue 4: State Pollution Between Tests

**Problem**: Tests affecting each other's state
**Solution**: Use `setup_method()` or proper fixtures for isolation

## Performance Considerations

### 1. Test Execution Speed

- Mock expensive operations (network calls, file I/O)
- Use appropriate timeouts for async operations
- Consider parallel test execution for large suites

### 2. Resource Management

- Clean up resources in test teardown
- Use context managers where appropriate
- Avoid memory leaks in long-running test suites

## Advanced Patterns

### 1. Custom Assertions

```python
def assert_valid_url_result(result, expected_url):
    """Custom assertion for URL processing results"""
    assert isinstance(result, dict)
    assert result['url'] == expected_url
    assert result['status'] == 'success'
    assert 'domain' in result
    assert 'path' in result
```

### 2. Test Helpers

```python
def create_test_urls(count=5):
    """Helper to generate test URLs"""
    return [f"https://test{i}.com" for i in range(count)]

def assert_processing_success(results, expected_count):
    """Helper to verify processing results"""
    assert len(results) == expected_count
    assert all(r['status'] == 'success' for r in results)
```

### 3. Fixture Patterns

```python
@pytest.fixture
def configured_processor():
    """Fixture providing pre-configured processor"""
    processor = URLProcessor()
    # Add any setup needed
    yield processor
    # Cleanup if needed
    processor.reset()
```

## Integration with Real Project

When applying these patterns to the Crawl4AI MCP server:

1. **Use Similar Structure**: Organize tests by functionality
2. **Mock External Dependencies**: Database, AI services, web requests
3. **Test Error Conditions**: Network failures, invalid data, timeouts
4. **Verify State Management**: Ensure proper cleanup and isolation
5. **Performance Testing**: Verify concurrent operations work correctly

## Next Steps

After mastering these basic patterns:

1. Move to Exercise 2 for advanced async patterns
2. Practice with more complex state management
3. Experiment with different assertion styles
4. Try adding performance benchmarks to tests
