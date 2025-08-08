# Performance Monitoring Plugin

## Overview

The performance monitoring plugin for pytest collects detailed performance metrics during test execution, including:

- Test execution time (total, setup, call, teardown)
- Memory usage (start, peak, end, delta)
- CPU usage (when available)
- System information

## Installation

The plugin is automatically loaded when pytest runs. The only additional dependency is `psutil`, which has been added to `pyproject.toml`.

## Usage

### Command Line Options

- `--perf-monitor`: Enable performance monitoring
- `--perf-output <file>`: Output file for metrics (default: performance_metrics.json)
- `--perf-system-info`: Include system information (default: true)
- `--perf-cpu-interval <seconds>`: CPU monitoring interval (default: 0.1)
- `--perf-print-summary`: Print summary to console after test run

### Examples

```bash
# Basic usage
uv run pytest --perf-monitor

# Custom output file
uv run pytest --perf-monitor --perf-output=my_metrics.json

# With summary printed to console
uv run pytest --perf-monitor --perf-print-summary

# Disable system info collection
uv run pytest --perf-monitor --no-perf-system-info
```

### CI/CD Integration

The plugin is integrated into the GitHub Actions workflow in `.github/workflows/test-coverage.yml`. Performance metrics are:

1. Collected for each test group (core, adapters, interfaces) and Python version
2. Stored as GitHub Actions artifacts with 30-day retention
3. Aggregated into a combined report with 90-day retention

### Output Format

The plugin generates a JSON file with the following structure:

```json
{
  "session": {
    "duration": 10.5,
    "total_tests": 25,
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "system": {
    "platform": "Linux",
    "python_version": "3.12.0",
    "cpu_count": 8,
    "memory_total_mb": 16384.0,
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "tests": {
    "tests/test_example.py::test_function": {
      "duration": 0.123,
      "setup_time": 0.01,
      "call_time": 0.1,
      "teardown_time": 0.013,
      "memory": {
        "start_mb": 100.5,
        "peak_mb": 105.2,
        "end_mb": 101.0,
        "delta_mb": 0.5
      },
      "cpu_percent": 25.5
    }
  },
  "summary": {
    "total_duration": 10.5,
    "avg_duration": 0.42,
    "max_duration": 2.1,
    "min_duration": 0.05,
    "avg_memory_delta_mb": 1.2,
    "max_memory_delta_mb": 5.5
  }
}
```

## Performance Analysis

### Identifying Slow Tests

Look for tests with high `duration` values in the metrics:

```python
import json

with open('performance_metrics.json') as f:
    data = json.load(f)

# Find slowest tests
slow_tests = sorted(
    data['tests'].items(), 
    key=lambda x: x[1]['duration'], 
    reverse=True
)[:10]
```

### Memory Leak Detection

Check for tests with high `memory.delta_mb` values:

```python
# Find tests with potential memory leaks
memory_leaks = [
    (test, metrics) 
    for test, metrics in data['tests'].items() 
    if metrics['memory']['delta_mb'] > 10  # 10MB threshold
]
```

### CPU Usage Analysis

Identify CPU-intensive tests:

```python
# Find CPU-intensive tests
cpu_intensive = [
    (test, metrics) 
    for test, metrics in data['tests'].items() 
    if metrics.get('cpu_percent', 0) > 80
]
```

## Troubleshooting

### CPU Monitoring Not Available

On some systems (especially containers), CPU monitoring might not work. The plugin will gracefully handle this and set `cpu_percent` to `null`.

### Memory Measurements

Memory measurements are for the entire pytest process, not just the test code. This includes:

- pytest framework overhead
- imported modules
- test fixtures
- Any background threads

### Performance Overhead

The monitoring itself has minimal overhead:

- Memory checks: ~0.1ms per test
- CPU monitoring: ~1-5ms per test (when enabled)
- JSON writing: ~10-50ms at session end

## Best Practices

1. **Baseline Establishment**: Run performance monitoring on your main branch to establish baselines
2. **PR Comparison**: Compare PR metrics against baseline to catch performance regressions
3. **Resource Limits**: Set up alerts for tests exceeding resource thresholds
4. **Trend Analysis**: Track performance metrics over time to identify degradation
5. **Test Isolation**: Be aware that parallel test execution can affect CPU measurements

## Future Enhancements

Potential improvements for the plugin:

1. **Grafana Integration**: Export metrics in Prometheus format
2. **Historical Tracking**: Store metrics in a database for trend analysis
3. **Automatic Regression Detection**: Flag tests that become significantly slower
4. **Resource Prediction**: Estimate resource needs for test runs
5. **Parallel Test Support**: Better metrics for tests run in parallel
