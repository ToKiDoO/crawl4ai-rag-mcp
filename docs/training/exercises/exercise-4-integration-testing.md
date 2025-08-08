# Exercise 4: Integration Testing with Docker Services

**Duration**: 90 minutes  
**Difficulty**: Advanced  
**Prerequisites**: Docker, Docker Compose, completion of Exercises 1-3, understanding of containerized applications

## Learning Objectives

After completing this exercise, you will be able to:

- Set up integration test environments with Docker Compose
- Test real service interactions (databases, APIs, message queues)
- Manage test data lifecycle in containerized environments
- Handle service dependencies and startup ordering
- Implement health checks and service discovery patterns
- Debug integration test failures effectively
- Use test containers for isolated testing

## Exercise Overview

You'll create comprehensive integration tests that verify the Crawl4AI MCP server works correctly with real Docker services. This includes testing with Qdrant vector database, caching layers, and external APIs.

## Part 1: Docker Test Environment Setup (25 minutes)

### Task 4.1: Create Docker test environment

Create `exercises/docker-compose.test.yml`:

```yaml
version: '3.8'

services:
  # Vector Database for testing
  qdrant-test:
    image: qdrant/qdrant:v1.7.4
    ports:
      - "6333:6333"
      - "6334:6334"
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
      - QDRANT__LOG_LEVEL=INFO
    volumes:
      - qdrant_test_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 5s
      timeout: 3s
      retries: 5
      start_period: 10s

  # Redis cache for testing
  redis-test:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Test database (PostgreSQL for comparison)
  postgres-test:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=test_crawl4ai
      - POSTGRES_USER=test_user
      - POSTGRES_PASSWORD=test_password
    volumes:
      - postgres_test_data:/var/lib/postgresql/data
      - ./exercises/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user -d test_crawl4ai"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Mock API server for testing external integrations
  mock-api:
    image: wiremock/wiremock:2.35.0
    ports:
      - "8080:8080"
    volumes:
      - ./exercises/wiremock:/home/wiremock
    command: ["--global-response-templating", "--verbose"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/__admin/health"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Test runner service
  test-runner:
    build:
      context: .
      dockerfile: exercises/Dockerfile.test
    depends_on:
      qdrant-test:
        condition: service_healthy
      redis-test:
        condition: service_healthy
      postgres-test:
        condition: service_healthy
      mock-api:
        condition: service_healthy
    environment:
      - QDRANT_URL=http://qdrant-test:6333
      - REDIS_URL=redis://redis-test:6379
      - POSTGRES_URL=postgresql://test_user:test_password@postgres-test:5432/test_crawl4ai
      - MOCK_API_URL=http://mock-api:8080
      - OPENAI_API_KEY=test-key-mock
      - PYTHONPATH=/app
    volumes:
      - .:/app
      - /app/exercises/.pytest_cache
    working_dir: /app
    command: ["python", "-m", "pytest", "exercises/test_integration.py", "-v"]

volumes:
  qdrant_test_data:
  postgres_test_data:
```

### Task 4.2: Create test Dockerfile

Create `exercises/Dockerfile.test`:

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv
RUN uv sync --frozen

# Copy application code
COPY . /app
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Default command
CMD ["python", "-m", "pytest", "exercises/", "-v"]
```

### Task 4.3: Create database initialization script

Create `exercises/sql/init.sql`:

```sql
-- Initialize test database schema
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table for document metadata
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for embeddings (if using PostgreSQL with pgvector)
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    embedding vector(1536),  -- OpenAI embedding dimension
    model_name TEXT NOT NULL DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_documents_url ON documents(url);
CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_embeddings_doc_id ON embeddings(document_id);

-- Test data
INSERT INTO documents (url, title, content, content_hash) VALUES
('https://test.com/doc1', 'Test Document 1', 'This is test content for document 1', md5('This is test content for document 1')),
('https://test.com/doc2', 'Test Document 2', 'This is test content for document 2', md5('This is test content for document 2')),
('https://test.com/doc3', 'Test Document 3', 'This is test content for document 3', md5('This is test content for document 3'));
```

### Task 4.4: Create WireMock API stubs

Create `exercises/wiremock/mappings/openai-embeddings.json`:

```json
{
  "request": {
    "method": "POST",
    "url": "/v1/embeddings",
    "headers": {
      "Authorization": {
        "matches": "Bearer .*"
      },
      "Content-Type": {
        "equalTo": "application/json"
      }
    }
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "jsonBody": {
      "object": "list",
      "data": [
        {
          "object": "embedding",
          "embedding": "{{range 0 1536}}{{random type='FLOAT' min=-1.0 max=1.0}}{{#unless @last}},{{/unless}}{{/range}}",
          "index": 0
        }
      ],
      "model": "text-embedding-ada-002",
      "usage": {
        "prompt_tokens": "{{jsonPath request.body '$.input.length'}}",
        "total_tokens": "{{jsonPath request.body '$.input.length'}}"
      }
    }
  }
}
```

Create `exercises/wiremock/mappings/search-api.json`:

```json
{
  "request": {
    "method": "GET",
    "urlPattern": "/search\\?.*"
  },
  "response": {
    "status": 200,
    "headers": {
      "Content-Type": "application/json"
    },
    "jsonBody": {
      "results": [
        {
          "title": "Mock Search Result 1",
          "url": "https://example.com/result1",
          "snippet": "This is a mock search result for testing purposes"
        },
        {
          "title": "Mock Search Result 2", 
          "url": "https://example.com/result2",
          "snippet": "Another mock search result with different content"
        }
      ],
      "total": 2,
      "query": "{{request.query.q}}"
    }
  }
}
```

## Part 2: Integration Test Implementation (25 minutes)

### Task 4.5: Create integration test framework

Create `exercises/integration_test_framework.py`:

```python
import asyncio
import time
import httpx
import psycopg2
import redis
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for external services"""
    qdrant_url: str
    redis_url: str
    postgres_url: str
    mock_api_url: str
    
class IntegrationTestManager:
    """Manage integration test environment and data lifecycle"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.test_collections = []
        self.test_documents = []
        self.redis_client = None
        self.postgres_conn = None
        
    async def wait_for_services(self, timeout: int = 60):
        """Wait for all services to be ready"""
        start_time = time.time()
        
        services = {
            'Qdrant': f"{self.config.qdrant_url}/health",
            'MockAPI': f"{self.config.mock_api_url}/__admin/health",
        }
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                all_ready = True
                
                for service_name, health_url in services.items():
                    try:
                        response = await client.get(health_url, timeout=5.0)
                        if response.status_code != 200:
                            all_ready = False
                            logger.info(f"Waiting for {service_name}...")
                    except Exception as e:
                        all_ready = False
                        logger.info(f"Waiting for {service_name}: {e}")
                
                # Check Redis
                try:
                    redis_client = redis.from_url(self.config.redis_url)
                    redis_client.ping()
                except Exception:
                    all_ready = False
                    logger.info("Waiting for Redis...")
                
                # Check PostgreSQL
                try:
                    conn = psycopg2.connect(self.config.postgres_url)
                    conn.close()
                except Exception:
                    all_ready = False
                    logger.info("Waiting for PostgreSQL...")
                
                if all_ready:
                    logger.info("All services are ready!")
                    return
                
                await asyncio.sleep(2)
        
        raise TimeoutError(f"Services not ready after {timeout} seconds")
    
    async def setup_test_data(self):
        """Set up test data in all services"""
        # TODO: Implement test data setup
        # 1. Create test collection in Qdrant
        # 2. Set up Redis test keys
        # 3. Insert test documents if needed
        pass
    
    async def cleanup_test_data(self):
        """Clean up all test data"""
        # TODO: Implement cleanup
        # 1. Delete Qdrant collections
        # 2. Clear Redis keys
        # 3. Clean up database records
        pass
    
    @asynccontextmanager
    async def test_environment(self):
        """Context manager for test environment lifecycle"""
        try:
            await self.wait_for_services()
            await self.setup_test_data()
            yield self
        finally:
            await self.cleanup_test_data()

class QdrantTestClient:
    """Test client for Qdrant operations"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def create_test_collection(self, collection_name: str) -> str:
        """Create a test collection"""
        # TODO: Implement Qdrant collection creation
        # Use httpx to make REST API calls to Qdrant
        pass
    
    async def store_test_vectors(self, collection_name: str, vectors: List[Dict]) -> List[str]:
        """Store test vectors in collection"""
        # TODO: Implement vector storage
        pass
    
    async def search_vectors(self, collection_name: str, query_vector: List[float], limit: int = 10) -> List[Dict]:
        """Search for similar vectors"""
        # TODO: Implement vector search
        pass
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a test collection"""
        # TODO: Implement collection deletion
        pass
```

### Task 4.6: Create comprehensive integration tests

Create `exercises/test_integration.py`:

```python
import pytest
import asyncio
import os
import uuid
from integration_test_framework import IntegrationTestManager, ServiceConfig, QdrantTestClient

# Configuration from environment variables
SERVICE_CONFIG = ServiceConfig(
    qdrant_url=os.getenv('QDRANT_URL', 'http://localhost:6333'),
    redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    postgres_url=os.getenv('POSTGRES_URL', 'postgresql://test_user:test_password@localhost:5432/test_crawl4ai'),
    mock_api_url=os.getenv('MOCK_API_URL', 'http://localhost:8080')
)

@pytest.fixture(scope="session")
async def integration_manager():
    """Session-scoped integration test manager"""
    manager = IntegrationTestManager(SERVICE_CONFIG)
    async with manager.test_environment() as mgr:
        yield mgr

@pytest.fixture
async def qdrant_client():
    """Qdrant test client"""
    return QdrantTestClient(SERVICE_CONFIG.qdrant_url)

class TestServiceIntegration:
    """Test integration with real services"""
    
    @pytest.mark.asyncio
    async def test_qdrant_connection_and_health(self, qdrant_client):
        """Test Qdrant service connectivity"""
        # TODO:
        # 1. Test health endpoint
        # 2. Test creating a collection
        # 3. Test basic operations
        # 4. Clean up collection
        pass
    
    @pytest.mark.asyncio
    async def test_redis_connection_and_operations(self, integration_manager):
        """Test Redis connectivity and basic operations"""
        # TODO:
        # 1. Connect to Redis
        # 2. Test SET/GET operations
        # 3. Test expiration
        # 4. Test cleanup
        pass
    
    @pytest.mark.asyncio
    async def test_postgres_connection_and_queries(self, integration_manager):
        """Test PostgreSQL connectivity and queries"""
        # TODO:
        # 1. Connect to PostgreSQL
        # 2. Test basic queries
        # 3. Test document insertion/retrieval
        # 4. Clean up test data
        pass
    
    @pytest.mark.asyncio
    async def test_mock_api_endpoints(self, integration_manager):
        """Test mock API endpoints"""
        # TODO:
        # 1. Test embedding API endpoint
        # 2. Test search API endpoint
        # 3. Verify response formats
        pass

class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.mark.asyncio
    async def test_document_storage_and_retrieval_workflow(self, integration_manager, qdrant_client):
        """Test complete document processing workflow"""
        # TODO:
        # 1. Store documents with embeddings in Qdrant
        # 2. Store metadata in PostgreSQL
        # 3. Cache results in Redis
        # 4. Perform search operations
        # 5. Verify results across all services
        pass
    
    @pytest.mark.asyncio  
    async def test_caching_behavior_across_services(self, integration_manager):
        """Test caching behavior with Redis"""
        # TODO:
        # 1. Perform expensive operation (embedding generation)
        # 2. Verify result is cached
        # 3. Perform same operation again
        # 4. Verify cache hit behavior
        # 5. Test cache expiration
        pass
    
    @pytest.mark.asyncio
    async def test_search_with_ai_enhancement_integration(self, integration_manager, qdrant_client):
        """Test AI-enhanced search with real services"""
        # TODO:
        # 1. Store test documents with embeddings
        # 2. Perform semantic search using real Qdrant
        # 3. Use mock OpenAI API for embeddings
        # 4. Verify search results and rankings
        pass
    
    @pytest.mark.asyncio
    async def test_error_handling_with_service_failures(self, integration_manager):
        """Test error handling when services fail"""
        # This test will simulate service failures
        # TODO:
        # 1. Start with all services working
        # 2. Simulate Qdrant failure (stop container or block network)
        # 3. Verify graceful degradation
        # 4. Restore service and verify recovery
        pass

class TestPerformanceAndScaling:
    """Test performance characteristics with real services"""
    
    @pytest.mark.asyncio
    async def test_bulk_document_processing_performance(self, integration_manager, qdrant_client):
        """Test performance with bulk document processing"""
        import time
        
        # Generate test documents
        documents = [
            {
                'id': str(uuid.uuid4()),
                'content': f'Test document content {i} with enough text to generate meaningful embeddings',
                'url': f'https://test.com/doc{i}',
                'title': f'Test Document {i}'
            }
            for i in range(100)  # Process 100 documents
        ]
        
        # TODO:
        # 1. Measure time to process all documents
        # 2. Store embeddings in Qdrant
        # 3. Store metadata in PostgreSQL
        # 4. Verify all documents are searchable
        # 5. Assert performance is within acceptable limits
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_search_operations(self, integration_manager, qdrant_client):
        """Test concurrent search operations"""
        # TODO:
        # 1. Set up test data
        # 2. Perform multiple concurrent searches
        # 3. Verify all searches complete successfully
        # 4. Verify results are consistent
        # 5. Measure and assert performance characteristics
        pass
    
    @pytest.mark.asyncio
    async def test_memory_usage_during_processing(self, integration_manager):
        """Test memory usage patterns"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # TODO:
        # 1. Process large batch of documents
        # 2. Monitor memory usage throughout
        # 3. Verify memory is released after processing
        # 4. Assert memory usage stays within reasonable bounds
        pass

class TestDataConsistency:
    """Test data consistency across services"""
    
    @pytest.mark.asyncio
    async def test_transaction_consistency(self, integration_manager):
        """Test data consistency across multiple services"""
        # TODO:
        # 1. Start a transaction across multiple operations
        # 2. Store data in PostgreSQL
        # 3. Store vectors in Qdrant
        # 4. Cache results in Redis
        # 5. Simulate failure during process
        # 6. Verify data is consistent (all succeed or all fail)
        pass
    
    @pytest.mark.asyncio
    async def test_eventual_consistency_patterns(self, integration_manager):
        """Test eventual consistency between services"""
        # TODO:
        # 1. Store document in PostgreSQL
        # 2. Asynchronously process embeddings
        # 3. Store in Qdrant with delay
        # 4. Verify eventual consistency
        # 5. Test search behavior during inconsistent state
        pass
```

**Your Tasks for Part 2:**

1. Implement the IntegrationTestManager methods
2. Implement the QdrantTestClient methods
3. Complete all TODO items in the test classes
4. Ensure proper cleanup in all tests

## Part 3: Service Health and Dependencies (15 minutes)

### Task 4.7: Implement service health monitoring

Add to `exercises/test_integration.py`:

```python
class TestServiceHealth:
    """Test service health and dependency management"""
    
    @pytest.mark.asyncio
    async def test_service_startup_order(self, integration_manager):
        """Test that services start in correct order"""
        # TODO:
        # 1. Verify Qdrant is ready before tests start
        # 2. Verify Redis is ready before tests start
        # 3. Verify PostgreSQL is ready before tests start
        # 4. Verify Mock API is ready before tests start
        # 5. Test dependency relationships
        pass
    
    @pytest.mark.asyncio
    async def test_service_health_endpoints(self, integration_manager):
        """Test all service health endpoints"""
        import httpx
        
        # TODO:
        # 1. Check Qdrant health endpoint
        # 2. Check Mock API health endpoint
        # 3. Check Redis connectivity
        # 4. Check PostgreSQL connectivity
        # 5. Verify health check response formats
        pass
    
    @pytest.mark.asyncio
    async def test_service_resilience_to_failures(self, integration_manager):
        """Test service behavior during partial failures"""
        # TODO:
        # 1. Test behavior when Qdrant is slow to respond
        # 2. Test behavior when Redis is unavailable
        # 3. Test behavior when PostgreSQL is under load
        # 4. Verify graceful degradation patterns
        pass
```

### Task 4.8: Test configuration and environment

```python
class TestEnvironmentConfiguration:
    """Test environment configuration and setup"""
    
    def test_environment_variables_are_set(self):
        """Test that all required environment variables are configured"""
        required_vars = [
            'QDRANT_URL',
            'REDIS_URL', 
            'POSTGRES_URL',
            'MOCK_API_URL'
        ]
        
        # TODO:
        # 1. Verify all required environment variables are set
        # 2. Verify URLs are valid formats
        # 3. Verify services are accessible at configured URLs
        pass
    
    @pytest.mark.asyncio
    async def test_service_configuration_consistency(self):
        """Test that service configurations are consistent"""
        # TODO:
        # 1. Verify Qdrant collection configuration
        # 2. Verify Redis memory configuration
        # 3. Verify PostgreSQL database schema
        # 4. Test configuration consistency across test runs
        pass
```

## Part 4: Advanced Integration Patterns (15 minutes)

### Task 4.9: Test complex integration scenarios

```python
class TestComplexIntegrationScenarios:
    """Test complex real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_multi_service_transaction_rollback(self, integration_manager):
        """Test transaction rollback across multiple services"""
        # TODO:
        # 1. Start operations across multiple services
        # 2. Simulate failure in the middle of process
        # 3. Verify partial operations can be rolled back
        # 4. Verify system returns to consistent state
        pass
    
    @pytest.mark.asyncio
    async def test_service_discovery_and_failover(self, integration_manager):
        """Test service discovery and failover patterns"""
        # TODO:
        # 1. Configure multiple instances of same service type
        # 2. Test automatic failover when primary fails
        # 3. Test service discovery mechanisms
        # 4. Verify load balancing behavior
        pass
    
    @pytest.mark.asyncio
    async def test_data_migration_between_services(self, integration_manager):
        """Test data migration scenarios"""
        # TODO:
        # 1. Store data in one format/service
        # 2. Migrate to different format/service
        # 3. Verify data integrity during migration
        # 4. Test rollback capabilities
        pass
    
    @pytest.mark.asyncio
    async def test_cross_service_search_and_aggregation(self, integration_manager):
        """Test search and aggregation across multiple services"""
        # TODO:
        # 1. Store related data in different services
        # 2. Perform complex queries that span services
        # 3. Aggregate results from multiple sources
        # 4. Verify result consistency and performance
        pass
```

## Part 5: Test Environment Management (10 minutes)

### Task 4.10: Create test management utilities

Create `exercises/test_utils.py`:

```python
import asyncio
import docker
import time
from typing import List, Dict, Any

class DockerTestManager:
    """Manage Docker containers for integration testing"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.test_containers = []
    
    def start_test_services(self, compose_file: str = "docker-compose.test.yml"):
        """Start all test services"""
        # TODO:
        # 1. Use docker-compose to start services
        # 2. Wait for health checks to pass
        # 3. Return when all services are ready
        pass
    
    def stop_test_services(self):
        """Stop and clean up test services"""
        # TODO:
        # 1. Stop all test containers
        # 2. Remove volumes
        # 3. Clean up networks
        pass
    
    def restart_service(self, service_name: str):
        """Restart a specific service for testing"""
        # TODO:
        # 1. Stop specific service
        # 2. Start it again
        # 3. Wait for health check
        pass
    
    def get_service_logs(self, service_name: str) -> str:
        """Get logs from a service for debugging"""
        # TODO:
        # 1. Get container for service
        # 2. Return recent logs
        pass

class TestDataManager:
    """Manage test data across multiple services"""
    
    def __init__(self, config: ServiceConfig):
        self.config = config
        self.created_collections = []
        self.created_keys = []
        self.created_records = []
    
    async def create_test_dataset(self, dataset_name: str, size: int = 100):
        """Create a named test dataset"""
        # TODO:
        # 1. Generate test documents
        # 2. Store in all relevant services
        # 3. Track created resources for cleanup
        pass
    
    async def cleanup_all_test_data(self):
        """Clean up all created test data"""
        # TODO:
        # 1. Remove all created collections
        # 2. Delete all test keys
        # 3. Clean up database records
        pass
    
    async def backup_test_state(self, backup_name: str):
        """Backup current test state"""
        # TODO:
        # 1. Export data from all services
        # 2. Save to backup location
        pass
    
    async def restore_test_state(self, backup_name: str):
        """Restore test state from backup"""
        # TODO:
        # 1. Clear current state
        # 2. Restore from backup
        pass
```

## Running Integration Tests

### Task 4.11: Create test runner scripts

Create `exercises/run_integration_tests.sh`:

```bash
#!/bin/bash

set -e

echo "Starting integration test environment..."

# Cleanup any existing test containers
docker-compose -f exercises/docker-compose.test.yml down -v

# Start test services
docker-compose -f exercises/docker-compose.test.yml up -d

# Wait for services to be healthy
echo "Waiting for services to be ready..."
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose -f exercises/docker-compose.test.yml ps | grep -q "healthy"; then
        echo "Services are ready!"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done

if [ $elapsed -ge $timeout ]; then
    echo "Timeout waiting for services to be ready"
    docker-compose -f exercises/docker-compose.test.yml logs
    exit 1
fi

# Run integration tests
echo "Running integration tests..."
docker-compose -f exercises/docker-compose.test.yml exec -T test-runner \
    python -m pytest exercises/test_integration.py -v --tb=short

test_result=$?

# Collect logs for debugging if tests failed
if [ $test_result -ne 0 ]; then
    echo "Tests failed. Collecting logs..."
    mkdir -p test-logs
    docker-compose -f exercises/docker-compose.test.yml logs > test-logs/integration-test-logs.txt
fi

# Cleanup
echo "Cleaning up test environment..."
docker-compose -f exercises/docker-compose.test.yml down -v

exit $test_result
```

### Local Testing Commands

```bash
# Start test environment manually
docker-compose -f exercises/docker-compose.test.yml up -d

# Check service health
curl http://localhost:6333/health  # Qdrant
redis-cli -h localhost ping        # Redis
curl http://localhost:8080/__admin/health  # Mock API

# Run specific test categories
uv run pytest exercises/test_integration.py::TestServiceIntegration -v
uv run pytest exercises/test_integration.py::TestEndToEndWorkflows -v
uv run pytest exercises/test_integration.py::TestPerformanceAndScaling -v

# Run with detailed output
uv run pytest exercises/test_integration.py -v -s --tb=long

# Run with coverage
uv run pytest exercises/test_integration.py --cov=exercises --cov-report=html

# Debug specific test
uv run pytest exercises/test_integration.py::TestEndToEndWorkflows::test_document_storage_and_retrieval_workflow -v -s --pdb

# Cleanup
docker-compose -f exercises/docker-compose.test.yml down -v
```

## Debugging Integration Tests

### Common Issues and Solutions

**Issue**: Services not ready when tests start

```python
# Solution: Implement proper health checks and waits
async def wait_for_service_ready(url: str, timeout: int = 60):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False
```

**Issue**: Port conflicts with existing services

```yaml
# Solution: Use different ports for testing
services:
  qdrant-test:
    ports:
      - "16333:6333"  # Use non-standard port
```

**Issue**: Data persistence between test runs

```python
# Solution: Implement thorough cleanup
@pytest.fixture(autouse=True)
async def cleanup_test_data():
    yield
    # Cleanup code runs after each test
    await cleanup_all_test_collections()
    await clear_redis_keys()
    await truncate_test_tables()
```

**Issue**: Tests are too slow

```python
# Solution: Use session-scoped fixtures and optimize test data
@pytest.fixture(scope="session")
async def test_data():
    # Create test data once per session
    data = await create_large_test_dataset()
    yield data
    await cleanup_test_dataset()
```

## Assessment Criteria

Your integration tests will be evaluated on:

1. **Service Integration**: Proper integration with real Docker services
2. **Test Data Management**: Clean setup and teardown of test data
3. **Error Handling**: Robust handling of service failures and network issues
4. **Performance Testing**: Meaningful performance assertions and monitoring
5. **Environment Management**: Proper Docker environment setup and configuration
6. **Test Isolation**: Tests don't interfere with each other
7. **Documentation**: Clear setup instructions and troubleshooting guides

## Next Steps

After completing this exercise:

1. Review the solution for best practices
2. Experiment with different service configurations
3. Try adding new services to the test environment
4. Move on to Exercise 5 for coverage analysis and improvement

## Reflection Questions

1. What are the key differences between unit tests and integration tests?
2. How do you balance test speed with test realism in integration testing?
3. What strategies help make integration tests more reliable?
4. How do you handle test data lifecycle in multi-service environments?
5. What are the trade-offs between using real services vs. test doubles in integration tests?
