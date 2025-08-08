#!/usr/bin/env python3
"""
Performance testing script for Crawl4AI MCP tests

This script measures and reports test execution performance with various optimizations.
"""

import subprocess
import time


def run_tests(test_file, options=""):
    """Run tests and measure execution time"""
    cmd = f"uv run python -m pytest {test_file} {options} -q"

    start_time = time.time()
    result = subprocess.run(
        cmd, check=False, shell=True, capture_output=True, text=True
    )
    execution_time = time.time() - start_time

    # Extract test counts from output
    passed = failed = 0
    for line in result.stdout.split("\n"):
        if "passed" in line and "failed" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    passed = int(parts[i - 1])
                elif part == "failed":
                    failed = int(parts[i - 1])

    return {
        "execution_time": execution_time,
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def print_results(name, results):
    """Pretty print test results"""
    print(f"\n{'=' * 60}")
    print(f"{name}")
    print(f"{'=' * 60}")
    print(f"Execution Time: {results['execution_time']:.2f} seconds")
    print(f"Tests Passed: {results['passed']}")
    print(f"Tests Failed: {results['failed']}")
    print(f"Total Tests: {results['total']}")
    if results["failed"] > 0:
        print(f"Return Code: {results['returncode']}")
    print(f"{'=' * 60}")


def main():
    """Run performance comparisons"""
    print("Crawl4AI MCP Test Performance Analysis")
    print("=" * 60)

    # Test configurations
    configs = [
        {
            "name": "Baseline (Sequential, No Optimization)",
            "file": "tests/test_mcp_tools_unit.py",
            "options": "",
        },
        {
            "name": "Optimized (Mocked OpenAI, Cached Fixtures)",
            "file": "tests/test_mcp_tools_unit_optimized.py",
            "options": "",
        },
        {
            "name": "Parallel Execution (2 workers)",
            "file": "tests/test_mcp_tools_unit_optimized.py",
            "options": "-n 2",
        },
        {
            "name": "Parallel Execution (4 workers)",
            "file": "tests/test_mcp_tools_unit_optimized.py",
            "options": "-n 4",
        },
        {
            "name": "Parallel Execution (auto workers)",
            "file": "tests/test_mcp_tools_unit_optimized.py",
            "options": "-n auto",
        },
    ]

    results = []

    for config in configs:
        print(f"\nRunning: {config['name']}...")
        result = run_tests(config["file"], config["options"])
        result["name"] = config["name"]
        results.append(result)
        print_results(config["name"], result)

    # Summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"{'Configuration':<40} {'Time (s)':>10} {'Speedup':>10}")
    print("-" * 60)

    baseline_time = results[0]["execution_time"]
    for result in results:
        speedup = (
            baseline_time / result["execution_time"]
            if result["execution_time"] > 0
            else 0
        )
        print(
            f"{result['name']:<40} {result['execution_time']:>10.2f} {speedup:>10.2f}x",
        )

    print("\nRecommendations:")
    fastest = min(results, key=lambda x: x["execution_time"])
    print(
        f"- Fastest configuration: {fastest['name']} ({fastest['execution_time']:.2f}s)",
    )
    print(f"- Speedup vs baseline: {baseline_time / fastest['execution_time']:.2f}x")

    if fastest["execution_time"] < 90:
        print("✓ Target of <90 seconds achieved!")
    else:
        print(
            "✗ Target of <90 seconds not yet achieved. Consider additional optimizations.",
        )


if __name__ == "__main__":
    main()
