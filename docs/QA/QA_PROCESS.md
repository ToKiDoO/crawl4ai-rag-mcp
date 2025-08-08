# QA Process for Qdrant Implementation

This document outlines the Quality Assurance process for testing the Qdrant vector database implementation in the Crawl4AI MCP server.

## Overview

The QA process ensures that the Qdrant adapter correctly implements the VectorDatabase interface and that the MCP server functions properly with Qdrant as the backend.

## Prerequisites

1. **Development Environment**
   - Python 3.12+
   - UV package manager
   - Docker and Docker Compose
   - Git

2. **Configuration**
   - `.env` file configured with `VECTOR_DATABASE=qdrant`
   - OpenAI API key for embeddings
   - Qdrant accessible at configured URL

## Testing Phases

**Important**: Always use `uv run` prefix when executing Python scripts to ensure proper dependency resolution.

### Phase 1: Pre-Connection Validation

Before connecting any MCP client, validate the environment:

```bash
# 1. Run comprehensive pre-connection checklist with UV
uv run python tests/pre_connection_checklist.py

# 2. Quick validation (optional)
./scripts/validate_mcp_server.sh
```

Expected output:

- Python Version: PASS (3.12+)
- Environment File: PASS (all variables present)
- Dependencies: PASS (all critical dependencies available)
- Vector Database Config: PASS (Qdrant accessible)
- Database Initialization: PASS (QdrantAdapter initialized)
- MCP Server Startup: PASS (tools registered)

**Acceptable Warnings:**

- Playwright browser check warnings (async/sync API conflict)
- Docker compose status check warnings
- Tool registration warnings about duplicates

### Phase 2: Unit Testing

Run unit tests for core functionality:

```bash
# Run all unit tests
uv run pytest tests/ -v -k "not integration"

# Specific test categories
uv run pytest tests/test_mcp_protocol.py -v        # Protocol compliance
uv run pytest tests/test_qdrant_adapter.py -v      # Adapter implementation
uv run pytest tests/test_database_interface.py -v  # Interface contracts
uv run pytest tests/test_database_factory.py -v    # Factory pattern
uv run pytest tests/test_utils.py -v    # Utility functions
uv run pytest tests/test_crawl4ai_mcp.py -v        # Core MCP server
```

### Phase 3: Integration Testing

Test end-to-end functionality with Qdrant:

```bash
# Start Qdrant container
docker compose -f docker-compose.test.yml up -d

# Wait for Qdrant to be ready
curl --retry 5 --retry-delay 2 http://localhost:6333

# Run integration tests
uv run pytest tests/test_mcp_qdrant_integration.py -v -m integration
uv run pytest tests/test_integration_simple.py -v
uv run pytest tests/test_integration.py -v
```

### Phase 4: MCP Client Testing

Connect and test with Claude Desktop:

1. **Configure Claude Desktop**

   Edit `%APPDATA%\Claude\claude_desktop_config.json`:

   ```json
   {
     "mcpServers": {
       "crawl4ai-rag-qdrant": {
         "command": "wsl",
         "args": [
           "--cd",
           "/home/krashnicov/crawl4aimcp",
           "--",
           "bash",
           "-c",
           "export TRANSPORT=stdio VECTOR_DATABASE=qdrant QDRANT_URL=http://localhost:6333 && /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
         ]
       }
     }
   }
   ```

2. **Restart Claude Desktop**
   - Close Claude Desktop completely
   - Start Claude Desktop
   - Check for MCP server connection

3. **Manual Test Scenarios**

   **Test 1: Basic Connectivity**

   ```
   Ask: "What MCP tools are available?"
   Expected: List including scrape_urls, perform_rag_query, etc.
   ```

   **Test 2: URL Scraping**

   ```
   Ask: "Scrape https://example.com"
   Expected: Success message with content stored
   ```

   **Test 3: RAG Query**

   ```
   Ask: "Search for 'example' in the scraped content"
   Expected: Retrieved relevant chunks with similarity scores
   ```

   **Test 4: Code Search**

   ```
   Ask: "Search for Python code examples"
   Expected: Code snippets if available, or "No code examples found"
   ```

## Test Scenarios

### Functional Tests

1. **Document Storage**
   - Single URL scraping
   - Batch URL processing
   - Large document handling
   - Special character handling

2. **Search Operations**
   - Vector similarity search
   - Keyword search
   - Filtered search by source
   - Empty result handling

3. **Code Extraction** (if enabled)
   - Python code detection
   - JavaScript code detection
   - Code summary generation

4. **Error Handling**
   - Invalid URLs
   - Network timeouts
   - Qdrant connection loss
   - Invalid embeddings

### Performance Tests

1. **Throughput**
   - Scrape 10 URLs concurrently
   - Measure time and resource usage

2. **Query Performance**
   - RAG query response time <2s
   - Search result quality

3. **Scalability**
   - Handle 1000+ documents
   - Concurrent query handling

## Debugging Guide

### Enable Debug Logging

```bash
export MCP_DEBUG=true
```

### Common Issues

1. **MCP Connection Failures**

   ```bash
   # Check logs
   tail -f ~/.cache/crawl4ai/logs/*.log
   
   # Validate configuration
   uv run python tests/pre_connection_checklist.py
   ```

2. **Qdrant Connection Issues**

   ```bash
   # Check Qdrant status
   curl http://localhost:6333
   
   # Check collections
   curl http://localhost:6333/collections
   ```

3. **Embedding Failures**
   - Verify OpenAI API key
   - Check network connectivity
   - Monitor API rate limits

### Log Analysis

Important log patterns to watch:

```
[INFO] Starting {tool_name} request     # Tool execution start
[ERROR] Failed {tool_name}              # Tool execution failure  
[DEBUG] Arguments: {args}               # Request parameters
[INFO] Completed {tool_name} in Xs      # Performance metrics
```

## Test Data Management

### Setup Test Data

```bash
# Create test collection
python scripts/setup_test_data.py

# Populate with sample documents
python scripts/populate_qdrant.py
```

### Cleanup

```bash
# Remove test data
docker compose -f docker-compose.test.yml down -v

# Clean cache
rm -rf ~/.cache/crawl4ai/
```

## Reporting

### Test Results Format

Document test results in this format:

```markdown
## QA Test Results - [Date]

**Environment:**
- Python: 3.12.x
- Qdrant: 1.7.x
- Platform: WSL/Windows/Mac

**Test Summary:**
- Unit Tests: X/Y passed
- Integration Tests: X/Y passed  
- Manual Tests: X/Y passed

**Issues Found:**
1. [Issue description]
   - Severity: High/Medium/Low
   - Status: Fixed/Open

**Performance Metrics:**
- Avg scrape time: Xs
- Avg query time: Xms
- Memory usage: XMB
```

## Continuous Testing

### Automated Testing

Run tests before each commit:

```bash
# Add to pre-commit hook
uv run pytest tests/ -v --tb=short
```

### Regression Testing

After fixes or updates:

1. Run full test suite
2. Verify previously reported issues
3. Check performance metrics
4. Update test cases as needed

## Sign-off Criteria

The QA process is complete when:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual MCP client tests successful
- [ ] Performance meets requirements
- [ ] No critical/high severity issues
- [ ] Documentation updated
- [ ] Test results documented

## Additional Resources

- [MCP Testing Guide](./MCP_TESTING.md) - Detailed testing framework documentation
- [Claude Desktop Config](./CLAUDE_DESKTOP_CONFIG_WINDOWS.md) - Windows configuration guide
- [Test Scripts](./tests/) - Automated test implementations
