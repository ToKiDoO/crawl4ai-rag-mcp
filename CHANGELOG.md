# Changelog

All notable changes to this project will be documented in this file.

## [2025-08-07] - QdrantAdapter Parameter Name Consistency Fix

### Fixed

- Fixed parameter name inconsistency in QdrantAdapter causing "unexpected keyword argument 'filter_metadata'" errors
  - **Root Cause**: QdrantAdapter methods used `metadata_filter` while VectorDatabase protocol defined `filter_metadata`
  - **Files Updated**:
    - `src/database/qdrant_adapter.py`:
      - Line 288: `search()` method parameter changed from `metadata_filter` to `filter_metadata`
      - Line 319: `hybrid_search()` method parameter changed from `metadata_filter` to `filter_metadata`
      - Line 338: Internal call in `hybrid_search()` updated to use `filter_metadata`
      - Line 541: `search_code_examples()` method parameter changed from `metadata_filter` to `filter_metadata`
    - `src/services/validated_search.py` (line 220): Updated call to use `filter_metadata` parameter
    - `src/database/rag_queries.py` (line 176): Updated call to use `filter_metadata` parameter
  - **Impact**: Resolves runtime errors in semantic search, hybrid search, and code example search operations
  - **Validation**: All database adapters now consistently implement the VectorDatabase protocol interface

## [2025-08-07] - Neo4j Aggregation Warning Suppression

### Fixed

- Eliminated Neo4j aggregation warnings about null values in repository metadata queries
  - Implemented driver-level warning suppression using `NotificationMinimumSeverity.OFF` for Neo4j driver 5.21.0+
  - Added fallback to logging suppression for older Neo4j driver versions
  - Updated all 5 Neo4j driver initialization points across the codebase:
    - `src/knowledge_graph/queries.py` (line 65)
    - `knowledge_graphs/parse_repo_into_neo4j.py` (line 427)
    - `src/services/validated_search.py` (line 85)
    - `knowledge_graphs/query_knowledge_graph.py` (line 37)
    - `knowledge_graphs/knowledge_graph_validator.py` (line 127)
  - Fixed exception handling to properly catch both `ImportError` and `AttributeError`
  - Updated aggregation query in `src/knowledge_graph/repository.py` (line 354) to filter null files

### Technical Details

- Warning suppression is configured at Neo4j driver initialization
- Backward compatible with Neo4j driver versions < 5.21.0 via logging configuration
- No performance impact - warnings are suppressed, not the underlying aggregation
- Maintains full data integrity and calculation accuracy

## [2025-08-07] - Validated Search Parameter Fix

### Fixed

- Fixed parameter name mismatch in `src/services/validated_search.py` causing "unexpected keyword argument 'filter_metadata'" error
  - Changed `filter_metadata` to `metadata_filter` when calling `QdrantAdapter.search_code_examples()` (line 207)
  - This resolves the error that was preventing validated code search from working with source filters

## [2025-08-06] - Hallucination Detection Volume Mounting Fix

### Added

- Created `analysis_scripts/` directory structure for script analysis
  - `user_scripts/` - For user Python scripts
  - `test_scripts/` - For test scripts  
  - `validation_results/` - For storing analysis results
- Added Docker volume mounts in `docker-compose.dev.yml`:
  - `./analysis_scripts:/app/analysis_scripts:rw` - Script directories
  - `/tmp:/app/tmp_scripts:ro` - Temporary scripts (read-only)
- New helper tool `get_script_analysis_info()` to provide setup information
- Comprehensive documentation in README.md and CLAUDE.md

### Changed

- Enhanced `validate_script_path()` in `src/utils/validation.py`:
  - Added automatic path translation from host to container paths
  - Improved error messages with helpful guidance
- Updated hallucination detection tools in `src/tools.py`:
  - `check_ai_script_hallucinations` now uses container paths
  - `check_ai_script_hallucinations_enhanced` now uses container paths
- Updated `.gitignore` to exclude analysis scripts while keeping directory structure

### Fixed

- Resolved "Script not found" errors in hallucination detection tools
- Fixed path accessibility issues between host and Docker container
- Tools can now access scripts placed in designated directories

### Technical Details

- Path mapping: Host paths automatically translate to container paths
- Security: /tmp mount is read-only to prevent container writing to host
- Convenience: Scripts can be referenced with simple relative paths
