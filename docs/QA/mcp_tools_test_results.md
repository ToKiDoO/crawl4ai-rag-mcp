# MCP crawl4ai-docker Tools Test Results

**Test Date**: 2025-08-04  
**Environment**: crawl4aimcp project  
**Total Tools Tested**: 9  
**Success Rate**: 0% (0/9) - See critical findings below

## ⚠️ Critical Finding

During testing, Docker logs revealed that tools reporting "success" actually failed to generate embeddings due to an invalid OpenAI API key (401 Unauthorized). This means content was scraped but not properly embedded for vector search, making RAG queries impossible.

## Summary Table

| Tool Name | Status | Error/Notes |
|-----------|--------|-------------|
| get_available_sources | ✅ Success* | Retrieved 4 sources (but see embedding issue) |
| search | ❌ Failure | Search worked but scraping failed: 'FunctionTool' object is not callable |
| scrape_urls | ❌ Failure | Scraped but embedding failed (401 OpenAI API error) |
| smart_crawl_url | ❌ Failure | Crawled but embedding failed (401 OpenAI API error) |
| perform_rag_query | ❌ Failure | metadata_filter argument error |
| search_code_examples | ❌ Failure | Feature disabled - requires ENABLE_AGENTIC_RAG=true |
| parse_github_repository | ❌ Failure | Knowledge graph disabled - requires USE_KNOWLEDGE_GRAPH=true |
| query_knowledge_graph | ❌ Failure | Knowledge graph disabled - requires USE_KNOWLEDGE_GRAPH=true |
| check_ai_script_hallucinations | ❌ Failure | Knowledge graph disabled - requires USE_KNOWLEDGE_GRAPH=true |

## Detailed Test Results

### 1. get_available_sources ✅

- **Test**: Called with no parameters
- **Result**: Successfully retrieved 4 sources
- **Sources Found**:
  - delete-test.example.com
  - example.com
  - github.com
  - mcp-test.example.com
- **Observation**: Works as expected, provides good overview of stored content

### 2. search ❌

- **Test**: Searched for "python tutorial" with 3 results
- **Result**: Partial failure
- **Details**:
  - SearXNG search successful - returned 3 URLs
  - Scraping phase failed with 'FunctionTool' object is not callable
- **URLs Retrieved**:
  - <https://docs.python.org/3/tutorial/index.html>
  - <https://www.w3schools.com/python/>
  - <https://www.pythontutorial.net/>
- **Issue**: Internal implementation error in scraping component

### 3. scrape_urls ❌

- **Test**: Scraped <https://example.com>
- **Result**: False Success (Embedding Failed)
- **Details**:
  - Content scraped: 230 characters, 29 words
  - Tool reported: 1 chunk stored
  - **Actual issue**: OpenAI API 401 error prevented embedding generation
  - Without embeddings, content cannot be searched via RAG
- **Docker logs**: `Error code: 401 - Invalid API key`

### 4. smart_crawl_url ❌

- **Test**: Crawled Python docs with max_depth=1
- **Result**: False Success (Embedding Failed)
- **Details**:
  - Content crawled: 1 page
  - Tool reported: 5 chunks stored
  - **Actual issue**: OpenAI API 401 error prevented embedding generation
  - Without embeddings, content cannot be searched via RAG
- **Docker logs**: `Error code: 401 - Invalid API key`

### 5. perform_rag_query ❌

- **Test**: Queried "what is python" with match_count=3
- **Result**: Failure
- **Error**: QdrantAdapter.search_documents() got an unexpected keyword argument 'metadata_filter'
- **Issue**: Implementation mismatch between expected and actual API

### 6. search_code_examples ❌

- **Test**: Searched for "print" in code examples
- **Result**: Failure
- **Error**: "Code example extraction is disabled. Perform a normal RAG search."
- **Resolution**: Requires ENABLE_AGENTIC_RAG=true in environment

### 7. parse_github_repository ❌

- **Test**: Parse octocat/Hello-World repository
- **Result**: Failure
- **Error**: "Knowledge graph functionality is disabled"
- **Resolution**: Requires USE_KNOWLEDGE_GRAPH=true in environment

### 8. query_knowledge_graph ❌

- **Test**: Query with "repos" command
- **Result**: Failure
- **Error**: "Knowledge graph functionality is disabled"
- **Resolution**: Requires USE_KNOWLEDGE_GRAPH=true in environment

### 9. check_ai_script_hallucinations ❌

- **Test**: Created test script with deliberate hallucinations
- **Result**: Failure
- **Error**: "Knowledge graph functionality is disabled"
- **Resolution**: Requires USE_KNOWLEDGE_GRAPH=true in environment
- **Note**: Test script created at `/home/krashnicov/crawl4aimcp/test_ai_script.py`

## Key Findings

### Critical Infrastructure Issue

**Invalid OpenAI API Key**: The most critical issue is that the OpenAI API key is invalid (401 Unauthorized), preventing embedding generation. This means:

- Content can be scraped but not embedded
- RAG queries cannot function without embeddings
- The entire vector search functionality is broken
- Tools report "success" but silently fail during embedding phase

### Actual Working Features

1. **get_available_sources**: Can list previously stored sources (read-only operation)
2. **Web Scraping**: Content extraction works, but without embedding it's incomplete
3. **Search**: SearXNG integration works for finding URLs

### Issues Identified

1. **Critical**: Invalid OpenAI API key blocks all embedding generation
2. **Search Tool**: FunctionTool implementation error in scraping phase
3. **RAG Query**: metadata_filter parameter mismatch (would fail even with valid embeddings)
4. **Disabled Features**: Multiple features require environment variables:
   - Code examples: ENABLE_AGENTIC_RAG=true
   - Knowledge graph tools: USE_KNOWLEDGE_GRAPH=true

### Recommendations (Priority Order)

1. **Fix OpenAI API Key** (CRITICAL):
   - Update OPENAI_API_KEY in .env file
   - Verify API key has embedding permissions
   - Consider alternative embedding models if OpenAI is not available

2. **Fix Implementation Bugs**:
   - Resolve FunctionTool callable issue in search tool
   - Fix metadata_filter parameter in RAG query implementation
   - Add error handling to surface embedding failures

3. **Enable Features**:
   - Set ENABLE_AGENTIC_RAG=true for code example extraction
   - Set USE_KNOWLEDGE_GRAPH=true for Neo4j-based features

4. **Improve Error Reporting**:
   - Tools should fail explicitly when embeddings fail
   - Add validation for critical dependencies
   - Surface infrastructure errors to MCP clients

## Overall Assessment

The MCP crawl4ai-docker server is currently **non-functional** for its primary use case (RAG-based search) due to the invalid OpenAI API key. While the scraping components work, without embeddings the system cannot perform vector search or RAG queries.

**Actual success rate: 0%** - No tool completed its full intended functionality.

The architecture appears sound, but the system needs:

1. Valid API credentials
2. Better error handling to surface infrastructure failures
3. Bug fixes for implementation issues
4. Feature flags enabled for full functionality
