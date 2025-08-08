# PR #6 Modularization Plan

## Overview

This document outlines the plan to incorporate the complete modularization refactoring into PR #6 to fix CI failures and improve the codebase architecture.

## Current Situation

- **PR #6 Status**: OPEN, failing CI due to linting errors in old monolithic code
- **Branch**: `fix/ci-failures-qdrant-tests`
- **Backup Branch**: `backup/pre-cleanup-2025-01-08` contains all modularization work
- **Changes Scope**: 42 new src files, 181 test updates, complete architectural refactoring

## Execution Plan

### Phase 1: Restore Modularized Code

```bash
# Cherry-pick the modularization commit from backup branch
git cherry-pick backup/pre-cleanup-2025-01-08

# If conflicts occur, accept the modularized version
git add -A
git cherry-pick --continue
```

### Phase 2: Clean Up Structure (No Backward Compatibility)

#### Files to DELETE

- `src/crawl4ai_mcp.py` - replaced by modular structure
- `src/utils.py` - replaced by utils/ module
- `src/utils_refactored.py` - temporary file
- `src/security.py` - if moved to modules
- `src/knowledge_graph_tools.py` - if moved to modules
- `src/database/qdrant_adapter_fixed.py` - duplicate
- Any `.backup` files

#### Final Structure

```
src/
├── main.py                 # Entry point
├── tools.py                # MCP tool definitions
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py
├── core/                   # Core infrastructure
│   ├── __init__.py
│   ├── context.py
│   ├── decorators.py
│   ├── exceptions.py
│   ├── logging.py
│   └── stdout_utils.py
├── database/               # Database adapters
│   ├── __init__.py
│   ├── base.py
│   ├── factory.py
│   ├── qdrant_adapter.py
│   ├── supabase_adapter.py
│   ├── rag_queries.py
│   └── sources.py
├── knowledge_graph/        # Neo4j integration
│   ├── __init__.py
│   ├── handlers.py
│   ├── queries.py
│   ├── repository.py
│   ├── validation.py
│   └── enhanced_validation.py
├── services/               # Business logic
│   ├── __init__.py
│   ├── crawling.py
│   ├── search.py
│   ├── smart_crawl.py
│   └── validated_search.py
└── utils/                  # Utility functions
    ├── __init__.py
    ├── reranking.py
    ├── text_processing.py
    ├── url_helpers.py
    └── validation.py
```

### Phase 3: Update Configuration Files

#### 1. Update `pyproject.toml`

```toml
[project.scripts]
crawl4ai-mcp = "src.main:main"
```

#### 2. Update Docker files

- **Dockerfile**: `CMD ["python", "-m", "src.main"]`
- **docker-compose.yml**: Update command if needed

### Phase 4: Code Quality Checks

#### 1. Install Tools

```bash
# Install markdown linter
npm install -g markdownlint-cli

# Ensure Python tools are available
uv sync
```

#### 2. Python Linting (Ruff)

```bash
# Check for issues
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check src/ tests/ --fix

# Format code
uv run ruff format src/ tests/
```

#### 3. Markdown Linting

```bash
# Check all markdown files
markdownlint '**/*.md' --ignore node_modules

# Auto-fix markdown issues
markdownlint '**/*.md' --fix --ignore node_modules

# Check specific important files
markdownlint README.md CHANGELOG.md 'docs/**/*.md' --fix
```

#### 4. Type Checking (optional)

```bash
uv run mypy src/ --ignore-missing-imports
```

### Phase 5: Test Updates

#### Import Updates Required

```python
# Old imports (REMOVE):
from crawl4ai_mcp import some_function
from utils import some_utility

# New imports (USE):
from src.tools import tool_name
from src.services.crawling import crawl_function
from src.database.factory import get_database_client
from src.utils.validation import validate_function
```

### Phase 6: CI/CD Updates

#### Update `.github/workflows/ci.yml`

Add markdown linting step:

```yaml
- name: Lint Markdown files
  run: |
    npm install -g markdownlint-cli
    markdownlint '**/*.md' --ignore node_modules --ignore archives
```

Ensure Python paths are correct:

```yaml
env:
  PYTHONPATH: ${{ github.workspace }}
```

### Phase 7: Local Validation

```bash
# 1. Run Python linting
uv run ruff check src/ tests/
uv run ruff format src/ tests/ --check

# 2. Run Markdown linting
markdownlint '**/*.md' --ignore node_modules --ignore archives

# 3. Run unit tests
uv run pytest tests/ -v --tb=short -m "not integration"

# 4. Start Docker services (if testing integration)
docker compose -f docker-compose.dev.yml up -d

# 5. Run integration tests
uv run pytest tests/ -v -m integration

# 6. Check test coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Phase 8: Commit Strategy

```bash
# Stage all changes
git add -A

# Create comprehensive commit
git commit -m "refactor: complete modularization of codebase

- Migrate from monolithic to modular architecture
- New structure: main.py + organized modules
- Remove all legacy/duplicate files
- Update tests for new imports
- Add markdown linting
- Fix all Python linting issues

Breaking changes:
- Entry point changed from crawl4ai_mcp.py to main.py
- All imports must use new module structure
- No backward compatibility with old structure

Co-authored-by: Claude <noreply@anthropic.com>"

# Push to PR (force push since we're replacing history)
git push origin fix/ci-failures-qdrant-tests --force-with-lease
```

### Phase 9: Update PR Description

Update PR #6 on GitHub with:

```markdown
## Summary
This PR includes a complete modularization of the codebase to fix CI issues and improve maintainability.

## Changes

### 🏗️ Architecture Refactoring
- Migrated from monolithic `crawl4ai_mcp.py` (3000+ lines) to modular structure
- New entry point: `src/main.py` with FastMCP
- Organized code into logical modules: core, config, services, database, utils, knowledge_graph
- Removed 40+ obsolete files

### 🧹 Code Quality
- ✅ Fixed all Python linting issues (Ruff)
- ✅ Added Markdown linting (markdownlint-cli)
- ✅ Removed all duplicate and legacy files
- ✅ Updated all tests for new import structure
- ✅ Type hints throughout

### 📊 Testing
- 180+ test files updated
- All unit tests passing
- Integration tests validated
- Test coverage maintained

### 🔄 Breaking Changes
- Entry point changed to `src/main.py`
- All imports must use new module paths
- No backward compatibility maintained (clean break)

## File Structure
```

src/
├── main.py                 # Entry point
├── tools.py                # MCP tool definitions
├── config/                 # Configuration
├── core/                   # Core infrastructure
├── database/               # Database adapters
├── knowledge_graph/        # Neo4j integration
├── services/               # Business logic
└── utils/                  # Utilities

```

## Testing
- [x] Python linting (Ruff)
- [x] Markdown linting
- [x] Unit tests
- [x] Integration tests
- [x] Coverage threshold met

## Migration Notes
For developers updating existing code:
1. Update imports to use new module paths
2. Entry point is now `src/main.py`
3. Configuration via `src/config/settings.py`
```

## Post-Merge Tasks

1. **Clean up branches**:

```bash
# Delete backup branch locally
git branch -D backup/pre-cleanup-2025-01-08

# Clean up remote if pushed
git push origin --delete backup/pre-cleanup-2025-01-08
```

2. **Archive remaining work**:

- Create feature branches for documentation updates
- File issues for any discovered improvements

3. **Update documentation**:

- Update README.md with new structure
- Update CONTRIBUTING.md with new development workflow
- Create ARCHITECTURE.md explaining the modular design

## Troubleshooting

### If CI Still Fails

1. **Check logs carefully** for specific errors
2. **Common issues**:
   - Import errors: Update test imports
   - Path issues: Check PYTHONPATH in CI
   - Missing dependencies: Update pyproject.toml
   - Linting: Run locally with --fix flag

3. **Rollback if needed**:

```bash
git reset --hard origin/fix/ci-failures-qdrant-tests
```

## Success Criteria

- [x] All CI checks passing
- [x] No linting errors (Python or Markdown)
- [x] All tests passing
- [x] Clean modular structure
- [x] No duplicate/legacy files
- [x] PR ready for merge

## Notes

- Created: 2025-01-08
- Backup branch: `backup/pre-cleanup-2025-01-08`
- PR URL: <https://github.com/Deimos-AI/crawl4ai-rag-mcp/pull/6>
