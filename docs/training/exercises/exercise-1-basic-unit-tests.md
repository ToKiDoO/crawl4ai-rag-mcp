# Exercise 1: Basic Unit Tests with Async/Await Patterns

**Duration**: 45 minutes  
**Difficulty**: Beginner  
**Prerequisites**: Basic Python knowledge, async/await familiarity

## Learning Objectives

After completing this exercise, you will be able to:

- Write basic unit tests for async functions
- Use pytest-asyncio effectively
- Create mock contexts for testing
- Test both success and failure scenarios
- Apply the Arrange-Act-Assert pattern

## Exercise Overview

You'll create unit tests for a simplified URL validation and content processing system. This mirrors the patterns used in the Crawl4AI MCP server but with reduced complexity for learning.

## Part 1: Setup and Basic Async Testing (15 minutes)

### Task 1.1: Create a simple async function to test

First, let's create a simple module to test. Create `exercises/url_processor.py`:

```python
import asyncio
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

class URLProcessor:
    """Simple URL processor for learning testing patterns"""
    
    def __init__(self):
        self.processed_urls = []
    
    def validate_url(self, url: str) -> bool:
        """Validate that a URL is properly formatted"""
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")
        
        # Basic URL validation
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL format")
        
        # Only allow HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("Only HTTP and HTTPS URLs are supported")
        
        return True
    
    async def fetch_url_info(self, url: str) -> Dict[str, str]:
        """Simulate fetching URL information (async)"""
        self.validate_url(url)
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        # Simulate processing
        parsed = urlparse(url)
        result = {
            'url': url,
            'domain': parsed.netloc,
            'path': parsed.path or '/',
            'status': 'success'
        }
        
        self.processed_urls.append(url)
        return result
    
    async def process_multiple_urls(self, urls: List[str]) -> List[Dict[str, str]]:
        """Process multiple URLs concurrently"""
        if not urls:
            return []
        
        # Process URLs concurrently
        tasks = [self.fetch_url_info(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        successful_results = []
        for result in results:
            if not isinstance(result, Exception):
                successful_results.append(result)
        
        return successful_results
    
    def get_processed_count(self) -> int:
        """Get the number of URLs processed"""
        return len(self.processed_urls)
    
    def reset(self):
        """Reset the processor state"""
        self.processed_urls.clear()
```

### Task 1.2: Write your first async test

Create `exercises/test_exercise_1.py`:

```python
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from url_processor import URLProcessor

class TestURLProcessor:
    """Test the URLProcessor class"""
    
    def setup_method(self):
        """Set up test fixtures before each test"""
        self.processor = URLProcessor()
    
    # TODO: Write test_validate_url_success
    # Test that valid URLs pass validation
    def test_validate_url_success(self):
        """Test that valid URLs pass validation"""
        # Your code here
        pass
    
    # TODO: Write test_validate_url_invalid_format
    # Test that invalid URLs raise ValueError
    def test_validate_url_invalid_format(self):
        """Test that invalid URLs raise ValueError"""
        # Your code here
        pass
    
    # TODO: Write test_fetch_url_info_success
    # Test async URL fetching with valid URL
    @pytest.mark.asyncio
    async def test_fetch_url_info_success(self):
        """Test successful URL info fetching"""
        # Your code here
        pass
    
    # TODO: Write test_fetch_url_info_invalid_url
    # Test async URL fetching with invalid URL
    @pytest.mark.asyncio
    async def test_fetch_url_info_invalid_url(self):
        """Test URL info fetching with invalid URL"""
        # Your code here
        pass
```

**Your Tasks:**

1. Implement the four TODO test methods
2. Use proper Arrange-Act-Assert structure
3. Test both success and failure cases
4. Make sure async tests use `@pytest.mark.asyncio` decorator

**Hints:**

- For success cases, verify the expected return values
- For failure cases, use `pytest.raises()` context manager
- Valid URLs: `"https://example.com"`, `"http://test.org/path"`
- Invalid URLs: `"not-a-url"`, `"ftp://example.com"`, `""`, `None`

## Part 2: Mocking and Async Dependencies (15 minutes)

### Task 2.1: Test concurrent processing

Now let's test the more complex `process_multiple_urls` method:

```python
# Add these tests to your TestURLProcessor class

@pytest.mark.asyncio
async def test_process_multiple_urls_success(self):
    """Test processing multiple URLs successfully"""
    # TODO: Test with 3 valid URLs
    # Verify all URLs are processed and results returned
    # Check that processed_urls list is updated correctly
    pass

@pytest.mark.asyncio  
async def test_process_multiple_urls_empty_list(self):
    """Test processing empty URL list"""
    # TODO: Test with empty list
    # Should return empty list without errors
    pass

@pytest.mark.asyncio
async def test_process_multiple_urls_mixed_validity(self):
    """Test processing mix of valid and invalid URLs"""
    # TODO: Test with mix of valid and invalid URLs
    # Should return only successful results
    # Invalid URLs should not crash the whole operation
    pass
```

### Task 2.2: Mock external dependencies

Let's simulate testing with external dependencies by mocking the `asyncio.sleep`:

```python
@pytest.mark.asyncio
@patch('asyncio.sleep', new_callable=AsyncMock)
async def test_fetch_url_info_mocked_delay(self, mock_sleep):
    """Test URL fetching with mocked delay"""
    # TODO: Test that sleep is called for delay simulation
    # Verify the function still works correctly
    # Check that mock_sleep was called once
    pass

@pytest.mark.asyncio
async def test_process_multiple_urls_concurrent_execution(self):
    """Test that URLs are processed concurrently, not sequentially"""
    import time
    
    urls = [
        "https://example.com",
        "https://test.org", 
        "https://sample.net"
    ]
    
    # TODO: Measure execution time
    # With 3 URLs and 0.1s delay each:
    # - Sequential would take ~0.3s  
    # - Concurrent should take ~0.1s
    # Verify it's closer to concurrent timing
    pass
```

## Part 3: Advanced Testing Patterns (15 minutes)

### Task 3.1: Parametrized tests

Use pytest's parametrize decorator to test multiple scenarios:

```python
@pytest.mark.parametrize("url,expected_domain", [
    ("https://example.com", "example.com"),
    ("http://test.org/path", "test.org"),
    ("https://sub.domain.com/long/path", "sub.domain.com"),
])
@pytest.mark.asyncio
async def test_fetch_url_info_domain_extraction(self, url, expected_domain):
    """Test domain extraction from various URLs"""
    # TODO: Test that domain is correctly extracted
    pass

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
    # TODO: Test that all invalid inputs raise ValueError or TypeError
    pass
```

### Task 3.2: Test state management

Test that the processor correctly tracks state:

```python
@pytest.mark.asyncio
async def test_processor_state_tracking(self):
    """Test that processor correctly tracks processed URLs"""
    # TODO: 
    # 1. Verify initial state (empty)
    # 2. Process some URLs
    # 3. Verify state is updated
    # 4. Reset and verify state is cleared
    pass

@pytest.mark.asyncio
async def test_multiple_processors_independent_state(self):
    """Test that multiple processor instances have independent state"""
    # TODO:
    # 1. Create two processor instances
    # 2. Process different URLs with each
    # 3. Verify their states are independent
    pass
```

## Part 4: Error Handling and Edge Cases (10 minutes)

### Task 4.1: Comprehensive error testing

```python
@pytest.mark.asyncio
async def test_fetch_url_info_exception_handling(self):
    """Test proper exception handling in async context"""
    
    # Test with various invalid inputs
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
    urls = [
        "https://example.com",    # Valid
        "invalid-url",            # Invalid  
        "https://test.org",       # Valid
        "ftp://bad.com",          # Invalid
    ]
    
    # TODO: Process the URLs and verify:
    # 1. Function doesn't crash on invalid URLs
    # 2. Valid URLs are still processed
    # 3. Result count matches valid URL count
    # 4. Invalid URLs don't appear in processed_urls list
    pass
```

## Verification Checklist

Before moving to the next exercise, verify your tests:

- [ ] All tests pass when run with `pytest exercises/test_exercise_1.py -v`
- [ ] Tests cover both success and failure scenarios  
- [ ] Async tests use `@pytest.mark.asyncio` decorator
- [ ] Proper use of `pytest.raises()` for exception testing
- [ ] Tests follow Arrange-Act-Assert pattern
- [ ] Parametrized tests work correctly
- [ ] State management tests verify independent instances
- [ ] Error handling tests cover edge cases

## Running Your Tests

```bash
# Run all tests
uv run pytest exercises/test_exercise_1.py -v

# Run only async tests
uv run pytest exercises/test_exercise_1.py -v -k "async"

# Run with coverage
uv run pytest exercises/test_exercise_1.py --cov=exercises --cov-report=term-missing

# Run specific test
uv run pytest exercises/test_exercise_1.py::TestURLProcessor::test_validate_url_success -v
```

## Expected Output

Your tests should produce output similar to:

```
========================= test session starts =========================
collected 12 items

test_exercise_1.py::TestURLProcessor::test_validate_url_success PASSED
test_exercise_1.py::TestURLProcessor::test_validate_url_invalid_format PASSED  
test_exercise_1.py::TestURLProcessor::test_fetch_url_info_success PASSED
test_exercise_1.py::TestURLProcessor::test_fetch_url_info_invalid_url PASSED
test_exercise_1.py::TestURLProcessor::test_process_multiple_urls_success PASSED
test_exercise_1.py::TestURLProcessor::test_process_multiple_urls_empty_list PASSED
test_exercise_1.py::TestURLProcessor::test_process_multiple_urls_mixed_validity PASSED
test_exercise_1.py::TestURLProcessor::test_fetch_url_info_mocked_delay PASSED
test_exercise_1.py::TestURLProcessor::test_process_multiple_urls_concurrent_execution PASSED
test_exercise_1.py::TestURLProcessor::test_fetch_url_info_domain_extraction[https://example.com-example.com] PASSED
test_exercise_1.py::TestURLProcessor::test_fetch_url_info_domain_extraction[http://test.org/path-test.org] PASSED
test_exercise_1.py::TestURLProcessor::test_fetch_url_info_domain_extraction[https://sub.domain.com/long/path-sub.domain.com] PASSED

========================= 12 passed in 1.23s =========================
```

## Common Issues and Solutions

**Issue**: `RuntimeError: no running event loop`  
**Solution**: Make sure async tests have `@pytest.mark.asyncio` decorator

**Issue**: Tests run too slowly  
**Solution**: Mock `asyncio.sleep()` to avoid actual delays

**Issue**: `TypeError: 'Mock' object is not awaitable`  
**Solution**: Use `AsyncMock()` instead of `Mock()` for async functions

**Issue**: Parametrized tests not generating multiple test cases  
**Solution**: Check parameter names match function argument names exactly

## Next Steps

Once you complete this exercise:

1. Review the solution file to compare approaches
2. Experiment with different test scenarios
3. Try adding more complex validation rules
4. Move on to Exercise 2 for advanced async patterns

## Reflection Questions

1. What's the difference between testing sync and async functions?
2. Why is mocking important for unit tests?
3. How does parametrized testing improve test coverage?
4. What are the benefits of testing error conditions?
5. How would you test this code if it made real HTTP requests?
