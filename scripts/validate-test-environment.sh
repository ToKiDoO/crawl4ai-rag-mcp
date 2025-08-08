#!/bin/bash

# ========================================
# Test Environment Validation Script
# ========================================
# This script validates that the test environment is properly configured
# and all components are working correctly.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is available
port_available() {
    ! nc -z localhost "$1" 2>/dev/null
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local health_check=$2
    local max_attempts=30
    local attempt=1

    print_status "INFO" "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if eval "$health_check" >/dev/null 2>&1; then
            print_status "SUCCESS" "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_status "ERROR" "$service_name failed to become ready after $((max_attempts * 2)) seconds"
    return 1
}

print_status "INFO" "Starting Test Environment Validation"
echo "======================================================"

# 1. Check Prerequisites
print_status "INFO" "Checking prerequisites..."

if ! command_exists "docker"; then
    print_status "ERROR" "Docker is not installed or not in PATH"
    exit 1
fi
print_status "SUCCESS" "Docker is available"

if ! command_exists "docker"; then
    print_status "ERROR" "Docker Compose is not available"
    exit 1
fi
print_status "SUCCESS" "Docker Compose is available"

if ! command_exists "uv"; then
    print_status "ERROR" "UV is not installed or not in PATH"
    exit 1
fi
print_status "SUCCESS" "UV is available"

if ! command_exists "make"; then
    print_status "ERROR" "Make is not installed or not in PATH"
    exit 1
fi
print_status "SUCCESS" "Make is available"

# 2. Check Configuration Files
print_status "INFO" "Checking configuration files..."

if [ ! -f ".env.test" ]; then
    print_status "ERROR" ".env.test file is missing"
    exit 1
fi
print_status "SUCCESS" ".env.test file exists"

if [ ! -f "docker-compose.test.yml" ]; then
    print_status "ERROR" "docker-compose.test.yml file is missing"
    exit 1
fi
print_status "SUCCESS" "docker-compose.test.yml file exists"

if [ ! -f "pytest.ini" ]; then
    print_status "ERROR" "pytest.ini file is missing"
    exit 1
fi
print_status "SUCCESS" "pytest.ini file exists"

# 3. Check Port Availability
print_status "INFO" "Checking port availability..."

REQUIRED_PORTS=(6333 7474 7687 8081 8052)
for port in "${REQUIRED_PORTS[@]}"; do
    if ! port_available "$port"; then
        print_status "WARNING" "Port $port is already in use - may cause conflicts"
    else
        print_status "SUCCESS" "Port $port is available"
    fi
done

# 4. Check Python Dependencies
print_status "INFO" "Checking Python dependencies..."

if ! uv run python -c "import pytest" 2>/dev/null; then
    print_status "ERROR" "pytest is not installed"
    exit 1
fi
print_status "SUCCESS" "pytest is available"

if ! uv run python -c "import docker" 2>/dev/null; then
    print_status "WARNING" "docker-py is not available - some tests may fail"
else
    print_status "SUCCESS" "docker-py is available"
fi

# 5. Start Test Environment
print_status "INFO" "Starting test environment..."

if ! docker compose -f docker-compose.test.yml up -d --remove-orphans; then
    print_status "ERROR" "Failed to start test environment"
    exit 1
fi
print_status "SUCCESS" "Test containers started"

# 6. Wait for Services
print_status "INFO" "Waiting for services to be ready..."

# Wait for Qdrant
if ! wait_for_service "Qdrant" "curl -f http://localhost:6333/readyz"; then
    print_status "ERROR" "Qdrant failed to start"
    docker compose -f docker-compose.test.yml logs qdrant-test
    exit 1
fi

# Wait for Neo4j
if ! wait_for_service "Neo4j" "docker exec neo4j_test cypher-shell -u neo4j -p testpassword123 'RETURN 1'"; then
    print_status "ERROR" "Neo4j failed to start"
    docker compose -f docker-compose.test.yml logs neo4j-test
    exit 1
fi

# Wait for SearXNG (this might take longer)
if ! wait_for_service "SearXNG" "curl -f http://localhost:8081/healthz"; then
    print_status "WARNING" "SearXNG failed to start - SearXNG tests will be skipped"
    docker compose -f docker-compose.test.yml logs searxng-test
else
    print_status "SUCCESS" "All services are ready!"
fi

# 7. Run Quick Test
print_status "INFO" "Running quick validation test..."

if ! cp .env.test .env; then
    print_status "ERROR" "Failed to copy test configuration"
    exit 1
fi

if ! uv run pytest tests/test_utils_refactored.py::test_get_database_adapter -v --tb=short; then
    print_status "ERROR" "Quick validation test failed"
    exit 1
fi
print_status "SUCCESS" "Quick validation test passed"

# 8. Service Status
print_status "INFO" "Test environment status:"
docker compose -f docker-compose.test.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

# 9. Cleanup Option
echo ""
print_status "INFO" "Test environment validation completed successfully!"
print_status "INFO" "Test environment is running and ready for use."
echo ""
print_status "INFO" "Available commands:"
echo "  make test-unit                 - Run unit tests"
echo "  make test-integration          - Run integration tests"
echo "  make test-coverage             - Run tests with coverage"
echo "  make docker-test-down          - Stop test environment"
echo "  make docker-test-logs          - View service logs"
echo ""

read -p "Would you like to stop the test environment now? (y/N): " -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "INFO" "Stopping test environment..."
    docker compose -f docker-compose.test.yml down -v
    print_status "SUCCESS" "Test environment stopped"
else
    print_status "INFO" "Test environment is still running. Use 'make docker-test-down' to stop it."
fi

print_status "SUCCESS" "Test environment validation completed!"