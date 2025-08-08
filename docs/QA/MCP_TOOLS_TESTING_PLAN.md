# MCP crawl4ai-docker Tools Testing Plan

## Overview

This document provides a comprehensive testing plan for validating all MCP tools in the crawl4ai-docker server in a **production-grade environment** with proper API keys and all features enabled.

**Important**: While we use `make dev-bg` to run the services, this is a production-grade testing environment:

- Real OpenAI API key with full access
- All RAG features enabled (contextual embeddings, hybrid search, reranking, agentic RAG)
- Knowledge graph (Neo4j) fully operational
- Production-ready vector database (Qdrant)
- Full SearXNG search capabilities
- The only "dev" aspects are debug logging and mailhog for email capture

These tests will be executed whilst being connected to the MCP server, which will already be started by the user.

## Test Execution Process

### 1. Create Test Results File

Before starting tests, create a new results file:

```bash
mkdir -p tests/results
touch tests/results/$(date +%Y%m%d_%H%M)-MCP_TOOLS_TESTING.md
```

### 2. Document Environment

Start your test results file with:

- Date and time of test
- Docker compose file used (e.g., docker-compose.dev.yml)
- Environment variables verified (especially OPENAI_API_KEY)
- Service health check results

### 3. Execute Tests

Follow the test sequence below, documenting each result in your test file.

## Prerequisites

### MCP Connection Setup

**For Claude Code Testing**: Ensure the MCP server is connected via the `/mcp` command if needed. The server should appear as `crawl4ai-docker` and all tools will be accessed with the `mcp__crawl4ai-docker__` prefix.

### Neo4j-Qdrant Integration Requirements

**Configuration Requirements**:

- Neo4j must be running and accessible on ports 7474 (browser) and 7687 (bolt)
- Qdrant must have `code_examples` collection initialized
- Integration features enabled via environment variables:
  - `USE_KNOWLEDGE_GRAPH=true`
  - `ENABLE_AGENTIC_RAG=true` (for code extraction)
  - `USE_RERANKING=true` (for validation scoring)

### Service Health Checks

Before testing, verify all services are running:

```bash
# Check Docker services
make ps  # Shows status across all environments

# Expected services:
# - mcp-crawl4ai-dev: healthy on ports 5678, 8051
# - qdrant-dev: healthy on ports 6333-6334
# - neo4j-dev: healthy on ports 7474, 7687
# - searxng-dev: healthy on port 8080 (internal only)
# - valkey-dev: healthy on port 6379
# - mailhog-dev: running on ports 1025, 8025
```

## Testing Sequence

**IMPORTANT**: These tests assume you, Claude Code, are already connected to the MCP server. All tools should be called using the `mcp__crawl4ai-docker__` prefix.

After each test, monitor logs in a separate terminal:

```bash
make dev-logs-grep
```

### Test Result Documentation

For each test, document in your results file:

- Test ID and name
- Exact tool invocation used
- Expected result (from this plan)
- Actual result
- Status: ✅ PASSED or ❌ FAILED
- If failed: exact error message and relevant logs
- Execution time

### Phase 1: Tool-by-Tool Testing

#### Test 1.1: get_available_sources

**Purpose**: List all available sources in the database

**Claude Code Execution**:

```
Use tool: mcp__crawl4ai-docker__get_available_sources
Parameters: (none)
```

**Expected Result**:

- success: true
- sources: array (can be empty)
- Each source should have: source_id, summary, created_at, updated_at
- count: number of sources

**Success Criteria**:

- Tool executes without errors
- Valid JSON response with proper structure
- Check logs: `make dev-logs-grep PATTERN="get_available_sources"`

**IMPORTANT**: All tests require MATERIAL PASSES - the tool must return actual, relevant results as expected, not just execute without errors. Empty results when content is expected = FAILED test.

#### Test 1.2: scrape_urls (Single URL)

**Purpose**: Test basic scraping with embedding generation

```yaml
Tool: mcp__crawl4ai-docker__scrape_urls
Parameters:
  url: "https://example.com"
Expected Result:
  - chunks_stored > 0
  - No embedding errors in logs
  - Source added to database
Success Criteria:
  - Content scraped successfully
  - Embeddings generated (check logs)
  - Can query content later via RAG
Post-Test Validation:
  - Run get_available_sources to confirm new source
```

#### Test 2.3: scrape_urls (Multiple URLs)

**Purpose**: Test batch scraping functionality

```yaml
Tool: mcp__crawl4ai-docker__scrape_urls
Parameters:
  url: ["https://example.com", "https://httpbin.org/html", "https://www.iana.org/help/example-domains"]
  max_concurrent: 3
Expected Result:
  - All URLs processed
  - Parallel processing utilized
  - No timeouts or failures
Success Criteria:
  - All URLs scraped
  - Embeddings for all content
  - Efficient parallel execution
```

#### Test 2.4: search

**Purpose**: Test search and scrape pipeline

```yaml
Tool: mcp__crawl4ai-docker__search
Parameters:
  query: "latest docker documentation"
  num_results: 3
Expected Result:
  - Search results from SearXNG
  - All results scraped successfully
  - Content embedded and stored
Success Criteria:
  - No FunctionTool errors
  - All URLs processed
  - Content searchable via RAG
```

#### Test 2.5: smart_crawl_url (Regular Website - Small)

**Purpose**: Test intelligent crawling with depth on a small site first

```yaml
Tool: mcp__crawl4ai-docker__smart_crawl_url
Parameters:
  url: "https://example.com"
  max_depth: 1
  chunk_size: 2000
Expected Result:
  - Base page crawled
  - Any linked pages within depth 1
  - Efficient chunking
Success Criteria:
  - Completes successfully
  - Returns crawl summary
  - All content embedded
```

#### Test 2.5b: smart_crawl_url (Regular Website - Large)

**Purpose**: Test intelligent crawling with depth on larger site

```yaml
Tool: mcp__crawl4ai-docker__smart_crawl_url
Parameters:
  url: "https://docs.python.org/3/tutorial/index.html"
  max_depth: 2
  chunk_size: 2000
Expected Result:
  - Multiple pages crawled
  - Respects max_depth limit
  - Efficient chunking
Success Criteria:
  - Crawls index + linked pages
  - Stays within depth limit
  - All content embedded
Note: Only run if small test passes
```

#### Test 2.6: smart_crawl_url (Sitemap)

**Purpose**: Test sitemap parsing

```yaml
Tool: mcp__crawl4ai-docker__smart_crawl_url
Parameters:
  url: "https://example.com/sitemap.xml"  # Replace with actual sitemap
Expected Result:
  - Detects sitemap format
  - Extracts all URLs
  - Processes URLs in parallel
Success Criteria:
  - Sitemap parsed correctly
  - All URLs from sitemap processed
```

#### Test 2.7: perform_rag_query

**Purpose**: Test RAG retrieval on scraped content

```yaml
Tool: mcp__crawl4ai-docker__perform_rag_query
Parameters:
  query: "what is python"
  match_count: 5
Expected Result:
  - Relevant chunks returned
  - Similarity scores included
  - Source attribution correct
Success Criteria:
  - No metadata_filter errors
  - Results are relevant
  - Reranking applied (if enabled)
```

#### Test 2.8: perform_rag_query (With Source Filter)

**Purpose**: Test filtered RAG queries

```yaml
Tool: mcp__crawl4ai-docker__perform_rag_query
Parameters:
  query: "example domain"
  source: "example.com"
  match_count: 3
Expected Result:
  - Only results from specified source
  - Accurate filtering
Success Criteria:
  - Source filter works correctly
  - No irrelevant results
```

#### Test 2.9: search_code_examples

**Purpose**: Test code example extraction (requires ENABLE_AGENTIC_RAG=true)

```yaml
Tool: mcp__crawl4ai-docker__search_code_examples
Parameters:
  query: "print function"
  match_count: 5
Expected Result:
  - Code snippets returned
  - Language detection accurate
  - Context preserved
Success Criteria:
  - Feature enabled and working
  - Relevant code examples found
```

#### Test 2.10: parse_github_repository

**Purpose**: Test GitHub parsing (requires USE_KNOWLEDGE_GRAPH=true)

```yaml
Tool: mcp__crawl4ai-docker__parse_github_repository
Parameters:
  repo_url: "https://github.com/octocat/Hello-World"
Expected Result:
  - Repository cloned
  - Code structure analyzed
  - Knowledge graph populated
Success Criteria:
  - Neo4j contains repo data
  - Classes/methods extracted
  - Relationships mapped
```

#### Test 2.11: parse_repository_branch

**Purpose**: Test parsing specific branches of GitHub repositories

```yaml
Tool: mcp__crawl4ai-docker__parse_repository_branch
Parameters:
  repo_url: "https://github.com/agent0ai/agent-zero"
  branch: "development"
Expected Result:
  - Repository cloned from specific branch
  - Branch metadata stored
  - Code structure analyzed
  - Git metadata extracted (commits, contributors)
Success Criteria:
  - Neo4j contains repo data from specified branch
  - Branch information stored correctly
  - Git metadata (branches, commits) populated
  - Statistics include branch-specific info
Post-Test Validation:
  - Query knowledge graph to verify branch data
```

#### Test 2.12: get_repository_info

**Purpose**: Test comprehensive repository metadata retrieval

```yaml
Tool: mcp__crawl4ai-docker__get_repository_info
Parameters:
  repo_name: "agent-zero"
Expected Result:
  - Repository metadata returned
  - Branches list included
  - Recent commits included
  - Code statistics (classes, methods, functions)
  - Git metadata (contributors, size, file count)
Success Criteria:
  - All metadata fields populated
  - Branches and commits retrieved
  - Statistics accurate
  - JSON response well-formatted
Prerequisites:
  - Repository must be parsed first (Test 2.10)
```

#### Test 2.13: update_parsed_repository

**Purpose**: Test repository update functionality

```yaml
Tool: mcp__crawl4ai-docker__update_parsed_repository
Parameters:
  repo_url: "https://github.com/agent0ai/agent-zerod"
Expected Result:
  - Repository updated with latest changes
  - Changed files identified (if any)
  - Metadata refreshed
Success Criteria:
  - Update completes without errors
  - Repository data refreshed in Neo4j
  - Response indicates success
Prerequisites:
  - Repository must be parsed first (Test 2.10)
Note: Currently performs full re-parse (incremental updates planned)
```

#### Test 2.14: extract_and_index_repository_code

**Purpose**: Test Neo4j to Qdrant bridge functionality

```yaml
Tool: mcp__crawl4ai-docker__extract_and_index_repository_code
Parameters:
  repo_name: "agent-zero"
Expected Result:
  - Code examples extracted from Neo4j
  - Embeddings generated for each example
  - Examples indexed in Qdrant with metadata
  - Reports number of examples processed
Success Criteria:
  - Successful extraction and indexing
  - No errors in embedding generation
  - Response includes count of indexed examples
Prerequisites:
  - Repository must be parsed first (Test 2.10)
Post-Test Validation:
  - Use search_code_examples to verify indexed content
```

#### Test 2.15: smart_code_search

**Purpose**: Test intelligent code search with validation

```yaml
Tool: mcp__crawl4ai-docker__smart_code_search
Parameters:
  query: "print function"
  validation_mode: "balanced"  # Options: "fast", "balanced", "thorough"
  min_confidence: 0.6
  match_count: 5
Expected Result:
  - Validated code results with confidence scores
  - Each result includes validation status
  - Results filtered by min_confidence
Success Criteria:
  - Returns relevant code examples
  - Confidence scores between 0 and 1
  - Validation status included
Prerequisites:
  - Code must be indexed (Test 2.14)

Additional Test Scenarios:
1. Fast mode (no validation):
   validation_mode: "fast"
   Expected: Quick results without Neo4j validation
   
2. Thorough mode (full validation):
   validation_mode: "thorough" 
   Expected: Complete validation with higher confidence

3. Source filtering:
   source_filter: "Hello-World"
   Expected: Only results from specified repository
```

#### Test 2.16: check_ai_script_hallucinations_enhanced

**Purpose**: Test enhanced hallucination detection with dual database validation

```yaml
Preparation: Create test script with known hallucinations
Tool: mcp__crawl4ai-docker__check_ai_script_hallucinations_enhanced
Parameters:
  script_path: "/home/krashnicov/crawl4aimcp/test_hallucination_script.py"
  include_code_suggestions: true
  detailed_analysis: true
Expected Result:
  - Comprehensive hallucination report
  - Code suggestions from real repositories
  - Confidence scores for each finding
  - Risk assessment (critical/medium/low)
Success Criteria:
  - Correctly identifies fake methods
  - Provides real code examples as suggestions
  - Uses both Neo4j and Qdrant for validation
Prerequisites:
  - Code indexed in both Neo4j and Qdrant (Tests 2.10, 2.14)

Test Script Hallucinations:
1. response.extract_json_data() - method doesn't exist on Response object
2. datetime.now().add_days(1) - method doesn't exist on datetime object  
3. requests.post(..., auto_retry=True) - parameter doesn't exist
```

#### Test 2.17: query_knowledge_graph

**Purpose**: Test knowledge graph queries

```yaml
Tool: mcp__crawl4ai-docker__query_knowledge_graph
Parameters:
  command: "repos"
Expected Result:
  - List of parsed repositories
  - Graph data returned
Success Criteria:
  - Query executes successfully
  - Data format correct
```

#### Test 2.18: check_ai_script_hallucinations (Original)

**Purpose**: Test basic hallucination detection (Neo4j only)

```yaml
Preparation: Create test script with known hallucinations
Tool: mcp__crawl4ai-docker__check_ai_script_hallucinations
Parameters:
  script_path: "/home/krashnicov/crawl4aimcp/test_hallucination_script.py"
Expected Result:
  - Hallucinations detected
  - Confidence scores provided
  - Recommendations given
Success Criteria:
  - Correctly identifies fake methods
  - Provides actionable feedback

Test Script Hallucinations:
1. response.extract_json_data() - method doesn't exist on Response object
2. datetime.now().add_days(1) - method doesn't exist on datetime object
3. requests.post(..., auto_retry=True) - parameter doesn't exist
```

### Phase 3: Integration Testing

#### Test 3.1: End-to-End RAG Pipeline

1. Scrape multiple sources
2. Perform RAG queries across sources
3. Verify cross-source results

#### Test 3.2: Git Repository Analysis Pipeline

**Purpose**: Test complete Git repository analysis workflow

```yaml
Steps:
  1. Parse main repository:
     Tool: parse_github_repository
     Parameters: 
       repo_url: "https://github.com/fastapi/fastapi"
  
  2. Parse specific branch:
     Tool: parse_repository_branch
     Parameters:
       repo_url: "https://github.com/fastapi/fastapi"
       branch: "master"
  
  3. Get repository info:
     Tool: get_repository_info
     Parameters:
       repo_name: "fastapi"
  
  4. Query knowledge graph for details:
     Tool: query_knowledge_graph
     Parameters:
       command: "explore fastapi"
  
  5. Check for specific classes:
     Tool: query_knowledge_graph
     Parameters:
       command: "class FastAPI"
  
  6. Update repository:
     Tool: update_parsed_repository
     Parameters:
       repo_url: "https://github.com/fastapi/fastapi"

Expected Results:
  - Complete repository structure in Neo4j
  - Git metadata (branches, commits, contributors)
  - Accurate class/method extraction
  - Successful updates without duplication

Success Criteria:
  - All steps complete without errors
  - Data consistency across queries
  - Git metadata accurately extracted
  - Performance acceptable for large repo
```

#### Test 3.3: Performance Testing

1. Scrape 50+ URLs in parallel
2. Measure throughput and latency
3. Monitor resource usage

#### Test 3.4: Error Handling

1. Test with invalid URLs
2. Test with timeout scenarios
3. Test with malformed content

#### Test 3.5: Git-Specific Error Handling

**Purpose**: Test error handling for Git operations

```yaml
Test Cases:
  1. Invalid repository URL:
     Tool: parse_github_repository
     Parameters:
       repo_url: "https://github.com/nonexistent/repo"
     Expected: Clear error message about invalid repo
  
  2. Non-existent branch:
     Tool: parse_repository_branch
     Parameters:
       repo_url: "https://github.com/octocat/Hello-World"
       branch: "nonexistent-branch"
     Expected: Error about branch not found
  
  3. Repository not parsed:
     Tool: get_repository_info
     Parameters:
       repo_name: "never-parsed-repo"
     Expected: Error that repo not found in knowledge graph
  
  4. Update non-existent repository:
     Tool: update_parsed_repository
     Parameters:
       repo_url: "https://github.com/fake/repository"
     Expected: Error about repository not found

Success Criteria:
  - All errors handled gracefully
  - Clear, actionable error messages
  - No system crashes or hangs
  - Appropriate HTTP status codes
```

### Phase 4: Neo4j-Qdrant Integration Testing

#### Test 4.1: Complete Code Validation Workflow

**Purpose**: Test end-to-end Neo4j-Qdrant integration workflow

```yaml
Steps:
  1. Parse repository:
     Tool: parse_github_repository
     Parameters: 
       repo_url: "https://github.com/qdrant/mcp-server-qdrant.git"
  
  2. Extract and index code:
     Tool: extract_and_index_repository_code
     Parameters:
       repo_name: "mcp-server-qdrant"
  
  3. Search with validation:
     Tool: smart_code_search
     Parameters:
       query: "main function"
       validation_mode: "thorough"
       min_confidence: 0.7
  
  4. Verify results:
     - Results should have validation status
     - Confidence scores should be present
     - Results should be from indexed repository

Expected Results:
  - Repository parsed into Neo4j
  - Code examples indexed in Qdrant
  - Search returns validated results
  - High confidence scores for valid code

Success Criteria:
  - Complete workflow without errors
  - Data consistency between Neo4j and Qdrant
  - Validation improves result quality
```

#### Test 4.2: Validation Mode Comparison

**Purpose**: Compare performance and accuracy across validation modes

```yaml
Test Setup:
  - Use same query for all modes
  - Query: "error handling try catch"
  - Repository: Previously indexed from Test 4.1

Test Cases:
  1. Fast Mode:
     Tool: smart_code_search
     Parameters:
       query: "error handling try catch"
       validation_mode: "fast"
       match_count: 10
     Expected: <200ms response, no validation
  
  2. Balanced Mode:
     Tool: smart_code_search
     Parameters:
       query: "error handling try catch"
       validation_mode: "balanced"
       match_count: 10
     Expected: 200-500ms, partial validation
  
  3. Thorough Mode:
     Tool: smart_code_search
     Parameters:
       query: "error handling try catch"
       validation_mode: "thorough"
       match_count: 10
     Expected: 500ms-2s, full validation

Comparison Metrics:
  - Response time
  - Number of validated results
  - Average confidence scores
  - False positive rate
```

#### Test 4.3: Cross-Repository Code Search

**Purpose**: Test searching across multiple indexed repositories

```yaml
Setup:
  1. Parse additional repository:
     Tool: parse_github_repository
     Parameters:
       repo_url: "https://github.com/github/gitignore"
  
  2. Index second repository:
     Tool: extract_and_index_repository_code
     Parameters:
       repo_name: "gitignore"

Test Cases:
  1. Search across all repositories:
     Tool: smart_code_search
     Parameters:
       query: "configuration file"
       match_count: 10
     Expected: Results from both repositories
  
  2. Filter by repository:
     Tool: smart_code_search
     Parameters:
       query: "configuration file"
       source_filter: "gitignore"
       match_count: 10
     Expected: Results only from gitignore repo

Success Criteria:
  - Can search across multiple repositories
  - Source filtering works correctly
  - Results properly attributed to sources
```

#### Test 4.4: Hallucination Detection Accuracy

**Purpose**: Test enhanced hallucination detection with code suggestions

```yaml
Preparation:
  Create test script with mix of valid and invalid code:
  - Valid: requests.get(url)
  - Invalid: requests.fetch(url)
  - Valid: datetime.now()
  - Invalid: datetime.current()
  - Valid: json.loads(data)
  - Invalid: json.parse(data)

Test:
  Tool: check_ai_script_hallucinations_enhanced
  Parameters:
    script_path: "/home/krashnicov/crawl4aimcp/test_mixed_hallucinations.py"
    include_code_suggestions: true
    detailed_analysis: true

Expected Results:
  - Correctly identifies all invalid methods
  - Provides real code suggestions for fixes
  - Risk assessment for each issue
  - Confidence scores for detections

Success Criteria:
  - 100% detection of known hallucinations
  - Relevant code suggestions from indexed repos
  - No false positives on valid code
  - Clear actionable recommendations
```

## Monitoring During Tests

### Docker Logs

```bash
# Monitor main service (follow mode)
make dev-logs

# Check all containers for patterns (last 100 lines)
make dev-logs-grep  # Default: ERROR|WARNING|embedding|success

# Monitor specific issues across all containers
make dev-logs-grep PATTERN="ERROR|WARNING|401|403|500"

# Monitor embedding generation across all containers
make dev-logs-grep PATTERN="embedding"

# Search for specific tool execution
make dev-logs-grep PATTERN="get_available_sources|scrape_urls"

# Check for timeout or connection issues
make dev-logs-grep PATTERN="timeout|connection|refused"
```

### Key Metrics to Track

1. **Embedding Success Rate**: All scraped content should be embedded
2. **API Response Times**: OpenAI API calls should be <2s
3. **Error Rate**: Should be <1% for valid inputs
4. **Parallel Efficiency**: Multi-URL operations should show parallelism

## Performance Benchmarks

### Neo4j-Qdrant Integration Performance

#### Code Extraction and Indexing

- **Small repository (<100 files)**: <10 seconds
- **Medium repository (100-500 files)**: 10-30 seconds  
- **Large repository (500+ files)**: 30-60 seconds
- **Embedding generation**: ~100-200ms per code example
- **Batch processing**: 10-20 examples per second

#### Smart Code Search Performance by Mode

- **Fast mode (no validation)**: <200ms
  - Direct Qdrant search only
  - No Neo4j validation
  - Best for exploratory searches
  
- **Balanced mode (default)**: 200-500ms
  - Qdrant search + partial Neo4j validation
  - Validates top results only
  - Good balance of speed and accuracy
  
- **Thorough mode (full validation)**: 500ms-2s
  - Complete Neo4j validation for all results
  - Highest confidence scores
  - Best for production code suggestions

#### Hallucination Detection Performance

- **Script analysis time**: 1-3 seconds
- **AST parsing**: <100ms
- **Neo4j validation**: 200-500ms per element
- **Qdrant suggestion search**: 100-200ms per hallucination
- **Complete report generation**: 2-5 seconds total

#### Resource Utilization

- **Memory usage**: <500MB for typical operations
- **CPU usage**: <30% average, <80% peak
- **Network bandwidth**: <10MB/s during indexing
- **Database connections**: <10 concurrent connections

## Expected Production Results

### Success Criteria Summary

- ✅ All tools return successful responses
- ✅ No 401/403 authentication errors
- ✅ Embeddings generated for all content
- ✅ RAG queries return relevant results
- ✅ Knowledge graph operations work (if enabled)
- ✅ Code extraction works (if enabled)
- ✅ Performance meets expectations

### Common Production Issues

1. **Rate Limiting**: OpenAI API rate limits
2. **Timeouts**: Large documents or slow sites
3. **Memory Usage**: Large crawls may need tuning
4. **Blocked Scraping**: Some sites block automated access

## Test Result Template

Create your test results file in `tests/results/YYYYMMDD-hhmm-MCP_TOOLS_TESTING.md` (from Step 1):

```markdown
# MCP Tools Production-Grade Testing Results - [DATE]

**Date**: [DATE]
**Time**: [TIME]
**Environment**: Production-grade (docker-compose.dev.yml)
**Testing Tool**: Claude Code with MCP connection

## Production Configuration
- OPENAI_API_KEY: ✓ Valid production key
- USE_CONTEXTUAL_EMBEDDINGS: true
- USE_HYBRID_SEARCH: true  
- USE_AGENTIC_RAG: true
- USE_RERANKING: true
- USE_KNOWLEDGE_GRAPH: true
- VECTOR_DATABASE: qdrant

### Test Summary
| Tool | Test Case | Status | Time | Notes |
|------|-----------|--------|------|-------|
| get_available_sources | List sources | ✅/❌ | Xs | |
| scrape_urls | Single URL | ✅/❌ | Xs | |
| scrape_urls | Multiple URLs | ✅/❌ | Xs | |
| search | Search and scrape | ✅/❌ | Xs | |
| smart_crawl_url | Regular website | ✅/❌ | Xs | |
| smart_crawl_url | Sitemap | ✅/❌ | Xs | |
| perform_rag_query | Basic query | ✅/❌ | Xs | |
| perform_rag_query | Filtered query | ✅/❌ | Xs | |
| search_code_examples | Code search | ✅/❌ | Xs | |
| parse_github_repository | Basic parsing | ✅/❌ | Xs | |
| parse_repository_branch | Branch parsing | ✅/❌ | Xs | |
| get_repository_info | Metadata retrieval | ✅/❌ | Xs | |
| update_parsed_repository | Repository update | ✅/❌ | Xs | |
| extract_and_index_repository_code | Neo4j-Qdrant bridge | ✅/❌ | Xs | |
| smart_code_search | Fast mode | ✅/❌ | Xs | |
| smart_code_search | Balanced mode | ✅/❌ | Xs | |
| smart_code_search | Thorough mode | ✅/❌ | Xs | |
| check_ai_script_hallucinations_enhanced | Enhanced detection | ✅/❌ | Xs | |
| query_knowledge_graph | Graph queries | ✅/❌ | Xs | |
| check_ai_script_hallucinations | Basic detection | ✅/❌ | Xs | |

### Detailed Results
[For each test, document actual vs expected results]

### Performance Metrics
- Average embedding time: Xs
- Average scrape time: Xs
- Parallel efficiency: X%

### Neo4j-Qdrant Integration Metrics
- Code extraction time: Xs per repository
- Indexing throughput: X examples/second
- Validation confidence scores: X% average
- Search response by mode:
  - Fast: Xms average
  - Balanced: Xms average
  - Thorough: Xms average
- Hallucination detection accuracy: X%
- Code suggestions provided: X per hallucination

### Issues Found
[List any issues discovered]

### Deprecation Warnings
Document any deprecation warnings found during testing:

#### Warning Template:
- **Component**: [Library/service showing the warning]
- **Warning**: [Exact deprecation message]
- **Recommendation**: [Suggested fix/migration path]
- **Reproduction**: [How to reproduce the warning]
- **First seen**: [Which test first showed this warning]

### Recommendations
[Based on test results]
```

## Automation Script

Consider creating an automated test script:

```python
# test_mcp_tools.py
import asyncio
import json
from datetime import datetime

async def test_all_tools():
    results = {}
    
    # Test each tool systematically
    # Record results, timings, errors
    # Generate report
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_all_tools())
    
    # Generate markdown report
    with open(f"test_results_{datetime.now().isoformat()}.md", "w") as f:
        f.write(generate_report(results))
```

## Post-Test Checklist

- [ ] All tools tested with production configuration
- [ ] Docker logs reviewed for hidden errors
- [ ] Performance metrics collected
- [ ] Edge cases tested
- [ ] Results documented
- [ ] Recommendations for improvements noted
- [ ] Any configuration changes documented
