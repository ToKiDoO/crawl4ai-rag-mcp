# Deprecation Warnings Documentation

This document tracks all deprecation warnings in the Crawl4AI MCP project. These warnings should be reviewed during each testing cycle to ensure we're aware of upcoming changes in dependencies.

**Last Updated**: 2025-01-05  
**Related**: [MCP Tools Test Results](../mcp_tools_test_results.md) | [QA Progress](../qa_progress.md)

## Current Deprecation Warnings

### 1. Pydantic V2 Class-Based Config Deprecation

**Source**: `pydantic` library (dependency)  
**Location**: `.venv/lib/python3.12/site-packages/pydantic/_internal/_config.py:323`  
**Warning**:

```
PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. 
Deprecated in Pydantic V2.0 to be removed in V3.0.
```

**Impact**: Low - This is from an external dependency, not our code  
**Action Required**: None currently. Will need attention when Pydantic V3 is released  
**Tracking**: Monitor pydantic upgrade paths in dependencies that use it  

### 2. Importlib Resources read_text Deprecation

**Source**: `fake_http_header` library (transitive dependency via crawl4ai)  
**Location**: `.venv/lib/python3.12/site-packages/fake_http_header/constants.py:5`  
**Warning**:

```
DeprecationWarning: read_text is deprecated. Use files() instead. 
Refer to https://importlib-resources.readthedocs.io/en/latest/using.html#migrating-from-legacy for migration advice.
```

**Impact**: Low - This is from a transitive dependency  
**Action Required**: None - Wait for crawl4ai to update its dependencies  
**Tracking**: Monitor crawl4ai releases for updates to fake_http_header  

## How to Review Deprecation Warnings

1. **During Test Runs**: Run tests with Python warnings enabled:

   ```bash
   python -W default::DeprecationWarning -m pytest tests/
   ```

2. **Check Test Logs**: Review `test_baseline.log` or pytest output for new warnings

3. **Update This Document**: Add any new deprecation warnings found

## Deprecation Review Checklist

When reviewing deprecation warnings:

- [ ] Check if warning is from our code or a dependency
- [ ] Note the deprecation timeline (when will it be removed?)
- [ ] Assess impact on our functionality
- [ ] Create issue/task if action needed
- [ ] Update this document with findings

## Historical Deprecations (Resolved)

None yet - this is the initial documentation.

## References

- [Python Deprecation Warning Documentation](https://docs.python.org/3/library/warnings.html#warning-categories)
- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [Importlib Resources Migration Guide](https://importlib-resources.readthedocs.io/en/latest/using.html#migrating-from-legacy)
