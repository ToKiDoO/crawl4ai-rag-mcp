# Development Environment with Docker Watch

This guide provides a comprehensive overview of the Crawl4AI MCP Server development environment, focusing on Docker watch capabilities for efficient development workflows.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Docker Watch Configuration](#docker-watch-configuration)
4. [Development Workflow](#development-workflow)
5. [Service Architecture](#service-architecture)
6. [Environment Configuration](#environment-configuration)
7. [Development Commands](#development-commands)
8. [Testing](#testing)
9. [Debugging](#debugging)
10. [Best Practices](#best-practices)

## Overview

The Crawl4AI MCP Server uses a dual Docker Compose configuration for clear separation between production and development environments. The development setup (`docker-compose.dev.yml`) extends the base configuration with hot-reloading capabilities, enabling immediate reflection of code changes without rebuilding containers.

### Key Features

- **Hot Reloading**: Automatic service restart on code changes with comprehensive ignore patterns
- **Multi-Service Stack**: Integrated development with SearXNG, Valkey, Qdrant, and Neo4j (all enabled by default)
- **Isolated Environment**: All dependencies containerized for consistency
- **Development Tools**: Built-in health checks, logging, debugging capabilities, and shell access

## Prerequisites

### Required Software

- Docker Desktop 4.27+ or Docker Engine 24.0+ with Docker Compose v2.23+
- Git for version control
- A code editor (VS Code recommended)
- Python 3.12+ (optional, for local testing)

### System Requirements

- 8GB RAM minimum (16GB recommended)
- 10GB free disk space
- Windows 10/11, macOS 10.15+, or Linux

## Docker Watch Configuration

The development environment leverages Docker Compose's watch feature with comprehensive monitoring and ignore patterns. All watch configuration is defined in `docker-compose.dev.yml` (not in the production `docker-compose.yml`):

```yaml
develop:
  watch:
    # Source code changes trigger sync+restart
    - action: sync+restart
      path: ./src
      target: /app/src
      ignore:
        - __pycache__/
        - "*.pyc"
        - "*.pyo"
        - "*.pyd"
        - .Python
        - "*.so"
        - .pytest_cache/
        - .mypy_cache/
        - .ruff_cache/
        - .coverage
        - "*.egg-info/"
        - .git/
        - .venv/
        - venv/
        - .DS_Store
        - "*.swp"
        - "*.swo"
        - "*~"
    
    # Dependency changes trigger full rebuild
    - action: rebuild
      path: ./pyproject.toml
    
    # Test changes sync without restart
    - action: sync
      path: ./tests
      target: /app/tests
      ignore:
        - __pycache__/
        - "*.pyc"
        - .pytest_cache/
        - .coverage
        - htmlcov/
        - "*.swp"
```

### How It Works

1. Developer modifies a file in `./src`
2. Docker detects the change via filesystem events
3. Changed files are synchronized to the container (ignoring cache files)
4. Container process is restarted automatically
5. New code is live within seconds

### Watch Configuration Details

- **Source Code** (`./src`): Monitors Python files with sync+restart action
- **Dependencies** (`./pyproject.toml`): Triggers container rebuild for dependency changes
- **Tests** (`./tests`): Syncs test files without restarting the main service
- **Comprehensive Ignore**: Skips cache files, compiled Python, IDE temp files, and virtual environments

## Development Workflow

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/crawl4ai-mcp.git
   cd crawl4ai-mcp
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Check for existing services**:
   ```bash
   # Check if any services are already running
   docker compose ps
   
   # If services are running, stop them first
   make dev-down
   ```

4. **Start development environment**:
   ```bash
   # Start in background with watch mode
   make dev-bg
   ```

### Daily Development

1. **Start your development session**:
   ```bash
   # Start services in background with watch mode
   make dev-bg
   
   # View logs in a separate terminal
   make dev-logs
   ```

2. **Make code changes**:
   - Edit files in `./src` directory
   - Save changes
   - Watch logs for restart confirmation
   - Changes to `./tests` sync without restart

3. **Test your changes**:
   - Use MCP client to test new functionality
   - Check service health: `make health`
   - Run tests: `make test`

4. **Development tools**:
   ```bash
   # Open shell in development container
   make dev-shell
   
   # Open Python REPL in development container
   make dev-python
   ```

5. **Stop development**:
   ```bash
   make dev-down
   ```

## Service Architecture

### Core Services

#### MCP Server (mcp-crawl4ai)
- **Purpose**: Main application server implementing MCP protocol
- **Port**: 8051
- **Watch Path**: `./src` (sync+restart), `./tests` (sync only)
- **Dependencies**: SearXNG, Valkey, Qdrant, Neo4j

#### SearXNG
- **Purpose**: Privacy-respecting metasearch engine
- **Port**: 8080 (localhost only)
- **Configuration**: `./searxng/settings.yml` with development overrides

#### Valkey
- **Purpose**: Redis-compatible caching layer
- **Port**: 6379 (exposed in dev for debugging)
- **Persistence**: 30-second snapshots with debug logging

### Default Services (Always Enabled in Development)

#### Qdrant
- **Purpose**: Vector database for embeddings
- **Ports**: 6333 (HTTP), 6334 (gRPC)
- **Dashboard**: http://localhost:6333/dashboard
- **Status**: Enabled by default in development

#### Neo4j
- **Purpose**: Graph database for knowledge graphs
- **Ports**: 7474 (HTTP), 7687 (Bolt)
- **Browser**: http://localhost:7474
- **Status**: Enabled by default in development

## Environment Configuration

### Essential Variables

```bash
# API Keys
OPENAI_API_KEY=your-openai-key
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key

# Server Configuration
TRANSPORT=sse
HOST=0.0.0.0
PORT=8051

# Service URLs
SEARXNG_URL=http://searxng:8080

# Vector Database Configuration
VECTOR_DATABASE=supabase  # or 'qdrant'
QDRANT_URL=http://qdrant:6333

# Graph Database Configuration
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

### Development-Specific Settings

```bash
# Enable debug logging
DEBUG=true
LOG_LEVEL=DEBUG

# FastMCP development mode
FASTMCP_DEV_MODE=true

# RAG Strategy Flags
ENHANCED_CONTEXT=true
USE_RERANKING=true
ENABLE_AGENTIC_RAG=true
ENABLE_HYBRID_SEARCH=true
```

## Development Commands

### Primary Development Commands

```bash
# Start development environment in background
make dev-bg

# View development logs (use in separate terminal)
make dev-logs

# Stop development environment
make dev-down

# Restart development services
make dev-restart

# Rebuild development environment
make dev-rebuild

# Open shell in development container
make dev-shell

# Open Python REPL in development container
make dev-python
```

### Development Tools

```bash
# Open shell in development container
make dev-shell

# Open Python REPL in development container
make dev-python

# Start only Docker watch mode (if services already running)
make watch
```

### Service Management

```bash
# Check service health and status
make health

# View all service logs
make logs

# Show service status
make ps

# Restart specific service
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart mcp-crawl4ai
```

### Testing Commands

```bash
# Run unit tests
make test-unit

# Run integration tests (starts test containers)
make test-integration

# Run all tests
make test-all

# Test with coverage report
make test-coverage

# Clean test artifacts
make clean
```

### Database Operations

```bash
# Test database connections
make db-test

# Open Qdrant dashboard
make qdrant-shell

# Open Neo4j browser
make neo4j-shell

# Interactive database shell menu
make db-shell
```

## Testing

### Test Structure

```
tests/
├── test_unit/           # Unit tests (no external deps)
├── test_integration/    # Integration tests
├── test_searxng/       # SearXNG-specific tests
└── conftest.py         # Pytest configuration
```

### Running Tests

1. **Unit Tests** (fast, no dependencies):
   ```bash
   make test-unit
   ```

2. **Integration Tests** (requires services):
   ```bash
   make test-integration
   ```

3. **Watch Mode Testing**:
   ```bash
   # In one terminal
   make dev
   
   # In another terminal
   make test-watch
   ```

### Writing Tests

Example test with Docker environment:

```python
import pytest
from testcontainers.compose import DockerCompose

@pytest.fixture(scope="session")
def docker_services():
    with DockerCompose(".", compose_file_name="docker-compose.test.yml") as compose:
        compose.wait_for("http://localhost:8051/health")
        yield compose

def test_mcp_server_health(docker_services):
    response = requests.get("http://localhost:8051/health")
    assert response.status_code == 200
```

## Debugging

### Viewing Logs

```bash
# Development logs (specific to dev environment)
make dev-logs

# All services
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f mcp-crawl4ai

# Last 100 lines with timestamps
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=100 -t mcp-crawl4ai
```

### Common Issues and Solutions

1. **Service won't start**:
   ```bash
   # Check service health
   make health
   
   # View detailed errors
   make dev-logs
   
   # Check port conflicts
   lsof -i :8051 -i :6333 -i :7474
   ```

2. **Code changes not reflecting**:
   ```bash
   # Ensure development compose is running
   make ps
   
   # Check if watch mode is active
   make watch
   
   # Force restart
   make dev-restart
   ```

3. **Database connection issues**:
   ```bash
   # Test connections
   make db-test
   
   # Check Qdrant dashboard
   make qdrant-shell
   
   # Check Neo4j browser
   make neo4j-shell
   ```

### Interactive Debugging

1. **Shell access** (development container):
   ```bash
   make dev-shell
   ```

2. **Python REPL** (development container):
   ```bash
   make dev-python
   ```

3. **IPython with auto-reload**:
   ```python
   # In development container shell
   pip install ipython
   ipython
   
   # In IPython
   %load_ext autoreload
   %autoreload 2
   from crawl4ai_mcp import *
   ```

## Best Practices

### Code Organization

1. **Modular Structure**:
   - Keep MCP tools in `crawl4ai_mcp.py`
   - Database operations in `utils.py`
   - Service-specific code in subdirectories

2. **Async Patterns**:
   ```python
   @mcp.tool()
   async def my_tool(param: str) -> str:
       """Tool description"""
       async with AsyncWebCrawler() as crawler:
           result = await crawler.arun(url=param)
       return result
   ```

3. **Error Handling**:
   ```python
   try:
       result = await operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}")
       return f"Error: {str(e)}"
   ```

### Development Tips

1. **Use Type Hints**:
   ```python
   from typing import List, Dict, Optional
   
   async def search_pages(query: str, limit: int = 10) -> List[Dict[str, any]]:
       """Search with proper typing"""
   ```

2. **Environment-Based Configuration**:
   ```python
   DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
   if DEBUG:
       logger.setLevel(logging.DEBUG)
   ```

3. **Health Checks**:
   ```python
   @mcp.tool()
   async def health_check() -> Dict[str, any]:
       """Check service health"""
       return {
           "status": "healthy",
           "services": await check_all_services()
       }
   ```

### Performance Optimization

1. **Batch Operations**:
   ```python
   # Good: Batch embedding generation
   embeddings = await generate_embeddings(texts)
   
   # Avoid: Individual embedding calls
   for text in texts:
       embedding = await generate_embedding(text)
   ```

2. **Connection Pooling**:
   ```python
   # Reuse client instances
   if not hasattr(search_crawled_pages, '_client'):
       search_crawled_pages._client = get_supabase_client()
   ```

3. **Async Context Managers**:
   ```python
   async with AsyncWebCrawler() as crawler:
       # Crawler is properly initialized and cleaned up
       results = await crawler.arun_many(urls)
   ```

### Docker Best Practices

1. **Development vs Production Separation**:
   - Base `docker-compose.yml` for production
   - `docker-compose.dev.yml` for development overrides
   - Clear separation of concerns

2. **Resource Management**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         cpus: '1'
         memory: 1G
   ```

3. **Security**:
   - Expose ports only in development
   - Use environment variables for secrets
   - Enable debugging features only in development

## Troubleshooting Checklist

- [ ] Check all required environment variables are set: `make env-check`
- [ ] Verify Docker Compose version: `docker compose version`
- [ ] Ensure ports are not already in use: `lsof -i :8051 -i :6333 -i :7474`
- [ ] Check service health: `make health`
- [ ] Review logs for errors: `make dev-logs`
- [ ] Test database connectivity: `make db-test`
- [ ] Verify file permissions on mounted volumes
- [ ] Check available disk space: `df -h`
- [ ] Ensure development compose files are used: `make dev-bg`

## Additional Resources

- [Docker Compose Watch Documentation](https://docs.docker.com/compose/file-watch/)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Crawl4AI Documentation](https://crawl4ai.com/docs/)
- [Project README](../README.md)
- [Development Quick Start Guide](./DEVELOPMENT_QUICKSTART.md)