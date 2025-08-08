# Test Helpers Reference Guide

## Overview

This document describes the test helper utilities created to improve test quality and reduce duplication in the Crawl4AI MCP test suite.

## Test Helpers (`tests/test_helpers.py`)

### TestDataBuilder

Builder pattern for creating consistent test data with sensible defaults.

#### Methods

**`random_string(length: int = 10) -> str`**

```python
# Generate random string for unique test data
unique_id = TestDataBuilder.random_string(8)  # "a3B9xY2m"
```

**`document(**kwargs) -> Dict[str, Any]`**

```python
# Create a test document with defaults
doc = TestDataBuilder.document(
    url="https://example.com",
    content="Test content",
    chunk_number=1,
    metadata={"category": "test"},
    embedding=[0.1] * 1536
)
```

**`search_result(score: float = 0.9, **kwargs) -> Dict[str, Any]`**

```python
# Create a search result
result = TestDataBuilder.search_result(
    score=0.85,
    url="https://test.com",
    content="Matching content"
)
```

**`code_example(language: str = "python", **kwargs) -> Dict[str, Any]`**

```python
# Create a code example
example = TestDataBuilder.code_example(
    language="python",
    code="def hello(): return 'world'",
    description="Hello world function"
)
```

**`batch_documents(count: int = 10, **kwargs) -> List[Dict[str, Any]]`**

```python
# Create multiple documents
docs = TestDataBuilder.batch_documents(100)  # 100 test documents
```

### TestAssertions

Custom assertions with detailed error messages for better test debugging.

#### Methods

**`assert_search_result_valid(result: Dict[str, Any]) -> None`**

```python
# Validate search result structure
TestAssertions.assert_search_result_valid(search_result)
# Checks: id, score (0-1), content, url, metadata fields
```

**`assert_embedding_valid(embedding: List[float], expected_dim: int = 1536) -> None`**

```python
# Validate embedding structure
TestAssertions.assert_embedding_valid(embedding, 1536)
# Checks: list type, dimension, numeric values
```

**`assert_api_response_valid(response: Dict[str, Any]) -> None`**

```python
# Validate API response structure
TestAssertions.assert_api_response_valid(response)
# Checks: success field, data/error fields based on success
```

**`assert_async_callable(func) -> None`**

```python
# Verify function is async
TestAssertions.assert_async_callable(adapter.search_documents)
```

### TestFixtures

Reusable test fixtures for common testing scenarios.

#### Methods

**`create_test_database(adapter_class, **kwargs)`**

```python
# Create and initialize a test database adapter
adapter = await TestFixtures.create_test_database(
    QdrantAdapter,
    url="http://localhost:6333"
)
```

**`load_test_config(env_file: str = ".env.test") -> Dict[str, str]`**

```python
# Load test configuration
config = TestFixtures.load_test_config()
api_key = config.get("OPENAI_API_KEY")
```

**`mock_async_response(data: Any, delay: float = 0.0)`**

```python
# Create mock async response with optional delay
mock_response = TestFixtures.mock_async_response(
    {"status": "ok"},
    delay=0.1  # 100ms delay
)
```

### TestMetrics

Track and report test performance metrics.

#### Usage Example

```python
metrics = TestMetrics()

# In test
metrics.start_timer("test_search")
metrics.record_assertion()
metrics.record_mock()
# ... test code ...
metrics.end_timer("test_search")

# Get report
report = metrics.report()
# {
#     "total_tests": 1,
#     "total_duration": 0.123,
#     "average_duration": 0.123,
#     "total_assertions": 5,
#     "total_mocks": 2,
#     "mocks_per_test": 2.0
# }
```

## Test Doubles (`tests/test_doubles.py`)

### FakeQdrantClient

Test double for Qdrant client with controllable behavior.

#### Features

- In-memory storage for testing
- Controllable failure modes
- Consistent behavior across tests

#### Usage

```python
fake_client = FakeQdrantClient(
    search_results=[
        {"id": "1", "score": 0.9, "payload": {"content": "Test"}}
    ],
    should_fail=False
)

# Normal operation
results = fake_client.search("collection", [0.1] * 1536, limit=10)

# Test failure scenarios
fake_client.should_fail = True
# Now operations will raise exceptions
```

### FakeEmbeddingService

Test double for embedding generation.

#### Features

- Consistent fake embeddings
- Configurable embedding dimension
- Controllable failures

#### Usage

```python
fake_service = FakeEmbeddingService(
    embedding_dim=1536,
    should_fail=False
)

embeddings = fake_service.create_embeddings(["text1", "text2"])
# Returns [[0.1] * 1536, [0.1] * 1536]
```

### FakeCrawler

Test double for web crawler operations.

#### Features

- Predefined responses per URL
- Default content for unknown URLs
- Controllable failures

#### Usage

```python
fake_crawler = FakeCrawler(
    responses={
        "https://example.com": "<html>Custom content</html>"
    },
    default_content="<html>Default</html>"
)

result = await fake_crawler.arun("https://example.com")
# Returns CrawlResult with custom content
```

## Test Data Fixtures (`tests/fixtures/test_data.json`)

### Sample Documents

```json
{
  "sample_documents": [
    {
      "url": "https://example.com/doc1",
      "content": "Introduction to machine learning basics",
      "metadata": {"category": "ML", "difficulty": "beginner"}
    }
  ]
}
```

### Sample Queries

```json
{
  "sample_queries": [
    "What is machine learning?",
    "How do neural networks work?",
    "Python coding standards"
  ]
}
```

### Sample Code Blocks

```json
{
  "sample_code_blocks": [
    {
      "language": "python",
      "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"
    }
  ]
}
```

## Usage Patterns

### 1. Reducing Mock Complexity

```python
# Instead of complex nested mocks
mock_client = MagicMock()
mock_client.search.return_value.results[0].score = 0.9

# Use test doubles
fake_client = FakeQdrantClient(search_results=[...])
```

### 2. Consistent Test Data

```python
# Create consistent test documents
docs = TestDataBuilder.batch_documents(
    10,
    metadata={"source": "test"}
)

# All documents will have proper structure
for doc in docs:
    TestAssertions.assert_embedding_valid(doc["embedding"])
```

### 3. Performance Tracking

```python
def test_with_metrics():
    metrics = TestMetrics()
    
    for test_name in ["test1", "test2", "test3"]:
        metrics.start_timer(test_name)
        # Run test
        metrics.end_timer(test_name)
    
    # Identify slow tests
    report = metrics.report()
    if report["average_duration"] > 1.0:
        print("Tests running too slowly!")
```

## Best Practices

1. **Use Test Builders**: Always use `TestDataBuilder` for creating test data
2. **Validate with Assertions**: Use `TestAssertions` for consistent validation
3. **Prefer Test Doubles**: Replace complex mocks with `Fake*` classes
4. **Track Performance**: Use `TestMetrics` to identify slow tests
5. **Reuse Fixtures**: Use `TestFixtures` for common setup patterns

## Integration Example

```python
class TestSearchFunctionality:
    @pytest.fixture
    async def adapter(self):
        # Use test fixture
        return await TestFixtures.create_test_database(
            QdrantAdapter,
            url="http://localhost:6333"
        )
    
    async def test_search_with_helpers(self, adapter):
        # Create test data
        docs = TestDataBuilder.batch_documents(5)
        
        # Add to database
        await adapter.add_documents_batch(docs)
        
        # Create query
        query = TestDataBuilder.document()
        
        # Search
        results = await adapter.search_documents(
            query_embedding=query["embedding"],
            match_count=3
        )
        
        # Validate results
        for result in results:
            TestAssertions.assert_search_result_valid(result)
```

## Conclusion

These test helpers significantly improve test quality by:

- Reducing code duplication
- Providing consistent test data
- Simplifying mock creation
- Improving error messages
- Tracking test performance

Use them throughout the test suite to maintain high-quality, maintainable tests.
