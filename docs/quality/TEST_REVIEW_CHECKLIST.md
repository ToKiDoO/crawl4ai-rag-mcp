# Test Review Checklist

This checklist ensures comprehensive test quality for the Crawl4AI MCP Server project. Use this for reviewing test implementations and maintaining our 80% minimum coverage requirement.

## 📋 Pre-Review Setup

- [ ] **Environment Validation**: Test runs successfully with `uv run pytest`
- [ ] **Dependencies**: All test dependencies are properly mocked or available
- [ ] **Configuration**: Test environment variables are properly set (`.env.test`)
- [ ] **Isolation**: Tests can run independently and in any order

## 🎯 Test Coverage Requirements

### Coverage Thresholds

- [ ] **Overall Coverage**: ≥80% (enforced in pyproject.toml)
- [ ] **Critical Paths**: ≥90% for core MCP tools and database operations
- [ ] **Error Handling**: ≥70% for exception paths and edge cases
- [ ] **New Code**: 100% coverage for all new functions/methods

### Coverage Validation

- [ ] **HTML Report**: Run `uv run pytest --cov=src --cov-report=html` and review `htmlcov/index.html`
- [ ] **Missing Lines**: Address any missing lines shown in `--cov-report=term-missing`
- [ ] **Branch Coverage**: Ensure all conditional branches are tested
- [ ] **Edge Cases**: Cover boundary conditions and exceptional scenarios

## 🧪 Test Quality Criteria

### Test Structure & Organization

- [ ] **Descriptive Names**: Test names clearly describe what is being tested

  ```python
  # Good: test_crawl_url_returns_structured_content_with_valid_url
  # Bad: test_crawl_url
  ```

- [ ] **AAA Pattern**: Tests follow Arrange-Act-Assert structure
- [ ] **Single Responsibility**: Each test validates one specific behavior
- [ ] **Test Categories**: Proper pytest markers applied (`@pytest.mark.unit`, `@pytest.mark.integration`)

### Test Data & Fixtures

- [ ] **Realistic Data**: Test data mirrors production scenarios
- [ ] **Fixture Reuse**: Common test data defined in `conftest.py` fixtures
- [ ] **Data Isolation**: Tests don't share mutable state
- [ ] **Cleanup**: Proper teardown of test resources and temporary data

### Assertions & Validation

- [ ] **Specific Assertions**: Use precise assertions rather than generic `assert result`
- [ ] **Multiple Validations**: Test both positive and negative cases
- [ ] **Error Messages**: Custom assertion messages for complex validations
- [ ] **Type Validation**: Verify return types match expected interfaces

## 🚀 MCP-Specific Testing Considerations

### FastMCP Framework Testing

- [ ] **Tool Registration**: Verify MCP tools are properly registered with `@mcp.tool()` decorator
- [ ] **Tool Metadata**: Validate tool descriptions, parameters, and return types
- [ ] **Error Handling**: Test MCP-specific error responses and formatting
- [ ] **Protocol Compliance**: Ensure responses conform to MCP protocol standards

### MCP Tool Validation

- [ ] **Parameter Validation**: Test all parameter combinations and edge cases
- [ ] **Return Value Structure**: Verify JSON serializable responses
- [ ] **Error Propagation**: Ensure internal errors are properly wrapped in `MCPToolError`
- [ ] **Resource Management**: Validate proper cleanup of resources (connections, files)

### Context Management

- [ ] **Lifespan Events**: Test FastMCP lifespan management (`crawl4ai_lifespan`)
- [ ] **State Persistence**: Verify shared state handling across tool calls
- [ ] **Concurrency**: Test concurrent tool invocations don't cause conflicts
- [ ] **Resource Limits**: Validate behavior under resource constraints

## ⚡ Async Testing Best Practices

### Async Test Structure

- [ ] **AsyncIO Decorator**: All async tests use `@pytest.mark.asyncio`
- [ ] **Proper Awaiting**: All async calls are properly awaited
- [ ] **Event Loop Management**: Tests don't interfere with event loop
- [ ] **Timeout Handling**: Long-running operations have appropriate timeouts

### Async Patterns

- [ ] **Concurrent Operations**: Test parallel async operations where applicable
- [ ] **Error Propagation**: Verify async exceptions are properly handled
- [ ] **Resource Cleanup**: Ensure async context managers are used correctly
- [ ] **Deadlock Prevention**: No blocking calls in async contexts

### Database Async Operations

- [ ] **Connection Pooling**: Test async database connection management
- [ ] **Transaction Isolation**: Verify async transaction boundaries
- [ ] **Batch Operations**: Test async bulk operations for performance
- [ ] **Connection Recovery**: Test reconnection logic for network failures

## 🎭 Mock Usage Guidelines

### Mock Strategy

- [ ] **External Dependencies**: Mock all external services (OpenAI, databases, web requests)
- [ ] **Deterministic Behavior**: Mocks provide consistent, predictable responses
- [ ] **Realistic Responses**: Mock data matches expected production formats
- [ ] **Error Simulation**: Include mocks for error conditions and edge cases

### Mock Implementation

- [ ] **Patch Paths**: Mock patches target the correct import paths
- [ ] **Return Values**: Mock return values match expected types and structures
- [ ] **Side Effects**: Use `side_effect` for complex mock behaviors
- [ ] **Call Verification**: Verify mock calls with expected parameters

### Database Mocking

- [ ] **Vector Dimensions**: OpenAI embeddings mocked with 1536 dimensions
- [ ] **Async Client Mocking**: Database clients properly mocked for async operations
- [ ] **Batch Operations**: Mock batch insert/update operations realistically
- [ ] **Error Conditions**: Mock database connection errors and timeouts

### API Mocking

- [ ] **HTTP Responses**: Mock external API responses with realistic data
- [ ] **Rate Limiting**: Mock API rate limiting and retry behavior
- [ ] **Authentication**: Mock authentication flows and token management
- [ ] **Network Errors**: Mock network failures and timeout scenarios

## 🔗 Integration Test Requirements

### Service Dependencies

- [ ] **Docker Services**: Integration tests use Docker Compose services
- [ ] **Service Health**: Verify service readiness before running tests
- [ ] **Port Management**: Tests use consistent, non-conflicting ports
- [ ] **Resource Cleanup**: Proper cleanup of Docker resources after tests

### Database Integration

- [ ] **Qdrant Testing**: Vector database operations with real Qdrant instance
- [ ] **Neo4j Testing**: Graph database operations with real Neo4j instance
- [ ] **Data Persistence**: Verify data persists across service restarts
- [ ] **Migration Testing**: Test database schema migrations and upgrades

### End-to-End Workflows

- [ ] **Complete Pipelines**: Test full crawl → embed → store → retrieve workflows
- [ ] **Error Recovery**: Test system behavior under partial failures
- [ ] **Performance**: Validate response times meet acceptable thresholds
- [ ] **Concurrent Access**: Test multiple simultaneous operations

## 🏗️ Test Architecture & Patterns

### Test Organization

- [ ] **Module Structure**: Tests mirror source code structure
- [ ] **Shared Utilities**: Common test helpers in `tests/conftest.py`
- [ ] **Test Categories**: Clear separation of unit, integration, and performance tests
- [ ] **Parallel Execution**: Tests can run in parallel with `pytest-xdist`

### Test Doubles Strategy

- [ ] **Stub vs Mock**: Appropriate use of stubs for state, mocks for behavior
- [ ] **Fake Objects**: Use fake implementations for complex dependencies
- [ ] **Test Builders**: Builder pattern for complex test data creation
- [ ] **Factory Methods**: Factory methods for creating test objects

### Error Testing Patterns

- [ ] **Exception Types**: Test specific exception types, not just generic `Exception`
- [ ] **Error Messages**: Validate error message content and formatting
- [ ] **Error Recovery**: Test system recovery from error conditions
- [ ] **Logging Verification**: Verify appropriate error logging occurs

## 🔍 Code Quality Integration

### Static Analysis Integration

- [ ] **Ruff Compliance**: Tests pass ruff linting and formatting checks
- [ ] **Type Hints**: Test code includes appropriate type annotations
- [ ] **Documentation**: Complex test logic includes explanatory comments
- [ ] **Security**: Tests don't expose secrets or sensitive information

### Performance Considerations

- [ ] **Test Speed**: Unit tests complete in <5 seconds, integration tests <30 seconds
- [ ] **Resource Usage**: Tests don't consume excessive memory or CPU
- [ ] **Cleanup Efficiency**: Efficient cleanup of test resources
- [ ] **Parallel Safety**: Tests can run concurrently without interference

### Maintenance Guidelines

- [ ] **Brittle Test Prevention**: Tests focus on behavior, not implementation details
- [ ] **Test Readability**: Tests serve as living documentation
- [ ] **Refactoring Safety**: Tests enable confident refactoring
- [ ] **Debug Information**: Failed tests provide clear diagnostic information

## ✅ Review Completion Checklist

### Final Validation

- [ ] **All Tests Pass**: Complete test suite passes locally
- [ ] **Coverage Goals Met**: Coverage reports show ≥80% overall coverage
- [ ] **CI Compatibility**: Tests pass in CI/CD environment
- [ ] **Documentation Updated**: Test documentation reflects any new patterns

### Sign-off Requirements

- [ ] **Reviewer Approval**: At least one team member has reviewed tests
- [ ] **Coverage Report**: HTML coverage report reviewed for gaps
- [ ] **Performance Check**: No significant performance regression in test execution
- [ ] **Integration Validation**: Integration tests pass with real services

---

## 📚 Additional Resources

- **Test Documentation**: `/tests/README.md`
- **Test Helpers Reference**: `/docs/testing/test-helpers-reference.md`
- **Coverage Configuration**: `pyproject.toml` - `[tool.coverage.*]` sections
- **CI Configuration**: `.github/workflows/test-coverage.yml`
- **Performance Monitoring**: `tests/performance_plugin.py`
