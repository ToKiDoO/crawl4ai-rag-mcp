# Makefile for Crawl4AI MCP Server Testing

.PHONY: help test test-unit test-integration test-searxng test-all docker-test-up docker-test-down clean

help:
	@echo "Crawl4AI MCP Server - Test Commands"
	@echo "==================================="
	@echo "make test-unit       - Run unit tests only (no external dependencies)"
	@echo "make test-searxng    - Run SearXNG integration tests"
	@echo "make test-integration- Run all integration tests"
	@echo "make test-all        - Run all tests (unit + integration)"
	@echo "make docker-test-up  - Start test environment containers"
	@echo "make docker-test-down- Stop test environment containers"
	@echo "make test            - Run unit tests (alias)"
	@echo "make clean           - Clean test artifacts"

# Default test command runs unit tests
test: test-unit

# Unit tests only (no external dependencies)
test-unit:
	uv run pytest tests/ -v -m "not integration"

# SearXNG integration tests
test-searxng: docker-test-up
	@echo "Waiting for services to be ready..."
	@sleep 10
	uv run pytest tests/ -v -m searxng

# All integration tests
test-integration: docker-test-up
	@echo "Waiting for services to be ready..."
	@sleep 10
	uv run pytest tests/ -v -m integration

# All tests
test-all: docker-test-up
	@echo "Waiting for services to be ready..."
	@sleep 10
	uv run pytest tests/ -v

# Docker test environment management
docker-test-up:
	docker compose -f docker-compose.test.yml up -d
	@echo "Test environment started. Checking health..."
	@docker compose -f docker-compose.test.yml ps

docker-test-down:
	docker compose -f docker-compose.test.yml down -v

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete