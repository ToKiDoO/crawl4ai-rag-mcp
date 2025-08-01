#!/bin/bash
# Script to run all tests with coverage reporting

set -e

echo "🧪 Running unit tests with coverage..."

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Install dependencies if needed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Please install it first."
    exit 1
fi

echo "📦 Installing test dependencies..."
uv sync

# Run different test suites
echo ""
echo "🔬 Running unit tests..."
uv run pytest tests/test_utils_refactored.py tests/test_database_factory.py tests/test_crawl4ai_mcp.py -v --cov=src --cov-report=term-missing --cov-report=html

echo ""
echo "🔌 Running adapter tests..."
uv run pytest tests/test_supabase_adapter.py tests/test_qdrant_adapter.py -v --cov=src --cov-append --cov-report=term-missing --cov-report=html

echo ""
echo "🔗 Running interface contract tests..."
uv run pytest tests/test_database_interface.py -v --cov=src --cov-append --cov-report=term-missing --cov-report=html

echo ""
echo "🧩 Running simple integration tests..."
uv run pytest tests/test_integration_simple.py -v --cov=src --cov-append --cov-report=term-missing --cov-report=html

# Generate final coverage report
echo ""
echo "📊 Generating coverage report..."
uv run coverage report
uv run coverage html

echo ""
echo "✅ Test coverage report generated!"
echo "   - Terminal report above"
echo "   - HTML report: htmlcov/index.html"
echo "   - XML report: coverage.xml"

# Check if coverage meets threshold
uv run coverage report --fail-under=80
if [ $? -eq 0 ]; then
    echo "✅ Coverage threshold met (>80%)"
else
    echo "❌ Coverage below threshold (80%)"
    exit 1
fi