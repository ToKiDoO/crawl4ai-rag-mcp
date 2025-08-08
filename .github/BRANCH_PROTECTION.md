# Branch Protection Configuration

This directory contains workflows and documentation for enforcing code quality and branch protection rules in the Crawl4AI MCP project.

## Quick Start

### Manual Setup (Recommended)

1. Go to Settings → Branches in your GitHub repository
2. Follow the guide in [docs/BRANCH_PROTECTION_GUIDE.md](../docs/BRANCH_PROTECTION_GUIDE.md)
3. Configure protection for `main` and `develop` branches

### Automated Setup (Optional)

```bash
# Install dependencies
pip install PyGithub

# Check current status
export GITHUB_TOKEN=your_token_here
python scripts/setup_branch_protection.py --check

# Apply protection rules
python scripts/setup_branch_protection.py --apply
```

## Protection Overview

### Protected Branches

- **`main`** - Production branch with strict protection
- **`develop`** - Development integration branch with balanced protection

### Key Requirements

1. **Code Review**: At least 1 approval required
2. **Status Checks**: All CI/CD checks must pass
3. **Coverage**: Minimum 80% code coverage enforced
4. **No Direct Push**: Changes must go through pull requests
5. **Up-to-date**: Branches must be current with base branch

## Workflows

### 1. `test-coverage.yml`

Main CI/CD pipeline that runs:

- Code quality checks (linting, formatting)
- Unit tests (Python 3.12 & 3.13)
- Integration tests with Docker services
- Coverage reporting and enforcement
- Security scanning
- Docker build validation

### 2. `pr-validation.yml`

PR-specific validation that checks:

- PR title follows conventional commits
- PR description is meaningful (50+ chars)
- Branch naming conventions
- Coverage requirements
- Dependency security

### 3. `qdrant-qa.yml`

Specialized QA for Qdrant vector database:

- Adapter unit tests
- Integration tests
- Performance benchmarks
- Interface contract validation

## Status Checks

These checks are required for protected branches:

### Critical (Block Merge)

- ✅ Code Quality & Linting
- ✅ Unit Tests (all variations)
- ✅ Integration Tests
- ✅ Coverage Report & Status (80% minimum)
- ✅ PR Validation

### Additional for `main`

- ✅ Security Scan
- ✅ Build & Docker Test

## Common Scenarios

### Adding a New Feature

1. Create branch: `feature/your-feature-name`
2. Make changes and push
3. Open PR to `develop`
4. Ensure all checks pass
5. Get code review approval
6. Merge to `develop`
7. Later: PR from `develop` to `main`

### Emergency Hotfix

1. Create branch: `hotfix/critical-issue`
2. Make minimal necessary changes
3. Open PR directly to `main`
4. Get expedited review
5. Admin can bypass if truly critical

### Documentation Updates

1. Create branch: `docs/update-description`
2. Make documentation changes
3. Open PR to `develop` or `main`
4. Simplified review process for docs-only changes

## Troubleshooting

### "Required status check is expected"

- Wait for all workflows to complete
- Check Actions tab for any failures
- Ensure your branch is up to date with base

### "At least 1 approving review required"

- Request review from team member
- Cannot approve your own PR
- Dismissed reviews need re-approval

### "Coverage decreased"

- Run tests locally: `uv run pytest --cov`
- Add tests for new code
- Check coverage report in PR comments

## Monitoring

### PR Dashboard

Track PR status at: `https://github.com/[owner]/crawl4ai-mcp/pulls`

### Actions Dashboard

Monitor CI/CD at: `https://github.com/[owner]/crawl4ai-mcp/actions`

### Coverage Reports

View coverage trends at PR comments and artifacts

## Best Practices

1. **Keep PRs Small**: Easier to review and less likely to have conflicts
2. **Write Descriptive Titles**: Use conventional commits format
3. **Update Tests**: Add tests for new functionality
4. **Check Locally**: Run `make test` before pushing
5. **Resolve Conversations**: Address all review comments

## References

- [Detailed Protection Guide](../docs/BRANCH_PROTECTION_GUIDE.md)
- [GitHub Branch Protection Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Project Contributing Guidelines](../CONTRIBUTING.md)
