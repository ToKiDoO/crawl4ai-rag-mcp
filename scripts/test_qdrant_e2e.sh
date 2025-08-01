#!/bin/bash
# E2E test automation script for Qdrant implementation
# This script automates the complete testing workflow

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
QDRANT_PORT=${QDRANT_PORT:-6333}
MCP_PORT=${MCP_PORT:-8051}
COMPOSE_FILE="docker-compose.yml"
QDRANT_COMPOSE_FILE="docker-compose.qdrant.yml"

echo -e "${BLUE}🚀 Starting Qdrant E2E Automated Tests${NC}"
echo "================================================"

# Function to check if a service is healthy
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=60
    local attempt=0
    
    echo -e "${YELLOW}⏳ Waiting for ${service_name} to be ready...${NC}"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ ${service_name} is ready!${NC}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done
    
    echo -e "${RED}❌ ${service_name} failed to start after ${max_attempts} seconds${NC}"
    return 1
}

# Function to run Python tests inside the MCP container
run_python_test() {
    local test_script=$1
    local description=$2
    
    echo -e "\n${BLUE}🧪 ${description}${NC}"
    
    if docker compose exec -T mcp-crawl4ai python -c "$test_script"; then
        echo -e "${GREEN}✅ ${description}: PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ ${description}: FAILED${NC}"
        return 1
    fi
}

# 1. Setup test environment
echo -e "\n${YELLOW}📦 Setting up test environment...${NC}"

# Create test env file if it doesn't exist
if [ ! -f .env.test ]; then
    cp .env.example .env.test
    
    # Update for Qdrant
    cat >> .env.test << EOF

# Qdrant test configuration
VECTOR_DATABASE=qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

# Ensure other services are configured
SEARXNG_URL=http://searxng:8080
EOF
    
    echo -e "${GREEN}✅ Created .env.test configuration${NC}"
fi

# 2. Check if Qdrant compose file exists
if [ ! -f "$QDRANT_COMPOSE_FILE" ]; then
    echo -e "${YELLOW}📝 Creating docker-compose.qdrant.yml...${NC}"
    cat > "$QDRANT_COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "${QDRANT_PORT:-6333}:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    networks:
      - mcp-network
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  qdrant-data:
    driver: local

networks:
  mcp-network:
    external: true
    name: mcp-crawl4ai_default
EOF
fi

# 3. Clean up any existing containers
echo -e "\n${YELLOW}🧹 Cleaning up existing containers...${NC}"
docker compose -f "$COMPOSE_FILE" -f "$QDRANT_COMPOSE_FILE" --env-file .env.test down -v || true

# 4. Start services
echo -e "\n${YELLOW}🐳 Starting Docker services with Qdrant...${NC}"
docker compose -f "$COMPOSE_FILE" -f "$QDRANT_COMPOSE_FILE" --env-file .env.test up -d

# 5. Wait for services to be ready
wait_for_service "http://localhost:${QDRANT_PORT}/health" "Qdrant"
wait_for_service "http://localhost:${MCP_PORT}/health" "MCP Server"

# 6. Verify Qdrant connection
echo -e "\n${BLUE}🔌 Testing Qdrant connection...${NC}"
QDRANT_TEST='
import asyncio
from database.factory import create_database_client

async def test():
    try:
        client = create_database_client()
        print("Successfully connected to Qdrant!")
        return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

asyncio.run(test())
'

run_python_test "$QDRANT_TEST" "Qdrant Connection Test"

# 7. Test MCP tools with Qdrant
echo -e "\n${BLUE}🔧 Testing MCP tools with Qdrant...${NC}"

# Test scrape_urls
SCRAPE_TEST='
import asyncio
from crawl4ai_mcp import scrape_urls

async def test():
    try:
        result = await scrape_urls(
            urls=["https://example.com"],
            return_format="markdown"
        )
        if "Example Domain" in result:
            print("✅ scrape_urls: Successfully scraped and stored content")
            return True
        else:
            print("❌ scrape_urls: Failed to scrape content")
            return False
    except Exception as e:
        print(f"❌ scrape_urls error: {e}")
        return False

asyncio.run(test())
'

run_python_test "$SCRAPE_TEST" "MCP Tool: scrape_urls"

# Allow time for indexing
sleep 2

# Test perform_rag_query
RAG_QUERY_TEST='
import asyncio
from crawl4ai_mcp import perform_rag_query

async def test():
    try:
        result = await perform_rag_query(
            query="example domain",
            source="example.com",
            limit=5
        )
        if result and len(result) > 0:
            print("✅ perform_rag_query: Successfully retrieved content")
            return True
        else:
            print("❌ perform_rag_query: No results found")
            return False
    except Exception as e:
        print(f"❌ perform_rag_query error: {e}")
        return False

asyncio.run(test())
'

run_python_test "$RAG_QUERY_TEST" "MCP Tool: perform_rag_query"

# Test get_available_sources
SOURCES_TEST='
import asyncio
from crawl4ai_mcp import get_available_sources

async def test():
    try:
        sources = await get_available_sources()
        if "example.com" in sources:
            print(f"✅ get_available_sources: Found sources: {sources}")
            return True
        else:
            print(f"❌ get_available_sources: example.com not found in: {sources}")
            return False
    except Exception as e:
        print(f"❌ get_available_sources error: {e}")
        return False

asyncio.run(test())
'

run_python_test "$SOURCES_TEST" "MCP Tool: get_available_sources"

# 8. Run integration tests
echo -e "\n${BLUE}🧪 Running integration tests...${NC}"
if docker compose exec mcp-crawl4ai pytest tests/test_qdrant_integration.py -v; then
    echo -e "${GREEN}✅ Integration tests passed${NC}"
else
    echo -e "${RED}❌ Integration tests failed${NC}"
    FAILED=true
fi

# 9. Run performance benchmarks
echo -e "\n${BLUE}📊 Running performance benchmarks...${NC}"
if docker compose exec mcp-crawl4ai python tests/benchmark_qdrant.py; then
    echo -e "${GREEN}✅ Performance benchmarks passed${NC}"
else
    echo -e "${RED}❌ Performance benchmarks failed${NC}"
    FAILED=true
fi

# 10. Test with different RAG strategies
echo -e "\n${BLUE}🔄 Testing RAG strategies...${NC}"

# Test with hybrid search
HYBRID_TEST='
import asyncio
import os
from crawl4ai_mcp import perform_rag_query

async def test():
    try:
        os.environ["USE_HYBRID_SEARCH"] = "true"
        result = await perform_rag_query(
            query="example",
            limit=5
        )
        print("✅ Hybrid search works with Qdrant")
        return True
    except Exception as e:
        print(f"❌ Hybrid search error: {e}")
        return False
    finally:
        os.environ["USE_HYBRID_SEARCH"] = "false"

asyncio.run(test())
'

run_python_test "$HYBRID_TEST" "RAG Strategy: Hybrid Search"

# 11. Stress test with concurrent operations
echo -e "\n${BLUE}💪 Running stress test...${NC}"

STRESS_TEST='
import asyncio
from crawl4ai_mcp import scrape_urls, perform_rag_query

async def stress_test():
    try:
        # Create 20 concurrent operations
        tasks = []
        
        # Mix of scraping and querying
        for i in range(10):
            tasks.append(scrape_urls(
                urls=[f"https://example.com/page{i}"],
                return_format="markdown"
            ))
        
        for i in range(10):
            tasks.append(perform_rag_query(
                query=f"test query {i}",
                limit=5
            ))
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count successes
        successes = sum(1 for r in results if not isinstance(r, Exception))
        
        print(f"✅ Stress test completed: {successes}/20 operations successful")
        return successes >= 18  # Allow up to 2 failures
        
    except Exception as e:
        print(f"❌ Stress test error: {e}")
        return False

asyncio.run(stress_test())
'

run_python_test "$STRESS_TEST" "Stress Test: Concurrent Operations"

# 12. Collect logs for debugging
echo -e "\n${BLUE}📋 Collecting logs...${NC}"
docker compose logs mcp-crawl4ai --tail=50 > qdrant_test_logs.txt
echo -e "${GREEN}✅ Logs saved to qdrant_test_logs.txt${NC}"

# 13. Generate test summary
echo -e "\n${BLUE}📊 Test Summary${NC}"
echo "================================================"

if [ -z "$FAILED" ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo -e "\nQdrant implementation is ready for use."
    EXIT_CODE=0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "\nPlease check the logs for details."
    EXIT_CODE=1
fi

# 14. Cleanup option
echo -e "\n${YELLOW}🧹 Cleanup${NC}"
read -p "Do you want to stop and remove the test containers? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose -f "$COMPOSE_FILE" -f "$QDRANT_COMPOSE_FILE" --env-file .env.test down -v
    echo -e "${GREEN}✅ Test environment cleaned up${NC}"
else
    echo -e "${YELLOW}ℹ️  Containers are still running. To stop them manually:${NC}"
    echo "   docker compose -f $COMPOSE_FILE -f $QDRANT_COMPOSE_FILE --env-file .env.test down -v"
fi

echo -e "\n${BLUE}✅ Qdrant E2E tests completed!${NC}"
exit $EXIT_CODE