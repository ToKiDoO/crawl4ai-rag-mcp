# Test Automation Workshop: Crawl4AI MCP Server

**Stream 5 Training & Enablement Program**

Welcome to this comprehensive hands-on workshop on test automation for the Crawl4AI MCP Server. This workshop covers modern testing practices for Python async applications with FastMCP, Docker services, and real-world AI systems.

## Table of Contents

1. [Workshop Overview](#workshop-overview)
2. [Prerequisites](#prerequisites)
3. [Learning Objectives](#learning-objectives)
4. [Module 1: Testing FastMCP Servers](#module-1-testing-fastmcp-servers)
5. [Module 2: Async Python Testing Patterns](#module-2-async-python-testing-patterns)
6. [Module 3: Mocking and Test Doubles](#module-3-mocking-and-test-doubles)
7. [Module 4: Docker Integration Testing](#module-4-docker-integration-testing)
8. [Module 5: Coverage Analysis & Improvement](#module-5-coverage-analysis--improvement)
9. [Module 6: Performance Monitoring](#module-6-performance-monitoring)
10. [Module 7: Security Testing Patterns](#module-7-security-testing-patterns)
11. [Advanced Topics](#advanced-topics)
12. [Best Practices & Guidelines](#best-practices--guidelines)

## Workshop Overview

This workshop is designed for developers working on the Crawl4AI MCP Server project. We'll learn practical test automation skills through hands-on exercises that mirror real development scenarios.

### What We'll Build

- Comprehensive test suite achieving 80%+ coverage
- Performance monitoring framework
- Security testing patterns
- CI/CD integration strategies
- Automated quality gates

### Teaching Approach

- **Learn by Doing**: Each concept reinforced with practical exercises
- **Real-World Scenarios**: Tests based on actual project challenges
- **Progressive Complexity**: Start simple, build to enterprise patterns
- **Best Practices**: Industry-standard testing approaches

## Prerequisites

### Technical Requirements

- Python 3.12+ with `uv` package manager
- Docker and Docker Compose
- Basic understanding of:
  - Python async/await patterns
  - HTTP APIs and web crawling concepts
  - Database operations (basic SQL/NoSQL)
  - Version control with Git

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/your-org/crawl4aimcp.git
cd crawl4aimcp

# Install dependencies
uv sync

# Start required services
make dev-bg-nobuild

# Verify test environment
uv run pytest tests/test_setup.py -v
```

### Knowledge Prerequisites

- **Basic Python**: Functions, classes, modules, exception handling
- **Testing Fundamentals**: Understand why we test and basic test structure
- **Async Programming**: Familiarity with async/await is helpful but not required

## Learning Objectives

By the end of this workshop, you will be able to:

1. **Design Effective Test Suites**
   - Apply the test pyramid principle
   - Write maintainable test code
   - Create meaningful test scenarios

2. **Master Async Testing**
   - Test async functions and coroutines
   - Handle event loops and timing issues
   - Mock async dependencies effectively

3. **Build Integration Tests**
   - Test with Docker containers
   - Handle database connections
   - Test external service integrations

4. **Achieve High Test Coverage**
   - Analyze coverage reports
   - Identify and fill coverage gaps
   - Balance coverage with quality

5. **Implement Security Testing**
   - Test for common vulnerabilities
   - Validate input sanitization
   - Secure credential handling

6. **Monitor Performance**
   - Set up performance baselines
   - Detect regressions automatically
   - Optimize test execution

## Module 1: Testing FastMCP Servers

### Understanding MCP Architecture

FastMCP (Model Context Protocol) servers expose AI tools through a standardized interface. Our server provides web crawling capabilities with the following key components:

```python
# Core MCP Server Structure
@mcp.tool()
async def scrape_urls(ctx: Context, urls: List[str]) -> str:
    """Tool exposed to MCP clients"""
    return await crawl_and_process(urls)

# Context provides access to shared resources
class Crawl4AIContext:
    crawler: AsyncWebCrawler
    database_client: VectorDatabase
    reranking_model: CrossEncoder
```

### Testing MCP Tools

MCP tools are decorated functions that need special testing approaches:

```python
# Extract function from MCP tool wrapper
def get_tool_function(tool_name):
    """Extract the actual function from a FunctionTool wrapper."""
    tool = getattr(crawl4ai_mcp, tool_name)
    if hasattr(tool, 'fn'):
        return tool.fn
    else:
        return tool

# Test the extracted function
scrape_urls = get_tool_function('scrape_urls')

@pytest.mark.asyncio
async def test_scrape_urls_success():
    # Create mock context
    ctx = MockContext()
    
    # Test the tool
    result = await scrape_urls(ctx, ["https://example.com"])
    assert result is not None
```

### Key MCP Testing Patterns

1. **Context Mocking**: Create mock contexts with controlled dependencies
2. **Tool Extraction**: Get actual functions from MCP decorators
3. **Async Handling**: Proper async test setup with pytest-asyncio
4. **Error Propagation**: Test how MCP errors are handled and returned

### Common Challenges and Solutions

**Challenge**: MCP tools are wrapped in decorators
**Solution**: Extract the underlying function for direct testing

**Challenge**: Context dependencies are complex
**Solution**: Create lightweight mock contexts for unit tests

**Challenge**: Error handling differs from regular functions
**Solution**: Test both successful paths and error conditions

## Module 2: Async Python Testing Patterns

### Async Test Fundamentals

Modern Python applications heavily use async/await. Testing async code requires special considerations:

```python
# Basic async test structure
@pytest.mark.asyncio
async def test_async_function():
    """Test an async function"""
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    result = await async_function(input_data)
    
    # Assert
    assert result == expected_output
```

### Event Loop Management

pytest-asyncio handles event loops automatically with proper configuration:

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

### Testing Async Dependencies

When testing functions that call other async functions:

```python
@pytest.mark.asyncio
@patch('module.async_dependency')
async def test_with_async_mock(mock_dependency):
    """Test function with async dependencies"""
    # Configure async mock
    mock_dependency.return_value = asyncio.Future()
    mock_dependency.return_value.set_result("mocked_result")
    
    # Or use AsyncMock (Python 3.8+)
    mock_dependency = AsyncMock(return_value="mocked_result")
    
    # Test
    result = await function_under_test()
    assert result == "expected"
    mock_dependency.assert_called_once()
```

### Common Async Testing Patterns

1. **AsyncMock**: Use for async dependencies
2. **Future Results**: Set up mock futures for complex scenarios
3. **Event Loop Issues**: Use session-scoped fixtures for expensive setup
4. **Timeout Testing**: Test async operations with timeouts

### Database Async Patterns

When testing database operations:

```python
@pytest.mark.asyncio
async def test_database_operation():
    """Test async database operation"""
    # Use asyncio.run_in_executor for sync clients
    with patch('database.client.search') as mock_search:
        mock_search.return_value = [{"id": 1, "data": "test"}]
        
        # The actual function uses run_in_executor
        result = await search_function("query")
        
        assert len(result) > 0
        mock_search.assert_called_once()
```

## Module 3: Mocking and Test Doubles

### Understanding Test Doubles

Test doubles replace dependencies to create isolated, fast, predictable tests:

- **Mock**: Configurable fake with behavior verification
- **Stub**: Returns pre-configured responses
- **Fake**: Working implementation (in-memory database)
- **Spy**: Records interactions with real object

### Effective Mocking Strategies

```python
# Mock external services completely
@patch('requests.get')
def test_http_request(mock_get):
    mock_get.return_value.json.return_value = {"status": "ok"}
    mock_get.return_value.status_code = 200
    
    result = make_api_call()
    assert result["status"] == "ok"

# Mock expensive operations
@patch('utils.generate_embeddings')
@pytest.mark.asyncio
async def test_store_content(mock_embeddings):
    # Return realistic embeddings (1536 dimensions for OpenAI)
    mock_embeddings.return_value = [0.1] * 1536
    
    await store_crawled_content("test content")
    mock_embeddings.assert_called_once()
```

### Database Mocking Patterns

For the Crawl4AI project, we mock database operations extensively:

```python
# Mock vector database operations
@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client with realistic behavior"""
    mock_client = MagicMock()
    
    # Mock successful upsert
    mock_client.upsert.return_value = MagicMock(
        operation_id="test-op-123",
        status="completed"
    )
    
    # Mock search results
    mock_client.search.return_value = [
        MagicMock(
            id="doc-1",
            score=0.95,
            payload={"text": "relevant content"}
        )
    ]
    
    return mock_client
```

### Mock State Management

Track mock state for complex scenarios:

```python
class StatefulMockDatabase:
    """Mock database that tracks state"""
    def __init__(self):
        self.stored_documents = {}
        self.deleted_urls = set()
    
    def store_document(self, doc_id, content):
        self.stored_documents[doc_id] = content
        return {"status": "success", "id": doc_id}
    
    def search_documents(self, query):
        # Return documents matching query
        return [doc for doc in self.stored_documents.values() 
                if query.lower() in doc.lower()]
```

### Best Practices for Mocking

1. **Mock at the Right Level**: Mock external boundaries, not internal logic
2. **Use Realistic Data**: Mock responses should match real API responses
3. **Verify Interactions**: Check that mocks were called with expected parameters
4. **Reset Mock State**: Clear mock state between tests
5. **Mock Consistently**: Use the same mocking patterns across the project

## Module 4: Docker Integration Testing

### Integration Testing Strategy

Integration tests verify that components work together correctly. For the Crawl4AI project, this means testing with real Docker services:

```bash
# Services in our integration environment
- Qdrant (vector database)
- Neo4j (knowledge graph)
- Valkey (Redis cache)
- SearXNG (search engine)
```

### Setting Up Integration Tests

```python
# conftest.py - Integration test setup
@pytest.fixture(scope="session")
async def integration_environment():
    """Set up integration test environment"""
    # Check if services are available
    services = ["qdrant", "neo4j", "valkey"]
    
    for service in services:
        if not await check_service_health(service):
            pytest.skip(f"{service} not available for integration tests")
    
    yield
    
    # Cleanup after tests
    await cleanup_test_data()

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_crawling(integration_environment):
    """Test complete crawling workflow"""
    # This test uses real services
    url = "https://httpbin.org/json"
    
    # Crawl with real crawler
    result = await crawl_url(url)
    
    # Store in real database
    doc_id = await store_document(result)
    
    # Search in real database
    search_results = await search_documents("test query")
    
    assert len(search_results) > 0
```

### Docker Compose for Testing

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  qdrant-test:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
    volumes:
      - ./qdrant-test-data:/qdrant/storage
    
  mcp-test:
    build: .
    depends_on:
      - qdrant-test
    environment:
      - QDRANT_URL=http://qdrant-test:6333
      - OPENAI_API_KEY=test-key
    command: pytest tests/integration/ -v
```

### Managing Test Data

```python
class IntegrationTestManager:
    """Manage test data for integration tests"""
    
    def __init__(self):
        self.test_collections = []
        self.test_documents = []
    
    async def setup_test_data(self):
        """Create test collections and documents"""
        # Create test collection in Qdrant
        collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
        await self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        self.test_collections.append(collection_name)
        
        return collection_name
    
    async def cleanup(self):
        """Clean up test data"""
        for collection in self.test_collections:
            await self.qdrant_client.delete_collection(collection)
```

### Performance Considerations

Integration tests are slower than unit tests. Optimize them:

1. **Test Containers**: Use testcontainers library for lightweight containers
2. **Shared Fixtures**: Use session-scoped fixtures for expensive setup
3. **Parallel Execution**: Run integration tests in parallel when possible
4. **Selective Running**: Use markers to run only relevant integration tests

### CI/CD Integration

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install uv
          uv sync
      
      - name: Run integration tests
        run: |
          uv run pytest tests/integration/ -v -m integration
        env:
          QDRANT_URL: http://localhost:6333
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

## Module 5: Coverage Analysis & Improvement

### Understanding Test Coverage

Test coverage measures which parts of your code are executed during tests. Our target is 80% overall coverage with 90%+ for critical paths.

### Current Project Status

```
Overall Coverage: 56.71% → Target: 80%+
- crawl4ai_mcp.py: 53% (main application)
- utils.py: 94% ✅ (utilities)
- qdrant_adapter.py: 73% (database)
- database/factory.py: 35% (needs improvement)
```

### Coverage Tools and Configuration

```ini
# pytest.ini
[coverage:run]
source = src
omit = 
    */tests/*
    */test_*
    */__init__.py
    */conftest.py

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    if __name__ == .__main__.:
    raise NotImplementedError
```

### Analyzing Coverage Reports

```bash
# Generate coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term-missing

# View HTML report
open htmlcov/index.html

# Generate detailed analysis
uv run coverage report --show-missing --skip-covered
```

### Coverage Analysis Workflow

1. **Identify Gaps**: Find uncovered lines in critical modules
2. **Prioritize**: Focus on error handling and edge cases
3. **Test Design**: Create tests for uncovered scenarios
4. **Verify**: Confirm tests actually improve coverage
5. **Maintain**: Set up coverage monitoring in CI/CD

### Strategic Coverage Improvement

```python
# Example: Covering error paths
def test_database_connection_failure():
    """Test handling of database connection errors"""
    with patch('database.connect') as mock_connect:
        mock_connect.side_effect = ConnectionError("Database unavailable")
        
        with pytest.raises(ServiceUnavailableError):
            initialize_database()
        
        # This test covers the error handling path
        # that wasn't covered before

def test_invalid_url_format():
    """Test URL validation error paths"""
    invalid_urls = [
        "",           # Empty string
        "not-a-url",  # Invalid format
        "ftp://bad",  # Wrong protocol
        None,         # None value
    ]
    
    for invalid_url in invalid_urls:
        with pytest.raises(ValueError):
            validate_url(invalid_url)
```

### Coverage Gotchas and Solutions

**Problem**: High coverage but poor test quality
**Solution**: Review tests for meaningful assertions, not just execution

**Problem**: Hard-to-test code (complex functions)
**Solution**: Refactor into smaller, testable functions

**Problem**: External dependencies make testing difficult
**Solution**: Use dependency injection and mocking

**Problem**: Coverage drops with new features
**Solution**: Set up coverage thresholds in CI/CD

### Quality Gates with Coverage

```yaml
# CI/CD coverage enforcement
- name: Check coverage threshold
  run: |
    uv run pytest --cov=src --cov-fail-under=80
    
    # Specific module thresholds
    uv run coverage report --fail-under=90 src/utils.py
    uv run coverage report --fail-under=70 src/crawl4ai_mcp.py
```

## Module 6: Performance Monitoring

### Performance Testing Philosophy

Performance testing ensures our MCP server remains responsive under load and doesn't have memory leaks or resource issues.

### Built-in Performance Plugin

The project includes a custom pytest plugin for performance monitoring:

```bash
# Enable performance monitoring
uv run pytest --perf-monitor --perf-print-summary

# Custom output file
uv run pytest --perf-monitor --perf-output=performance_metrics.json
```

### Understanding Performance Metrics

```json
{
  "tests": {
    "test_scrape_urls": {
      "duration": 0.123,
      "memory": {
        "start_mb": 100.5,
        "peak_mb": 105.2,
        "delta_mb": 4.7
      },
      "cpu_percent": 25.5
    }
  }
}
```

### Performance Test Patterns

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_bulk_crawling_performance():
    """Test performance with multiple URLs"""
    urls = [f"https://httpbin.org/delay/{i}" for i in range(10)]
    
    start_time = time.time()
    start_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    results = await scrape_urls_bulk(urls)
    
    end_time = time.time()
    end_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    # Performance assertions
    assert (end_time - start_time) < 30  # Under 30 seconds
    assert len(results) == 10
    assert (end_memory - start_memory) < 50  # Under 50MB increase

@pytest.mark.benchmark
def test_embedding_generation_benchmark(benchmark):
    """Benchmark embedding generation"""
    text = "Sample text for embedding generation" * 100
    
    # Benchmark the function
    result = benchmark(generate_embeddings, text)
    
    assert len(result) == 1536  # OpenAI embedding dimension
    assert isinstance(result[0], float)
```

### Memory Leak Detection

```python
import gc
import psutil

class MemoryTracker:
    """Track memory usage across test runs"""
    
    def __init__(self):
        self.initial_memory = None
        self.measurements = []
    
    def start_tracking(self):
        gc.collect()  # Force garbage collection
        self.initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    
    def take_measurement(self, label):
        gc.collect()
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        self.measurements.append({
            'label': label,
            'memory_mb': current_memory,
            'delta_mb': current_memory - self.initial_memory
        })
    
    def check_for_leaks(self, threshold_mb=10):
        """Check if memory increased beyond threshold"""
        final_delta = self.measurements[-1]['delta_mb']
        if final_delta > threshold_mb:
            raise AssertionError(f"Potential memory leak: {final_delta}MB increase")

# Usage in tests
@pytest.fixture
def memory_tracker():
    tracker = MemoryTracker()
    tracker.start_tracking()
    yield tracker
    tracker.check_for_leaks()

def test_no_memory_leak(memory_tracker):
    """Test that repeated operations don't leak memory"""
    for i in range(100):
        # Perform memory-intensive operation
        result = process_large_document(generate_test_document())
        
        if i % 20 == 0:
            memory_tracker.take_measurement(f"iteration_{i}")
    
    # Memory leak check happens in fixture cleanup
```

### CI/CD Performance Monitoring

```yaml
# Performance regression detection
- name: Run performance tests
  run: |
    uv run pytest tests/performance/ --perf-monitor --perf-output=current_metrics.json
    
- name: Compare with baseline
  run: |
    python scripts/compare_performance.py baseline_metrics.json current_metrics.json
    
- name: Upload performance artifacts
  uses: actions/upload-artifact@v3
  with:
    name: performance-metrics
    path: current_metrics.json
    retention-days: 30
```

### Performance Optimization Strategies

1. **Async Optimization**: Use `asyncio.gather()` for concurrent operations
2. **Caching**: Implement intelligent caching for expensive operations
3. **Batch Processing**: Process multiple items together when possible
4. **Resource Pooling**: Reuse connections and expensive objects
5. **Lazy Loading**: Load resources only when needed

## Module 7: Security Testing Patterns

### Security Testing Framework

Security testing ensures our MCP server is resilient against common attacks and follows security best practices.

### Input Validation Testing

```python
# Test against common injection attacks
MALICIOUS_QUERIES = [
    "'; DROP TABLE users; --",        # SQL injection
    "<script>alert('XSS')</script>",  # XSS
    "../../../etc/passwd",            # Path traversal
    "{{7*7}}",                        # Template injection
]

@pytest.mark.security
@pytest.mark.parametrize("malicious_input", MALICIOUS_QUERIES)
def test_input_sanitization(malicious_input):
    """Test that malicious inputs are properly sanitized"""
    sanitized = sanitize_search_query(malicious_input)
    
    # Verify dangerous patterns are removed
    assert "<script>" not in sanitized
    assert "DROP TABLE" not in sanitized.upper()
    assert "../" not in sanitized
```

### URL Security Testing

```python
DANGEROUS_URLS = [
    "http://localhost/admin",          # SSRF attempt
    "file:///etc/passwd",             # File access
    "http://169.254.169.254/",        # AWS metadata
    "javascript:alert('XSS')",       # JavaScript URL
]

@pytest.mark.security
@pytest.mark.parametrize("dangerous_url", DANGEROUS_URLS)
def test_url_security_validation(dangerous_url):
    """Test that dangerous URLs are blocked"""
    with pytest.raises(ValueError) as exc_info:
        validate_url_security(dangerous_url)
    
    error_message = str(exc_info.value).lower()
    assert any(word in error_message for word in ["security", "blocked", "forbidden"])
```

### Credential Security Testing

```python
@pytest.mark.security
def test_credentials_not_in_logs():
    """Test that sensitive credentials are never logged"""
    sensitive_keys = ["sk-proj-secret123", "password123", "service_key_abc"]
    
    with capture_logs() as get_logs:
        # Simulate operations that might log credentials
        for key in sensitive_keys:
            try:
                process_with_credential(key)
            except Exception:
                pass
        
        logs = "\n".join(get_logs())
        
        # Ensure no credentials in logs
        for key in sensitive_keys:
            assert key not in logs

def test_error_messages_dont_leak_credentials():
    """Test that error messages don't expose sensitive data"""
    try:
        connect_to_database(password="secret123")
    except Exception as e:
        error_message = str(e)
        assert "secret123" not in error_message
        assert "[REDACTED]" in error_message
```

### Container Security Testing

```python
@pytest.mark.security
def test_container_security_configuration():
    """Test Docker container security settings"""
    with open("docker-compose.yml", 'r') as f:
        compose_config = yaml.safe_load(f)
    
    # Check for security best practices
    for service_name, config in compose_config["services"].items():
        # Should not run as root
        if service_name in ["mcp-crawl4ai", "searxng"]:
            assert "user" in config or service_name == "mcp-crawl4ai"
        
        # Check for capability restrictions
        if "cap_drop" in config:
            assert "ALL" in config["cap_drop"]
```

### API Security Testing

```python
@pytest.mark.security
@pytest.mark.asyncio
async def test_rate_limiting():
    """Test API rate limiting"""
    rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
    client_id = "test_client"
    
    # Make requests up to limit
    for i in range(5):
        assert rate_limiter.check_rate_limit(client_id) is True
    
    # Next request should be rate limited
    assert rate_limiter.check_rate_limit(client_id) is False

@pytest.mark.security
def test_cors_configuration():
    """Test CORS security configuration"""
    cors_config = get_cors_config()
    
    # Should not allow all origins
    assert cors_config["allow_origins"] != ["*"]
    
    # Should have restricted methods
    assert "DELETE" not in cors_config.get("allow_methods", [])
```

### Security Test Organization

```python
# Organize security tests by threat category
class TestOWASPTop10:
    """Test against OWASP Top 10 vulnerabilities"""
    
    def test_injection_prevention(self):
        """A03:2021 - Injection"""
        # Test SQL, NoSQL, Command injection prevention
        pass
    
    def test_broken_authentication(self):
        """A07:2021 - Identification and Authentication Failures"""
        # Test authentication bypass attempts
        pass
    
    def test_sensitive_data_exposure(self):
        """A02:2021 - Cryptographic Failures"""
        # Test for exposed credentials, tokens
        pass
```

## Advanced Topics

### Property-Based Testing

Use Hypothesis for generating test cases:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=1000))
def test_text_processing_with_random_input(text_input):
    """Test text processing with randomly generated strings"""
    result = process_text(text_input)
    
    # Properties that should always hold
    assert isinstance(result, str)
    assert len(result) <= len(text_input) * 2  # Reasonable upper bound
    assert not any(char in result for char in ['<', '>', '&'])  # No HTML

@given(st.lists(st.text(), min_size=1, max_size=100))
@pytest.mark.asyncio
async def test_bulk_processing_properties(url_list):
    """Test bulk processing with property-based testing"""
    # Convert to valid URLs
    urls = [f"https://example.com/{url}" for url in url_list if url.strip()]
    
    if urls:  # Only test if we have valid URLs
        results = await process_urls_bulk(urls)
        
        # Properties
        assert len(results) <= len(urls)  # Can't have more results than inputs
        assert all(isinstance(r, dict) for r in results)  # All results are dicts
```

### Mutation Testing

Test your tests with mutation testing:

```bash
# Install mutmut
pip install mutmut

# Run mutation testing
mutmut run --paths-to-mutate=src/

# View results
mutmut results
mutmut show
```

### Contract Testing

Test API contracts between components:

```python
import pact
from pact import Consumer, Provider

# Consumer test (MCP client perspective)
@pytest.fixture
def mcp_client_pact():
    pact = Consumer('mcp_client').has_pact_with(Provider('crawl4ai_mcp'))
    pact.start_service()
    yield pact
    pact.stop_service()

def test_scrape_url_contract(mcp_client_pact):
    """Test MCP client-server contract"""
    expected = {
        "result": {
            "url": "https://example.com",
            "content": pact.Term(r".+", "page content"),
            "status": "success"
        }
    }
    
    (mcp_client_pact
     .given('a valid URL to scrape')
     .upon_receiving('a scrape request')
     .with_request('POST', '/mcp/scrape')
     .will_respond_with(200, body=expected))
    
    # Make actual request
    response = mcp_client.scrape_url("https://example.com")
    assert response["status"] == "success"
```

### Load Testing

Test system behavior under load:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_crawling_load():
    """Test system under concurrent load"""
    # Create multiple concurrent requests
    urls = [f"https://httpbin.org/delay/1" for _ in range(50)]
    
    start_time = time.time()
    
    # Process URLs concurrently
    tasks = [scrape_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    
    # Performance assertions
    assert (end_time - start_time) < 10  # Should complete in under 10 seconds
    
    # Check success rate
    successful_results = [r for r in results if not isinstance(r, Exception)]
    success_rate = len(successful_results) / len(results)
    assert success_rate > 0.9  # 90% success rate minimum
```

## Best Practices & Guidelines

### Test Organization

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Tests with external services  
├── e2e/           # End-to-end user scenarios
├── performance/   # Load and performance tests
├── security/      # Security-focused tests
├── fixtures/      # Shared test data
└── conftest.py    # Pytest configuration
```

### Naming Conventions

```python
# Test method naming
def test_should_return_valid_result_when_given_valid_input():
    """Clear, descriptive test names"""
    pass

def test_should_raise_exception_when_given_invalid_input():
    """Include expected behavior in name"""
    pass

# Test class organization
class TestUserAuthentication:
    """Group related tests in classes"""
    
    def test_successful_login(self):
        pass
    
    def test_invalid_credentials(self):
        pass
    
    def test_account_lockout(self):
        pass
```

### Assertion Guidelines

```python
# Good: Specific assertions
assert response.status_code == 200
assert "success" in response.json()["status"]
assert len(results) == expected_count

# Avoid: Generic assertions
assert response  # Too vague
assert results   # Doesn't specify what we expect

# Good: Custom assertion messages
assert len(results) == 5, f"Expected 5 results, got {len(results)}"
assert user.is_active, f"User {user.id} should be active after registration"
```

### Test Data Management

```python
# Use factories for test data
class UserFactory:
    @staticmethod
    def create_valid_user():
        return {
            "username": f"testuser_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "password": "SecurePassword123!"
        }
    
    @staticmethod
    def create_invalid_user():
        return {
            "username": "",  # Invalid: empty username
            "email": "not-an-email",  # Invalid: bad format
            "password": "123"  # Invalid: too short
        }

# Use realistic test data
def generate_realistic_crawl_result():
    return {
        "url": "https://example.com/article/123",
        "title": "Sample Article Title",
        "content": "This is a sample article content...",
        "metadata": {
            "author": "John Doe",
            "published": "2024-01-01T12:00:00Z",
            "tags": ["technology", "python", "testing"]
        }
    }
```

### Continuous Improvement

1. **Regular Review**: Review and refactor tests regularly
2. **Test Coverage**: Monitor coverage trends, not just current numbers
3. **Performance Tracking**: Track test execution time and optimize slow tests
4. **Flaky Test Management**: Identify and fix non-deterministic tests
5. **Documentation**: Keep test documentation updated

### Integration with Development Workflow

```yaml
# Pre-commit hooks
repos:
  - repo: local
    hooks:
      - id: test-fast
        name: Run fast tests
        entry: uv run pytest tests/unit/ -x
        language: system
        always_run: true
      
      - id: security-tests
        name: Run security tests
        entry: uv run pytest tests/security/ -x
        language: system
        always_run: true
```

### Quality Gates

Set up automated quality gates:

```bash
# Quality gate script
#!/bin/bash
set -e

echo "Running quality gates..."

# 1. Fast tests must pass
uv run pytest tests/unit/ -x

# 2. Coverage threshold
uv run pytest tests/unit/ --cov=src --cov-fail-under=80

# 3. Security tests must pass
uv run pytest tests/security/ -x

# 4. Performance regression check
uv run pytest tests/performance/ --perf-monitor
python scripts/check_performance_regression.py

echo "All quality gates passed!"
```

## Workshop Wrap-up

### Key Takeaways

1. **Test Pyramid**: Focus on fast unit tests, supported by integration and E2E tests
2. **Async Testing**: Master async/await patterns and proper mocking techniques
3. **Real-World Testing**: Test with realistic data and scenarios
4. **Quality over Quantity**: High coverage with meaningful tests
5. **Continuous Monitoring**: Set up automated quality and performance monitoring

### Next Steps

1. Complete all workshop exercises
2. Apply patterns to your current work
3. Set up quality gates in your projects
4. Share knowledge with your team
5. Contribute improvements back to the project

### Resources for Continued Learning

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Google Testing Best Practices](https://testing.googleblog.com/)
- [Effective Python Testing](https://realpython.com/python-testing/)

### Getting Help

- **Project Issues**: File issues on the GitHub repository
- **Testing Questions**: Ask in the team's testing channel
- **Best Practices**: Review existing test patterns in the codebase
- **Security Concerns**: Consult the security team

---

**Remember**: Great tests are written for humans, not just computers. Make them clear, maintainable, and valuable to your future self and teammates.
