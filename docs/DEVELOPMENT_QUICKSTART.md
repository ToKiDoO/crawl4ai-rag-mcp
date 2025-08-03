# Development Environment Quick Start

This guide helps you get the Crawl4AI MCP Server development environment running quickly.

## Prerequisites

- Docker Desktop 4.27+ or Docker Engine 24.0+ with Docker Compose v2.23+
- Git
- 8GB RAM minimum (16GB recommended)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/crawl4ai-mcp.git
cd crawl4ai-mcp

# Copy environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your-key-here
```

### 2. Check for Running Services

```bash
# Check if services are already running
docker compose ps

# If services are running, stop them first
make dev-down
```

### 3. Start Development Environment

```bash
# Start services in background with watch mode
make dev-bg

# This runs services detached and starts watch mode separately,
# keeping your terminal free for other commands
```

This starts:
- MCP Server with hot-reload
- SearXNG (privacy-focused search)
- Valkey (Redis-compatible cache)
- Qdrant (vector database)
- Neo4j (knowledge graph)

### 4. Verify Services

```bash
# Check service health
make health

# View logs in a separate terminal
make dev-logs

# Access dashboards:
# - Qdrant: http://localhost:6333/dashboard
# - Neo4j: http://localhost:7474
# - SearXNG: http://localhost:8080
```

## Development Workflow

### Making Code Changes

1. Edit files in `./src` - changes auto-reload
2. View logs to confirm reload: `make dev-logs`
3. Test your changes with MCP client

### Common Commands

```bash
# Development
make dev-bg        # Start in background with watch
make dev-logs      # View logs (use in separate terminal)
make dev-restart   # Restart services
make dev-down      # Stop everything
make dev-shell     # Open shell in dev container
make dev-python    # Open Python REPL in dev container

# Testing
make test          # Run unit tests
make test-all      # Run all tests
make test-coverage # Generate coverage report

# Database
make db-test       # Test connections
make shell         # Container shell (production)
make python        # Python REPL (production)

# Utilities
make clean         # Clean artifacts
make validate      # Run all checks
```

### Testing Your Changes

1. **Unit Tests**: `make test-unit`
2. **Integration Tests**: `make test-integration`
3. **Manual Testing**: Use Claude Desktop or mcp-cli

### Docker Watch Mode

The development environment uses Docker's watch feature:
- Changes to `./src` automatically restart the MCP server
- Changes to `./pyproject.toml` trigger a rebuild
- Changes to `./tests` sync without restarting
- Comprehensive ignore patterns for cache files and temp files
- No need to manually rebuild for Python code changes

### Debugging

```bash
# Interactive shell in dev container
make dev-shell

# Python REPL in dev container
make dev-python

# Check specific service
docker compose logs -f qdrant

# Stop watch mode if running
# Press Ctrl+C in the terminal where watch is running
```

## Project Structure

```
crawl4ai-mcp/
├── src/                    # Source code (hot-reloaded)
│   ├── crawl4ai_mcp.py    # Main MCP server
│   ├── utils.py           # Utilities
│   └── database/          # Database adapters
├── docker-compose.yml      # Production config
├── docker-compose.dev.yml  # Development overrides
├── Makefile               # Development commands
└── .env.example           # Environment template
```

## Next Steps

- Read the full [Development Environment Guide](./DEVELOPMENT_ENVIRONMENT.md)
- Check [CLAUDE.md](../CLAUDE.md) for AI assistant guidelines
- Review [QA_PROCESS.md](../QA_PROCESS.md) for testing procedures

## Troubleshooting

### Services won't start
```bash
# Check port conflicts
lsof -i :8051 -i :6333 -i :7474

# Clean restart
make clean-all
make dev
```

### Code changes not reflecting
```bash
# Ensure watch is running
docker compose ps  # Should show "running"

# Force restart
make dev-restart
```

### Database connection errors
```bash
# Test connections
make db-test

# Check environment
docker compose exec mcp-crawl4ai env | grep -E "(QDRANT|NEO4J)"
```