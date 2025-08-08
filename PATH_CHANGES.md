# Path Changes Documentation

This document tracks all path changes made during the repository cleanup and reorganization.

## Docker Configuration

| Old Path | New Path | Notes |
|----------|----------|-------|
| `docker-compose.yml` | `docker-compose.yml` | Kept in root for simplicity |
| `docker-compose.dev.yml` | `docker-compose.dev.yml` | Kept in root for simplicity |
| `docker-compose.prod.yml` | `docker-compose.prod.yml` | Kept in root for simplicity |
| `docker-compose.test.yml` | `docker-compose.test.yml` | Kept in root for simplicity |
| `Dockerfile` | `Dockerfile` | Kept in root for simplicity |
| `searxng/` | `docker/searxng/` | Config moved to docker subdirectory |
| `searxng-test/` | `docker/searxng-test/` | Config moved to docker subdirectory |
| `searxng-backup/` | `docker/searxng-backup/` | Config moved to docker subdirectory |
| `qdrant-config/` | `docker/qdrant/` | Config moved to docker subdirectory |

## Archived Content

| Old Path | New Path |
|----------|----------|
| `archived_configs/` | `archives/configs/` |
| `archived_scripts/` | `archives/scripts/` |
| `archived_docs/` | `archives/docs/` |
| `*_SUMMARY.md` (root) | `archives/reports/summaries/` |
| `*_REPORT.md` (root) | `archives/reports/test-reports/` |
| `*.log` (root) | `archives/logs/` |
| `qa-logs/` | `archives/logs/qa-logs/` |
| `test_*.json` (root) | `archives/test-outputs/` |
| `implementation_fixes_summary.md` | `archives/reports/implementation/` |
| `pipeline_verification_report.md` | `archives/reports/test-reports/` |

## Documentation

| Old Path | New Path |
|----------|----------|
| `tests/plans/MCP_TOOLS_TESTING_PLAN.md` | `docs/QA/MCP_TOOLS_TESTING_PLAN.md` |
| `tests/plans/UNIT_TESTING_PLAN.md` | `docs/QA/UNIT_TESTING_PLAN.md` |
| `QA_PROCESS.md` | `docs/QA/QA_PROCESS.md` |
| `docs/TEST_AND_QA_PLAN.md` | `docs/QA/TEST_AND_QA_PLAN.md` |
| `MCP_CLIENT_CONFIG.md` | `docs/guides/MCP_CLIENT_CONFIG.md` |
| `MCP_TESTING.md` | `docs/QA/MCP_TESTING.md` |
| `CLAUDE_DESKTOP_*.md` | `docs/guides/CLAUDE_DESKTOP_*.md` |
| `NEO4J_*.md` | `docs/architecture/NEO4J_*.md` |
| `TEST_ENVIRONMENT_SETUP.md` | `docs/QA/TEST_ENVIRONMENT_SETUP.md` |
| `IDE_PRODUCTIVITY_IMPROVEMENTS.md` | `docs/development/IDE_PRODUCTIVITY_IMPROVEMENTS.md` |
| `PRE_COMMIT_INTEGRATION.md` | `docs/development/PRE_COMMIT_INTEGRATION.md` |
| `SEARCH_PIPELINE_VERIFICATION.md` | `docs/architecture/SEARCH_PIPELINE_VERIFICATION.md` |
| `fastMCP_docs.md` | `docs/architecture/fastMCP_docs.md` |

## Additional Files Archived

| Old Path | New Path |
|----------|----------|
| `qa_progress.md` | `archives/reports/qa_progress.md` |
| `test_execution_report.md` | `archives/reports/test-reports/test_execution_report.md` |
| `test_report_hallucination.md` | `archives/reports/test-reports/test_report_hallucination.md` |
| `test_report_integration.md` | `archives/reports/test-reports/test_report_integration.md` |
| `test_report_mcp_batch_errors.md` | `archives/reports/test-reports/test_report_mcp_batch_errors.md` |
| `test_report_scrape.md` | `archives/reports/test-reports/test_report_scrape.md` |
| `test_report_search_integration.md` | `archives/reports/test-reports/test_report_search_integration.md` |
| `test_report_batch_url_fix.md` | `archives/reports/test-reports/test_report_batch_url_fix.md` |
| `test_report_code_extraction_fix.md` | `archives/reports/test-reports/test_report_code_extraction_fix.md` |
| `crawl4aimcp.code-workspace` | `configs/crawl4aimcp.code-workspace` |
| `todo.md` | `archives/todo.md` |

## Notes

- **searxng directories**: The `searxng/`, `searxng-test/` directories have ownership by uid 977 (docker user) and require sudo permissions to move. They have been copied to `docker/` where possible, but the originals remain in root due to permission constraints.
| `mcp_test.md` | `docs/QA/mcp_test.md` |
| `mcp_tools_test_results.md` | `docs/QA/mcp_tools_test_results.md` |

## Configuration Files

| Old Path | New Path |
|----------|----------|
| `mcp-client-config.json` | `configs/mcp/mcp-client-config.json` |
| `crawl4aimcp.code-workspace` | `configs/crawl4aimcp.code-workspace` |
| `settings-fixed.yml` | `archives/configs/settings-fixed.yml` |

## Scripts

| Old Path | New Path |
|----------|----------|
| `run_mcp_server.sh` | `scripts/qa/run_mcp_server.sh` |
| `run_qdrant_qa.sh` | `scripts/qa/run_qdrant_qa.sh` |
| `test-*.sh` | `scripts/qa/test-*.sh` |
| `validate_claude_desktop.sh` | `scripts/qa/validate_claude_desktop.sh` |
| `http_to_stdio_bridge.py` | `scripts/http_to_stdio_bridge.py` |
| `test_*.py` (root validation scripts) | `archives/validation/` |
| `trigger_tool_test.py` | `archives/validation/trigger_tool_test.py` |
| `verify_code_extraction.py` | `archives/validation/verify_code_extraction.py` |

## Test Results

| Path | Status |
|------|--------|
| `tests/results/` | No change (kept as-is) |
| `tests/plans/` | Content moved to `docs/QA/`, directory removed |

## Analysis Scripts (NO CHANGE - Critical for hallucination detection)

| Path | Status |
|------|--------|
| `analysis_scripts/user_scripts/` | Keep as-is |
| `analysis_scripts/test_scripts/` | Keep as-is |
| `analysis_scripts/validation_results/` | Keep as-is |

## Important Notes

1. **Docker Files in Root**: docker-compose.yml files and Dockerfile kept in root for simplicity
2. **Docker Configs Organized**: Only service configs (searxng, qdrant) moved to `docker/` subdirectory
3. **Makefile Commands**: All operations should use Makefile commands instead of direct docker compose
4. **Archive Preservation**: All old files moved to archives, nothing deleted
5. **Test Plans Prominent**: QA documentation moved to `docs/QA/` for better visibility

## Command Changes

| Old Command | New Command |
|-------------|-------------|
| `docker compose up -d` | `make prod` |
| `docker compose -f docker-compose.dev.yml up` | `make dev-bg` |
| `docker compose logs -f` | `make logs` |
| `docker compose down` | `make down` |
| `docker compose restart` | `make restart` |

## Environment Setup

- `.env` file remains in root directory (no change)
- Docker services now reference configs from `docker/` subdirectories
- All service configurations preserved in their new locations
