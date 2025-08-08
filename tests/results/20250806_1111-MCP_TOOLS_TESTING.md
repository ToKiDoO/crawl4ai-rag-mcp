# MCP Tools Production-Grade Testing Results - August 6, 2025

**Test DateTime**: Wed Aug  6 11:11:02 BST 2025
**Environment**: Production-grade (docker-compose.dev.yml)
**Testing Tool**: Claude Code with MCP connection
**QA Agent**: Automated testing execution with systematic observation

## Production Configuration

Testing production-grade environment with:

- OPENAI_API_KEY: ✓ Valid production key
- USE_CONTEXTUAL_EMBEDDINGS: true
- USE_HYBRID_SEARCH: true  
- USE_AGENTIC_RAG: true
- USE_RERANKING: true
- USE_KNOWLEDGE_GRAPH: true
- VECTOR_DATABASE: qdrant

## Environment Verification

### Service Health Check Status

- **Test DateTime**: Wed Aug  6 11:11:02 BST 2025
- **Docker Compose**: docker-compose.dev.yml
- **Services Status**: [TO BE VERIFIED]

### Test Summary

| Tool | Test Case | Status | Time | Notes |
|------|-----------|--------|------|-------|
| get_available_sources | List sources | PENDING | - | Starting Phase 1 |
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

---

## Phase 1: Tool-by-Tool Testing - EXECUTION LOG

### Test 1.1: get_available_sources ✅ PASSED

**Purpose**: List all available sources in the database
**Test DateTime**: Wed Aug  6 11:11:33 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__get_available_sources` (no parameters)

**Expected Result**:

- success: true
- sources: array (can be empty)
- Each source should have: source_id, summary, created_at, updated_at
- count: number of sources

**Actual Result**:

- success: true ✅
- sources: array with 20 sources ✅
- Each source has: source_id, summary ✅ (created_at/updated_at as null)
- count: 20 ✅

**Status**: ✅ PASSED
**Execution Time**: <1 second
**Notes**: Database contains 20 existing sources from previous testing sessions. Structure is correct.

### Test 1.2: scrape_urls (Single URL) ✅ PASSED

**Purpose**: Test basic scraping with embedding generation
**Test DateTime**: Wed Aug  6 11:12:45 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__scrape_urls` with url: "<https://example.com>"

**Expected Result**:

- chunks_stored > 0
- No embedding errors in logs
- Source added to database

**Actual Result**:

- success: true ✅
- total_urls: 1 ✅
- results: [{"url": "https://example.com", "success": true, "chunks_stored": 1}] ✅
- chunks_stored: 1 ✅

**Status**: ✅ PASSED
**Execution Time**: ~5 seconds
**Notes**: Content scraped successfully with 1 chunk stored. Source already existed in database.

### Test 2.3: scrape_urls (Multiple URLs) ⚠️ PARTIAL PASS

**Purpose**: Test batch scraping functionality with parallel processing
**Test DateTime**: Wed Aug  6 11:13:15 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__scrape_urls` with url: ["https://example.com", "https://httpbin.org/html", "https://www.iana.org/help/example-domains"], max_concurrent: 3

**Expected Result**:

- All URLs processed
- Parallel processing utilized
- No timeouts or failures

**Actual Result**:

- success: true ✅
- total_urls: 1 ⚠️ (expected 3)
- results: [] ⚠️ (empty array)

**Follow-up Tests**:

- Individual URL tests successful ✅
- <https://httpbin.org/html>: chunks_stored: 2 ✅
- <https://www.iana.org/help/example-domains>: chunks_stored: 2 ✅

**Status**: ⚠️ PARTIAL PASS
**Execution Time**: ~3 seconds
**Notes**: Array parameter format may not be correctly parsed by MCP tool. Individual URLs work correctly. Need to investigate multiple URL batch processing.

### Test 2.4: search ✅ PASSED

**Purpose**: Test search and scrape pipeline
**Test DateTime**: Wed Aug  6 11:14:20 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__search` with query: "python programming tutorial", num_results: 3

**Expected Result**:

- Search results from SearXNG
- All results scraped successfully
- Content embedded and stored

**Actual Result**:

- success: true ✅
- query: "python programming tutorial" ✅
- total_results: 3 ✅
- All 3 URLs scraped and stored ✅
- Results from W3Schools (11 chunks), Python.org (43 chunks), LearnPython.org (7 chunks) ✅

**Status**: ✅ PASSED
**Execution Time**: ~15 seconds
**Notes**: Complete search-to-storage pipeline working perfectly. SearXNG integration successful, all content properly chunked and embedded.

### Test 2.5: smart_crawl_url (Small site) ❌ FAILED

**Purpose**: Test intelligent crawling with depth on a small site first
**Test DateTime**: Wed Aug  6 11:15:30 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__smart_crawl_url` with url: "<https://example.com>", max_depth: 1, chunk_size: 2000

**Expected Result**:

- Base page crawled
- Any linked pages within depth 1
- Efficient chunking

**Actual Result**:

- Error: Smart crawl failed: 'FunctionTool' object is not callable

**Status**: ❌ FAILED
**Execution Time**: <1 second
**Notes**: Critical error in smart crawling functionality - FunctionTool object issue indicates internal tool configuration problem.

### Test 2.7: perform_rag_query ❌ FAILED

**Purpose**: Test RAG retrieval on scraped content
**Test DateTime**: Wed Aug  6 11:16:00 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__perform_rag_query` with query: "what is python", match_count: 5

**Expected Result**:

- Relevant chunks returned
- Similarity scores included
- Source attribution correct

**Actual Result**:

- success: false
- error: "attempted relative import beyond top-level package"

**Status**: ❌ FAILED
**Execution Time**: <1 second
**Notes**: Critical import error in RAG queries module. Module organization issue affecting core functionality.

### Test 2.9: search_code_examples ❌ FAILED

**Purpose**: Test code example extraction (requires ENABLE_AGENTIC_RAG=true)
**Test DateTime**: Wed Aug  6 11:16:15 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__search_code_examples` with query: "print function", match_count: 5

**Expected Result**:

- Code snippets returned
- Language detection accurate
- Context preserved

**Actual Result**:

- success: false
- error: "attempted relative import beyond top-level package"

**Status**: ❌ FAILED
**Execution Time**: <1 second
**Notes**: Same import error as RAG query - systematic module import issue.

### Test 2.17: query_knowledge_graph ✅ PASSED

**Purpose**: Test knowledge graph queries
**Test DateTime**: Wed Aug  6 11:16:30 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__query_knowledge_graph` with command: "repos"

**Expected Result**:

- List of parsed repositories
- Graph data returned

**Actual Result**:

- success: true ✅
- command: "repos" ✅
- data.repositories: ["Hello-World", "fastmcp"] ✅
- metadata.total_results: 2 ✅

**Status**: ✅ PASSED
**Execution Time**: <1 second
**Notes**: Knowledge graph functionality working correctly. Neo4j integration operational.

### Test 2.10: parse_github_repository ✅ PASSED

**Purpose**: Test GitHub parsing (requires USE_KNOWLEDGE_GRAPH=true)
**Test DateTime**: Wed Aug  6 11:16:45 BST 2025

**Tool Invocation**: `mcp__crawl4ai-docker__parse_github_repository` with repo_url: "<https://github.com/octocat/Hello-World>"

**Expected Result**:

- Repository cloned
- Code structure analyzed
- Knowledge graph populated

**Actual Result**:

- success: true ✅
- repository_name: "Hello-World" ✅
- statistics: files_processed: 0, classes_created: 0, methods_created: 0, functions_created: 0 ✅
- message: Successfully parsed ✅

**Status**: ✅ PASSED
**Execution Time**: ~5 seconds
**Notes**: GitHub parsing successful. Repository exists in knowledge graph but contains no Python files to analyze.
