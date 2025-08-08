# Contributing to Crawl4AI MCP

Thank you for your interest in contributing to Crawl4AI MCP! This guide will help you understand our development process, branch protection rules, and how to submit contributions.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Branch Protection Rules](#branch-protection-rules)
- [Making Contributions](#making-contributions)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Code Review Guidelines](#code-review-guidelines)

## Getting Started

1. **Fork the Repository**

   ```bash
   # Fork via GitHub UI, then clone your fork
   git clone https://github.com/YOUR_USERNAME/crawl4ai-mcp.git
   cd crawl4ai-mcp
   ```

2. **Set Up Development Environment**

   ```bash
   # Install UV package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Install dependencies
   uv sync
   
   # Copy environment template
   cp .env.example .env
   ```

3. **Run Tests Locally**

   ```bash
   # Run all tests
   make test
   
   # Run specific test group
   uv run pytest tests/test_utils.py -v
   ```

## Development Process

### Branch Strategy

We use a Git flow-inspired branching strategy:

- **`main`** - Production-ready code (protected)
- **`develop`** - Integration branch for features (protected)
- **Feature branches** - `feature/description`
- **Bug fixes** - `fix/description`
- **Documentation** - `docs/description`
- **Hotfixes** - `hotfix/description`

### Branch Naming Conventions

Branches must follow this pattern: `{type}/{description}`

Valid types:

- `feature` - New features
- `fix` - Bug fixes
- `docs` - Documentation only
- `style` - Code style changes (formatting, etc.)
- `refactor` - Code refactoring
- `perf` - Performance improvements
- `test` - Test additions or corrections
- `build` - Build system changes
- `ci` - CI/CD changes
- `chore` - Maintenance tasks
- `hotfix` - Critical production fixes

## Branch Protection Rules

Both `main` and `develop` branches are protected with the following rules:

### Required Checks

All pull requests must pass these checks:

1. **Code Quality & Linting** - Ruff formatting and linting
2. **Unit Tests** - All test groups for Python 3.12 & 3.13
3. **Integration Tests** - Tests with real services
4. **Coverage Report** - Minimum 80% code coverage
5. **PR Validation** - Title, description, and naming checks

Additional for `main`:
6. **Security Scan** - Vulnerability scanning
7. **Build & Docker Test** - Container build validation

### Review Requirements

- At least 1 approving review required
- Reviews dismissed when new commits pushed (main branch)
- Cannot approve your own PR
- All conversations must be resolved

## Making Contributions

### 1. Create a Feature Branch

```bash
# Update your fork
git checkout develop
git pull upstream develop

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write clean, documented code
- Follow existing patterns and conventions
- Add or update tests as needed
- Update documentation if required

### 3. Commit Your Changes

Use conventional commit format:

```bash
git commit -m "feat: add new crawling strategy"
git commit -m "fix: resolve memory leak in vector storage"
git commit -m "docs: update API documentation"
```

Format: `{type}({scope}): {description}`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`

### 4. Push and Create PR

```bash
# Push your branch
git push origin feature/your-feature-name
```

Then create a pull request via GitHub UI.

## Code Quality Standards

### Python Code Style

- Follow PEP 8 with Ruff configuration
- Use type hints for function parameters and returns
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Code Organization

```python
# Good example
async def search_crawled_pages(
    query: str,
    match_count: int = 5,
    use_reranking: bool = True
) -> List[Dict[str, Any]]:
    """
    Search for crawled pages using semantic similarity.
    
    Args:
        query: Search query text
        match_count: Number of results to return
        use_reranking: Whether to apply reranking
        
    Returns:
        List of search results with metadata
    """
    # Implementation
```

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings
- Include examples for complex functionality
- Keep README files up to date

## Testing Requirements

### Test Coverage

- Minimum 80% code coverage required
- All new features must include tests
- Bug fixes should include regression tests

### Test Structure

```python
# tests/test_feature.py
import pytest
from unittest.mock import Mock, patch

class TestFeature:
    """Test suite for new feature"""
    
    def test_happy_path(self):
        """Test normal operation"""
        # Arrange
        # Act
        # Assert
        
    def test_edge_case(self):
        """Test boundary conditions"""
        pass
        
    def test_error_handling(self):
        """Test error scenarios"""
        pass
```

### Running Tests

```bash
# Run all tests with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_utils.py -v

# Run integration tests
uv run pytest -m integration
```

## Pull Request Process

### PR Title

Must follow conventional commits format:

- `feat: add new feature`
- `fix: resolve issue with X`
- `docs: update installation guide`

### PR Description Template

```markdown
## Description
Brief description of changes and why they're needed.

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Coverage remains above 80%
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the project style
- [ ] I've added tests for my changes
- [ ] I've updated relevant documentation
- [ ] I've checked for breaking changes
```

### PR Size Guidelines

- Keep PRs focused and small
- Aim for <500 lines of changes
- Split large features into multiple PRs
- PRs are automatically labeled by size

## Code Review Guidelines

### For Authors

1. **Self-Review First**: Review your own PR before requesting reviews
2. **Provide Context**: Explain why changes are needed
3. **Respond Promptly**: Address feedback quickly
4. **Be Open**: Accept constructive criticism gracefully

### For Reviewers

1. **Be Constructive**: Suggest improvements, don't just criticize
2. **Check Functionality**: Ensure code works as intended
3. **Verify Tests**: Confirm adequate test coverage
4. **Consider Performance**: Look for potential bottlenecks
5. **Security Review**: Check for security implications

### Review Checklist

- [ ] Code follows project conventions
- [ ] Tests are comprehensive
- [ ] Documentation is updated
- [ ] No sensitive data exposed
- [ ] Performance impact considered
- [ ] Error handling is appropriate

## Getting Help

### Resources

- [Development Guide](docs/DEVELOPMENT_QUICKSTART.md)
- [Branch Protection Guide](docs/BRANCH_PROTECTION_GUIDE.md)
- [Testing Guide](docs/testing/test-helpers-reference.md)

### Communication

- Open an issue for bugs or features
- Use discussions for questions
- Tag maintainers for urgent items

### Common Issues

1. **Tests Failing Locally**: Ensure Docker services are running
2. **Coverage Too Low**: Add tests for new code
3. **PR Checks Failing**: Check Actions tab for details
4. **Merge Conflicts**: Rebase on latest develop branch

## Recognition

Contributors are recognized in:

- Release notes
- Contributors file
- Project documentation

Thank you for contributing to Crawl4AI MCP! 🚀
