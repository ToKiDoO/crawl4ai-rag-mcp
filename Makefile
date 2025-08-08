# Makefile for Crawl4AI MCP Server Development

# Variables
DOCKER_COMPOSE := docker compose
DOCKER_COMPOSE_PROD := $(DOCKER_COMPOSE) -f docker-compose.prod.yml
DOCKER_COMPOSE_DEV := $(DOCKER_COMPOSE) -f docker-compose.dev.yml
DOCKER_COMPOSE_TEST := $(DOCKER_COMPOSE) -f docker-compose.test.yml
PYTHON := uv run python
PYTEST := uv run pytest
RUFF := uv run ruff

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
	@echo "  make dev-logs-grep   - Check all containers for patterns (last 100 lines)"
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
	@echo "  make test-quick      - Run quick unit tests (core only) for rapid feedback"
	@echo "  make test-integration- Run all integration tests with Docker services"
	@echo "  make test-all        - Run all tests (unit + integration)"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make test-coverage-ci- Run comprehensive tests with coverage for CI"
	@echo "  make test-ci         - Run complete CI test suite"
	@echo "  make test-file FILE=<path> - Run tests for specific file"
	@echo "  make test-mark MARK=<marker> - Run tests with specific marker"
	@echo "  make test-watch      - Run tests in watch mode (development)"
	@echo "  make test-debug      - Run tests in debug mode with verbose output"
	@echo "  make test-pdb        - Run tests with PDB debugger"
	@echo ""
	@echo "$(COLOR_YELLOW)Test Environment:$(COLOR_RESET)"
	@echo "  make docker-test-up  - Start test environment containers"
	@echo "  make docker-test-up-wait - Start test environment and wait for readiness"
	@echo "  make docker-test-down- Stop test environment containers"
	@echo "  make docker-test-status - Show test environment status"
	@echo "  make docker-test-logs- Show test environment logs"
	@echo "  make test-db-connect - Test database connections"
	@echo "  make test-qdrant     - Test Qdrant integration specifically"
	@echo "  make test-neo4j      - Test Neo4j integration specifically"
	@echo ""
	@echo "$(COLOR_YELLOW)Production Environment:$(COLOR_RESET)"
	@echo "  make prod            - Start production environment"
	@echo "  make prod-down       - Stop production environment"
	@echo "  make prod-logs       - View production logs"
	@echo "  make prod-ps         - Show production service status"
	@echo ""
	@echo "$(COLOR_YELLOW)Service Management:$(COLOR_RESET)"
	@echo "  make up              - Start production services (alias for prod)"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart services"
	@echo "  make logs            - View service logs"
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
.PHONY: dev dev-bg dev-logs dev-logs-grep dev-down dev-restart dev-rebuild watch
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
	@echo "$(COLOR_GREEN)Starting development environment (no rebuild)...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up --no-build

dev-bg-nobuild: env-check
	@echo "$(COLOR_GREEN)Starting development environment in background (no rebuild)...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) up -d --no-build
	@echo "$(COLOR_GREEN)Starting watch mode...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_DEV) watch

dev-logs:
	$(DOCKER_COMPOSE_DEV) logs -f mcp-crawl4ai

dev-logs-grep:
	@echo "$(COLOR_GREEN)Checking logs across all containers...$(COLOR_RESET)"
	@PATTERN="$${PATTERN:-ERROR|WARNING|embedding|success}"; \
	echo "$(COLOR_YELLOW)Searching for pattern: $$PATTERN$(COLOR_RESET)"; \
	echo ""; \
	for container in mcp-crawl4ai-dev valkey-dev searxng-dev qdrant-dev neo4j-dev mailhog-dev; do \
		echo "$(COLOR_GREEN)=== $$container ===$(COLOR_RESET)"; \
		docker logs --tail=100 $$container 2>&1 | grep -E "$$PATTERN" || echo "$(COLOR_YELLOW)No matches found$(COLOR_RESET)"; \
		echo ""; \
	done

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

# Production Environment Commands
.PHONY: prod prod-down prod-logs prod-ps prod-restart

prod: env-check
	@echo "$(COLOR_GREEN)Starting production environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_PROD) up -d

prod-down:
	@echo "$(COLOR_YELLOW)Stopping production environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_PROD) down

prod-logs:
	$(DOCKER_COMPOSE_PROD) logs -f

prod-ps:
	$(DOCKER_COMPOSE_PROD) ps

prod-restart:
	@echo "$(COLOR_YELLOW)Restarting production services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_PROD) restart

# Service Management Commands (aliases for production)
.PHONY: up down restart logs ps health

up: prod

down:
	@echo "$(COLOR_YELLOW)Stopping all environments...$(COLOR_RESET)"
	-$(DOCKER_COMPOSE_PROD) down
	-$(DOCKER_COMPOSE_DEV) down
	-$(DOCKER_COMPOSE_TEST) down

restart:
	@echo "$(COLOR_YELLOW)Which environment to restart?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@read -p "Enter choice (1-2): " choice; \
	case $$choice in \
		1) $(MAKE) prod-restart ;; \
		2) $(MAKE) dev-restart ;; \
		*) echo "Invalid choice" ;; \
	esac

logs:
	@echo "$(COLOR_YELLOW)Which environment logs?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@echo "3. Test"
	@read -p "Enter choice (1-3): " choice; \
	case $$choice in \
		1) $(MAKE) prod-logs ;; \
		2) $(MAKE) dev-logs ;; \
		3) $(MAKE) docker-test-logs ;; \
		*) echo "Invalid choice" ;; \
	esac

ps:
	@echo "$(COLOR_GREEN)Service status across environments:$(COLOR_RESET)"
	@echo "\n$(COLOR_YELLOW)Production:$(COLOR_RESET)"
	-@$(DOCKER_COMPOSE_PROD) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
	@echo "\n$(COLOR_YELLOW)Development:$(COLOR_RESET)"
	-@$(DOCKER_COMPOSE_DEV) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
	@echo "\n$(COLOR_YELLOW)Test:$(COLOR_RESET)"
	-@$(DOCKER_COMPOSE_TEST) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

health:
	@echo "$(COLOR_GREEN)Checking service health...$(COLOR_RESET)"
	@echo "\n$(COLOR_YELLOW)Production:$(COLOR_RESET)"
	-@$(DOCKER_COMPOSE_PROD) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"
	@echo "\n$(COLOR_YELLOW)Development:$(COLOR_RESET)"
	-@$(DOCKER_COMPOSE_DEV) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

# Database Operations
.PHONY: db-test db-shell qdrant-shell neo4j-shell

db-test:
	@echo "$(COLOR_GREEN)Testing database connections...$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)Which environment?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@read -p "Enter choice (1-2): " choice; \
	case $$choice in \
		1) $(DOCKER_COMPOSE_PROD) exec mcp-crawl4ai python -c "from utils import test_supabase_connection; test_supabase_connection()" ;; \
		2) $(DOCKER_COMPOSE_DEV) exec mcp-crawl4ai python -c "from utils import test_supabase_connection; test_supabase_connection()" ;; \
		*) echo "Invalid choice" ;; \
	esac

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
	@echo "$(COLOR_YELLOW)Which environment?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@read -p "Enter choice (1-2): " choice; \
	case $$choice in \
		1) $(DOCKER_COMPOSE_PROD) exec mcp-crawl4ai /bin/bash ;; \
		2) $(DOCKER_COMPOSE_DEV) exec mcp-crawl4ai /bin/bash ;; \
		*) echo "Invalid choice" ;; \
	esac

python:
	@echo "$(COLOR_YELLOW)Which environment?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@read -p "Enter choice (1-2): " choice; \
	case $$choice in \
		1) $(DOCKER_COMPOSE_PROD) exec mcp-crawl4ai python ;; \
		2) $(DOCKER_COMPOSE_DEV) exec mcp-crawl4ai python ;; \
		*) echo "Invalid choice" ;; \
	esac

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

# Copy test environment configuration
.PHONY: test-env-setup
test-env-setup:
	@echo "$(COLOR_GREEN)Setting up test environment configuration...$(COLOR_RESET)"
	@if [ ! -f .env.test ]; then \
		echo "$(COLOR_RED)ERROR: .env.test file not found!$(COLOR_RESET)"; \
		exit 1; \
	fi
	@cp .env.test .env
	@echo "$(COLOR_GREEN)Test environment configuration ready!$(COLOR_RESET)"

# Unit tests only (no external dependencies)
test-unit: test-env-setup
	@echo "$(COLOR_GREEN)Running unit tests...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -m "not integration" --tb=short

# Quick unit test for rapid feedback
test-quick: test-env-setup
	@echo "$(COLOR_GREEN)Running quick unit tests (core only)...$(COLOR_RESET)"
	$(PYTEST) tests/test_utils_refactored.py tests/test_database_factory.py -v --tb=line

# SearXNG integration tests
test-searxng: docker-test-up-wait
	@echo "$(COLOR_GREEN)Running SearXNG integration tests...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -m searxng --tb=short
	@$(MAKE) docker-test-down

# All integration tests
test-integration: docker-test-up-wait
	@echo "$(COLOR_GREEN)Running integration tests...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -m integration --tb=short --maxfail=5
	@$(MAKE) docker-test-down

# All tests (unit + integration)
test-all: docker-test-up-wait
	@echo "$(COLOR_GREEN)Running all tests...$(COLOR_RESET)"
	$(PYTEST) tests/ -v --tb=short --maxfail=10
	@$(MAKE) docker-test-down

# Test specific file or pattern
test-file: test-env-setup
	@if [ -z "$(FILE)" ]; then \
		echo "$(COLOR_RED)Usage: make test-file FILE=tests/test_example.py$(COLOR_RESET)"; \
		exit 1; \
	fi
	@echo "$(COLOR_GREEN)Running tests for $(FILE)...$(COLOR_RESET)"
	$(PYTEST) $(FILE) -v --tb=short

# Test in watch mode (for development)
test-watch: test-env-setup
	@echo "$(COLOR_GREEN)Running tests in watch mode...$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)Note: This requires pytest-watch to be installed$(COLOR_RESET)"
	$(PYTEST) tests/ -v --tb=short -f

# Test with coverage report
test-coverage: test-env-setup
	@echo "$(COLOR_GREEN)Running tests with coverage...$(COLOR_RESET)"
	$(PYTEST) tests/ -v --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml --tb=short
	@echo "$(COLOR_GREEN)Coverage report generated in htmlcov/index.html$(COLOR_RESET)"

# Test with coverage for CI (includes integration)
test-coverage-ci: docker-test-up-wait
	@echo "$(COLOR_GREEN)Running all tests with coverage for CI...$(COLOR_RESET)"
	$(PYTEST) tests/ -v --cov=src --cov-report=xml --cov-report=term-missing --tb=short --maxfail=5
	@$(MAKE) docker-test-down

# Performance/benchmark tests
test-performance: docker-test-up-wait
	@echo "$(COLOR_GREEN)Running performance tests...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -m "performance" --tb=short || echo "No performance tests marked"
	@$(MAKE) docker-test-down

# Test with specific markers
test-mark: test-env-setup
	@if [ -z "$(MARK)" ]; then \
		echo "$(COLOR_RED)Usage: make test-mark MARK=unit$(COLOR_RESET)"; \
		echo "Available marks: unit, integration, searxng, performance"; \
		exit 1; \
	fi
	@echo "$(COLOR_GREEN)Running tests with marker: $(MARK)...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -m "$(MARK)" --tb=short

# Docker test environment management with proper waiting
docker-test-up:
	@echo "$(COLOR_GREEN)Starting test environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) up -d --remove-orphans
	@echo "$(COLOR_GREEN)Test environment containers started!$(COLOR_RESET)"

docker-test-up-wait: docker-test-up
	@echo "$(COLOR_YELLOW)Waiting for services to be ready...$(COLOR_RESET)"
	@sleep 5
	@echo "$(COLOR_GREEN)Checking service health...$(COLOR_RESET)"
	@for i in {1..12}; do \
		if $(DOCKER_COMPOSE_TEST) ps --filter "status=running" | grep -q "healthy\|Up"; then \
			echo "$(COLOR_GREEN)Services are ready!$(COLOR_RESET)"; \
			break; \
		fi; \
		echo "$(COLOR_YELLOW)Waiting for services... ($$i/12)$(COLOR_RESET)"; \
		sleep 5; \
	done
	@$(DOCKER_COMPOSE_TEST) ps
	@echo "$(COLOR_GREEN)Service health check complete!$(COLOR_RESET)"

docker-test-down:
	@echo "$(COLOR_YELLOW)Stopping test environment...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) down -v --remove-orphans
	@echo "$(COLOR_GREEN)Test environment stopped and cleaned!$(COLOR_RESET)"

# Test environment status and logs
docker-test-status:
	@echo "$(COLOR_GREEN)Test environment status:$(COLOR_RESET)"
	@$(DOCKER_COMPOSE_TEST) ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

docker-test-logs:
	@echo "$(COLOR_GREEN)Test environment logs:$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) logs --tail=20

docker-test-logs-follow:
	@echo "$(COLOR_GREEN)Following test environment logs...$(COLOR_RESET)"
	$(DOCKER_COMPOSE_TEST) logs -f

# Test database operations
test-db-connect:
	@echo "$(COLOR_GREEN)Testing database connections...$(COLOR_RESET)"
	@echo "Testing Qdrant connection..."
	@curl -f http://localhost:6333/readyz 2>/dev/null && echo "✅ Qdrant is ready" || echo "❌ Qdrant is not ready"
	@echo "Testing Neo4j connection..."
	@docker exec neo4j_test cypher-shell -u neo4j -p testpassword123 "RETURN 1" 2>/dev/null && echo "✅ Neo4j is ready" || echo "❌ Neo4j is not ready"

# Integration test for specific services
test-qdrant: docker-test-up-wait
	@echo "$(COLOR_GREEN)Testing Qdrant integration...$(COLOR_RESET)"
	$(PYTEST) tests/test_qdrant_adapter.py -v --tb=short
	@$(MAKE) docker-test-down

test-neo4j: docker-test-up-wait
	@echo "$(COLOR_GREEN)Testing Neo4j integration...$(COLOR_RESET)"
	$(PYTEST) tests/ -k "neo4j" -v --tb=short
	@$(MAKE) docker-test-down

# Comprehensive test suite (mimics CI)
test-ci: lint
	@echo "$(COLOR_GREEN)Running CI test suite...$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)Step 1: Linting and formatting check$(COLOR_RESET)"
	$(RUFF) format src/ tests/ --check
	@echo "$(COLOR_YELLOW)Step 2: Running unit tests with coverage$(COLOR_RESET)"
	$(PYTEST) tests/ -v --tb=short --cov=src --cov-report=json --cov-report=term-missing -m "not integration" --maxfail=10
	@echo "$(COLOR_YELLOW)Step 3: Checking coverage threshold (80%)$(COLOR_RESET)"
	@python -c "import json; cov=json.load(open('coverage.json'))['totals']['percent_covered']; print(f'Coverage: {cov:.2f}%'); exit(0 if cov >= 80 else 1)"
	@echo "$(COLOR_GREEN)CI test suite completed successfully!$(COLOR_RESET)"

# CI lint command (matches GitHub Actions)
ci-lint:
	@echo "$(COLOR_GREEN)Running CI linting checks...$(COLOR_RESET)"
	$(RUFF) check src/ tests/ --output-format=github
	$(RUFF) format src/ tests/ --check
	@$(MAKE) test-unit
	@$(MAKE) test-coverage-ci
	@echo "$(COLOR_GREEN)✅ All tests completed successfully!$(COLOR_RESET)"

# Test debugging utilities
test-debug: test-env-setup
	@echo "$(COLOR_GREEN)Running tests in debug mode...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -s --tb=long --log-cli-level=DEBUG

test-pdb: test-env-setup
	@echo "$(COLOR_GREEN)Running tests with PDB debugger...$(COLOR_RESET)"
	$(PYTEST) tests/ -v -s --pdb --tb=short

# Build Commands
.PHONY: build build-no-cache

build:
	@echo "$(COLOR_GREEN)Building Docker images...$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)Which environment?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@echo "3. Test"
	@echo "4. All"
	@read -p "Enter choice (1-4): " choice; \
	case $$choice in \
		1) $(DOCKER_COMPOSE_PROD) build ;; \
		2) $(DOCKER_COMPOSE_DEV) build ;; \
		3) $(DOCKER_COMPOSE_TEST) build ;; \
		4) $(DOCKER_COMPOSE_PROD) build && $(DOCKER_COMPOSE_DEV) build && $(DOCKER_COMPOSE_TEST) build ;; \
		*) echo "Invalid choice" ;; \
	esac

build-no-cache:
	@echo "$(COLOR_GREEN)Building Docker images (no cache)...$(COLOR_RESET)"
	@echo "$(COLOR_YELLOW)Which environment?$(COLOR_RESET)"
	@echo "1. Production"
	@echo "2. Development"
	@echo "3. Test"
	@echo "4. All"
	@read -p "Enter choice (1-4): " choice; \
	case $$choice in \
		1) $(DOCKER_COMPOSE_PROD) build --no-cache ;; \
		2) $(DOCKER_COMPOSE_DEV) build --no-cache ;; \
		3) $(DOCKER_COMPOSE_TEST) build --no-cache ;; \
		4) $(DOCKER_COMPOSE_PROD) build --no-cache && $(DOCKER_COMPOSE_DEV) build --no-cache && $(DOCKER_COMPOSE_TEST) build --no-cache ;; \
		*) echo "Invalid choice" ;; \
	esac

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
	-$(DOCKER_COMPOSE_PROD) down -v
	-$(DOCKER_COMPOSE_DEV) down -v
	-$(DOCKER_COMPOSE_TEST) down -v
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