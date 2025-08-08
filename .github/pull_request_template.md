<!-- 
Thank you for contributing to the Crawl4AI MCP Server project! 
Please fill out this template to help us review your pull request efficiently.
-->

## 📝 Pull Request Summary

### Description
<!-- Provide a clear and concise description of what this PR does -->

### Type of Change
<!-- Mark the type of change with an 'x' -->
- [ ] 🐛 **Bug fix** (non-breaking change that fixes an issue)
- [ ] ✨ **New feature** (non-breaking change that adds functionality)
- [ ] 💥 **Breaking change** (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 **Documentation** (adding or updating documentation)
- [ ] 🎨 **Code style** (formatting, renaming, etc; no functional changes)
- [ ] ♻️  **Refactoring** (code restructuring without changing behavior)
- [ ] ⚡ **Performance** (changes that improve performance)
- [ ] 🧪 **Tests** (adding missing tests or correcting existing tests)
- [ ] 🔧 **Configuration** (changes to configuration files or CI/CD)

### Related Issues
<!-- Link any related issues using "Fixes #123" or "Closes #123" -->
- Fixes #
- Related to #

## 🧪 Testing & Quality Assurance

### Test Coverage
<!-- Complete this section for all code changes -->
- [ ] **Tests Added**: New tests added for new functionality
- [ ] **Tests Updated**: Existing tests updated for modified functionality  
- [ ] **Coverage Maintained**: Test coverage remains ≥80% overall
- [ ] **Critical Path Coverage**: ≥90% coverage for core MCP tools and database operations
- [ ] **Local Testing**: All tests pass locally with `uv run pytest`

### Test Types Implemented
<!-- Mark all applicable test types -->
- [ ] **Unit Tests**: Individual function/method testing
- [ ] **Integration Tests**: Component interaction testing
- [ ] **MCP Protocol Tests**: MCP tool compliance testing
- [ ] **Database Tests**: Database adapter and interface testing
- [ ] **Async Tests**: Async/await pattern testing
- [ ] **Error Handling Tests**: Exception and edge case testing
- [ ] **Performance Tests**: Response time and throughput testing

### Test Quality Verification

- [ ] **Descriptive Names**: Test names clearly describe what is being tested
- [ ] **AAA Pattern**: Tests follow Arrange-Act-Assert structure
- [ ] **Proper Mocking**: External dependencies are properly mocked
- [ ] **Async Compliance**: Async tests use `@pytest.mark.asyncio` decorator
- [ ] **Vector Dimensions**: OpenAI embeddings mocked with 1536 dimensions
- [ ] **Resource Cleanup**: Proper cleanup of test resources and connections

## 🔍 Code Quality Checklist

### Code Standards

- [ ] **Ruff Linting**: Code passes ruff linting (`uv run ruff check src/ tests/`)
- [ ] **Code Formatting**: Code passes ruff formatting (`uv run ruff format src/ tests/ --check`)
- [ ] **Type Hints**: New code includes appropriate type annotations
- [ ] **Documentation**: Public APIs include docstrings
- [ ] **No Debug Code**: No print statements or debugger calls in production code

### Architecture & Design

- [ ] **SOLID Principles**: Code follows SOLID design principles
- [ ] **Async Patterns**: Proper use of async/await throughout
- [ ] **Error Handling**: Comprehensive error handling with specific exceptions
- [ ] **Resource Management**: Proper cleanup of connections and resources
- [ ] **Interface Compliance**: Database adapters implement required interfaces

### Security Considerations

- [ ] **Input Validation**: All user inputs validated and sanitized
- [ ] **No Hardcoded Secrets**: Sensitive data stored in environment variables
- [ ] **SQL Injection Prevention**: Parameterized queries used
- [ ] **Logging Security**: No sensitive information logged
- [ ] **Dependency Security**: New dependencies scanned for vulnerabilities

## 🚀 MCP-Specific Requirements

### MCP Tool Implementation
<!-- Complete for MCP tool changes -->
- [ ] **Tool Registration**: MCP tools properly registered with `@mcp.tool()` decorator
- [ ] **Parameter Validation**: All tool parameters validated and typed
- [ ] **Return Types**: Tool responses are JSON serializable
- [ ] **Error Handling**: Internal errors wrapped in `MCPToolError`
- [ ] **Documentation**: Tool descriptions and parameters clearly documented

### Protocol Compliance

- [ ] **FastMCP Patterns**: Follows FastMCP framework patterns
- [ ] **Lifespan Management**: Proper resource lifecycle management
- [ ] **Context Handling**: Shared context properly managed
- [ ] **Async Operations**: All I/O operations are async
- [ ] **Response Format**: Responses conform to MCP protocol standards

## 📊 Performance Impact

### Performance Validation

- [ ] **Response Times**: MCP tools respond within acceptable thresholds (<2s for simple operations)
- [ ] **Memory Usage**: No significant memory leaks or excessive usage
- [ ] **Database Performance**: Database operations optimized and indexed
- [ ] **Concurrent Operations**: Code handles concurrent requests properly
- [ ] **Resource Cleanup**: Proper cleanup prevents resource leaks

### Performance Testing

- [ ] **Load Testing**: Tested under expected load conditions
- [ ] **Stress Testing**: Tested beyond normal operating conditions
- [ ] **Memory Profiling**: Memory usage profiled and optimized
- [ ] **Database Optimization**: Database queries optimized for performance

## 🐳 Docker & Infrastructure

### Docker Changes
<!-- Complete if Docker configuration is modified -->
- [ ] **Multi-stage Build**: Docker builds use efficient multi-stage process
- [ ] **Security**: Docker containers run as non-root user
- [ ] **Size Optimization**: Docker image size optimized
- [ ] **Health Checks**: Health check endpoints implemented
- [ ] **Environment Variables**: Configuration via environment variables

### Service Integration

- [ ] **Service Dependencies**: External service dependencies properly managed
- [ ] **Configuration**: Service configuration validated
- [ ] **Networking**: Network configuration secure and optimized
- [ ] **Volume Mounts**: Data persistence properly configured

## 📚 Documentation Updates

### Documentation Changes

- [ ] **README Updates**: README.md updated for user-facing changes
- [ ] **API Documentation**: API changes documented in docstrings
- [ ] **Configuration**: Environment variable changes documented
- [ ] **Migration Guide**: Breaking changes include migration instructions
- [ ] **CHANGELOG**: Changes documented in CHANGELOG.md

### Code Documentation

- [ ] **Inline Comments**: Complex logic includes explanatory comments
- [ ] **Docstrings**: Public functions include comprehensive docstrings
- [ ] **Type Annotations**: Function signatures include type hints
- [ ] **Examples**: Usage examples provided for new features

## 🔄 CI/CD Pipeline

### Pipeline Validation

- [ ] **All Stages Pass**: Complete CI/CD pipeline passes
- [ ] **Coverage Upload**: Coverage reports uploaded successfully
- [ ] **Security Scan**: Security scanning completes without critical issues
- [ ] **Performance Metrics**: Performance metrics collected and analyzed
- [ ] **Docker Build**: Docker image builds successfully

### Branch Status

- [ ] **Up-to-date**: Branch is up-to-date with target branch
- [ ] **Conflicts Resolved**: No merge conflicts with target branch
- [ ] **Clean History**: Commit history is clean and descriptive
- [ ] **Signed Commits**: Commits are signed (if required)

## 🎯 Review Guidelines

### For Reviewers

Please review the following aspects:

1. **Code Quality**: Architecture, patterns, and maintainability
2. **Test Coverage**: Comprehensive testing and quality
3. **Security**: Security implications and best practices
4. **Performance**: Performance impact and optimization
5. **Documentation**: Clear documentation and examples

### Breaking Changes
<!-- If this PR contains breaking changes, provide details -->
- [ ] **No Breaking Changes**: This PR does not contain breaking changes
- [ ] **Breaking Changes**: This PR contains breaking changes (provide details below)

**Breaking Change Details:**
<!-- Describe the breaking changes and migration path -->

## 📋 Pre-Review Self-Check

### Before Requesting Review

- [ ] **Self-Review**: I have reviewed my own code changes
- [ ] **Local Testing**: All tests pass locally
- [ ] **Documentation**: Documentation is complete and accurate
- [ ] **Clean Commits**: Commit messages are clear and descriptive
- [ ] **No WIP**: No work-in-progress or TODO comments

### Quality Gates

- [ ] **Coverage Threshold**: Code coverage meets ≥80% requirement
- [ ] **Linting Passes**: Ruff linting and formatting pass
- [ ] **Integration Tests**: Integration tests pass with Docker services
- [ ] **Performance Check**: No significant performance regression
- [ ] **Security Check**: No security vulnerabilities introduced

## 💬 Additional Notes

<!-- Any additional information that reviewers should know -->

---

## 🎉 Reviewer Assignment

<!-- Tag specific reviewers if needed -->
/cc @team-members

**Estimated Review Time:** <!-- e.g., 30 minutes, 2 hours -->

**Priority Level:**

- [ ] 🔴 **Critical** (hotfix, security issue)
- [ ] 🟡 **High** (major feature, breaking change)  
- [ ] 🟢 **Normal** (regular feature, bug fix)
- [ ] 🔵 **Low** (documentation, minor improvement)

---

<!-- 
Quality Gate Summary:
This PR template ensures comprehensive review coverage aligned with our quality gates.
For questions about quality requirements, see:
- docs/quality/TEST_REVIEW_CHECKLIST.md
- docs/quality/QUALITY_GATES.md
-->