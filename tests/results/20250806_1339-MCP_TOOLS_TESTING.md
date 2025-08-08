# MCP Tools Production-Grade Testing Results - 2025-08-06T13:39:16Z

**Date**: 2025-08-06T13:39:16Z
**Environment**: Production-grade (docker-compose.dev.yml)
**Testing Tool**: Claude Code with MCP connection
**Test Executor**: QA Agent

## Production Configuration

### Environment Variables Verified

- OPENAI_API_KEY: ✓ Valid production key (present)
- USE_CONTEXTUAL_EMBEDDINGS: true
- USE_HYBRID_SEARCH: true  
- USE_AGENTIC_RAG: true
- USE_RERANKING: true
- USE_KNOWLEDGE_GRAPH: true
- VECTOR_DATABASE: qdrant

## Service Health Check Results

### Pre-Test Service Health Validation

**Test DateTime**: 2025-08-06T13:39:16Z

## Test Summary

| Tool | Test Case | Status | Time | Notes |
|------|-----------|--------|------|-------|
| get_available_sources | List sources | PENDING | - | Starting Phase 1 testing |
| scrape_urls | Single URL | PENDING | - | |
| scrape_urls | Multiple URLs | PENDING | - | |
| search | Search and scrape | PENDING | - | |
| smart_crawl_url | Regular website | PENDING | - | |
| smart_crawl_url | Sitemap | PENDING | - | |
| perform_rag_query | Basic query | PENDING | - | |
| perform_rag_query | Filtered query | PENDING | - | |
| search_code_examples | Code search | PENDING | - | |
| parse_github_repository | Basic parsing | PENDING | - | |
| parse_repository_branch | Branch parsing | PENDING | - | |
| get_repository_info | Metadata retrieval | PENDING | - | |
| update_parsed_repository | Repository update | PENDING | - | |
| extract_and_index_repository_code | Neo4j-Qdrant bridge | PENDING | - | |
| smart_code_search | Fast mode | PENDING | - | |
| smart_code_search | Balanced mode | PENDING | - | |
| smart_code_search | Thorough mode | PENDING | - | |
| check_ai_script_hallucinations_enhanced | Enhanced detection | PENDING | - | |
| query_knowledge_graph | Graph queries | PENDING | - | |
| check_ai_script_hallucinations | Basic detection | PENDING | - | |

## Detailed Test Results

### Phase 1: Tool-by-Tool Testing
