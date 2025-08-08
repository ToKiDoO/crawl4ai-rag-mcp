# GitHub Branch Protection Setup Guide

This guide provides comprehensive instructions for setting up branch protection rules for the Crawl4AI MCP project to ensure code quality, maintain test coverage, and enforce review processes.

## Table of Contents

1. [Overview](#overview)
2. [Protected Branches](#protected-branches)
3. [Manual Setup Instructions](#manual-setup-instructions)
4. [Branch Protection Rules](#branch-protection-rules)
5. [Status Check Configuration](#status-check-configuration)
6. [Enforcement Exceptions](#enforcement-exceptions)
7. [Troubleshooting](#troubleshooting)

## Overview

Branch protection rules help maintain code quality by:

- Requiring code reviews before merging
- Enforcing CI/CD checks including test coverage
- Preventing direct pushes to protected branches
- Ensuring all tests pass before merging
- Maintaining minimum code coverage of 80%

## Protected Branches

The following branches should be protected:

- `main` - Production-ready code
- `develop` - Integration branch for features

## Manual Setup Instructions

### Step 1: Navigate to Branch Protection Settings

1. Go to your repository on GitHub
2. Click on **Settings** tab
3. In the left sidebar, click **Branches** under "Code and automation"
4. Click **Add rule** button

### Step 2: Configure Protection for `main` Branch

1. **Branch name pattern**: Enter `main`
2. Enable the following protections:

#### Required Status Checks

- [x] **Require status checks to pass before merging**
  - [x] **Require branches to be up to date before merging**
  - Add these required status checks:
    - `Code Quality & Linting`
    - `Unit Tests (3.12, core)`
    - `Unit Tests (3.12, adapters)`
    - `Unit Tests (3.12, interfaces)`
    - `Unit Tests (3.13, core)`
    - `Unit Tests (3.13, adapters)`
    - `Unit Tests (3.13, interfaces)`
    - `Integration Tests`
    - `Coverage Report & Status`
    - `Security Scan`
    - `Build & Docker Test`

#### Pull Request Reviews

- [x] **Require a pull request before merging**
  - [x] **Require approvals**: 1
  - [x] **Dismiss stale pull request approvals when new commits are pushed**
  - [x] **Require review from CODEOWNERS** (if CODEOWNERS file exists)
  - [x] **Require approval of the most recent reviewable push**

#### Additional Settings

- [x] **Require conversation resolution before merging**
- [x] **Require signed commits** (optional but recommended)
- [x] **Require linear history** (optional, prevents merge commits)
- [x] **Include administrators** (recommended for consistency)
- [x] **Restrict who can push to matching branches** (optional)
  - Add specific users or teams if needed

#### Force Push Protection

- [x] **Do not allow force pushes**
- [x] **Do not allow deletions**

3. Click **Create** to save the rule

### Step 3: Configure Protection for `develop` Branch

1. **Branch name pattern**: Enter `develop`
2. Enable similar protections as `main` but with some differences:

#### Required Status Checks

- [x] **Require status checks to pass before merging**
  - [x] **Require branches to be up to date before merging**
  - Add these required status checks (same as main):
    - `Code Quality & Linting`
    - `Unit Tests (3.12, core)`
    - `Unit Tests (3.12, adapters)`
    - `Unit Tests (3.12, interfaces)`
    - `Unit Tests (3.13, core)`
    - `Unit Tests (3.13, adapters)`
    - `Unit Tests (3.13, interfaces)`
    - `Integration Tests`
    - `Coverage Report & Status`

#### Pull Request Reviews

- [x] **Require a pull request before merging**
  - [x] **Require approvals**: 1
  - [ ] **Dismiss stale pull request approvals when new commits are pushed** (optional for develop)
  - [x] **Require approval of the most recent reviewable push**

#### Additional Settings

- [x] **Require conversation resolution before merging**
- [ ] **Require signed commits** (optional for develop)
- [x] **Do not allow force pushes**
- [x] **Do not allow deletions**

3. Click **Create** to save the rule

## Branch Protection Rules

### For Production (`main`) Branch

| Rule | Setting | Rationale |
|------|---------|-----------|
| Require PR | Yes | Ensures code review process |
| Required approvals | 1 | Minimum peer review |
| Dismiss stale approvals | Yes | Ensures reviews are for latest code |
| Require status checks | Yes | Ensures CI/CD passes |
| Require up-to-date branch | Yes | Prevents conflicts |
| Require conversation resolution | Yes | Ensures all feedback addressed |
| Block force pushes | Yes | Preserves history |
| Block deletions | Yes | Prevents accidental deletion |

### For Development (`develop`) Branch

| Rule | Setting | Rationale |
|------|---------|-----------|
| Require PR | Yes | Ensures code review process |
| Required approvals | 1 | Minimum peer review |
| Dismiss stale approvals | No | More flexible for active development |
| Require status checks | Yes | Ensures CI/CD passes |
| Require up-to-date branch | Yes | Prevents conflicts |
| Require conversation resolution | Yes | Ensures all feedback addressed |
| Block force pushes | Yes | Preserves history |
| Block deletions | Yes | Prevents accidental deletion |

## Status Check Configuration

### Critical Status Checks

These checks MUST pass for all protected branches:

1. **Code Quality & Linting**
   - Runs ruff linting and formatting checks
   - Ensures code style consistency

2. **Unit Tests**
   - Runs for Python 3.12 and 3.13
   - Split into core, adapters, and interfaces groups
   - Each group must pass independently

3. **Integration Tests**
   - Tests with real services (Qdrant, SearXNG, etc.)
   - Ensures end-to-end functionality

4. **Coverage Report & Status**
   - Enforces 80% minimum code coverage
   - Generates coverage reports

### Additional Checks for `main`

5. **Security Scan**
   - Runs Trivy vulnerability scanner
   - Identifies security issues

6. **Build & Docker Test**
   - Validates Docker build process
   - Ensures containerization works

### Qdrant-Specific Checks

When changes affect Qdrant components, these additional checks run:

- Qdrant QA tests
- Performance benchmarks
- Interface contract tests

## Enforcement Exceptions

### When to Allow Exceptions

1. **Emergency Hotfixes**
   - Security vulnerabilities
   - Production breaking bugs
   - Data corruption issues

2. **Documentation Updates**
   - README changes
   - Documentation-only PRs
   - License updates

### How to Bypass (Admin Only)

1. Go to the PR that needs to bypass
2. Look for "Merge without waiting for requirements to be met"
3. Select appropriate option:
   - "Merge anyway" (bypasses all checks)
   - "Merge when ready" (waits for in-progress checks)

**⚠️ Warning**: Always document why protection was bypassed in the merge commit message.

## Troubleshooting

### Common Issues

#### 1. Status Check Not Appearing

**Problem**: Required status check not available in dropdown  
**Solution**:

- Ensure the workflow has run at least once
- Check workflow file name matches the job name
- Wait for GitHub to index the check (can take up to 10 minutes)

#### 2. Coverage Failing Despite Good Coverage

**Problem**: Coverage check fails even with >80% coverage  
**Solution**:

- Check if all test groups are running
- Ensure coverage combination is working correctly
- Verify `.coveragerc` or `pyproject.toml` coverage settings

#### 3. "Waiting for status to be reported"

**Problem**: PR shows waiting for checks that never start  
**Solution**:

- Check if workflow triggers match (push/pull_request)
- Verify branch filters in workflow
- Check GitHub Actions isn't disabled

#### 4. Cannot Push to Protected Branch

**Problem**: Direct push rejected even for admins  
**Solution**:

- Create a PR instead of direct push
- If admin bypass needed, temporarily disable "Include administrators"
- Use GitHub web interface for emergency edits

### Getting Help

1. Check GitHub Actions logs for specific failures
2. Review `.github/workflows/` files for configuration
3. Consult GitHub's branch protection documentation
4. Open an issue with specific error messages

## Best Practices

1. **Regular Reviews**: Review and update protection rules quarterly
2. **Monitor Metrics**: Track how often protections are bypassed
3. **Team Training**: Ensure all contributors understand the rules
4. **Gradual Rollout**: Start with warnings before enforcing
5. **Clear Communication**: Document any changes to protection rules

## Related Documentation

- [GitHub Actions Workflows](.github/workflows/README.md)
- [Test Coverage Configuration](../pyproject.toml)
- [Development Guide](DEVELOPMENT_QUICKSTART.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
