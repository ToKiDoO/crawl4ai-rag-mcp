# MCP Server Testing Guide

This guide describes the comprehensive testing framework implemented for the Crawl4AI MCP server, based on best practices from the PubNub MCP testing article.

## Quick Start

### Pre-Connection Validation

Before connecting any MCP client (like Claude Desktop), run these validation steps:

```bash
# 1. Run the pre-connection checklist
python tests/pre_connection_checklist.py

# 2. Run the quick validation script
./scripts/validate_mcp_server.sh

# 3. Run MCP protocol tests
pytest tests/test_mcp_protocol.py -v
```

## Testing Components

### 1. Pre-Connection Checklist (`tests/pre_connection_checklist.py`)

Comprehensive validation of the MCP server environment:

- **Environment Checks**
  - Python version (>=3.12)
  - .env file configuration
  - Required dependencies
  - Playwright browser installation

- **Database Checks**
  - Vector database configuration (Qdrant/Supabase)
  - Database connectivity
  - Database initialization

- **MCP Server Checks**  
  - Server startup validation
  - Tool registration verification
  - Configuration validation

- **Infrastructure Checks**
  - Docker Compose services
  - Container health status

Run with color-coded output showing ✓ PASS, ✗ FAIL, and ! WARN statuses.

### 2. Quick Validation Script (`scripts/validate_mcp_server.sh`)

Bash script for rapid validation:

```bash
./scripts/validate_mcp_server.sh
```

Performs:
- Environment verification
- Dependency checks
- Vector database connectivity
- MCP server loading test
- JSON-RPC format validation

Returns exit code 0 on success, 1 on failure.

### 3. MCP Protocol Tests (`tests/test_mcp_protocol.py`)

Validates MCP protocol compliance:

- **Tool Discovery**
  - All tools are discoverable
  - Tool metadata is complete
  - Input schemas are valid

- **Parameter Validation**
  - Required parameters are enforced
  - Optional parameters have defaults
  - Type validation works correctly

- **Error Handling**
  - Missing parameters produce errors
  - Invalid types are caught
  - Error format follows JSON-RPC spec

Run with pytest:
```bash
pytest tests/test_mcp_protocol.py -v
```

### 4. MCP Test Utilities (`tests/mcp_test_utils.py`)

Helper utilities for MCP testing:

- `MCPRequest` - Create JSON-RPC requests
- `MCPResponse` - Parse JSON-RPC responses  
- `MCPTestClient` - Simulate MCP client behavior
- `MCPValidator` - Validate protocol compliance
- `MockMCPServer` - Mock server for testing

Example usage:
```python
from mcp_test_utils import MCPTestClient, MCPValidator

client = MCPTestClient()
request = client.create_tool_discovery_request()
# Send request and validate response
```

### 5. Qdrant Integration Tests (`tests/test_mcp_qdrant_integration.py`)

End-to-end tests with Qdrant:

- Complete flow testing (scrape → store → search → RAG)
- Error handling scenarios
- Batch processing validation
- Qdrant-specific features
- Reranking integration

Run integration tests:
```bash
pytest tests/test_mcp_qdrant_integration.py -v -m integration
```

## Enhanced Logging

The MCP server now includes comprehensive logging:

### Structured Logging
- Timestamp, level, component name in all logs
- Logs to stderr for clean JSON-RPC communication
- Request tracking with unique IDs

### Debug Mode
Enable detailed logging:
```bash
export MCP_DEBUG=true
```

### Request Tracking
All MCP tool requests are tracked with:
- Unique request ID (8-char UUID)
- Start/completion timestamps
- Duration measurements
- Error details with tracebacks

Example log output:
```
2024-01-15 10:23:45 [INFO] [crawl4ai-mcp] [a1b2c3d4] Starting search request
2024-01-15 10:23:45 [DEBUG] [crawl4ai-mcp] [a1b2c3d4] Arguments: {'query': 'python async', 'num_results': 5}
2024-01-15 10:23:47 [INFO] [crawl4ai-mcp] [a1b2c3d4] Completed search in 2.15s
```

## Testing Workflow

### Before First Connection

1. **Environment Setup**
   ```bash
   # Ensure .env is configured
   cp .env.example .env
   # Edit .env with your settings
   
   # Start Qdrant if using
   docker compose -f docker-compose.test.yml up -d
   ```

2. **Run Validation Suite**
   ```bash
   # Full validation
   python tests/pre_connection_checklist.py
   
   # Quick check
   ./scripts/validate_mcp_server.sh
   ```

3. **Run Tests**
   ```bash
   # Unit tests
   pytest tests/test_mcp_protocol.py -v
   
   # Integration tests (requires Qdrant running)
   pytest tests/test_mcp_qdrant_integration.py -v -m integration
   ```

### During Development

1. **Enable Debug Logging**
   ```bash
   export MCP_DEBUG=true
   ```

2. **Monitor Logs**
   ```bash
   # If using WSL/direct execution
   tail -f ~/.cache/crawl4ai/logs/*.log
   
   # If using Docker
   docker compose logs -f mcp-crawl4ai
   ```

3. **Test Individual Tools**
   ```python
   from mcp_test_utils import test_tool_directly
   
   result = await test_tool_directly(
       "search",
       {"query": "test query", "num_results": 3}
   )
   ```

## Troubleshooting

### Common Issues

1. **JSON Parsing Errors**
   - Check for print statements going to stdout
   - Ensure all output uses logger or stderr
   - Verify clean JSON-RPC responses

2. **Tool Discovery Failures**
   - Run `python tests/test_mcp_protocol.py::TestMCPProtocol::test_tool_discovery`
   - Check tool registration in server startup logs

3. **Database Connection Issues**
   - Verify Qdrant is running: `curl http://localhost:6333/health`
   - Check VECTOR_DATABASE and QDRANT_URL in .env
   - Run database-specific tests

4. **Async/Await Errors**
   - Qdrant client methods are synchronous (don't use await)
   - Check adapter implementation matches database client

### Debug Commands

```bash
# Test MCP server startup
python tests/test_mcp_basic.py

# Validate specific tool
pytest tests/test_mcp_protocol.py::TestMCPProtocol::test_tool_parameters -v

# Check Qdrant health
curl http://localhost:6333/health

# View Docker logs
docker compose -f docker-compose.test.yml logs qdrant-test
```

## Continuous Improvement

### Adding New Tests

When adding new MCP tools:

1. Add protocol tests in `test_mcp_protocol.py`
2. Add integration tests if tool uses database
3. Update validation scripts if new dependencies
4. Document any special testing requirements

### Performance Testing

Monitor performance with request tracking:
- Tool execution times logged automatically
- Identify slow operations in logs
- Set up alerts for operations >5s

### CI/CD Integration

Future: GitHub Actions workflow for automated testing
- Run on PR to feature/qdrant branch
- Execute full test suite
- Report coverage metrics
- Validate against multiple Python versions