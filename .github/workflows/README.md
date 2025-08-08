# CI/CD Workflows

This directory contains the GitHub Actions workflows for the crawl4ai-mcp project.

## Overview

We maintain a simple, focused CI/CD pipeline with two main workflows:

### 1. CI Workflow (`ci.yml`)

**Triggers**: Push to main/develop, Pull requests to main

**Purpose**: Test code quality and functionality

- Runs on every push and PR
- Lints code with ruff
- Runs unit tests with 80% coverage requirement
- Runs integration tests only when relevant files change
- Comments coverage report on PRs

**Key Features**:

- Single Python version (3.12) for faster execution
- Smart integration test triggering based on changed files
- Minimal service startup (only Qdrant for integration tests)
- Clear coverage reporting

### 2. Deploy Workflow (`deploy.yml`)

**Triggers**: Push to main branch only

**Purpose**: Build and publish Docker images

- Builds Docker image
- Runs security scan with Trivy
- Pushes to GitHub Container Registry
- Generates deployment summary

**Key Features**:

- Only runs on main branch (no PR builds)
- Security scanning before deployment
- Automatic image tagging
- Release notes generation

## Running Tests Locally

To replicate the CI environment locally:

```bash
# Install dependencies
uv sync --frozen

# Run linting
uv run ruff check src/ tests/
uv run ruff format src/ tests/ --check

# Run unit tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=term-missing -m "not integration"

# Run integration tests (requires Docker)
docker compose -f docker-compose.test.yml up -d qdrant-test
uv run pytest tests/ -v -m "integration"
docker compose -f docker-compose.test.yml down
```

## Configuration

- **Python Version**: 3.12
- **Coverage Threshold**: 80%
- **Test Markers**:
  - `unit`: Tests without external dependencies
  - `integration`: Tests requiring external services
  - `slow`: Long-running tests

## Maintenance

When adding new functionality:

1. Ensure unit tests maintain 80% coverage
2. Add integration tests only for external service interactions
3. Keep test files focused and avoid duplication
4. Use appropriate test markers

## Troubleshooting

### Tests Failing Locally

- Ensure UV is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Check environment variables match those in workflows
- For integration tests, ensure Docker is running

### Coverage Below Threshold

- Run coverage locally: `uv run pytest --cov=src --cov-report=html`
- Open `htmlcov/index.html` to see uncovered lines
- Focus on testing business logic in `src/`
