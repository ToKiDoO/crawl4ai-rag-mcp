#!/bin/bash
# One-command Qdrant QA execution script
# This script runs the complete Qdrant test suite with a single command

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create logs directory
LOG_DIR="$SCRIPT_DIR/qa-logs"
mkdir -p "$LOG_DIR"

# Log files with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MAIN_LOG="$LOG_DIR/qdrant_qa_${TIMESTAMP}.log"
DETAILED_LOG="$LOG_DIR/qdrant_qa_detailed_${TIMESTAMP}.log"

# Function to log to both console and file
log_message() {
    echo -e "$1" | tee -a "$MAIN_LOG"
}

# Function to log detailed output
log_detailed() {
    echo -e "$1" >> "$DETAILED_LOG"
}

echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}" | tee "$MAIN_LOG"
echo -e "${PURPLE}       🚀 QDRANT QA AUTOMATION SUITE 🚀${NC}" | tee -a "$MAIN_LOG"
echo -e "${PURPLE}═══════════════════════════════════════════════════════════════${NC}" | tee -a "$MAIN_LOG"
echo "" | tee -a "$MAIN_LOG"
echo "Log files:" | tee -a "$MAIN_LOG"
echo "  Main: $MAIN_LOG" | tee -a "$MAIN_LOG"
echo "  Detailed: $DETAILED_LOG" | tee -a "$MAIN_LOG"
echo "" | tee -a "$MAIN_LOG"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help           Show this help message"
    echo "  -q, --quick          Run quick tests only (skip benchmarks)"
    echo "  -b, --benchmarks     Run benchmarks only"
    echo "  -i, --integration    Run integration tests only"
    echo "  -e, --e2e            Run E2E tests only"
    echo "  -a, --all            Run all tests (default)"
    echo "  -c, --cleanup        Cleanup after tests"
    echo ""
    echo "Examples:"
    echo "  $0                   # Run all tests"
    echo "  $0 --quick           # Run quick tests only"
    echo "  $0 --benchmarks      # Run benchmarks only"
}

# Parse command line arguments
RUN_ALL=true
RUN_QUICK=false
RUN_BENCHMARKS=false
RUN_INTEGRATION=false
RUN_E2E=false
CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -q|--quick)
            RUN_ALL=false
            RUN_QUICK=true
            shift
            ;;
        -b|--benchmarks)
            RUN_ALL=false
            RUN_BENCHMARKS=true
            shift
            ;;
        -i|--integration)
            RUN_ALL=false
            RUN_INTEGRATION=true
            shift
            ;;
        -e|--e2e)
            RUN_ALL=false
            RUN_E2E=true
            shift
            ;;
        -a|--all)
            RUN_ALL=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            exit 1
            ;;
    esac
done

# Track test results
FAILED_TESTS=()
PASSED_TESTS=()

# Function to run a test and track results
run_test() {
    local test_name=$1
    local test_command=$2
    local test_log="$LOG_DIR/${test_name// /_}_${TIMESTAMP}.log"
    
    log_message "\n${BLUE}▶ Running: ${test_name}${NC}"
    log_message "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Log command being executed
    log_detailed "\n========== ${test_name} =========="
    log_detailed "Command: $test_command"
    log_detailed "Start time: $(date)"
    log_detailed "----------------------------------------"
    
    # Run test and capture output
    if eval "$test_command" 2>&1 | tee -a "$test_log" | tee -a "$DETAILED_LOG"; then
        log_message "${GREEN}✅ PASSED: ${test_name}${NC}"
        PASSED_TESTS+=("$test_name")
        log_detailed "Result: PASSED"
    else
        log_message "${RED}❌ FAILED: ${test_name}${NC}"
        FAILED_TESTS+=("$test_name")
        log_detailed "Result: FAILED"
    fi
    
    log_detailed "End time: $(date)"
    log_detailed "Individual log: $test_log"
    log_detailed "========================================\n"
}

# Ensure dependencies are installed
log_message "${YELLOW}📦 Checking dependencies...${NC}"
if ! command -v uv &> /dev/null; then
    log_message "${RED}❌ Error: uv is not installed. Please install it first.${NC}"
    log_message "   Run: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Ensure pytest is available
if ! uv run python -c "import pytest" 2>/dev/null; then
    log_message "${YELLOW}Installing test dependencies...${NC}"
    uv sync 2>&1 | tee -a "$DETAILED_LOG"
fi

# Check if Qdrant is running
log_message "\n${YELLOW}🔍 Checking Qdrant status...${NC}"
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    log_message "${GREEN}✅ Qdrant is running${NC}"
else
    log_message "${YELLOW}⚠️  Qdrant is not running. Starting it now...${NC}"
    docker run -d --name qdrant-qa -p 6333:6333 qdrant/qdrant:latest 2>&1 | tee -a "$DETAILED_LOG" || {
        log_message "${RED}❌ Failed to start Qdrant. Please ensure Docker is running.${NC}"
        exit 1
    }
    
    # Wait for Qdrant to be ready
    echo -n "Waiting for Qdrant to be ready" | tee -a "$MAIN_LOG"
    for i in {1..30}; do
        if curl -s http://localhost:6333/health > /dev/null 2>&1; then
            echo -e "\n${GREEN}✅ Qdrant is ready${NC}" | tee -a "$MAIN_LOG"
            break
        fi
        echo -n "." | tee -a "$MAIN_LOG"
        sleep 1
    done
fi

# Set environment variables
export VECTOR_DATABASE=qdrant
export QDRANT_URL=http://localhost:6333
export OPENAI_API_KEY=${OPENAI_API_KEY:-test-key}

# Log environment
log_detailed "\n========== ENVIRONMENT =========="
log_detailed "VECTOR_DATABASE=$VECTOR_DATABASE"
log_detailed "QDRANT_URL=$QDRANT_URL"
log_detailed "OPENAI_API_KEY=***${OPENAI_API_KEY: -4}"
log_detailed "Working Directory: $PWD"
log_detailed "================================\n"

# Start testing
log_message "\n${PURPLE}🧪 STARTING TEST EXECUTION${NC}"
START_TIME=$(date +%s)

# 1. Unit Tests
if [[ "$RUN_ALL" == "true" ]] || [[ "$RUN_QUICK" == "true" ]] || [[ "$RUN_INTEGRATION" == "true" ]]; then
    run_test "Unit Tests - Qdrant Adapter" \
        "uv run pytest tests/test_qdrant_adapter.py -v --tb=short"
    
    run_test "Unit Tests - Database Factory" \
        "uv run pytest tests/test_database_factory.py -v --tb=short"
fi

# 2. Integration Tests
if [[ "$RUN_ALL" == "true" ]] || [[ "$RUN_INTEGRATION" == "true" ]]; then
    run_test "Integration Tests - Qdrant" \
        "uv run pytest tests/test_qdrant_integration.py -v --tb=short"
    
    run_test "Interface Contract Tests" \
        "uv run pytest tests/test_database_interface.py::TestQdrantInterface -v --tb=short"
fi

# 3. Performance Benchmarks
if [[ "$RUN_ALL" == "true" ]] || [[ "$RUN_BENCHMARKS" == "true" ]]; then
    run_test "Performance Benchmarks" \
        "uv run python tests/benchmark_qdrant.py"
fi

# 4. E2E Tests (if not quick mode)
if [[ "$RUN_ALL" == "true" ]] || [[ "$RUN_E2E" == "true" ]]; then
    if [[ "$RUN_QUICK" != "true" ]]; then
        run_test "E2E Tests" \
            "./scripts/test_qdrant_e2e.sh"
    fi
fi

# 5. Coverage Report
if [[ "$RUN_ALL" == "true" ]] || [[ "$RUN_QUICK" == "true" ]]; then
    log_message "\n${BLUE}📊 Generating Coverage Report...${NC}"
    
    COVERAGE_LOG="$LOG_DIR/coverage_${TIMESTAMP}.log"
    uv run pytest tests/test_qdrant_*.py \
        --cov=src/database/qdrant_adapter \
        --cov=src/database/factory \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-report=xml \
        -v 2>&1 | tee "$COVERAGE_LOG" | tee -a "$DETAILED_LOG"
    
    log_message "${GREEN}✅ Coverage report generated in htmlcov/index.html${NC}"
    log_detailed "Coverage report saved to: $COVERAGE_LOG"
fi

# Calculate execution time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Generate summary report
log_message "\n${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
log_message "${PURPLE}                    📊 TEST SUMMARY REPORT 📊${NC}"
log_message "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"

log_message "\n${BLUE}Execution Time:${NC} ${MINUTES}m ${SECONDS}s"
log_message "${BLUE}Total Tests Run:${NC} $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))"
log_message "${GREEN}Tests Passed:${NC} ${#PASSED_TESTS[@]}"
log_message "${RED}Tests Failed:${NC} ${#FAILED_TESTS[@]}"

if [ ${#PASSED_TESTS[@]} -gt 0 ]; then
    log_message "\n${GREEN}✅ Passed Tests:${NC}"
    for test in "${PASSED_TESTS[@]}"; do
        log_message "   • $test"
    done
fi

if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
    log_message "\n${RED}❌ Failed Tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        log_message "   • $test"
    done
fi

# Save summary to file
REPORT_FILE="$LOG_DIR/qdrant_qa_summary_${TIMESTAMP}.txt"
{
    echo "QDRANT QA TEST REPORT"
    echo "===================="
    echo "Date: $(date)"
    echo "Duration: ${MINUTES}m ${SECONDS}s"
    echo ""
    echo "Results:"
    echo "- Total Tests: $((${#PASSED_TESTS[@]} + ${#FAILED_TESTS[@]}))"
    echo "- Passed: ${#PASSED_TESTS[@]}"
    echo "- Failed: ${#FAILED_TESTS[@]}"
    echo ""
    
    if [ ${#PASSED_TESTS[@]} -gt 0 ]; then
        echo ""
        echo "Passed Tests:"
        for test in "${PASSED_TESTS[@]}"; do
            echo "  ✅ $test"
        done
    fi
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo ""
        echo "Failed Tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  ❌ $test"
        done
    fi
    
    if [ -f "benchmark_results.txt" ]; then
        echo ""
        echo "Performance Benchmark Results:"
        echo "=============================="
        cat benchmark_results.txt
    fi
    
    echo ""
    echo "Log Files:"
    echo "- Main Log: $MAIN_LOG"
    echo "- Detailed Log: $DETAILED_LOG"
    echo "- Summary: $REPORT_FILE"
    echo ""
    echo "Individual Test Logs:"
    for log in "$LOG_DIR"/*_${TIMESTAMP}.log; do
        if [[ "$log" != "$MAIN_LOG" && "$log" != "$DETAILED_LOG" && -f "$log" ]]; then
            echo "- $log"
        fi
    done
} > "$REPORT_FILE"

log_message "\n${BLUE}📄 Test logs saved to: ${LOG_DIR}${NC}"
log_message "${BLUE}   - Summary: ${REPORT_FILE}${NC}"
log_message "${BLUE}   - Main log: ${MAIN_LOG}${NC}"
log_message "${BLUE}   - Detailed log: ${DETAILED_LOG}${NC}"

# Cleanup if requested
if [[ "$CLEANUP" == "true" ]]; then
    log_message "\n${YELLOW}🧹 Cleaning up...${NC}"
    
    # Stop Qdrant if we started it
    if docker ps --format '{{.Names}}' | grep -q '^qdrant-qa$'; then
        docker stop qdrant-qa && docker rm qdrant-qa
        log_message "${GREEN}✅ Removed Qdrant container${NC}"
    fi
    
    # Clean test artifacts but keep logs
    rm -f benchmark_results.txt qdrant_test_logs.txt
    log_message "${GREEN}✅ Cleaned up test artifacts (logs preserved in ${LOG_DIR})${NC}"
fi

# Copy benchmark results to log directory if exists
if [ -f "benchmark_results.txt" ]; then
    cp benchmark_results.txt "$LOG_DIR/benchmark_results_${TIMESTAMP}.txt"
fi

# Final result
log_message "\n${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    log_message "${GREEN}       🎉 ALL TESTS PASSED! QDRANT QA COMPLETE! 🎉${NC}"
    log_message "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    
    # Log final summary
    log_detailed "\n========== FINAL SUMMARY =========="
    log_detailed "Status: ALL TESTS PASSED"
    log_detailed "Total execution time: ${MINUTES}m ${SECONDS}s"
    log_detailed "Test results: ${#PASSED_TESTS[@]} passed, 0 failed"
    log_detailed "===================================\n"
    
    exit 0
else
    log_message "${RED}       ❌ SOME TESTS FAILED - REVIEW REQUIRED ❌${NC}"
    log_message "${PURPLE}═══════════════════════════════════════════════════════════════${NC}"
    
    # Log final summary
    log_detailed "\n========== FINAL SUMMARY =========="
    log_detailed "Status: SOME TESTS FAILED"
    log_detailed "Total execution time: ${MINUTES}m ${SECONDS}s"
    log_detailed "Test results: ${#PASSED_TESTS[@]} passed, ${#FAILED_TESTS[@]} failed"
    log_detailed "Failed tests:"
    for test in "${FAILED_TESTS[@]}"; do
        log_detailed "  - $test"
    done
    log_detailed "===================================\n"
    
    exit 1
fi