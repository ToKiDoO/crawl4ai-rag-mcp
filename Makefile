# Makefile for Crawl4AI MCP Server Development

# Variables
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml
DOCKER_COMPOSE_TEST := $(DOCKER_COMPOSE) -f docker-compose.test.yml
PYTHON := uv run python
PYTEST := uv run pytest

# Colors for output
COLOR_GREEN := \033[0;32m
COLOR_YELLOW := \033[0;33m
COLOR_RED := \033[0;31m
COLOR_RESET := \033[0m

.PHONY: help
help:
	@echo "$(COLOR_GREEN)Crawl4AI MCP Server - Development Commands$(COLOR_RESET)"
	@echo "============================================"
	@echo ""
	@echo "$(COLOR_YELLOW)Development Environment:$(COLOR_RESET)"
	@echo "  make dev             - Start development environment with watch mode (foreground)"
	@echo "  make dev-bg          - Start development environment in background with watch"
	@echo "  make dev-nobuild     - Start dev environment WITHOUT rebuilding (foreground)"
	@echo "  make dev-bg-nobuild  - Start dev environment WITHOUT rebuilding (background)"
	@echo "  make dev-logs        - View development logs (follow mode)"
	@echo "  make dev-down        - Stop development environment"
	@echo "  make dev-restart     - Restart development services"
	@echo "  make dev-rebuild     - Rebuild and restart development environment"
	@echo "  make dev-shell       - Open shell in dev container"
	@echo "  make dev-python      - Open Python REPL in dev container"
	@echo "  make watch           - Start Docker watch mode only"
	@echo ""
	@echo "$(COLOR_YELLOW)Testing:$(COLOR_RESET)"
	@echo "  make test            - Run unit tests (alias)"
	@echo "  make test-unit       - Run unit tests only (no external dependencies)"
	@echo "  make test-searxng    - Run SearXNG integration tests"
	@echo "  make test-integration- Run all integration tests"
	@echo "  make test-all        - Run all tests (unit + integration)"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make docker-test-up  - Start test environment containers"
	@echo "  make docker-test-down- Stop test environment containers"
	@echo ""
	@echo "$(COLOR_YELLOW)Service Management:$(COLOR_RESET)"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - View all service logs"
	@echo "  make ps              - Show service status"
	@echo "  make health          - Check service health"
	@echo ""
	@echo "$(COLOR_YELLOW)Database Operations:$(COLOR_RESET)"
	@echo "  make db-test         - Test database connections"
	@echo "  make db-shell        - Open database shell"
	@echo "  make qdrant-shell    - Open Qdrant shell"
	@echo "  make neo4j-shell     - Open Neo4j shell"
	@echo ""
	@echo "$(COLOR_YELLOW)Development Tools:$(COLOR_RESET)"
	@echo "  make shell           - Open shell in MCP container"
	@echo "  make python          - Open Python REPL in MCP container"
	@echo "  make lint            - Run code linting"
	@echo "  make format          - Format code"
	@echo "  make type-check      - Run type checking"
	@echo "  make validate        - Run all validation checks"
	@echo ""
	@echo "$(COLOR_YELLOW)Utilities:$(COLOR_RESET)"
	@echo "  make clean           - Clean test artifacts and caches"
	@echo "  make clean-all       - Clean everything including volumes"
	@echo "  make env-check       - Validate environment variables"
	@echo "  make deps            - Install/update dependencies"
	@echo "  make build           - Build Docker images"

# Default commands
.DEFAULT_GOAL := help
test: test-unit

# Development Environment Commands
.PHONY: dev dev-bg dev-logs dev-down dev-restart dev-rebuild watch
.PHONY: dev-nobuild dev-bg-nobuild

dev: env-check
	@echo "$(COLOR_GREEN)Starting development environment with watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up --build --watch

dev-bg: env-check
	@echo "$(COLOR_GREEN)Starting development environment in background...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up -d --build
	@echo "$(COLOR_GREEN)Starting watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) watch

# Development without rebuilding images
dev-nobuild: env-check
	@echo "$(COLOR_GREEN)Starting development environment (no rebuild) with watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up --watch

dev-bg-nobuild: env-check
	@echo "$(COLOR_GREEN)Starting development environment in background (no rebuild)...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up -d --no-build
	@echo "$(COLOR_GREEN)Starting watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) watch

dev-logs:
	$(DOCKER_COMPOSE_DEV) logs -f mcp-crawl4ai

dev-down:
	@echo "$(COLOR_YELLOW)Stopping development environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) down

dev-restart:
	@echo "$(COLOR_YELLOW)Restarting development services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) restart mcp-crawl4ai

dev-rebuild:
	@echo "$(COLOR_YELLOW)Rebuilding development environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) down
	$(DOCKER_COMPOSE_DEV) build --no-cache
	$(MAKE) dev

watch:
	@echo "$(COLOR_GREEN)Starting Docker watch mode for development...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) watch

# Service Management Commands
.PHONY: up down restart logs ps health

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

restart:
	$(DOCKER_COMPOSE) restart

logs:
	$(DOCKER_COMPOSE) logs -f

ps:
	$(DOCKER_COMPOSE) ps

health:
	@echo "$(COLOR_GREEN)Checking service health...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

# Database Operations
.PHONY: db-test db-shell qdrant-shell neo4j-shell

db-test:
	@echo "$(COLOR_GREEN)Testing database connections...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) exec mcp-crawl4ai python -c "from utils import test_supabase_connection; test_supabase_connection()"

db-shell:
	@echo "$(COLOR_YELLOW)Choose database:$(COLOR_RESET)"
	@echo "1. Supabase (via Python)"
	@echo "2. Qdrant"
	@echo "3. Neo4j"
	@read -p "Enter choice (1-3): " choice; \
	case $$choice in \
		1) $(MAKE) python ;; \
		2) $(MAKE) qdrant-shell ;; \
		3) $(MAKE) neo4j-shell ;; \
		*) echo "Invalid choice" ;; \
	esac

qdrant-shell:
	@echo "$(COLOR_GREEN)Opening Qdrant dashboard at http://localhost:6333/dashboard$(COLOR_RESET)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:6333/dashboard || \
	command -v open >/dev/null 2>&1 && open http://localhost:6333/dashboard || \
	echo "Please open http://localhost:6333/dashboard in your browser"

neo4j-shell:
	@echo "$(COLOR_GREEN)Opening Neo4j browser at http://localhost:7474$(COLOR_RESET)"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:7474 || \
	command -v open >/dev/null 2>&1 && open http://localhost:7474 || \
	echo "Please open http://localhost:7474 in your browser"

# Development Tools
.PHONY: shell python dev-shell dev-python lint format type-check validate

shell:
	$(DOCKER_COMPOSE) exec mcp-crawl4ai /bin/bash

python:
	$(DOCKER_COMPOSE) exec mcp-crawl4ai python

# Development-specific versions
dev-shell:
	$(DOCKER_COMPOSE_DEV) exec mcp-crawl4ai /bin/bash

dev-python:
	$(DOCKER_COMPOSE_DEV) exec mcp-crawl4ai python

lint:
	@echo "$(COLOR_GREEN)Running code linting...$(COLOR_RESET)"
	$(PYTHON) -m ruff check src/ tests/

format:
	@echo "$(COLOR_GREEN)Formatting code...$(COLOR_RESET)"
	$(PYTHON) -m ruff format src/ tests/

type-check:
	@echo "$(COLOR_GREEN)Running type checking...$(COLOR_RESET)"
	$(PYTHON) -m mypy src/

validate: lint type-check test-unit
	@echo "$(COLOR_GREEN)All validation checks passed!$(COLOR_RESET)"

# Testing Commands

# Unit tests only (no external dependencies)
test-unit:
	@echo "$(COLOR_GREEN)Running unit tests...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -m "not integration"

# SearXNG integration tests
test-searxng: docker-test-up
	@echo "$(COLOR_YELLOW)Waiting for services to be ready...$(COLOR_RESET)"
	@sleep 10
	$(PYTEST) tests/ -v -m searxng

# All integration tests
test-integration: docker-test-up
	@echo "$(COLOR_YELLOW)Waiting for services to be ready...$(COLOR_RESET)"
	@sleep 10
	$(PYTEST) tests/ -v -m integration

# All tests
test-all: docker-test-up
	@echo "$(COLOR_YELLOW)Waiting for services to be ready...$(COLOR_RESET)"
	@sleep 10
	$(PYTEST) tests/ -v

# Test in watch mode
test-watch:
	@echo "$(COLOR_GREEN)Running tests in watch mode...$(COLOR_RESET)"
	$(PYTEST) tests/ -v --watch

# Test with coverage
test-coverage:
	@echo "$(COLOR_GREEN)Running tests with coverage...$(COLOR_RESET)"
	$(PYTEST) tests/ -v --cov=src --cov-report=html --cov-report=term

# Docker test environment management
docker-test-up:
	@echo "$(COLOR_GREEN)Starting test environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) up -d
	@echo "$(COLOR_YELLOW)Test environment started. Checking health...$(COLOR_RESET)"
	@$(DOCKER_COMPOSE_TEST) ps

docker-test-down:
	@echo "$(COLOR_YELLOW)Stopping test environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) down -v

# Build Commands
.PHONY: build build-no-cache

build:
	@echo "$(COLOR_GREEN)Building Docker images...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) build

build-no-cache:
	@echo "$(COLOR_GREEN)Building Docker images (no cache)...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) build --no-cache

# Utility Commands
.PHONY: clean clean-all env-check deps

clean:
	@echo "$(COLOR_YELLOW)Cleaning test artifacts...$(COLOR_RESET)"
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf qa-logs/*.log
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(COLOR_GREEN)Clean complete!$(COLOR_RESET)"

clean-all: clean
	@echo "$(COLOR_RED)Removing Docker volumes...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE_TEST) down -v
	@echo "$(COLOR_GREEN)Full clean complete!$(COLOR_RESET)"

env-check:
	@echo "$(COLOR_GREEN)Checking environment variables...$(COLOR_RESET)"
	@if [ ! -f .env ]; then \
		echo "$(COLOR_RED)ERROR: .env file not found!$(COLOR_RESET)"; \
		echo "$(COLOR_YELLOW)Creating from .env.example...$(COLOR_RESET)"; \
		cp .env.example .env 2>/dev/null || echo "$(COLOR_RED)ERROR: .env.example not found!$(COLOR_RESET)"; \
		exit 1; \
	fi
	@echo "$(COLOR_GREEN)Environment check passed!$(COLOR_RESET)"

deps:
	@echo "$(COLOR_GREEN)Installing/updating dependencies...$(COLOR_RESET)"
	@command -v uv >/dev/null 2>&1 || { echo "$(COLOR_YELLOW)Installing UV...$(COLOR_RESET)"; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv sync
	@echo "$(COLOR_GREEN)Dependencies updated!$(COLOR_RESET)"

# Quick commands for common tasks
.PHONY: quick-test quick-fix quick-check

quick-test: test-unit

quick-fix: format lint

quick-check: validate