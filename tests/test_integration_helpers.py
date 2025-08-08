"""
Unit tests for integration helper utilities.

Tests the performance optimization utilities, caching strategies, and
integration management functions for Neo4j-Qdrant integration.
"""

import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.integration_helpers import (
    BatchProcessor,
    CircuitBreaker,
    IntegrationHealthMonitor,
    PerformanceCache,
    PerformanceOptimizer,
    create_cache_key,
    get_performance_optimizer,
    performance_monitor,
    validate_integration_health,
)


class TestPerformanceCache:
    """Test PerformanceCache functionality."""

    def test_cache_initialization(self):
        """Test cache initialization with default parameters."""
        cache = PerformanceCache()

        assert cache.max_size == 1000
        assert cache.default_ttl == 3600
        assert cache.hits == 0
        assert cache.misses == 0
        assert cache.evictions == 0
        assert len(cache._cache) == 0

    def test_cache_initialization_with_params(self):
        """Test cache initialization with custom parameters."""
        cache = PerformanceCache(max_size=500, default_ttl=1800)

        assert cache.max_size == 500
        assert cache.default_ttl == 1800

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = PerformanceCache()

        await cache.set("test_key", "test_value")
        result = await cache.get("test_key")

        assert result == "test_value"
        assert cache.hits == 1
        assert cache.misses == 0

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss behavior."""
        cache = PerformanceCache()

        result = await cache.get("nonexistent_key")

        assert result is None
        assert cache.hits == 0
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        cache = PerformanceCache()

        # Set item with 1 second TTL
        await cache.set("expire_key", "expire_value", ttl=1)

        # Should be available immediately
        result = await cache.get("expire_key")
        assert result == "expire_value"

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Should be expired
        result = await cache.get("expire_key")
        assert result is None
        assert cache.misses == 1  # One miss after expiration

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = PerformanceCache(max_size=2)  # Small cache for testing

        # Fill cache to capacity
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        # Access key1 to make it more recently used
        await cache.get("key1")

        # Add third item, should evict key2 (least recently used)
        await cache.set("key3", "value3")

        # key1 and key3 should exist, key2 should be evicted
        assert await cache.get("key1") == "value1"
        assert await cache.get("key3") == "value3"
        assert await cache.get("key2") is None
        assert cache.evictions == 1

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test cache clearing."""
        cache = PerformanceCache()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()

        assert len(cache._cache) == 0
        assert len(cache._access_times) == 0

    def test_cache_get_stats(self):
        """Test cache statistics."""
        cache = PerformanceCache(max_size=100)
        cache.hits = 15
        cache.misses = 5
        cache.evictions = 2

        stats = cache.get_stats()

        assert stats["size"] == 0  # No items in cache
        assert stats["max_size"] == 100
        assert stats["hits"] == 15
        assert stats["misses"] == 5
        assert stats["evictions"] == 2
        assert stats["hit_rate"] == 0.75  # 15 / (15 + 5)
        assert stats["total_requests"] == 20


class TestBatchProcessor:
    """Test BatchProcessor functionality."""

    def test_batch_processor_initialization(self):
        """Test BatchProcessor initialization."""
        processor = BatchProcessor()

        assert processor.max_concurrent == 10
        assert processor.batch_size == 20
        assert processor._semaphore._value == 10

    def test_batch_processor_custom_params(self):
        """Test BatchProcessor with custom parameters."""
        processor = BatchProcessor(max_concurrent=5, batch_size=10)

        assert processor.max_concurrent == 5
        assert processor.batch_size == 10

    @pytest.mark.asyncio
    async def test_process_batch_basic(self):
        """Test basic batch processing."""
        processor = BatchProcessor(batch_size=2)

        async def mock_processor_func(item):
            return f"processed_{item}"

        items = ["item1", "item2", "item3", "item4"]
        results = await processor.process_batch(items, mock_processor_func)

        assert len(results) == 4
        assert "processed_item1" in results
        assert "processed_item4" in results

    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self):
        """Test batch processing with some errors."""
        processor = BatchProcessor(batch_size=2)

        async def error_processor_func(item):
            if item == "error_item":
                raise ValueError("Processing error")
            return f"processed_{item}"

        items = ["item1", "error_item", "item3"]
        results = await processor.process_batch(items, error_processor_func)

        assert len(results) == 3

        # Check that errors are returned as exceptions
        error_count = sum(1 for r in results if isinstance(r, Exception))
        success_count = sum(1 for r in results if not isinstance(r, Exception))

        assert error_count == 1
        assert success_count == 2

    @pytest.mark.asyncio
    async def test_process_batch_concurrency_limit(self):
        """Test that batch processing respects concurrency limits."""
        processor = BatchProcessor(max_concurrent=2, batch_size=5)

        concurrent_count = 0
        max_concurrent_seen = 0

        async def tracking_processor_func(item):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

            await asyncio.sleep(0.1)  # Simulate work

            concurrent_count -= 1
            return f"processed_{item}"

        items = list(range(8))  # 8 items
        results = await processor.process_batch(items, tracking_processor_func)

        assert len(results) == 8
        assert max_concurrent_seen <= 2  # Should not exceed concurrency limit


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    def test_circuit_breaker_initialization(self):
        """Test CircuitBreaker initialization."""
        breaker = CircuitBreaker()

        assert breaker.failure_threshold == 5
        assert breaker.timeout == 60
        assert breaker.expected_exception == Exception
        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    def test_circuit_breaker_custom_params(self):
        """Test CircuitBreaker with custom parameters."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            timeout=30,
            expected_exception=ValueError,
        )

        assert breaker.failure_threshold == 3
        assert breaker.timeout == 30
        assert breaker.expected_exception == ValueError

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test circuit breaker with successful calls."""
        breaker = CircuitBreaker()

        async def success_func():
            return "success"

        result = await breaker.call(success_func)

        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        """Test circuit breaker opening after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1)

        async def failing_func():
            raise ValueError("Test failure")

        # First failure
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        assert breaker.state == "closed"
        assert breaker.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        assert breaker.state == "open"
        assert breaker.failure_count == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_state(self):
        """Test circuit breaker behavior when open."""
        breaker = CircuitBreaker(failure_threshold=1)

        async def failing_func():
            raise ValueError("Test failure")

        # Cause circuit to open
        with pytest.raises(ValueError):
            await breaker.call(failing_func)

        # Next call should fail fast
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        breaker = CircuitBreaker(failure_threshold=1, timeout=0.1)

        async def failing_func():
            raise ValueError("Test failure")

        async def success_func():
            return "success"

        # Open the circuit
        with pytest.raises(ValueError):
            await breaker.call(failing_func)
        assert breaker.state == "open"

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Should attempt half-open and succeed
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    def test_circuit_breaker_get_state(self):
        """Test getting circuit breaker state."""
        breaker = CircuitBreaker(failure_threshold=3)
        breaker.failure_count = 2
        breaker.last_failure_time = time.time()

        state = breaker.get_state()

        assert state["state"] == "closed"
        assert state["failure_count"] == 2
        assert state["failure_threshold"] == 3
        assert "last_failure_time" in state


class TestIntegrationHealthMonitor:
    """Test IntegrationHealthMonitor functionality."""

    @pytest.fixture
    def health_monitor(self):
        """Create IntegrationHealthMonitor instance."""
        return IntegrationHealthMonitor()

    @pytest.mark.asyncio
    async def test_check_neo4j_health_success(self, health_monitor):
        """Test successful Neo4j health check."""
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"health_check": 1}

        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.run.return_value = mock_result
        mock_result.single.return_value = mock_record

        health = await health_monitor.check_neo4j_health(mock_driver)

        assert health["status"] == "healthy"
        assert "latency_ms" in health

    @pytest.mark.asyncio
    async def test_check_neo4j_health_no_driver(self, health_monitor):
        """Test Neo4j health check with no driver."""
        health = await health_monitor.check_neo4j_health(None)

        assert health["status"] == "unavailable"
        assert health["reason"] == "No driver provided"

    @pytest.mark.asyncio
    async def test_check_neo4j_health_error(self, health_monitor):
        """Test Neo4j health check with connection error."""
        mock_driver = AsyncMock()
        mock_driver.session.side_effect = Exception("Connection failed")

        health = await health_monitor.check_neo4j_health(mock_driver)

        assert health["status"] == "error"
        assert "Connection failed" in health["reason"]

    @pytest.mark.asyncio
    async def test_check_qdrant_health_success(self, health_monitor):
        """Test successful Qdrant health check."""
        mock_client = AsyncMock()
        mock_client.get_collections.return_value = ["collection1", "collection2"]

        health = await health_monitor.check_qdrant_health(mock_client)

        assert health["status"] == "healthy"
        assert health["collections_count"] == 2

    @pytest.mark.asyncio
    async def test_check_qdrant_health_no_client(self, health_monitor):
        """Test Qdrant health check with no client."""
        health = await health_monitor.check_qdrant_health(None)

        assert health["status"] == "unavailable"
        assert health["reason"] == "No client provided"

    @pytest.mark.asyncio
    async def test_get_integration_health_fully_operational(self, health_monitor):
        """Test integration health when both services are healthy."""
        mock_db_client = AsyncMock()
        mock_db_client.get_collections.return_value = []

        mock_neo4j_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"health_check": 1}

        mock_neo4j_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.run.return_value = mock_result
        mock_result.single.return_value = mock_record

        health = await health_monitor.get_integration_health(
            mock_db_client,
            mock_neo4j_driver,
        )

        assert health["overall_status"] == "fully_operational"
        assert health["components"]["qdrant"]["status"] == "healthy"
        assert health["components"]["neo4j"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_integration_health_partially_operational(self, health_monitor):
        """Test integration health when one service is unavailable."""
        mock_db_client = AsyncMock()
        mock_db_client.get_collections.return_value = []

        health = await health_monitor.get_integration_health(
            mock_db_client,
            None,  # No Neo4j driver
        )

        assert health["overall_status"] == "partially_operational"
        assert health["components"]["qdrant"]["status"] == "healthy"
        assert health["components"]["neo4j"]["status"] == "unavailable"


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer functionality."""

    @pytest.fixture
    def optimizer(self):
        """Create PerformanceOptimizer instance."""
        return PerformanceOptimizer()

    def test_optimizer_initialization(self, optimizer):
        """Test PerformanceOptimizer initialization."""
        assert optimizer.cache is not None
        assert optimizer.batch_processor is not None
        assert optimizer.circuit_breaker is not None
        assert optimizer.health_monitor is not None

    @pytest.mark.asyncio
    async def test_optimize_search_query_with_cache(self, optimizer):
        """Test search query optimization with caching."""
        # Mock cache miss then hit
        optimizer.cache.get = AsyncMock(side_effect=[None, "cached_optimized_query"])
        optimizer.cache.set = AsyncMock()

        # First call - cache miss
        result1 = await optimizer.optimize_search_query(
            "test query",
            {"code_type": "function"},
        )

        # Should have called cache.set
        optimizer.cache.set.assert_called_once()

        # Second call - cache hit
        result2 = await optimizer.optimize_search_query(
            "test query",
            {"code_type": "function"},
        )

        assert result2 == "cached_optimized_query"

    def test_apply_query_optimizations(self, optimizer):
        """Test query optimization techniques."""
        # Test basic optimization
        optimized = optimizer._apply_query_optimizations(
            "find the best function",
            {"code_type": "function", "language": "python"},
        )

        assert "function" in optimized
        assert "python" in optimized
        assert "the" not in optimized  # Stop word removed
        assert "best" in optimized  # Non-stop word preserved

    def test_apply_query_optimizations_empty_result(self, optimizer):
        """Test query optimization with all stop words."""
        optimized = optimizer._apply_query_optimizations(
            "the and or",
            {},
        )

        # Should return the original if all words are filtered
        assert optimized == "the and or"

    @pytest.mark.asyncio
    async def test_get_performance_stats(self, optimizer):
        """Test getting performance statistics."""
        # Mock component stats
        optimizer.cache.get_stats = MagicMock(
            return_value={
                "hits": 10,
                "misses": 5,
            }
        )
        optimizer.circuit_breaker.get_state = MagicMock(
            return_value={
                "state": "closed",
                "failure_count": 0,
            }
        )

        stats = await optimizer.get_performance_stats()

        assert "cache_stats" in stats
        assert "circuit_breaker_state" in stats
        assert "batch_processor" in stats
        assert stats["cache_stats"]["hits"] == 10

    @pytest.mark.asyncio
    async def test_cleanup(self, optimizer):
        """Test optimizer cleanup."""
        optimizer.cache.clear = AsyncMock()

        await optimizer.cleanup()

        optimizer.cache.clear.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_cache_key_basic(self):
        """Test basic cache key creation."""
        key = create_cache_key("arg1", "arg2", param1="value1", param2="value2")

        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length

    def test_create_cache_key_consistency(self):
        """Test cache key consistency."""
        key1 = create_cache_key("test", param="value")
        key2 = create_cache_key("test", param="value")
        key3 = create_cache_key("test", param="different")

        assert key1 == key2  # Same inputs produce same key
        assert key1 != key3  # Different inputs produce different keys

    def test_create_cache_key_with_complex_objects(self):
        """Test cache key creation with complex objects."""
        obj1 = {"nested": {"key": "value"}}
        obj2 = [1, 2, 3]

        key = create_cache_key("test", obj1, list_param=obj2)

        assert isinstance(key, str)
        assert len(key) == 32

    @pytest.mark.asyncio
    async def test_performance_monitor_decorator_success(self):
        """Test performance monitor decorator with successful function."""

        @performance_monitor
        async def test_function(param):
            await asyncio.sleep(0.01)  # Small delay
            return f"result_{param}"

        with patch("utils.integration_helpers.logger") as mock_logger:
            result = await test_function("test")

            assert result == "result_test"
            mock_logger.debug.assert_called_once()
            # Check that execution time was logged
            log_call = mock_logger.debug.call_args[0][0]
            assert "test_function executed in" in log_call

    @pytest.mark.asyncio
    async def test_performance_monitor_decorator_error(self):
        """Test performance monitor decorator with function error."""

        @performance_monitor
        async def failing_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        with patch("utils.integration_helpers.logger") as mock_logger:
            with pytest.raises(ValueError, match="Test error"):
                await failing_function()

            mock_logger.error.assert_called_once()
            # Check that error and execution time were logged
            log_call = mock_logger.error.call_args[0][0]
            assert "failing_function failed after" in log_call
            assert "Test error" in log_call

    def test_get_performance_optimizer_singleton(self):
        """Test that get_performance_optimizer returns singleton."""
        optimizer1 = get_performance_optimizer()
        optimizer2 = get_performance_optimizer()

        assert optimizer1 is optimizer2  # Same instance

    @pytest.mark.asyncio
    async def test_validate_integration_health_function(self):
        """Test validate_integration_health utility function."""
        mock_db_client = AsyncMock()
        mock_neo4j_driver = AsyncMock()

        with patch(
            "utils.integration_helpers.get_performance_optimizer"
        ) as mock_get_optimizer:
            mock_optimizer = MagicMock()
            mock_health_monitor = AsyncMock()
            mock_health_monitor.get_integration_health.return_value = {
                "overall_status": "healthy",
                "components": {},
            }
            mock_optimizer.health_monitor = mock_health_monitor
            mock_get_optimizer.return_value = mock_optimizer

            result = await validate_integration_health(
                mock_db_client,
                mock_neo4j_driver,
            )

            assert result["overall_status"] == "healthy"
            mock_health_monitor.get_integration_health.assert_called_once_with(
                database_client=mock_db_client,
                neo4j_driver=mock_neo4j_driver,
            )


class TestIntegrationScenarios:
    """Test integration scenarios with multiple components."""

    @pytest.mark.asyncio
    async def test_cache_with_circuit_breaker(self):
        """Test cache operations with circuit breaker protection."""
        cache = PerformanceCache()
        breaker = CircuitBreaker(failure_threshold=2)

        async def failing_cache_operation():
            raise Exception("Cache operation failed")

        async def successful_cache_operation():
            await cache.set("test_key", "test_value")
            return await cache.get("test_key")

        # First failure
        with pytest.raises(Exception):
            await breaker.call(failing_cache_operation)

        # Second failure - opens circuit
        with pytest.raises(Exception):
            await breaker.call(failing_cache_operation)

        # Circuit should be open
        assert breaker.state == "open"

        # Next call should fail fast
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await breaker.call(successful_cache_operation)

    @pytest.mark.asyncio
    async def test_batch_processor_with_circuit_breaker(self):
        """Test batch processor with circuit breaker protection."""
        processor = BatchProcessor(batch_size=2)
        breaker = CircuitBreaker(failure_threshold=1)

        async def protected_processor_func(item):
            async def process_item():
                if item == "fail":
                    raise ValueError("Processing failed")
                return f"processed_{item}"

            return await breaker.call(process_item)

        # Process items with one failure
        items = ["item1", "fail", "item3"]

        results = await processor.process_batch(items, protected_processor_func)

        # Should have mix of successful results and exceptions
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        error_count = sum(1 for r in results if isinstance(r, Exception))

        assert success_count >= 1  # At least some should succeed
        assert error_count >= 1  # At least some should fail

    @pytest.mark.asyncio
    async def test_performance_monitoring_with_caching(self):
        """Test performance monitoring combined with caching."""
        cache = PerformanceCache()

        @performance_monitor
        async def cached_expensive_operation(param):
            cache_key = create_cache_key("expensive_op", param)

            # Check cache first
            cached_result = await cache.get(cache_key)
            if cached_result:
                return cached_result

            # Simulate expensive operation
            await asyncio.sleep(0.01)
            result = f"expensive_result_{param}"

            # Cache the result
            await cache.set(cache_key, result)
            return result

        with patch("utils.integration_helpers.logger") as mock_logger:
            # First call - cache miss
            result1 = await cached_expensive_operation("test")
            assert result1 == "expensive_result_test"

            # Second call - cache hit (should be faster)
            result2 = await cached_expensive_operation("test")
            assert result2 == "expensive_result_test"

            # Should have logged both operations
            assert mock_logger.debug.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
