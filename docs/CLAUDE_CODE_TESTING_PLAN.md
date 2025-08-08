# Claude Code MCP Testing Plan for Crawl4AI

This document provides a comprehensive testing plan for connecting Claude Code to the Crawl4AI MCP server and validating all functionality with live code changes using Docker watch mode.

## Prerequisites

- Docker and Docker Compose installed
- Claude Code (Claude Desktop) installed
- Git repository cloned locally
- OpenAI API key for embeddings

## Phase 1: Environment Setup and Configuration

### 1.1 Configure Environment Variables

1. **Verify .env file exists**

   ```bash
   ls -la | grep .env
   ```

2. **Configure .env file**
   - Ensure `OPENAI_API_KEY` is set
   - Set `VECTOR_DATABASE=qdrant` for local development
   - Set `NEO4J_URI=bolt://neo4j:7687` (for Docker container communication)
   - Set `NEO4J_PASSWORD=password` (default for dev)
   - Keep `TRANSPORT=http` and `PORT=8051`

### 1.2 Start Development Environment

```bash
# Start all services in background with watch mode
make dev-bg

# Alternative: Start in foreground to see logs
make dev
```

This command will:

- Build the MCP server with development target
- Start all required services:
  - MCP Crawl4AI Server (port 8051)
  - Qdrant vector database (port 6333)
  - Neo4j graph database (ports 7474, 7687)
  - SearXNG search engine (port 8080)
  - Valkey cache (port 6379)
- Enable Docker watch mode for hot-reload
- Mount source directories for live code updates

### 1.3 Verify Services Health

```bash
# Check all services are running
docker compose -f docker-compose.dev.yml ps

# Verify MCP server health
curl http://localhost:8051/health

# Check Qdrant
curl http://localhost:6333/readyz

# Check Neo4j
curl http://localhost:7474

# Check SearXNG
curl http://localhost:8080/healthz
```

## Phase 2: Configure Claude Code Connection

Assume the User has Claude Code configured with:

```json
{
  "mcpServers": {
    "crawl4ai-docker": {
      "url": "http://localhost:8051/mcp",
      "transport": "http"
    }
  }
}
```

## Phase 3: Connection Validation

### 3.1 Run Pre-Connection Validation

```bash
# Comprehensive validation (checks environment, deps, databases)
uv run python tests/pre_connection_checklist.py

# Quick validation script
./scripts/validate_mcp_server.sh

# MCP protocol tests
uv run pytest tests/test_mcp_protocol.py -v
```

## Phase 4: Testing MCP Tools

### 4.1 Test Basic Web Scraping

**Tool: `scrape_urls`**

```
Test 1: Single URL scraping
- Scrape https://example.com
- Verify content is returned
- Check it's stored in Qdrant

Test 2: Batch scraping
- Scrape multiple URLs: ["https://example.com", "https://httpbin.org/html"]
- Verify batch processing works
- Check performance metrics
```

### 4.2 Test Search Integration

**Tool: `search`**

```
Test 1: Basic search with RAG
- Search for "python async programming"
- Verify SearXNG returns results
- Check URLs are scraped automatically
- Verify RAG processing returns relevant chunks

Test 2: Raw markdown mode
- Same search with return_raw_markdown=true
- Verify full content is returned without RAG
```

### 4.3 Test RAG Queries

**Tool: `perform_rag_query`**

```
Test 1: Query scraped content
- Query: "what is async programming"
- Verify semantic search works
- Check similarity scores

Test 2: Source filtering
- Query with specific source_id
- Verify filtering works correctly
```

### 4.4 Test Source Management

**Tool: `get_available_sources`**

```
- List all scraped domains
- Verify sources from previous scrapes appear
- Check metadata is correct
```

### 4.5 Test Smart Crawling

**Tool: `smart_crawl_url`**

```
Test 1: Regular webpage
- Crawl a documentation site
- Verify recursive crawling works

Test 2: Sitemap
- Crawl a sitemap.xml URL
- Verify all pages are discovered
```

### 4.6 Test Knowledge Graph (Optional)

If `USE_KNOWLEDGE_GRAPH=true`:

**Tool: `parse_github_repository`**

```
- Parse a small Python repo
- Verify classes/methods are extracted
```

**Tool: `query_knowledge_graph`**

```
- Query for available repos
- List classes and methods
```

## Phase 5: Live Development Testing

### 5.1 Test Hot-Reload with Code Changes

1. **Make a simple change**:

   ```python
   # In src/crawl4ai_mcp.py, modify a tool description
   # For example, change the description of scrape_urls tool
   ```

2. **Verify automatic reload**:

   ```bash
   # Watch the logs
   docker compose -f docker-compose.dev.yml logs -f mcp-crawl4ai
   
   # You should see the service restart automatically
   ```

3. **Test the change**:
   - Use the modified tool in Claude Code
   - Verify the new behavior/description

### 5.2 Monitor Debugging

```bash
# Enable debug logging
export MCP_DEBUG=true

# View structured logs with request tracking
docker compose -f docker-compose.dev.yml logs -f mcp-crawl4ai | grep -E "\[INFO\]|\[ERROR\]|\[DEBUG\]"
```

### 5.3 Test Error Handling

1. **Invalid URL test**:
   - Try scraping "not-a-url"
   - Verify proper error response

2. **Missing parameters**:
   - Call tools without required params
   - Check error messages are helpful

3. **Database errors**:
   - Try queries when no content exists
   - Verify graceful handling

## Phase 6: Performance and Integration Testing

### 6.1 Run Test Suites

```bash
# Unit tests only
make test-unit

# Integration tests (requires services running)
make test-integration

# Specific Qdrant tests
make test-qdrant

# Full CI test suite
make test-ci
```

### 6.2 Test Concurrent Operations

1. **Batch scraping performance**:
   - Scrape 10+ URLs simultaneously
   - Monitor resource usage
   - Check completion times

2. **Concurrent searches**:
   - Run multiple search operations
   - Verify no conflicts

## Troubleshooting Guide

### Common Issues and Solutions

1. **Connection refused on port 8051**

   ```bash
   # Check if service is running
   docker compose -f docker-compose.dev.yml ps mcp-crawl4ai
   
   # Restart the service
   docker compose -f docker-compose.dev.yml restart mcp-crawl4ai
   ```

2. **Tools not appearing in Claude Code**
   - Verify MCP server config in claude_desktop_config.json
   - Restart Claude Code
   - Check server logs for errors

3. **Qdrant connection errors**

   ```bash
   # Verify Qdrant is healthy
   curl http://localhost:6333/health
   
   # Check Qdrant logs
   docker compose -f docker-compose.dev.yml logs qdrant
   ```

4. **Hot-reload not working**
   - Ensure you're using `make dev` or `make dev-bg`
   - Check volume mounts in docker-compose.dev.yml
   - Verify file changes are saved

### Useful Commands

```bash
# View all logs
docker compose -f docker-compose.dev.yml logs -f

# Restart specific service
docker compose -f docker-compose.dev.yml restart mcp-crawl4ai

# Stop everything
make dev-down

# Rebuild and restart
make dev-rebuild

# Open shell in container
make dev-shell

# Open Python REPL in container
make dev-python
```

## Success Criteria

✅ All services start successfully  
✅ Claude Code connects to MCP server  
✅ All tools are discoverable and functional  
✅ Web scraping stores content in Qdrant  
✅ Search integration works with SearXNG  
✅ RAG queries return relevant results  
✅ Hot-reload works for code changes  
✅ Error handling is graceful  
✅ Integration tests pass  

## Next Steps

Once testing is complete:

1. Document any issues found
2. Test production deployment with `docker-compose.prod.yml`
3. Set up monitoring for production use
4. Configure proper API keys and security for production
