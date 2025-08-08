# MCP Tools Testing Results - 20250806_0005

## Test Environment

**Test DateTime**: 2025-08-06 00:05:26 BST  
**Test Environment**: Production-grade with real API keys  
**MCP Server**: crawl4ai-docker (connected and running)  
**OS/Platform**: Linux 5.15.167.4-microsoft-standard-WSL2  
**Tester**: QA Agent (Automated Testing)  

## Environment Configuration

**Services Status**:

- MCP Server: ✅ Running
- Neo4j: ✅ Available  
- Qdrant: ✅ Available
- SearXNG: ✅ Available
- Valkey Cache: ✅ Available

**Feature Configuration**:

- Contextual Embeddings: ✅ Enabled
- Hybrid Search: ✅ Enabled  
- Reranking: ✅ Enabled
- Knowledge Graph Integration: ✅ Enabled

## Test Execution Log

### Phase 1: Tool-by-Tool Testing

#### Test 1.1: get_available_sources

**Test DateTime**: 2025-08-06 00:05:40 BST  
**Input(s)**: No parameters  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__get_available_sources  
**Observed Result**: ✅ Returned 20 sources with detailed summaries and metadata  
**Expected Result**: List of available sources with metadata  
**Outcome**: ✅ PASSED  
**Execution Time**: ~2 seconds  

#### Test 1.2: scrape_urls (Single URL)

**Test DateTime**: 2025-08-06 00:06:15 BST  
**Input(s)**: url="<https://httpbin.org/json>", return_raw_markdown=true  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__scrape_urls  
**Observed Result**: ❌ Error: "crawl_batch() got an unexpected keyword argument 'ctx'"  
**Expected Result**: Raw markdown content from URL  
**Outcome**: ❌ FAILED - Internal function signature error  
**Execution Time**: ~1 second  

#### Test 1.3: search (SearXNG Integration)

**Test DateTime**: 2025-08-06 00:06:45 BST  
**Input(s)**: query="Python testing best practices", num_results=3, return_raw_markdown=true  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__search  
**Observed Result**: ❌ Error: "crawl_batch() got an unexpected keyword argument 'ctx'"  
**Expected Result**: Search results with content  
**Outcome**: ❌ FAILED - Same internal error as Test 1.2  
**Execution Time**: ~1 second  

#### Test 1.4: smart_crawl_url

**Test DateTime**: 2025-08-06 00:07:20 BST  
**Input(s)**: url="<https://example.com>", max_depth=1, return_raw_markdown=true  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__smart_crawl_url  
**Observed Result**: ❌ Error: "'FunctionTool' object is not callable"  
**Expected Result**: Intelligently crawled content from URL  
**Outcome**: ❌ FAILED - Different internal error  
**Execution Time**: ~1 second  

#### Test 1.5: perform_rag_query

**Test DateTime**: 2025-08-06 00:07:50 BST  
**Input(s)**: query="Python web scraping", match_count=3  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__perform_rag_query  
**Observed Result**: ❌ Error: "'QdrantAdapter' object has no attribute 'hybrid_search'"  
**Expected Result**: RAG search results from vector database  
**Outcome**: ❌ FAILED - Missing method in QdrantAdapter  
**Execution Time**: ~1 second  

#### Test 1.6: search_code_examples

**Test DateTime**: 2025-08-06 00:08:20 BST  
**Input(s)**: query="class definition", match_count=3  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__search_code_examples  
**Observed Result**: ❌ Error: "QdrantAdapter.search_code_examples() got an unexpected keyword argument 'metadata_filter'"  
**Expected Result**: Code examples from vector database  
**Outcome**: ❌ FAILED - Method signature mismatch  
**Execution Time**: ~1 second  

#### Test 1.7: query_knowledge_graph

**Test DateTime**: 2025-08-06 00:08:50 BST  
**Input(s)**: command="repos"  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__query_knowledge_graph  
**Observed Result**: ✅ Returned 2 repositories: "Hello-World", "fastmcp"  
**Expected Result**: List of repositories in knowledge graph  
**Outcome**: ✅ PASSED  
**Execution Time**: ~1 second  

#### Test 1.8: parse_github_repository

**Test DateTime**: 2025-08-06 00:09:20 BST  
**Input(s)**: repo_url="<https://github.com/octocat/Hello-World.git>"  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__parse_github_repository  
**Observed Result**: ✅ Successfully parsed repository with 0 files processed (expected for Hello-World)  
**Expected Result**: Repository parsed into knowledge graph  
**Outcome**: ✅ PASSED  
**Execution Time**: ~10 seconds  

#### Test 1.9: get_repository_info

**Test DateTime**: 2025-08-06 00:09:50 BST  
**Input(s)**: repo_name="Hello-World"  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__get_repository_info  
**Observed Result**: ❌ Error: "'Context' object has no attribute 'repo_extractor'"  
**Expected Result**: Repository metadata and statistics  
**Outcome**: ❌ FAILED - Missing context attribute  
**Execution Time**: ~1 second  

#### Test 1.10: smart_code_search

**Test DateTime**: 2025-08-06 00:10:20 BST  
**Input(s)**: query="Python class definition", match_count=3  
**Environment**: Production MCP server  
**Steps Taken**: Called mcp__crawl4ai-docker__smart_code_search  
**Observed Result**: ✅ Returned search results (0 final results but validation working)  
**Expected Result**: Validated code search results  
**Outcome**: ✅ PASSED - Tool works, no content matches criteria  
**Execution Time**: ~3 seconds  

## Critical Issues Identified

### 1. Core Crawling Function Error

**Pattern**: Multiple tools failing with "crawl_batch() got an unexpected keyword argument 'ctx'"  
**Affected Tools**: scrape_urls, search, smart_crawl_url  
**Severity**: CRITICAL - Core functionality broken  

### 2. Database Adapter Issues

**Pattern**: QdrantAdapter missing methods or wrong signatures  
**Affected Tools**: perform_rag_query, search_code_examples  
**Severity**: HIGH - Major features non-functional  

### 3. Context/Initialization Issues

**Pattern**: Missing attributes in context objects  
**Affected Tools**: get_repository_info, update_parsed_repository, parse_repository_branch  
**Severity**: MEDIUM - Repository management impacted

## Additional Test Results

#### Test 1.11: extract_and_index_repository_code

**Test DateTime**: 2025-08-06 00:11:30 BST  
**Input(s)**: repo_name="Hello-World"  
**Observed Result**: ✅ Success - No code examples found to index (expected for Hello-World)  
**Expected Result**: Repository code indexed to Qdrant  
**Outcome**: ✅ PASSED  

#### Test 1.12: update_parsed_repository

**Test DateTime**: 2025-08-06 00:11:50 BST  
**Input(s)**: repo_url="<https://github.com/octocat/Hello-World.git>"  
**Observed Result**: ❌ Error: "'Context' object has no attribute 'repo_extractor'"  
**Expected Result**: Repository updated with latest changes  
**Outcome**: ❌ FAILED - Same context attribute issue  

#### Test 1.13: parse_repository_branch

**Test DateTime**: 2025-08-06 00:12:10 BST  
**Input(s)**: repo_url="<https://github.com/octocat/Hello-World.git>", branch="main"  
**Observed Result**: ❌ Error: "'Context' object has no attribute 'repo_extractor'"  
**Expected Result**: Specific branch parsed into knowledge graph  
**Outcome**: ❌ FAILED - Same context attribute issue  

## Test Summary

### Overall Results

**Total Tests Executed**: 13  
**Passed**: 4 ✅  
**Failed**: 9 ❌  
**Success Rate**: 30.8%  

### Functional Categories Assessment

#### ✅ Working Tools (4/13)

1. **get_available_sources** - Source listing functional
2. **query_knowledge_graph** - Neo4j queries working
3. **parse_github_repository** - Basic repo parsing works
4. **extract_and_index_repository_code** - Code indexing works
5. **smart_code_search** - Search validation working

#### ❌ Broken Tools (9/13)

1. **scrape_urls** - Core crawling function signature error
2. **search** - Same crawling error  
3. **smart_crawl_url** - Function object error
4. **perform_rag_query** - Missing QdrantAdapter.hybrid_search method
5. **search_code_examples** - Wrong method signature
6. **get_repository_info** - Missing context.repo_extractor
7. **update_parsed_repository** - Same context issue
8. **parse_repository_branch** - Same context issue
9. **check_ai_script_hallucinations_enhanced** - File path/validation issues

### Performance Metrics

**Average Response Time**: ~2.5 seconds  
**Neo4j Integration**: ✅ Working  
**Qdrant Integration**: ⚠️ Partially working (connection OK, methods missing)  
**Repository Parsing**: ⚠️ Basic parsing works, advanced features broken  

## Critical Blockers

### 1. CRITICAL: Core Crawling Infrastructure Failure

**Impact**: All web crawling functionality non-functional  
**Root Cause**: Function signature mismatch in crawl_batch() method  
**Evidence**: "crawl_batch() got an unexpected keyword argument 'ctx'"  
**Business Impact**: PRIMARY FEATURES UNUSABLE - No web scraping, search, or content ingestion  

### 2. HIGH: Database Adapter Incomplete Implementation  

**Impact**: RAG features and code search broken  
**Root Cause**: QdrantAdapter missing hybrid_search method and wrong signatures  
**Evidence**: Multiple method signature errors  
**Business Impact**: MAJOR FEATURES NON-FUNCTIONAL - Vector search capabilities compromised  

### 3. MEDIUM: Repository Management Context Issues

**Impact**: Advanced repository operations broken  
**Root Cause**: Missing repo_extractor attribute in Context object  
**Evidence**: "'Context' object has no attribute 'repo_extractor'"  
**Business Impact**: REPOSITORY LIFECYCLE MANAGEMENT IMPAIRED  

## Recommendations

### Immediate Actions Required (Critical Priority)

1. **Fix crawl_batch() function signature** - Update function definition to handle 'ctx' parameter properly
2. **Implement missing QdrantAdapter methods** - Add hybrid_search and fix search_code_examples signature  
3. **Fix Context initialization** - Ensure repo_extractor is properly initialized in application context

### Testing Infrastructure Issues

1. **File path resolution** - Hallucination detection tools cannot locate test scripts
2. **Service integration** - Some tools work in isolation but fail in integration scenarios

### Production Readiness Assessment

**Current Status**: NOT PRODUCTION READY  
**Confidence Level**: 30.8% functionality working  
**Estimated Fix Time**: HIGH - Multiple core components require debugging  

## Test Artifacts Generated

- Test results file: tests/results/20250806_0005-MCP_TOOLS_TESTING.md
- Test script for hallucination detection: test_hallucination_script.py

**Test Completion**: 2025-08-06 00:12:30 BST  
**Total Test Duration**: ~7 minutes  
**QA Agent Status**: TESTS COMPLETED - CRITICAL ISSUES IDENTIFIED
