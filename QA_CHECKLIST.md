# QA Quick Reference

This document provides quick access to all QA and testing procedures. For detailed instructions, see the linked documentation.

## 🚀 Quick Start

```bash
# Start development environment with all services
make dev-bg

# Run unit tests
make test-unit

# Run all tests
make test-all

# View logs
make dev-logs
```

## 📋 Pre-Release Testing

**Full Plan**: [MCP Tools Testing Plan](docs/QA/MCP_TOOLS_TESTING_PLAN.md)

### Quick Checklist

- [ ] All services healthy (`make ps`)
- [ ] Unit tests passing (`make test-unit`)
- [ ] Integration tests passing (`make test-integration`)
- [ ] MCP tools validated (see plan above)
- [ ] Performance benchmarks met (`make test-performance`)

## 🧪 Test Types

### Unit Testing

**Plan**: [Unit Testing Plan](docs/QA/UNIT_TESTING_PLAN.md)

```bash
make test-unit         # Run unit tests only
make test-quick        # Quick core tests
make test-coverage     # With coverage report
```

### Integration Testing

```bash
make test-integration  # Run integration tests
make test-qdrant      # Test Qdrant specifically
make test-neo4j       # Test Neo4j specifically
make test-searxng     # Test SearXNG specifically
```

### Full Test Suite

```bash
make test-all         # All tests (unit + integration)
make test-ci          # Complete CI test suite
make test-coverage-ci # CI with coverage
```

## 🐳 Environment Management

### Development

```bash
make dev-bg           # Start dev environment (background)
make dev              # Start dev environment (foreground)
make dev-logs         # View dev logs
make dev-down         # Stop dev environment
make dev-restart      # Restart dev services
```

### Production

```bash
make prod             # Start production
make prod-logs        # View production logs
make prod-down        # Stop production
make prod-restart     # Restart production
```

### Test Environment

```bash
make docker-test-up   # Start test containers
make docker-test-down # Stop test containers
make test-db-connect  # Test database connections
```

## 📊 Service Health Checks

```bash
# Check all services status
make ps

# Check service health
make health

# Test specific connections
curl http://localhost:6333/       # Qdrant
curl http://localhost:7474/       # Neo4j
```

## 📝 Test Results

Test results should be saved to: `tests/results/`

Format: `YYYYMMDD_HHMM-MCP_TOOLS_TESTING.md`

## 🔍 Debugging

```bash
make logs             # Choose environment for logs
make shell            # Open shell in container
make python           # Open Python REPL in container
```

## 📚 Additional Documentation

- [QA Process](docs/QA/QA_PROCESS.md)
- [MCP Testing Guide](docs/QA/MCP_TESTING.md)
- [Test Environment Setup](docs/QA/TEST_ENVIRONMENT_SETUP.md)
- [Test and QA Plan](docs/QA/TEST_AND_QA_PLAN.md)

## ⚠️ Important Notes

1. **Always use Makefile commands** - Do not use `docker compose` directly
2. **Check `.env` file** - Ensure all required environment variables are set
3. **Run tests before commits** - Use `make test-unit` at minimum
4. **Document test results** - Save results in `tests/results/`
5. **Monitor resource usage** - Docker containers can consume significant memory

## 🆘 Troubleshooting

If tests fail:

1. Check logs: `make logs`
2. Verify services: `make ps`
3. Restart services: `make restart`
4. Clean and rebuild: `make clean-all && make dev-rebuild`

For more help, see [Troubleshooting Guide](docs/TROUBLESHOOTING_GUIDE.md)
