# Neo4j-Qdrant Integration Troubleshooting Guide

**Comprehensive guide for diagnosing and resolving integration issues**

## Quick Diagnostic Commands

### System Health Check

```bash
# Check overall system health
curl -X GET "http://localhost:8051/health" | jq '.'

# Check specific components
curl -X GET "http://localhost:8051/health/neo4j" | jq '.'
curl -X GET "http://localhost:8051/health/qdrant" | jq '.'
curl -X GET "http://localhost:8051/health/integration" | jq '.'

# Test database connectivity
docker compose exec mcp-crawl4ai python -c "
import asyncio
from database.factory import create_database_client
from knowledge_graph.repository import RepositoryExtractor

async def test_connections():
    # Test Qdrant
    try:
        db_client = create_database_client()
        await db_client.initialize()
        print('✅ Qdrant: Connected')
    except Exception as e:
        print(f'❌ Qdrant: {e}')
    
    # Test Neo4j
    try:
        extractor = RepositoryExtractor()
        await extractor.test_connection()
        print('✅ Neo4j: Connected')
    except Exception as e:
        print(f'❌ Neo4j: {e}')

asyncio.run(test_connections())
"
```

### Performance Metrics

```bash
# Get performance statistics
curl -X GET "http://localhost:8051/metrics/performance" | jq '.'

# Check cache statistics
curl -X GET "http://localhost:8051/metrics/cache" | jq '.'

# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

## Common Issues and Solutions

### 1. Low Confidence Scores

**Symptoms:**

- All search results have confidence scores < 0.6
- Search returns few or no results
- Validation consistently fails

**Diagnosis:**

```bash
# Check repository coverage in Neo4j
curl -X POST "http://localhost:8051/query_knowledge_graph" \
  -H "Content-Type: application/json" \
  -d '{"command": "repos"}' | jq '.repositories | length'

# Check indexed code examples in Qdrant
curl -X POST "http://localhost:8051/get_available_sources" | jq '.sources | length'

# Verify specific repository data
curl -X POST "http://localhost:8051/query_knowledge_graph" \
  -H "Content-Type: application/json" \
  -d '{"command": "explore your-repo-name"}' | jq '.'
```

**Root Causes & Solutions:**

#### Repository Not Properly Parsed

```bash
# Check if repository exists in Neo4j
curl -X POST "http://localhost:8051/query_knowledge_graph" \
  -H "Content-Type: application/json" \
  -d '{"command": "repos"}' | jq '.repositories[]'

# If missing, re-parse the repository
curl -X POST "http://localhost:8051/parse_github_repository" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo.git"}'
```

#### Code Not Indexed in Qdrant

```bash
# Check available sources
curl -X POST "http://localhost:8051/get_available_sources" | jq '.sources[].source_id'

# If repository missing from Qdrant, re-index
curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "your-repo-name"}'
```

#### Query Too Specific or Vague

```bash
# Test with broader queries
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "function",
    "match_count": 10,
    "min_confidence": 0.3,
    "validation_mode": "fast"
  }'

# Test with more specific queries
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "async database connection with error handling",
    "source_filter": "your-repo-name",
    "match_count": 5,
    "min_confidence": 0.5
  }'
```

### 2. Performance Issues

**Symptoms:**

- Search response times > 2 seconds
- Timeouts during validation
- High memory usage
- System becomes unresponsive

**Diagnosis:**

```bash
# Monitor response times
time curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "validation_mode": "fast"}'

# Check system resources
docker stats
htop

# Monitor database performance
docker compose logs mcp-crawl4ai | grep "response_time"
```

**Solutions:**

#### Enable and Optimize Caching

```bash
# Check cache hit rate
curl -X GET "http://localhost:8051/metrics/cache" | jq '.cache_stats.hit_rate'

# If hit rate < 0.5, increase cache size in environment variables
echo "VALIDATION_CACHE_SIZE=2000" >> .env
echo "VALIDATION_CACHE_TTL=7200" >> .env
docker compose restart mcp-crawl4ai
```

#### Reduce Validation Complexity

```bash
# Use fast mode for interactive queries
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your query",
    "validation_mode": "fast",
    "match_count": 3
  }'

# Reduce match count for better performance
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your query",
    "match_count": 3,
    "min_confidence": 0.6
  }'
```

#### Optimize Database Configuration

```yaml
# docker-compose.yml adjustments
services:
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
      
  qdrant:
    environment:
      - QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=64
    deploy:
      resources:
        limits:
          memory: 4G
```

### 3. Connection Issues

**Symptoms:**

- "Database client not available" errors
- "Neo4j driver not found" errors
- Connection timeouts
- Intermittent failures

**Diagnosis:**

```bash
# Test direct connections
# Neo4j
docker run --rm --network crawl4aimcp_default neo4j:latest \
  cypher-shell -a bolt://neo4j:7687 -u neo4j -p your_password "RETURN 1"

# Qdrant
curl http://localhost:6333/health

# Check network connectivity
docker compose exec mcp-crawl4ai curl http://neo4j:7687
docker compose exec mcp-crawl4ai curl http://qdrant:6333/health
```

**Solutions:**

#### Fix Environment Configuration

```bash
# Check environment variables
docker compose exec mcp-crawl4ai env | grep -E "(NEO4J|QDRANT)"

# Common fixes in .env file
NEO4J_URI=bolt://neo4j:7687  # Use service name, not localhost
QDRANT_URL=http://qdrant:6333  # Use service name, not localhost
NEO4J_PASSWORD=your_actual_password  # Ensure correct password
```

#### Docker Networking Issues

```bash
# Check if services are in the same network
docker network ls
docker network inspect crawl4aimcp_default

# Restart services in correct order
docker compose down
docker compose up -d neo4j qdrant
sleep 30  # Wait for databases to be ready
docker compose up -d mcp-crawl4ai
```

#### Service Startup Order

```yaml
# docker-compose.yml - Add proper dependencies
services:
  mcp-crawl4ai:
    depends_on:
      neo4j:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    
  neo4j:
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      
  qdrant:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 5
```

### 4. Memory and Resource Issues

**Symptoms:**

- Out of memory errors
- Container crashes
- Slow garbage collection
- High CPU usage

**Diagnosis:**

```bash
# Monitor memory usage
docker stats --format "table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check for memory leaks
docker compose exec mcp-crawl4ai python -c "
import psutil
import gc
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
print(f'Objects: {len(gc.get_objects())}')
"

# Check embedding generation memory usage
docker compose logs mcp-crawl4ai | grep -i "memory\|embedding"
```

**Solutions:**

#### Optimize Memory Settings

```bash
# Reduce cache sizes
echo "VALIDATION_CACHE_SIZE=500" >> .env
echo "MAX_CONCURRENT_VALIDATIONS=5" >> .env

# Optimize batch sizes for embedding generation
echo "EMBEDDING_BATCH_SIZE=10" >> .env
echo "QDRANT_BATCH_SIZE=50" >> .env
```

#### Docker Resource Limits

```yaml
# docker-compose.yml
services:
  mcp-crawl4ai:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

#### Garbage Collection Optimization

```python
# Add to main.py or service initialization
import gc
import asyncio

async def periodic_gc():
    """Periodic garbage collection"""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        gc.collect()
        
# Start background task
asyncio.create_task(periodic_gc())
```

### 5. Validation Accuracy Issues

**Symptoms:**

- High false positive rates in hallucination detection
- Inconsistent confidence scores
- Valid code flagged as hallucinations
- Invalid code passing validation

**Diagnosis:**

```bash
# Test known good code
echo 'from pydantic_ai import Agent
agent = Agent("openai:gpt-4")
result = await agent.run("test")' > /tmp/good_code.py

curl -X POST "http://localhost:8051/check_ai_script_hallucinations_enhanced" \
  -H "Content-Type: application/json" \
  -d '{"script_path": "/tmp/good_code.py"}'

# Test known bad code
echo 'from pydantic_ai import Agent
agent = Agent("openai:gpt-4")
result = await agent.nonexistent_method("test")' > /tmp/bad_code.py

curl -X POST "http://localhost:8051/check_ai_script_hallucinations_enhanced" \
  -H "Content-Type: application/json" \
  -d '{"script_path": "/tmp/bad_code.py"}'
```

**Solutions:**

#### Update Knowledge Graph Data

```bash
# Re-parse repositories with latest code
curl -X POST "http://localhost:8051/parse_github_repository" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/pydantic/pydantic-ai.git"}'

# Re-index code examples
curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "pydantic-ai"}'
```

#### Adjust Confidence Thresholds

```bash
# Lower thresholds for exploratory analysis
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your query",
    "min_confidence": 0.4,
    "validation_mode": "balanced"
  }'

# Higher thresholds for production validation
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "your query",
    "min_confidence": 0.8,
    "validation_mode": "thorough"
  }'
```

#### Validate Against Multiple Repositories

```bash
# Index multiple related repositories
repositories=(
  "https://github.com/pydantic/pydantic-ai.git"
  "https://github.com/fastapi/fastapi.git"
  "https://github.com/sqlalchemy/sqlalchemy.git"
)

for repo in "${repositories[@]}"; do
  curl -X POST "http://localhost:8051/parse_github_repository" \
    -H "Content-Type: application/json" \
    -d "{\"repo_url\": \"$repo\"}"
  
  repo_name=$(basename "$repo" .git)
  curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
    -H "Content-Type: application/json" \
    -d "{\"repo_name\": \"$repo_name\"}"
done
```

## Best Practices

### Repository Management

#### Selecting Quality Repositories

```bash
# Choose repositories with:
# - Good documentation
# - Active maintenance
# - Clear code structure
# - Comprehensive examples

# Example quality repositories:
good_repos=(
  "https://github.com/fastapi/fastapi.git"
  "https://github.com/pydantic/pydantic.git"
  "https://github.com/sqlalchemy/sqlalchemy.git"
  "https://github.com/pandas-dev/pandas.git"
  "https://github.com/scikit-learn/scikit-learn.git"
)
```

#### Repository Update Strategy

```bash
# Create update script
cat > update_repositories.sh << 'EOF'
#!/bin/bash
set -e

REPOS=(
  "pydantic-ai"
  "fastapi"
  "sqlalchemy"
)

for repo in "${REPOS[@]}"; do
  echo "Updating $repo..."
  
  # Re-parse repository (gets latest changes)
  curl -X POST "http://localhost:8051/parse_github_repository" \
    -H "Content-Type: application/json" \
    -d "{\"repo_url\": \"https://github.com/user/$repo.git\"}"
  
  # Clean old examples and re-index
  curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
    -H "Content-Type: application/json" \
    -d "{\"repo_name\": \"$repo\"}"
  
  echo "✅ Updated $repo"
  sleep 10  # Rate limiting
done

echo "🎉 All repositories updated!"
EOF

chmod +x update_repositories.sh
```

### Search Optimization

#### Query Construction Guidelines

```bash
# Good queries (specific but not too narrow)
good_queries=(
  "async database connection with error handling"
  "JWT authentication middleware"
  "pydantic model with custom validation"
  "FastAPI dependency injection"
  "SQLAlchemy relationship with lazy loading"
)

# Bad queries (too vague or too specific)
bad_queries=(
  "function"  # Too vague
  "def create_user_with_email_validation_and_password_hashing_using_bcrypt_and_jwt_tokens"  # Too specific
  "async"  # Too generic
  "error"  # Too broad
)
```

#### Progressive Search Strategy

```python
# progressive_search.py
async def progressive_search(base_query: str, repo_filter: str = None):
    """Search with progressively relaxed constraints"""
    
    search_configs = [
        {"min_confidence": 0.8, "validation_mode": "thorough", "match_count": 3},
        {"min_confidence": 0.6, "validation_mode": "balanced", "match_count": 5},
        {"min_confidence": 0.4, "validation_mode": "fast", "match_count": 10},
    ]
    
    for i, config in enumerate(search_configs):
        print(f"Search attempt {i+1}: confidence >= {config['min_confidence']}")
        
        params = {
            "query": base_query,
            "source_filter": repo_filter,
            **config
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8051/smart_code_search",
                json=params
            ) as response:
                result = await response.json()
        
        if result.get('total_results', 0) >= 2:
            print(f"✅ Found {result['total_results']} results")
            return result
        else:
            print(f"❌ Only {result.get('total_results', 0)} results, trying next level")
    
    print("⚠️ No sufficient results found with any configuration") 
    return None

# Usage
# result = await progressive_search("async database transaction", "sqlalchemy")
```

### Performance Optimization

#### Cache Management Strategy

```python
# cache_manager.py
import asyncio
import aiohttp
from datetime import datetime, timedelta

class CacheManager:
    def __init__(self, base_url="http://localhost:8051"):
        self.base_url = base_url
    
    async def monitor_cache_performance(self):
        """Monitor cache performance and trigger optimization"""
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/metrics/cache") as response:
                stats = await response.json()
        
        hit_rate = stats['cache_stats']['hit_rate']
        memory_usage = stats['cache_stats']['memory_usage_mb']
        
        print(f"Cache Hit Rate: {hit_rate:.2%}")
        print(f"Memory Usage: {memory_usage:.1f} MB")
        
        # Optimize based on performance
        if hit_rate < 0.5:
            print("⚠️ Low cache hit rate - consider:")
            print("  • Increasing cache size")
            print("  • Reducing cache TTL variation")
            print("  • Pre-warming cache with common queries")
        
        if memory_usage > 200:
            print("⚠️ High memory usage - consider:")
            print("  • Reducing cache size")
            print("  • Implementing more aggressive eviction")
            print("  • Using external cache (Redis)")
    
    async def warm_cache(self, common_queries: list):
        """Pre-warm cache with common queries"""
        
        print("🔥 Warming cache with common queries...")
        
        async with aiohttp.ClientSession() as session:
            for query in common_queries:
                await session.post(
                    f"{self.base_url}/smart_code_search",
                    json={
                        "query": query,
                        "validation_mode": "fast",
                        "match_count": 3
                    }
                )
                await asyncio.sleep(0.5)  # Rate limiting
        
        print("✅ Cache warming completed")

# Usage
cache_manager = CacheManager()
common_queries = [
    "async function error handling",
    "database connection",
    "authentication middleware",
    "pydantic model validation",
    "FastAPI dependency injection"
]

# asyncio.run(cache_manager.warm_cache(common_queries))
```

#### Resource Monitoring

```bash
# Create monitoring script
cat > monitor_resources.sh << 'EOF'
#!/bin/bash

echo "🔍 Neo4j-Qdrant Integration Resource Monitor"
echo "=========================================="

# System resources
echo "📊 System Resources:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Service health
echo -e "\n💚 Service Health:"
curl -s http://localhost:8051/health | jq -r '
  "Overall: " + .status,
  "Neo4j: " + .components.neo4j.status + " (" + (.components.neo4j.response_time_ms | tostring) + "ms)",
  "Qdrant: " + .components.qdrant.status + " (" + (.components.qdrant.response_time_ms | tostring) + "ms)",
  "Cache Hit Rate: " + (.performance_stats.cache_statistics.hit_rate * 100 | floor | tostring) + "%"
'

# Database sizes
echo -e "\n💾 Database Status:"
echo "Neo4j Nodes: $(curl -s 'http://localhost:7474/db/data/cypher' \
  --user neo4j:your_password \
  -H 'Content-Type: application/json' \
  -d '{"query": "MATCH (n) RETURN count(n) as count"}' | jq -r '.data[0][0]')"

echo "Qdrant Points: $(curl -s http://localhost:6333/collections | jq '[.result.collections[].points] | add')"

# Recent errors
echo -e "\n🚨 Recent Errors (last 10 minutes):"
docker compose logs --since=10m mcp-crawl4ai 2>/dev/null | grep -i error | tail -5
EOF

chmod +x monitor_resources.sh
```

### Production Deployment

#### Security Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  neo4j:
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_dbms_security_auth__enabled=true
      - NEO4J_dbms_security_logs__query=true
    networks:
      - internal
    # Don't expose ports externally in production
    
  qdrant:
    environment:
      - QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}
      - QDRANT__SERVICE__ENABLE_CORS=false
    networks:
      - internal
    
  mcp-crawl4ai:
    environment:
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - QDRANT_API_KEY=${QDRANT_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - internal
      - external
    ports:
      - "127.0.0.1:8051:8051"  # Only local access

networks:
  internal:
    driver: bridge
    internal: true
  external:
    driver: bridge
```

#### Backup Strategy

```bash
# Create backup script
cat > backup_integration.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting backup to $BACKUP_DIR"

# Backup Neo4j
echo "📦 Backing up Neo4j..."
docker compose exec neo4j neo4j-admin database dump \
  --to-path=/tmp/backup.dump neo4j
docker compose cp neo4j:/tmp/backup.dump "$BACKUP_DIR/neo4j.dump"

# Backup Qdrant
echo "📦 Backing up Qdrant..."
docker compose exec qdrant curl -X POST \
  "http://localhost:6333/collections/crawled_pages/snapshots"
SNAPSHOT_NAME=$(docker compose exec qdrant curl -s \
  "http://localhost:6333/collections/crawled_pages/snapshots" | \
  jq -r '.result.snapshots[-1].name')
docker compose cp "qdrant:/qdrant/storage/collections/crawled_pages/snapshots/$SNAPSHOT_NAME" \
  "$BACKUP_DIR/qdrant_snapshot"

# Backup configuration
echo "⚙️ Backing up configuration..."
cp .env "$BACKUP_DIR/"
cp docker-compose.yml "$BACKUP_DIR/"

echo "✅ Backup completed: $BACKUP_DIR"
EOF

chmod +x backup_integration.sh
```

#### Health Monitoring

```python
# health_monitor.py
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

class HealthMonitor:
    def __init__(self, base_url="http://localhost:8051", alert_email=None):
        self.base_url = base_url
        self.alert_email = alert_email
        self.last_alert = {}
    
    async def check_health(self):
        """Comprehensive health check"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=30) as response:
                    health = await response.json()
            
            issues = []
            
            # Check overall status
            if health['status'] != 'healthy':
                issues.append(f"Overall status: {health['status']}")
            
            # Check components
            for component, details in health['components'].items():
                if details['status'] != 'healthy':
                    issues.append(f"{component}: {details['status']}")
                
                # Check response times
                if 'response_time_ms' in details and details['response_time_ms'] > 1000:
                    issues.append(f"{component}: slow response ({details['response_time_ms']}ms)")
            
            # Check performance metrics
            cache_hit_rate = health['performance_stats']['cache_statistics']['hit_rate']
            if cache_hit_rate < 0.3:
                issues.append(f"Low cache hit rate: {cache_hit_rate:.2%}")
            
            return {
                'healthy': len(issues) == 0,
                'issues': issues,
                'timestamp': datetime.now(),
                'details': health
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'issues': [f"Health check failed: {str(e)}"],
                'timestamp': datetime.now(),
                'details': None
            }
    
    async def monitor_continuously(self, interval=300):  # 5 minutes
        """Continuous health monitoring with alerts"""
        while True:
            health_status = await self.check_health()
            
            if not health_status['healthy']:
                print(f"🚨 Health issues detected at {health_status['timestamp']}")
                for issue in health_status['issues']:
                    print(f"  • {issue}")
                
                if self.alert_email:
                    await self.send_alert(health_status)
            else:
                print(f"✅ System healthy at {health_status['timestamp']}")
            
            await asyncio.sleep(interval)
    
    async def send_alert(self, health_status):
        """Send email alert for health issues"""
        # Implement email alerting logic here
        pass

# Usage
# monitor = HealthMonitor(alert_email="admin@example.com")
# asyncio.run(monitor.monitor_continuously())
```

This comprehensive troubleshooting guide covers the most common issues you'll encounter with the Neo4j-Qdrant integration and provides practical solutions for each scenario. Regular monitoring and following these best practices will ensure optimal performance and reliability.
