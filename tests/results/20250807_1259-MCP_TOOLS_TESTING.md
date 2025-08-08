# MCP Tools Production-Grade Testing Results - 2025-08-07

**Date**: 2025-08-07
**Time**: 12:59:35 BST
**Environment**: Production-grade (docker-compose.dev.yml)
**Testing Tool**: Claude Code with MCP connection

## Test DateTime

2025-08-07T11:59:35Z

## Production Configuration

- OPENAI_API_KEY:  Valid production key (confirmed via service startup)
- USE_CONTEXTUAL_EMBEDDINGS: true
- USE_HYBRID_SEARCH: true  
- USE_AGENTIC_RAG: true
- USE_RERANKING: true
- USE_KNOWLEDGE_GRAPH: true
- VECTOR_DATABASE: qdrant

## Environment Health Check Results

- **Qdrant**:  Healthy (version 1.15.1) - <http://localhost:6333/>
- **Neo4j**:  Healthy (HTTP 200) - <http://localhost:7474/>
- **SearXNG**:  Healthy (OK response) - internal port 8080
- **MCP Server**:  Healthy - ports 5678, 8051
- **Valkey**:  Healthy - port 6379
- **MailHog**:  Running - ports 1025, 8025

## Test Results Summary

| Test ID | Tool | Test Case | Status | Time | Notes |
|---------|------|-----------|--------|------|-------|

## Detailed Test Results
