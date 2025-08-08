"""
Integration helper utilities for Neo4j-Qdrant integration layer.

Provides performance optimization utilities, caching strategies, and
integration management functions.
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class PerformanceCache:
    """
    High-performance cache for validation results and search queries.

    Features:
    - TTL-based expiration
    - Size-based eviction (LRU)
    - Performance metrics
    - Async-safe operations
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize the performance cache.

        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = {}
        self._access_times = {}
        self._lock = asyncio.Lock()

        # Performance metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    async def get(self, key: str) -> Any | None:
        """Get an item from the cache."""
        async with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            item, expiry_time = self._cache[key]

            # Check if expired
            if time.time() > expiry_time:
                del self._cache[key]
                del self._access_times[key]
                self.misses += 1
                return None

            # Update access time for LRU
            self._access_times[key] = time.time()
            self.hits += 1
            return item

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set an item in the cache."""
        async with self._lock:
            ttl = ttl or self.default_ttl
            expiry_time = time.time() + ttl

            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()

            self._cache[key] = (value, expiry_time)
            self._access_times[key] = time.time()

    async def _evict_lru(self) -> None:
        """Evict the least recently used item."""
        if not self._access_times:
            return

        # Find LRU item
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]

        # Remove from cache
        del self._cache[lru_key]
        del self._access_times[lru_key]
        self.evictions += 1

    async def clear(self) -> None:
        """Clear the entire cache."""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) if total_requests > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": hit_rate,
            "total_requests": total_requests,
        }


class BatchProcessor:
    """
    Utility for batching and parallelizing validation operations.
    """

    def __init__(self, max_concurrent: int = 10, batch_size: int = 20):
        """
        Initialize the batch processor.

        Args:
            max_concurrent: Maximum number of concurrent operations
            batch_size: Size of each processing batch
        """
        self.max_concurrent = max_concurrent
        self.batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def process_batch(
        self,
        items: list[Any],
        processor_func: Callable,
        *args,
        **kwargs,
    ) -> list[Any]:
        """
        Process items in batches with concurrency control.

        Args:
            items: List of items to process
            processor_func: Async function to process each item
            *args, **kwargs: Additional arguments for processor function

        Returns:
            List of processing results
        """
        results = []

        # Process in chunks
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]

            # Create tasks for this batch
            tasks = [
                self._process_with_semaphore(processor_func, item, *args, **kwargs)
                for item in batch
            ]

            # Execute batch and collect results
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        return results

    async def _process_with_semaphore(
        self, processor_func: Callable, item: Any, *args, **kwargs
    ):
        """Process an item with semaphore control."""
        async with self._semaphore:
            try:
                return await processor_func(item, *args, **kwargs)
            except Exception as e:
                logger.warning(f"Error processing item: {e}")
                return e


class CircuitBreaker:
    """
    Circuit breaker pattern for handling service failures gracefully.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting to close circuit
            expected_exception: Type of exception that triggers the circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func: Callable, *args, **kwargs):
        """Call a function through the circuit breaker."""
        # Check if circuit should be half-open
        if self.state == "open" and self._should_attempt_reset():
            self.state = "half-open"

        # If circuit is open, fail fast
        if self.state == "open":
            raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            # Success - reset failure count
            if self.state == "half-open":
                self.state = "closed"
            self.failure_count = 0
            return result

        except self.expected_exception as e:
            self._record_failure()
            raise e

    def _record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.timeout
        )

    def get_state(self) -> dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
        }


def create_cache_key(*args, **kwargs) -> str:
    """
    Create a deterministic cache key from arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        MD5 hash of the arguments as cache key
    """
    # Create a string representation of all arguments
    key_parts = []

    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        else:
            key_parts.append(str(hash(str(arg))))

    # Add keyword arguments (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        if isinstance(value, (str, int, float, bool)):
            key_parts.append(f"{key}={value}")
        else:
            key_parts.append(f"{key}={hash(str(value))}")

    # Create MD5 hash
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def performance_monitor(func):
    """
    Decorator to monitor function performance.

    Logs execution time and catches exceptions.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = func.__name__

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.debug(f"{function_name} executed in {execution_time:.3f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{function_name} failed after {execution_time:.3f}s: {e}")
            raise

    return wrapper


class IntegrationHealthMonitor:
    """
    Monitor the health of Neo4j-Qdrant integration components.
    """

    def __init__(self):
        self.health_checks = {}
        self.last_check_time = {}

    async def check_neo4j_health(self, neo4j_driver) -> dict[str, Any]:
        """Check Neo4j connection health."""
        try:
            if not neo4j_driver:
                return {"status": "unavailable", "reason": "No driver provided"}

            session = neo4j_driver.session()
            try:
                # Simple health query
                result = await session.run("RETURN 1 as health_check")
                record = await result.single()

                if record and record["health_check"] == 1:
                    return {
                        "status": "healthy",
                        "latency_ms": 0,
                    }  # Could measure actual latency
                return {"status": "unhealthy", "reason": "Unexpected query result"}

            finally:
                await session.close()

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def check_qdrant_health(self, qdrant_client) -> dict[str, Any]:
        """Check Qdrant connection health."""
        try:
            if not qdrant_client:
                return {"status": "unavailable", "reason": "No client provided"}

            # Try to get collection info
            collections = await qdrant_client.get_collections()

            if collections is not None:
                return {
                    "status": "healthy",
                    "collections_count": len(collections)
                    if hasattr(collections, "__len__")
                    else 0,
                }
            return {"status": "unhealthy", "reason": "Could not retrieve collections"}

        except Exception as e:
            return {"status": "error", "reason": str(e)}

    async def get_integration_health(
        self,
        database_client=None,
        neo4j_driver=None,
    ) -> dict[str, Any]:
        """Get overall integration health status."""
        health_status = {
            "overall_status": "unknown",
            "timestamp": time.time(),
            "components": {},
        }

        # Check Qdrant health
        qdrant_health = await self.check_qdrant_health(database_client)
        health_status["components"]["qdrant"] = qdrant_health

        # Check Neo4j health
        neo4j_health = await self.check_neo4j_health(neo4j_driver)
        health_status["components"]["neo4j"] = neo4j_health

        # Determine overall status
        qdrant_ok = qdrant_health["status"] in ["healthy", "unavailable"]
        neo4j_ok = neo4j_health["status"] in ["healthy", "unavailable"]

        if qdrant_ok and neo4j_ok:
            # Both components are working or gracefully unavailable
            if (
                qdrant_health["status"] == "healthy"
                and neo4j_health["status"] == "healthy"
            ):
                health_status["overall_status"] = "fully_operational"
            elif (
                qdrant_health["status"] == "healthy"
                or neo4j_health["status"] == "healthy"
            ):
                health_status["overall_status"] = "partially_operational"
            else:
                health_status["overall_status"] = "degraded"
        else:
            health_status["overall_status"] = "error"

        return health_status


class PerformanceOptimizer:
    """
    Performance optimization utilities for the integration layer.
    """

    def __init__(self):
        self.cache = PerformanceCache()
        self.batch_processor = BatchProcessor()
        self.circuit_breaker = CircuitBreaker()
        self.health_monitor = IntegrationHealthMonitor()

    @performance_monitor
    async def optimize_search_query(self, query: str, context: dict[str, Any]) -> str:
        """
        Optimize search queries for better performance and accuracy.

        Args:
            query: Original search query
            context: Additional context for optimization

        Returns:
            Optimized search query
        """
        # Cache key for query optimization
        cache_key = create_cache_key("query_opt", query, context)

        # Check cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # Perform optimization
        optimized_query = self._apply_query_optimizations(query, context)

        # Cache the result
        await self.cache.set(cache_key, optimized_query, ttl=1800)  # 30 minutes

        return optimized_query

    def _apply_query_optimizations(self, query: str, context: dict[str, Any]) -> str:
        """Apply various query optimization techniques."""
        optimized = query.strip()

        # Add context-specific terms
        if context.get("code_type"):
            optimized = f"{context['code_type']} {optimized}"

        # Add programming language context
        if context.get("language"):
            optimized = f"{optimized} {context['language']}"

        # Remove redundant words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words = optimized.split()
        filtered_words = [word for word in words if word.lower() not in stop_words]

        if len(filtered_words) > 0:
            optimized = " ".join(filtered_words)

        return optimized

    async def get_performance_stats(self) -> dict[str, Any]:
        """Get comprehensive performance statistics."""
        return {
            "cache_stats": self.cache.get_stats(),
            "circuit_breaker_state": self.circuit_breaker.get_state(),
            "batch_processor": {
                "max_concurrent": self.batch_processor.max_concurrent,
                "batch_size": self.batch_processor.batch_size,
            },
        }

    async def cleanup(self):
        """Cleanup resources."""
        await self.cache.clear()


# Global performance optimizer instance
_performance_optimizer = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


async def validate_integration_health(
    database_client=None, neo4j_driver=None
) -> dict[str, Any]:
    """
    Quick health check for the integration layer.

    Args:
        database_client: Qdrant database client
        neo4j_driver: Neo4j driver

    Returns:
        Health status report
    """
    optimizer = get_performance_optimizer()
    return await optimizer.health_monitor.get_integration_health(
        database_client=database_client,
        neo4j_driver=neo4j_driver,
    )
