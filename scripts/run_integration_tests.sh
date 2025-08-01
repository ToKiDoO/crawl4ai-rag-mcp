#!/bin/bash
# Script to run integration tests with Docker containers

set -e

echo "🚀 Starting integration test environment..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please copy .env.example and configure it."
    exit 1
fi

# Start test containers
echo "📦 Starting test containers..."
docker-compose -f docker-compose.test.yml up -d

# Wait for Qdrant to be ready
echo "⏳ Waiting for Qdrant to be ready..."
timeout=30
counter=0
until curl -s http://localhost:6333/readyz > /dev/null 2>&1; do
    sleep 1
    counter=$((counter + 1))
    if [ $counter -ge $timeout ]; then
        echo "❌ Timeout waiting for Qdrant to start"
        docker-compose -f docker-compose.test.yml logs qdrant-test
        exit 1
    fi
done
echo "✅ Qdrant is ready!"

# Check if Supabase is configured
if grep -q "SUPABASE_URL=" .env && grep -q "SUPABASE_SERVICE_KEY=" .env; then
    echo "✅ Supabase configuration found"
else
    echo "⚠️  Warning: Supabase not configured. Only Qdrant tests will run."
    echo "   To test Supabase, add SUPABASE_URL and SUPABASE_SERVICE_KEY to .env"
fi

# Run integration tests
echo "🧪 Running integration tests..."
python -m pytest tests/test_integration.py -v -s --tb=short

# Capture exit code
TEST_EXIT_CODE=$?

# Show container logs if tests failed
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo "❌ Tests failed. Showing container logs..."
    docker-compose -f docker-compose.test.yml logs
fi

# Cleanup
echo "🧹 Cleaning up test containers..."
docker-compose -f docker-compose.test.yml down

# Exit with test exit code
exit $TEST_EXIT_CODE