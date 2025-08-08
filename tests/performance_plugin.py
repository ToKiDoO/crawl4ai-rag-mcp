"""
Performance monitoring plugin for pytest.

This plugin collects performance metrics during test execution including:
- Test execution time
- Memory usage
- CPU usage (if available)
- Test setup/teardown times

Metrics are output in JSON format suitable for GitHub Actions artifacts.
"""

import json
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil
import pytest


class PerformanceMetrics:
    """Container for test performance metrics."""

    def __init__(self):
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.setup_time: float | None = None
        self.teardown_time: float | None = None
        self.call_time: float | None = None
        self.memory_start: int | None = None
        self.memory_peak: int | None = None
        self.memory_end: int | None = None
        self.cpu_percent: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "duration": self.end_time - self.start_time
            if self.start_time and self.end_time
            else None,
            "setup_time": self.setup_time,
            "call_time": self.call_time,
            "teardown_time": self.teardown_time,
            "memory": {
                "start_mb": self.memory_start / (1024 * 1024)
                if self.memory_start
                else None,
                "peak_mb": self.memory_peak / (1024 * 1024)
                if self.memory_peak
                else None,
                "end_mb": self.memory_end / (1024 * 1024) if self.memory_end else None,
                "delta_mb": (self.memory_end - self.memory_start) / (1024 * 1024)
                if self.memory_start and self.memory_end
                else None,
            },
            "cpu_percent": self.cpu_percent,
        }


class PerformanceMonitorPlugin:
    """Pytest plugin for monitoring test performance."""

    def __init__(self, config):
        self.config = config
        self.enabled = config.getoption("--perf-monitor", default=False)
        self.output_file = config.getoption(
            "--perf-output",
            default="performance_metrics.json",
        )
        self.include_system = config.getoption("--perf-system-info", default=True)
        self.cpu_interval = config.getoption("--perf-cpu-interval", default=0.1)

        self.metrics: dict[str, dict[str, Any]] = {}
        self.session_start_time = None
        self.session_end_time = None
        self.process = psutil.Process()

        # Track if CPU monitoring is available
        self.cpu_monitoring_available = self._check_cpu_monitoring()

    def _check_cpu_monitoring(self) -> bool:
        """Check if CPU monitoring is available on this system."""
        try:
            # Try to get CPU percent with a small interval
            self.process.cpu_percent(interval=0.01)
            return True
        except Exception:
            return False

    def pytest_sessionstart(self, session):
        """Called at the start of the test session."""
        if not self.enabled:
            return

        self.session_start_time = time.time()

        # Collect system information
        if self.include_system:
            self.system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total_mb": psutil.virtual_memory().total / (1024 * 1024),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    def pytest_sessionfinish(self, session):
        """Called at the end of the test session."""
        if not self.enabled:
            return

        self.session_end_time = time.time()

        # Prepare final report
        report = {
            "session": {
                "duration": self.session_end_time - self.session_start_time,
                "total_tests": len(self.metrics),
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "tests": self.metrics,
        }

        if self.include_system:
            report["system"] = self.system_info

        # Add summary statistics
        if self.metrics:
            durations = [
                m["duration"] for m in self.metrics.values() if m.get("duration")
            ]
            memory_deltas = [
                m["memory"]["delta_mb"]
                for m in self.metrics.values()
                if m.get("memory", {}).get("delta_mb") is not None
            ]

            report["summary"] = {
                "total_duration": sum(durations) if durations else 0,
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "avg_memory_delta_mb": sum(memory_deltas) / len(memory_deltas)
                if memory_deltas
                else 0,
                "max_memory_delta_mb": max(memory_deltas) if memory_deltas else 0,
            }

        # Write metrics to file
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        # Also print summary to console if verbose
        if self.config.getoption("--perf-print-summary", default=False):
            print("\n\nPerformance Summary:")
            print(f"Total tests: {report['session']['total_tests']}")
            print(f"Total duration: {report['session']['duration']:.2f}s")
            if "summary" in report:
                print(
                    f"Average test duration: {report['summary']['avg_duration']:.3f}s",
                )
                print(f"Max test duration: {report['summary']['max_duration']:.3f}s")
                print(
                    f"Average memory delta: {report['summary']['avg_memory_delta_mb']:.1f}MB",
                )

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        """Monitor the entire test protocol (setup, call, teardown)."""
        if not self.enabled:
            yield
            return

        nodeid = item.nodeid
        metrics = PerformanceMetrics()

        # Record start metrics
        metrics.start_time = time.time()
        metrics.memory_start = self.process.memory_info().rss

        # Monitor CPU if available
        if self.cpu_monitoring_available:
            # Reset CPU counter
            self.process.cpu_percent(interval=None)

        # Track memory peak
        peak_memory = metrics.memory_start

        # Run the test
        outcome = yield

        # Record end metrics
        metrics.end_time = time.time()
        metrics.memory_end = self.process.memory_info().rss
        metrics.memory_peak = max(peak_memory, metrics.memory_end)

        # Get CPU usage if available
        if self.cpu_monitoring_available:
            try:
                metrics.cpu_percent = self.process.cpu_percent(interval=None)
            except Exception:
                metrics.cpu_percent = None

        # Store metrics
        self.metrics[nodeid] = metrics.to_dict()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        """Monitor test setup phase."""
        if not self.enabled:
            yield
            return

        start = time.time()
        yield
        duration = time.time() - start

        # Update metrics with setup time
        if item.nodeid in self.metrics:
            self.metrics[item.nodeid]["setup_time"] = duration

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        """Monitor test execution phase."""
        if not self.enabled:
            yield
            return

        start = time.time()
        yield
        duration = time.time() - start

        # Update metrics with call time
        if item.nodeid in self.metrics:
            self.metrics[item.nodeid]["call_time"] = duration

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        """Monitor test teardown phase."""
        if not self.enabled:
            yield
            return

        start = time.time()
        yield
        duration = time.time() - start

        # Update metrics with teardown time
        if item.nodeid in self.metrics:
            self.metrics[item.nodeid]["teardown_time"] = duration


def pytest_addoption(parser):
    """Add performance monitoring options to pytest."""
    group = parser.getgroup("performance", "performance monitoring")

    group.addoption(
        "--perf-monitor",
        action="store_true",
        default=False,
        help="Enable performance monitoring during test execution",
    )

    group.addoption(
        "--perf-output",
        action="store",
        default="performance_metrics.json",
        help="Output file for performance metrics (default: performance_metrics.json)",
    )

    group.addoption(
        "--perf-system-info",
        action="store_true",
        default=True,
        help="Include system information in performance report",
    )

    group.addoption(
        "--perf-cpu-interval",
        action="store",
        type=float,
        default=0.1,
        help="CPU monitoring interval in seconds (default: 0.1)",
    )

    group.addoption(
        "--perf-print-summary",
        action="store_true",
        default=False,
        help="Print performance summary to console after test run",
    )


def pytest_configure(config):
    """Configure the performance monitoring plugin."""
    # Register the plugin
    if config.getoption("--perf-monitor") or config.getoption("--perf-output"):
        config.pluginmanager.register(
            PerformanceMonitorPlugin(config),
            "performance_monitor",
        )


def pytest_report_header(config):
    """Add performance monitoring status to pytest header."""
    if config.getoption("--perf-monitor"):
        output_file = config.getoption("--perf-output")
        return [
            "Performance monitoring: enabled",
            f"Performance output: {output_file}",
        ]
    return []
