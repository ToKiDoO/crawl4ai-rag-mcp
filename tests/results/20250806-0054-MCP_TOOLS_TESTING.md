# MCP Tools Production-Grade Testing Results - 2025-08-06T00:54:26 BST

**Date**: 2025-08-06T00:54:26 BST
**Environment**: Production-grade (docker-compose.dev.yml)  
**Testing Tool**: Claude Code with MCP connection
**Tester**: QA Agent (automated testing)

## Production Configuration

Verifying environment configuration...

### Environment Variables Status

- OPENAI_API_KEY: ✓ Valid production key (verified in containers)
- USE_CONTEXTUAL_EMBEDDINGS: true
- USE_HYBRID_SEARCH: true  
- USE_AGENTIC_RAG: true
- USE_RERANKING: true
- USE_KNOWLEDGE_GRAPH: true
- VECTOR_DATABASE: qdrant

### Service Health Check Results

**All Services: ✅ HEALTHY**

- **mcp-crawl4ai-dev**: ✅ healthy on ports 5678, 8051
- **qdrant-dev**: ✅ healthy on ports 6333-6334 (v1.15.1)
- **neo4j-dev**: ✅ healthy on ports 7474, 7687 (HTTP 200 OK)
- **searxng-dev**: ✅ healthy on port 8080 (responds OK)
- **valkey-dev**: ✅ healthy on port 6379
- **mailhog-dev**: ✅ running on ports 1025, 8025

**Environment Status**: ✅ Production-grade environment ready

## Test Execution Log

### Phase 1: Tool-by-Tool Testing

Starting systematic test execution at 2025-08-06T00:54:26 BST...
