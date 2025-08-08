# Codecov Setup Guide

This document explains how to configure Codecov for the Crawl4AI MCP Server project.

## Overview

The project uses Codecov for coverage tracking and reporting with the following features:

- **80% coverage threshold** enforcement
- **Automated PR comments** with coverage details
- **Multi-flag reporting** for different test types (unit tests, integration tests)
- **Matrix testing coverage** across Python versions

## GitHub Repository Setup

### 1. Codecov Account Setup

1. Go to [codecov.io](https://codecov.io) and sign up/login with your GitHub account
2. Add your repository (krashnicov/crawl4aimcp) to Codecov
3. Note your repository's **Codecov Token** from the repository settings

### 2. GitHub Secrets Configuration

Add the following secret to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add:
   - **Name**: `CODECOV_TOKEN`
   - **Value**: Your Codecov repository token from step 1

### 3. Configuration Files

The project includes two main configuration files:

#### `codecov.yml` (Root of repository)

- Defines coverage thresholds (80% minimum)
- Configures PR comment behavior
- Sets up ignore patterns for non-source files
- Enables GitHub status checks

#### `.github/workflows/test-coverage.yml`

- GitHub Actions workflow for running tests
- Uploads coverage reports to Codecov with proper flags
- Runs matrix testing across Python versions

## Coverage Flags

The project uses the following Codecov flags:

| Flag | Description | Source |
|------|-------------|---------|
| `unittests` | All unit tests | Unit test jobs |
| `core` | Core functionality tests | Unit test matrix |
| `adapters` | Database adapter tests | Unit test matrix |
| `interfaces` | Interface tests | Unit test matrix |
| `integration` | Integration tests | Integration test job |

## Coverage Reporting

### Automatic Reporting

- **Push/PR triggers**: Coverage reports uploaded automatically on code push/PR
- **PR Comments**: Codecov automatically comments on PRs with coverage details
- **Status Checks**: GitHub status checks show pass/fail based on coverage thresholds

### Manual Coverage Checks

```bash
# Generate local coverage report
make test-coverage

# View coverage report
open htmlcov/index.html

# Run CI-style coverage (matches GitHub Actions)
make test-coverage-ci
```

## Troubleshooting

### Common Issues

**Upload failures:**

- Verify `CODECOV_TOKEN` is set correctly in GitHub Secrets
- Check GitHub Actions logs for upload errors
- Ensure coverage.xml files are generated correctly

**Low coverage warnings:**

- Review codecov.yml ignore patterns
- Check that test files are properly excluded
- Verify source code paths are correct

**PR comment issues:**

- Ensure the GitHub app has proper permissions
- Check if base branch has coverage data
- Verify PR comes from the same repository (not a fork)

### Configuration Validation

Test your codecov.yml configuration:

```bash
# Install codecov CLI (optional)
pip install codecov

# Validate configuration
codecov --validate
```

## Best Practices

1. **Test Coverage**: Maintain minimum 80% coverage on new code
2. **PR Reviews**: Review coverage changes in PR comments
3. **Flag Usage**: Use appropriate flags for different test types
4. **Ignore Patterns**: Keep ignore patterns updated for non-source files
5. **Threshold Updates**: Adjust thresholds carefully as the codebase matures

## Links

- [Codecov Dashboard](https://codecov.io/gh/krashnicov/crawl4aimcp)
- [Codecov Documentation](https://docs.codecov.com/)
- [GitHub Actions Integration](https://docs.codecov.com/docs/github-actions)
