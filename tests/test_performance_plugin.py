"""
Test script to verify the performance monitoring plugin works correctly.
"""

import asyncio
import time

import pytest


def test_simple_performance():
    """Simple test to verify performance monitoring."""
    time.sleep(0.1)  # Simulate some work
    assert True


def test_memory_allocation():
    """Test that allocates memory to verify memory tracking."""
    # Allocate some memory
    data = [i for i in range(1000000)]  # ~4MB of integers
    time.sleep(0.05)
    assert len(data) == 1000000


@pytest.mark.asyncio
async def test_async_performance():
    """Async test to verify async test monitoring."""
    await asyncio.sleep(0.1)
    assert True


def test_with_setup_teardown(tmp_path):
    """Test with fixture to verify setup/teardown monitoring."""
    # tmp_path fixture has setup/teardown
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    time.sleep(0.05)
    assert test_file.exists()


class TestPerformanceClass:
    """Test class to verify class-based test monitoring."""

    def test_class_method(self):
        """Test method in a class."""
        time.sleep(0.05)
        assert True

    def test_another_method(self):
        """Another test method."""
        time.sleep(0.03)
        assert True


@pytest.mark.parametrize("value", [1, 2, 3])
def test_parametrized(value):
    """Parametrized test to verify multiple test instances."""
    time.sleep(0.02 * value)
    assert value > 0


def test_cpu_intensive():
    """Test that uses CPU to verify CPU monitoring."""
    # Perform some CPU-intensive calculation
    result = 0
    for i in range(1000000):
        result += i**2
    assert result > 0
