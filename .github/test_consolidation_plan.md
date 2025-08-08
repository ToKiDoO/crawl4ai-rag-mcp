# Test Consolidation Plan

## Core Test Files to Keep

### Unit Tests (no external dependencies)

1. `test_crawl4ai_mcp_unit.py` - Main unit tests for MCP server
2. `test_database_factory_unit.py` - Database factory tests
3. `test_database_adapters_unit.py` - Database adapter tests
4. `test_utils.py` - Utility function tests

### Integration Tests (require services)

1. `test_integration_simple.py` - Basic integration tests
2. `test_qdrant_integration.py` - Qdrant integration tests
3. `test_neo4j_integration.py` - Neo4j integration tests

## Files to Remove (redundant)

### Redundant crawl4ai_mcp tests

- `test_crawl4ai_mcp_basic.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp_comprehensive.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp_coverage.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp_crawling.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp_lifespan.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp_simple.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp_tools.py` → merge into `test_crawl4ai_mcp_unit.py`
- `test_crawl4ai_mcp.py` → keep unique tests, merge into `test_crawl4ai_mcp_unit.py`

### Redundant database tests

- `test_database_factory.py` → merge into `test_database_factory_unit.py`
- `test_database_integration.py` → merge into `test_integration_simple.py`
- `test_database_interface.py` → merge into `test_database_adapters_unit.py`
- `test_database_errors_comprehensive.py` → merge error tests into respective unit tests

### Redundant Qdrant tests

- `test_qdrant_adapter.py` → merge into `test_database_adapters_unit.py`
- `test_qdrant_config.py` → merge into `test_database_adapters_unit.py`
- `test_qdrant_connection_failures.py` → merge into `test_qdrant_integration.py`
- `test_qdrant_crawl4ai_integration.py` → merge into `test_qdrant_integration.py`
- `test_qdrant_database_integration.py` → merge into `test_qdrant_integration.py`
- `test_qdrant_error_handling.py` → merge into `test_qdrant_integration.py`
- `test_qdrant_integration_comprehensive.py` → merge into `test_qdrant_integration.py`
- `test_qdrant_mcp_tools_integration.py` → merge into `test_qdrant_integration.py`
- `test_qdrant_store_crawled_page.py` → merge into `test_qdrant_integration.py`
- `test_mcp_qdrant_integration.py` → merge into `test_qdrant_integration.py`

## Additional cleanup

- Remove test reports and documentation files from tests directory
- Keep only essential test fixtures and helpers
- Consolidate mock helpers into a single file
