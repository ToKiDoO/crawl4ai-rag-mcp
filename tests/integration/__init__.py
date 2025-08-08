"""
Integration tests for Crawl4AI MCP.

This package contains integration tests that use real services running in Docker containers
to validate the complete system behavior and performance characteristics.

Test Structure:
- conftest.py: Integration test fixtures and configuration
- test_e2e_workflows.py: End-to-end workflow tests for the complete RAG pipeline
- test_database_integration.py: Database integration tests with real Qdrant/Supabase
- test_performance_benchmarks.py: Performance and scalability benchmarks

Running Integration Tests:
```bash
# Start Docker services first
make dev

# Run all integration tests
pytest tests/integration/ -m integration

# Run specific test categories
pytest tests/integration/ -m e2e
pytest tests/integration/ -m performance

# Run with verbose output
pytest tests/integration/ -v -s

# Skip slow tests
pytest tests/integration/ -m "integration and not slow"
```

Requirements:
- Docker and Docker Compose must be available
- Services (Qdrant, SearXNG) must be running via `make dev`
- Sufficient system resources for concurrent operations
- Network access for downloading dependencies

Performance Targets:
- E2E workflow: < 20 seconds
- Single crawl: < 5 seconds
- Batch crawl (20 URLs): < 15 seconds
- Search latency: < 2 seconds
- Storage latency: < 1 second
- Throughput: > 2 URLs/sec crawling, > 5 searches/sec
"""
