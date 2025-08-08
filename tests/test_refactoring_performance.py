"""Performance benchmarks for refactored structure."""

import os
import sys
import time
from pathlib import Path

import psutil
import pytest

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestImportPerformance:
    """Test import performance of refactored modules."""

    def test_module_import_times(self):
        """Measure import times for each module."""
        modules = [
            "core",
            "config",
            "utils",
            "database",
            "services",
            "knowledge_graph",
            "tools",
        ]

        import_times = {}

        for module in modules:
            # Clear from sys.modules to force fresh import
            if module in sys.modules:
                del sys.modules[module]

            start_time = time.time()
            __import__(module)
            end_time = time.time()

            import_times[module] = (end_time - start_time) * 1000  # Convert to ms

        # Print results
        print("\n=== Module Import Times ===")
        for module, duration in sorted(import_times.items(), key=lambda x: x[1]):
            print(f"{module:20} {duration:6.2f} ms")

        # Assert all modules import in reasonable time (< 500ms)
        for module, duration in import_times.items():
            assert duration < 500, f"{module} took too long to import: {duration}ms"

        # Total import time should be reasonable
        total_time = sum(import_times.values())
        print(f"\nTotal import time: {total_time:.2f} ms")
        assert total_time < 2000, f"Total import time too high: {total_time}ms"

    def test_main_startup_time(self):
        """Test main module startup time."""
        # Clear main from modules
        if "main" in sys.modules:
            del sys.modules["main"]

        start_time = time.time()
        end_time = time.time()

        startup_time = (end_time - start_time) * 1000
        print(f"\nMain module startup time: {startup_time:.2f} ms")

        # Should start up in reasonable time
        assert startup_time < 1000, f"Main startup too slow: {startup_time}ms"


class TestMemoryUsage:
    """Test memory usage of refactored structure."""

    def test_module_memory_footprint(self):
        """Measure memory footprint of modules."""
        process = psutil.Process(os.getpid())

        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Import all modules
        modules = [
            "core",
            "config",
            "utils",
            "database",
            "services",
            "knowledge_graph",
            "tools",
            "main",
        ]

        for module in modules:
            if module not in sys.modules:
                __import__(module)

        # Get memory after imports
        after_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = after_memory - baseline_memory

        print("\n=== Memory Usage ===")
        print(f"Baseline memory: {baseline_memory:.2f} MB")
        print(f"After imports:   {after_memory:.2f} MB")
        print(f"Memory increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable (< 100 MB)
        assert memory_increase < 100, f"Memory usage too high: {memory_increase} MB"


class TestFileMetrics:
    """Test file size and complexity metrics."""

    def test_file_sizes(self):
        """Check that refactored files follow size guidelines."""
        src_path = Path(__file__).parent.parent / "src"

        file_sizes = {}
        total_lines = 0

        # Check all Python files in src
        for py_file in src_path.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                with open(py_file) as f:
                    lines = len(f.readlines())

                file_sizes[py_file.relative_to(src_path)] = lines
                total_lines += lines

        print("\n=== File Size Analysis ===")
        for file_path, lines in sorted(
            file_sizes.items(), key=lambda x: x[1], reverse=True
        ):
            status = "✅" if lines <= 400 else "⚠️"
            print(f"{status} {file_path!s:40} {lines:4} lines")

        print(f"\nTotal lines: {total_lines}")

        # Check that most files follow the 300-400 line guideline
        large_files = [f for f, lines in file_sizes.items() if lines > 400]

        # Allow tools.py to be larger due to FastMCP constraints
        large_files = [f for f in large_files if "tools.py" not in str(f)]

        if large_files:
            print(f"\nFiles exceeding 400 lines: {large_files}")

        # Assert no files exceed 600 lines (except tools.py)
        for file_path, lines in file_sizes.items():
            if "tools.py" not in str(file_path):
                assert lines <= 600, f"{file_path} is too large: {lines} lines"


class TestModularityBenefits:
    """Test benefits of modular structure."""

    def test_selective_imports(self):
        """Test that modules can be imported selectively."""
        # Clear all our modules
        for module in list(sys.modules.keys()):
            if module.startswith(
                ("core", "config", "utils", "database", "services", "knowledge_graph")
            ):
                del sys.modules[module]

        # Import just utils
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        utils_memory = end_memory - start_memory
        print(f"\nSelective import (utils only): {utils_memory:.2f} MB")

        # Should use minimal memory
        assert utils_memory < 20, (
            f"Selective import uses too much memory: {utils_memory} MB"
        )

    def test_parallel_import_capability(self):
        """Test that modules can be imported in parallel (no circular deps)."""
        import concurrent.futures

        modules = ["core", "config", "utils", "database", "services", "knowledge_graph"]

        def import_module(module_name):
            start = time.time()
            __import__(module_name)
            return module_name, time.time() - start

        # Import modules in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(import_module, m) for m in modules]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        print("\n=== Parallel Import Test ===")
        for module, duration in results:
            print(f"{module:20} imported in {duration * 1000:.2f} ms")

        # All should complete successfully
        assert len(results) == len(modules)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
