# Test Suite for Crawl4AI MCP Server

This directory contains comprehensive tests for the Crawl4AI MCP server with database abstraction support.

## Test Structure

### Unit Tests
- `test_utils_refactored.py` - Tests for utility functions (embeddings, document processing, etc.)
- `test_database_factory.py` - Tests for database factory and adapter creation
- `test_crawl4ai_mcp.py` - Tests for MCP tool functions

### Adapter Tests
- `test_supabase_adapter.py` - Supabase-specific adapter tests with mocks
- `test_qdrant_adapter.py` - Qdrant-specific adapter tests with mocks
- `test_database_interface.py` - Interface contract tests that both adapters must pass

### Integration Tests
- `test_integration.py` - Full integration tests with real Docker containers
- `test_integration_simple.py` - Integration tests with mocked dependencies

## Running Tests

### Quick Start
```bash
# Run all unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_utils_refactored.py -v
```

### Using Test Scripts
```bash
# Run unit tests with coverage reporting
./scripts/run_tests_with_coverage.sh

# Run integration tests with Docker
./scripts/run_integration_tests.sh
```

## Test Coverage

Current test coverage targets:
- Overall: >80%
- Critical paths: >90%
- Error handling: >70%

### Coverage Reports
- Terminal: Shown after test runs
- HTML: Generated in `htmlcov/index.html`
- XML: Generated as `coverage.xml` for CI/CD

### Viewing HTML Coverage
```bash
# After running tests with coverage
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Writing Tests

### Test Guidelines
1. Use descriptive test names that explain what is being tested
2. Follow the Arrange-Act-Assert pattern
3. Mock external dependencies (databases, APIs)
4. Test both success and failure cases
5. Include edge cases (empty inputs, large batches, special characters)

### Example Test Structure
```python
@pytest.mark.asyncio
async def test_feature_success_case(self, mock_dependency):
    """Test that feature works correctly with valid input"""
    # Arrange
    input_data = {"key": "value"}
    mock_dependency.method.return_value = "expected"
    
    # Act
    result = await function_under_test(input_data)
    
    # Assert
    assert result == "expected"
    mock_dependency.method.assert_called_once_with(input_data)
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:
- `get_adapter()` - Factory for creating database adapters
- `mock_openai_embeddings()` - Mock OpenAI API responses
- `event_loop` - Async event loop for tests

## Continuous Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

See `.github/workflows/test-coverage.yml` for CI configuration.

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure you're running tests from project root
2. **Async warnings**: Use `@pytest.mark.asyncio` decorator
3. **Mock not working**: Check mock patch paths match actual imports
4. **Coverage missing files**: Check `pytest.ini` for exclusions

### Debug Mode
```bash
# Run with verbose output and show print statements
pytest tests/ -v -s

# Run with debugger on failure
pytest tests/ --pdb
```