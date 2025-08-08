# MCP Tools Production-Grade Testing Results - 2025-08-05

**Test DateTime**: 2025-08-05T23:56:12Z
**Environment**: Production-grade (docker-compose.dev.yml)  
**Testing Tool**: Claude Code QA Agent
**Executed by**: Automated QA Agent following systematic test plan

## Production Configuration Status

- OPENAI_API_KEY: [TO BE VERIFIED]
- USE_CONTEXTUAL_EMBEDDINGS: [TO BE VERIFIED]
- USE_HYBRID_SEARCH: [TO BE VERIFIED]
- USE_AGENTIC_RAG: [TO BE VERIFIED]
- USE_RERANKING: [TO BE VERIFIED]
- USE_KNOWLEDGE_GRAPH: [TO BE VERIFIED]
- VECTOR_DATABASE: [TO BE VERIFIED]

## Test Execution Log

### Prerequisites Check

**Test DateTime**: 2025-08-05T23:56:12Z
**Status**: ✅ PASSED

#### Service Health Check Results

- **mcp-crawl4ai-dev**: ✅ UP (healthy) on ports 5678, 8051
- **qdrant-dev**: ✅ UP (healthy) on ports 6333-6334, version 1.15.1
- **neo4j-dev**: ✅ UP (healthy) on ports 7474, 7687, HTTP 200 OK
- **searxng-dev**: ✅ UP (healthy) on port 8080, internal health check OK
- **valkey-dev**: ✅ UP (healthy) on port 6379
- **mailhog-dev**: ✅ UP on ports 1025, 8025

**Artifacts**: All services healthy and responding
**Timestamp**: 2025-08-05T23:56:35Z

---

## Phase 1: Tool-by-Tool Testing

### Test 1.1: get_available_sources

**Test DateTime**: 2025-08-05T23:56:51Z
**Input(s)**: mcp__crawl4ai-docker__get_available_sources (no parameters)
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation
**Observed Result**:

- success: true
- sources: array with 20 entries
- Each source contains: source_id, summary, total_chunks (null), first_crawled (null), last_crawled (null)
- count: 20
- message: "Found 20 unique sources."
**Expected Result**: success: true, sources array (can be empty), each source with proper structure, count number
**Outcome**: ✅ PASSED
**Artifacts**: 20 sources found including example.com, docs.python.org, realpython.com, and others
**Timestamp**: 2025-08-05T23:56:57Z
**Duration**: 6 seconds

### Test 1.2: scrape_urls (Single URL)

**Test DateTime**: 2025-08-05T23:57:10Z
**Input(s)**: mcp__crawl4ai-docker__scrape_urls with url: "<https://example.com>"
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with single URL
**Observed Result**:

- success: true
- total_urls: 1
- results[0]: url: "<https://example.com>", success: false, error: "smart_chunk_markdown() got an unexpected keyword argument 'max_chunk_size'", chunks_stored: 0
**Expected Result**: chunks_stored > 0, no embedding errors, source added to database
**Outcome**: ❌ FAILED
**Artifacts**: Docker logs show "Failed to store <https://example.com>: smart_chunk_markdown() got an unexpected keyword argument 'max_chunk_size'"
**Timestamp**: 2025-08-05T23:57:15Z
**Duration**: 5 seconds

### Test 2.3: scrape_urls (Multiple URLs)

**Test DateTime**: 2025-08-05T23:57:31Z
**Input(s)**: mcp__crawl4ai-docker__scrape_urls with url: ["https://example.com", "https://httpbin.org/html", "https://www.iana.org/help/example-domains"], max_concurrent: 3
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with array of URLs and concurrency parameter
**Observed Result**:

- success: true
- total_urls: 1
- results: [] (empty array)
**Expected Result**: All URLs processed, parallel processing utilized, no timeouts or failures
**Outcome**: ❌ FAILED
**Artifacts**: Docker logs show "Completed scrape_urls in 0.02s", but results array is empty despite total_urls=1
**Timestamp**: 2025-08-05T23:57:39Z
**Duration**: 8 seconds

### Test 2.4: search

**Test DateTime**: 2025-08-05T23:57:51Z
**Input(s)**: mcp__crawl4ai-docker__search with query: "python programming tutorial", num_results: 3
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with search query and result limit
**Observed Result**:

- success: true
- query: "python programming tutorial"
- total_results: 3
- results: 3 entries with titles, URLs, snippets, but all have stored: false, chunks: 0
- URLs found: W3Schools Python, Python docs tutorial, LearnPython.org
**Expected Result**: Search results from SearXNG, all results scraped successfully, content embedded and stored
**Outcome**: ❌ FAILED
**Artifacts**: Docker logs show same error for all 3 URLs: "smart_chunk_markdown() got an unexpected keyword argument 'max_chunk_size'"
**Timestamp**: 2025-08-05T23:58:01Z
**Duration**: 10 seconds

### Test 2.5: smart_crawl_url (Regular Website - Small)

**Test DateTime**: 2025-08-05T23:58:14Z
**Input(s)**: mcp__crawl4ai-docker__smart_crawl_url with url: "<https://example.com>", max_depth: 1, chunk_size: 2000
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with URL and crawl parameters
**Observed Result**: Error calling tool 'smart_crawl_url': Smart crawl failed: 'FunctionTool' object is not callable
**Expected Result**: Base page crawled, any linked pages within depth 1, efficient chunking
**Outcome**: ❌ FAILED
**Artifacts**: Docker logs show "'FunctionTool' object failed"
**Timestamp**: 2025-08-05T23:58:20Z
**Duration**: 6 seconds

### Test 2.7: perform_rag_query

**Test DateTime**: 2025-08-05T23:58:35Z
**Input(s)**: mcp__crawl4ai-docker__perform_rag_query with query: "what is python", match_count: 5
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with RAG query
**Observed Result**:

- success: false
- query: "what is python"
- error: "attempted relative import beyond top-level package"
**Expected Result**: Relevant chunks returned, similarity scores included, source attribution correct
**Outcome**: ❌ FAILED
**Artifacts**: Docker logs show "Error in perform_rag_query: attempted relative import beyond top-level package"
**Timestamp**: 2025-08-05T23:58:39Z
**Duration**: 4 seconds

### Test 2.9: search_code_examples

**Test DateTime**: 2025-08-05T23:58:59Z
**Input(s)**: mcp__crawl4ai-docker__search_code_examples with query: "print function", match_count: 5
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with code search query
**Observed Result**:

- success: false
- query: "print function"
- error: "attempted relative import beyond top-level package"
**Expected Result**: Code snippets returned, language detection accurate, context preserved
**Outcome**: ❌ FAILED
**Artifacts**: Same import error as RAG query test
**Timestamp**: 2025-08-05T23:59:02Z
**Duration**: 3 seconds

### Test 2.10: parse_github_repository

**Test DateTime**: 2025-08-05T23:59:07Z
**Input(s)**: mcp__crawl4ai-docker__parse_github_repository with repo_url: "<https://github.com/octocat/Hello-World>"
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with GitHub repository URL
**Observed Result**:

- success: true
- repo_url: "<https://github.com/octocat/Hello-World>"
- repository_name: "Hello-World"
- statistics: files_processed: 0, classes_created: 0, methods_created: 0, functions_created: 0
- message: "Successfully parsed repository 'Hello-World' into the knowledge graph"
- next_steps: provided for further exploration
**Expected Result**: Repository cloned, code structure analyzed, knowledge graph populated
**Outcome**: ⚠️ UNEXPECTED (Success but no files processed)
**Artifacts**: Repository parsed but shows 0 files processed - may be an empty repository
**Timestamp**: 2025-08-05T23:59:16Z
**Duration**: 9 seconds

### Test 2.17: query_knowledge_graph

**Test DateTime**: 2025-08-05T23:59:27Z
**Input(s)**: mcp__crawl4ai-docker__query_knowledge_graph with command: "repos"
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with knowledge graph query
**Observed Result**:

- success: true
- command: "repos"
- data: repositories: ["Hello-World", "fastmcp"]
- metadata: total_results: 2, limited: false
**Expected Result**: List of parsed repositories, graph data returned
**Outcome**: ✅ PASSED
**Artifacts**: Found 2 repositories in knowledge graph
**Timestamp**: 2025-08-05T23:59:34Z
**Duration**: 7 seconds

### Test 2.16: check_ai_script_hallucinations_enhanced

**Test DateTime**: 2025-08-05T23:59:46Z
**Input(s)**: mcp__crawl4ai-docker__check_ai_script_hallucinations_enhanced with script_path: "/home/krashnicov/crawl4aimcp/test_hallucination_script.py", include_code_suggestions: true, detailed_analysis: true
**Environment**: Docker compose dev environment, all services healthy
**Steps Taken**: Direct MCP tool invocation with test script path
**Observed Result**: Error calling tool: Enhanced hallucination check failed: {'valid': False, 'error': 'Script not found: /home/krashnicov/crawl4aimcp/test_hallucination_script.py'}
**Expected Result**: Comprehensive hallucination report, code suggestions from real repositories
**Outcome**: ❌ FAILED
**Artifacts**: Script not found error - file creation failed due to Write tool restriction
**Timestamp**: 2025-08-05T23:59:54Z
**Duration**: 8 seconds

---

## Test Summary

**Total Test Duration**: 2025-08-05T23:56:12Z to 2025-08-06T00:00:05Z (≈4 minutes)
**Tests Executed**: 9 out of planned test suite
**Test Completion Status**: INCOMPLETE - Multiple critical failures prevented comprehensive execution

### Test Results Matrix

| Tool | Test Case | Status | Duration | Critical Issues |
|------|-----------|--------|----------|----------------|
| get_available_sources | List sources | ✅ PASSED | 6s | None |
| scrape_urls | Single URL | ❌ FAILED | 5s | smart_chunk_markdown() argument error |
| scrape_urls | Multiple URLs | ❌ FAILED | 8s | Empty results array |
| search | Search and scrape | ❌ FAILED | 10s | Same chunking error on all URLs |
| smart_crawl_url | Regular website | ❌ FAILED | 6s | FunctionTool object error |
| perform_rag_query | Basic query | ❌ FAILED | 4s | Import error |
| search_code_examples | Code search | ❌ FAILED | 3s | Same import error |
| parse_github_repository | Basic parsing | ⚠️ UNEXPECTED | 9s | Success but 0 files processed |
| query_knowledge_graph | Graph queries | ✅ PASSED | 7s | None |
| check_ai_script_hallucinations_enhanced | Enhanced detection | ❌ FAILED | 8s | Script file not found |

### Critical System Failures Identified

#### 1. Text Processing Module Failure

**Error**: `smart_chunk_markdown() got an unexpected keyword argument 'max_chunk_size'`
**Impact**: ALL content scraping operations fail
**Affected Tools**: scrape_urls, search (all content ingestion)
**Severity**: CRITICAL - Core functionality broken

#### 2. Database/Import System Failure  

**Error**: `attempted relative import beyond top-level package`
**Impact**: ALL RAG and code search operations fail
**Affected Tools**: perform_rag_query, search_code_examples
**Severity**: CRITICAL - No content retrieval possible

#### 3. Smart Crawling System Failure

**Error**: `'FunctionTool' object is not callable`  
**Impact**: Advanced crawling features unusable
**Affected Tools**: smart_crawl_url
**Severity**: HIGH - Advanced features broken

### Operational Status Assessment

#### ✅ Working Systems

- **Service Infrastructure**: All Docker containers healthy and responsive
- **MCP Protocol**: Tool invocation and response handling functional
- **Basic Database Operations**: Source listing works correctly
- **Knowledge Graph**: Repository parsing and querying functional
- **Authentication**: No auth errors observed

#### ❌ Broken Systems

- **Content Ingestion**: Cannot scrape or store any web content
- **RAG Pipeline**: Cannot query stored content
- **Code Search**: Cannot search code examples
- **Smart Crawling**: Advanced crawling features non-functional
- **Hallucination Detection**: Cannot analyze scripts (file I/O limitation)

### System State Analysis

The MCP server infrastructure is healthy but core content processing functionality is completely broken. The system appears to have:

1. **Code-level regressions** in text processing functions
2. **Import/module structure issues** affecting database operations  
3. **Function composition problems** in crawling tools
4. **Working knowledge graph operations** (Neo4j integration functional)

### Immediate Escalation Required

**Severity**: CRITICAL - Production system non-functional
**Priority**: P0 - Immediate attention required
**Business Impact**: Complete failure of core content processing capabilities

The system cannot fulfill its primary purpose of web content scraping, processing, and retrieval. Only basic administrative and knowledge graph functions remain operational.

### Test Environment Details

**Final Timestamp**: 2025-08-06T00:00:05Z
**Test Agent**: QA Agent following systematic validation protocol
**Test Adherence**: Strict observational discipline maintained
**Anomalies Flagged**: 3 critical system failures requiring immediate triage
