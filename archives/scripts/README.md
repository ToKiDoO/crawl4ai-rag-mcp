# Archived Test Scripts

This directory contains temporary test scripts created during the MCP Tools Testing issue resolution process on 2025-08-05.

## Purpose

These scripts were created as quick debugging and validation tools during the resolution of issues identified in the MCP Tools Testing Results. They are separate from the actual unit test suite in the `tests/` directory.

## Related Documentation

- **Primary Outcome Document**: `../mcp_tools_test_results.md` - Contains the full test results and resolution summary
- **Test Plan**: `../tests/plans/MCP_TOOLS_TESTING_PLAN.md` - Original testing plan
- **Test Results**: `../tests/results/20250804-MCP_TOOLS_TESTING.md` - Detailed test execution results

## Scripts Overview

### Fix 1: API Key Loading

- `test_api_key_validation.py` - Validates API key loading from .env file and security validation

### Fix 2: Neo4j Connection

- `test_neo4j_direct.py` - Direct Neo4j connection testing for NEO4J_USERNAME standardization
- `test_neo4j_tools.py` - MCP tools testing for Neo4j functionality

### Fix 3: Array Parameter Handling

- `test_url_parsing.py` - Tests smart JSON array parsing for multiple URL inputs
- `test_batch_mcp.js` - JavaScript test for batch URL scraping via MCP
- `test_batch_scraping.py` - Python batch scraping tests
- `test_batch_via_http.py` - HTTP-based batch testing
- `test_batch_mcp_stdio.py` - STDIO-based MCP batch testing
- `test_scrape_urls_formats.py` - URL format validation tests
- `test_scrape_formats_mcp.py` - MCP-specific format tests
- `test_input_parsing_logic.py` - Input parsing logic validation

### Fix 4: Code Extraction (Incomplete)

- `test_code_extraction_direct.py` - Direct code extraction testing
- `test_code_extraction_integration.py` - Integration testing for code extraction
- `test_final_code_extraction.py` - Final validation of code extraction
- `test_code_extraction_fix.py` - Verifies the environment variable name correction

**Note**: These scripts were created to test the code extraction functionality but the implementation remains incomplete. The extract_code_blocks and store_code_example functions exist in utils.py but are not integrated into the scraping pipeline.

### General Testing Scripts

- `test_mcp_client.py` - Basic MCP client testing
- `test_mcp_simple.py` - Simple MCP functionality tests
- `test_direct.py` - Direct function call tests
- `test_mcp_startup.py` - MCP server startup validation
- `test_mcp_tools_list.py` - Tool listing functionality
- `test_proper_mcp_client.py` - Proper MCP client implementation tests
- `test_final_batch_validation.py` - Final batch processing validation
- `test_search_pipeline.py` - Search pipeline testing
- `test_search_integration.py` - Search integration tests
- `test_e2e_pipeline.py` - End-to-end pipeline tests
- `test_hallucination_script.py` - AI hallucination detection tests
- `test_integration_summary.py` - Integration test summary
- `test_live_scrape.py` - Live scraping tests

## Status

These scripts served their purpose during the debugging process and have been archived. The fixes they validated have been implemented in the main codebase:

✅ Fix 1: API key loading resolved
✅ Fix 2: Neo4j connection fixed
✅ Fix 3: Array parameter handling implemented
🔄 Fix 4: Code extraction (in progress)
⏳ Fix 5: Deprecated methods (pending)

For ongoing testing, use the proper test suite in the `tests/` directory.
