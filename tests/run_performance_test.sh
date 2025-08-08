#!/bin/bash
# Script to demonstrate running tests with performance monitoring

echo "Running tests with performance monitoring..."
echo "============================================"

# Run the performance test suite with monitoring enabled
uv run pytest tests/test_performance_plugin.py -v \
    --perf-monitor \
    --perf-output=test_performance_report.json \
    --perf-print-summary

echo ""
echo "Performance metrics saved to: test_performance_report.json"
echo ""
echo "Sample output:"
cat test_performance_report.json | head -50