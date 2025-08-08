"""
Performance benchmark tests for integration scenarios.

Measures and validates performance characteristics:
- Throughput benchmarks for batch operations
- Latency measurements for real-time operations
- Memory and resource usage monitoring
- Scalability testing under load
- Performance regression detection
"""

import asyncio
import gc
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import psutil
import pytest

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))


class PerformanceMonitor:
    """Monitor system performance during tests."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = None
        self.start_time = None
        self.metrics = {}

    def start_monitoring(self):
        """Start performance monitoring."""
        self.start_memory = self.process.memory_info().rss
        self.start_time = time.time()
        gc.collect()  # Clean up before monitoring

    def stop_monitoring(self, operation_name: str):
        """Stop monitoring and record metrics."""
        end_time = time.time()
        end_memory = self.process.memory_info().rss

        self.metrics[operation_name] = {
            "duration_ms": (end_time - self.start_time) * 1000,
            "memory_delta_mb": (end_memory - self.start_memory) / 1024 / 1024,
            "peak_memory_mb": end_memory / 1024 / 1024,
            "cpu_percent": self.process.cpu_percent(),
        }

        return self.metrics[operation_name]


@pytest.fixture
def performance_monitor():
    """Provide performance monitoring capabilities."""
    return PerformanceMonitor()


@pytest.mark.integration
@pytest.mark.performance
class TestThroughputBenchmarks:
    """Test throughput for batch operations."""

    @pytest.mark.asyncio
    async def test_batch_crawl_throughput(
        self,
        qdrant_client,
        performance_monitor,
        performance_thresholds,
    ):
        """Benchmark batch crawling throughput."""

        # Generate test URLs - various sizes
        test_urls = []
        expected_results = []

        for i in range(20):  # Test with 20 URLs
            url = f"https://example.com/benchmark/{i}"
            content_size = 1000 + (i * 100)  # Varying content sizes
            content = f"Benchmark content {i}. " + "Test data. " * (content_size // 10)

            test_urls.append(url)
            expected_results.append(
                {
                    "url": url,
                    "extracted_content": content,
                    "markdown": f"# Page {i}\n{content}",
                    "success": True,
                    "status_code": 200,
                },
            )

        # Mock crawler for consistent results
        from unittest.mock import AsyncMock, MagicMock

        from crawl4ai_mcp import crawl_batch

        mock_crawler = AsyncMock()
        mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
        mock_crawler.__aexit__ = AsyncMock(return_value=None)
        mock_crawler.arun_many = AsyncMock(return_value=expected_results)

        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.database_client = qdrant_client
        mock_ctx.request_context.lifespan_context.crawler = mock_crawler
        mock_ctx.request_context.lifespan_context.reranking_model = None

        # Benchmark different concurrency levels
        concurrency_levels = [1, 2, 5, 10]
        results = {}

        for concurrency in concurrency_levels:
            performance_monitor.start_monitoring()

            with patch("src.utils.create_embedding") as mock_embeddings:
                mock_embeddings.return_value = [0.1] * 1536

                with patch("src.crawl4ai_mcp.mcp") as mock_mcp:
                    batch_func = (
                        crawl_batch.fn if hasattr(crawl_batch, "fn") else crawl_batch
                    )

                    start_time = time.time()
                    batch_results = await batch_func(
                        mock_ctx,
                        urls=test_urls,
                        store_results=True,
                        max_concurrent=concurrency,
                    )
                    end_time = time.time()

            metrics = performance_monitor.stop_monitoring(f"batch_crawl_c{concurrency}")

            # Calculate throughput
            duration_seconds = end_time - start_time
            throughput = len(test_urls) / duration_seconds

            results[concurrency] = {
                "urls_processed": len(batch_results),
                "duration_seconds": duration_seconds,
                "throughput_urls_per_second": throughput,
                "memory_usage_mb": metrics["memory_delta_mb"],
                "cpu_percent": metrics["cpu_percent"],
            }

            # Verify all URLs processed successfully
            assert len(batch_results) == len(test_urls)
            successful = sum(1 for r in batch_results if r["success"])
            assert successful == len(test_urls)

            print(
                f"Concurrency {concurrency}: {throughput:.2f} URLs/sec, {metrics['memory_delta_mb']:.1f}MB",
            )

        # Performance analysis
        best_throughput = max(
            results.values(),
            key=lambda x: x["throughput_urls_per_second"],
        )

        # Should achieve reasonable throughput
        assert (
            best_throughput["throughput_urls_per_second"] > 2.0
        )  # At least 2 URLs/sec

        # Memory usage should be reasonable
        for result in results.values():
            assert result["memory_usage_mb"] < 100  # Less than 100MB delta

        print(
            f"✅ Best throughput: {best_throughput['throughput_urls_per_second']:.2f} URLs/sec",
        )
        return results

    @pytest.mark.asyncio
    async def test_search_throughput(
        self,
        qdrant_client,
        performance_monitor,
        performance_thresholds,
    ):
        """Benchmark search operation throughput."""

        # Pre-populate database with test data
        test_documents = []
        for i in range(100):  # 100 test documents
            test_documents.append(
                {
                    "url": f"https://example.com/doc/{i}",
                    "content": f"Document {i} about topic {i % 10}. Contains keywords: search, benchmark, performance, test, data.",
                    "title": f"Test Document {i}",
                    "metadata": {"doc_id": i, "topic": i % 10, "category": "benchmark"},
                },
            )

        # Store all documents
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            for doc in test_documents:
                await qdrant_client.store_crawled_page(
                    url=doc["url"],
                    content=doc["content"],
                    title=doc["title"],
                    metadata=doc["metadata"],
                )

        print(f"Pre-populated database with {len(test_documents)} documents")

        # Test different search patterns
        search_queries = [
            "search benchmark performance",
            "topic 5 data keywords",
            "document test performance",
            "benchmark data search",
            "keywords performance test",
        ]

        # Sequential search benchmark
        performance_monitor.start_monitoring()

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()
            sequential_results = []

            for query in search_queries * 5:  # 25 total searches
                results = await qdrant_client.search_crawled_pages(
                    query=query,
                    match_count=10,
                )
                sequential_results.append(results)

            sequential_time = time.time() - start_time

        sequential_metrics = performance_monitor.stop_monitoring("sequential_search")
        sequential_throughput = len(sequential_results) / sequential_time

        # Concurrent search benchmark
        performance_monitor.start_monitoring()

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()

            # Create concurrent search tasks
            concurrent_tasks = []
            for query in search_queries * 5:  # 25 total searches
                task = qdrant_client.search_crawled_pages(query=query, match_count=10)
                concurrent_tasks.append(task)

            concurrent_results = await asyncio.gather(*concurrent_tasks)
            concurrent_time = time.time() - start_time

        concurrent_metrics = performance_monitor.stop_monitoring("concurrent_search")
        concurrent_throughput = len(concurrent_results) / concurrent_time

        # Verify search quality
        assert len(sequential_results) == 25
        assert len(concurrent_results) == 25

        for results in sequential_results + concurrent_results:
            assert len(results) <= 10  # Respects match_count limit
            for result in results:
                assert "content" in result
                assert "score" in result
                assert result["score"] >= 0  # Valid similarity score

        # Performance validation
        assert sequential_throughput > 5.0  # At least 5 searches/sec sequential
        assert (
            concurrent_throughput > sequential_throughput
        )  # Concurrent should be faster

        # Memory usage should be reasonable
        assert sequential_metrics["memory_delta_mb"] < 50
        assert concurrent_metrics["memory_delta_mb"] < 100

        print(
            f"✅ Search throughput: {sequential_throughput:.2f} seq, {concurrent_throughput:.2f} concurrent searches/sec",
        )

        return {
            "sequential_throughput": sequential_throughput,
            "concurrent_throughput": concurrent_throughput,
            "speedup_factor": concurrent_throughput / sequential_throughput,
        }

    @pytest.mark.asyncio
    async def test_storage_throughput(self, qdrant_client, performance_monitor):
        """Benchmark document storage throughput."""

        # Generate documents of varying sizes
        small_docs = [
            {
                "url": f"https://example.com/small/{i}",
                "content": f"Small document {i}. " + "Content. " * 50,  # ~500 chars
                "title": f"Small Doc {i}",
                "metadata": {"size": "small", "doc_id": i},
            }
            for i in range(50)
        ]

        large_docs = [
            {
                "url": f"https://example.com/large/{i}",
                "content": f"Large document {i}. " + "Detailed content. " * 500,  # ~8KB
                "title": f"Large Doc {i}",
                "metadata": {"size": "large", "doc_id": i},
            }
            for i in range(10)
        ]

        # Test small document storage
        performance_monitor.start_monitoring()

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()

            small_ids = []
            for doc in small_docs:
                doc_id = await qdrant_client.store_crawled_page(
                    url=doc["url"],
                    content=doc["content"],
                    title=doc["title"],
                    metadata=doc["metadata"],
                )
                small_ids.append(doc_id)

            small_time = time.time() - start_time

        small_metrics = performance_monitor.stop_monitoring("small_docs_storage")
        small_throughput = len(small_docs) / small_time

        # Test large document storage
        performance_monitor.start_monitoring()

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()

            large_ids = []
            for doc in large_docs:
                doc_id = await qdrant_client.store_crawled_page(
                    url=doc["url"],
                    content=doc["content"],
                    title=doc["title"],
                    metadata=doc["metadata"],
                )
                large_ids.append(doc_id)

            large_time = time.time() - start_time

        large_metrics = performance_monitor.stop_monitoring("large_docs_storage")
        large_throughput = len(large_docs) / large_time

        # Concurrent storage test
        performance_monitor.start_monitoring()

        mixed_docs = small_docs[:10] + large_docs[:5]  # 15 mixed documents

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()

            async def store_doc(doc):
                return await qdrant_client.store_crawled_page(
                    url=doc["url"],
                    content=doc["content"],
                    title=doc["title"],
                    metadata=doc["metadata"],
                )

            # Store concurrently
            concurrent_tasks = [store_doc(doc) for doc in mixed_docs]
            concurrent_ids = await asyncio.gather(*concurrent_tasks)

            concurrent_time = time.time() - start_time

        concurrent_metrics = performance_monitor.stop_monitoring("concurrent_storage")
        concurrent_throughput = len(mixed_docs) / concurrent_time

        # Verify all documents stored
        assert len(small_ids) == 50
        assert len(large_ids) == 10
        assert len(concurrent_ids) == 15
        assert all(
            doc_id is not None for doc_id in small_ids + large_ids + concurrent_ids
        )

        # Performance validation
        assert small_throughput > 5.0  # At least 5 small docs/sec
        assert large_throughput > 1.0  # At least 1 large doc/sec
        assert concurrent_throughput > large_throughput  # Concurrency helps

        print(
            f"✅ Storage throughput: {small_throughput:.2f} small, {large_throughput:.2f} large, {concurrent_throughput:.2f} concurrent docs/sec",
        )

        return {
            "small_doc_throughput": small_throughput,
            "large_doc_throughput": large_throughput,
            "concurrent_throughput": concurrent_throughput,
            "small_doc_memory_mb": small_metrics["memory_delta_mb"],
            "large_doc_memory_mb": large_metrics["memory_delta_mb"],
        }


@pytest.mark.integration
@pytest.mark.performance
class TestLatencyBenchmarks:
    """Test latency for real-time operations."""

    @pytest.mark.asyncio
    async def test_single_operation_latencies(
        self,
        qdrant_client,
        performance_thresholds,
    ):
        """Benchmark latency for individual operations."""

        # Pre-populate with some data for search tests
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            for i in range(10):
                await qdrant_client.store_crawled_page(
                    url=f"https://example.com/latency/{i}",
                    content=f"Latency test document {i} with searchable content.",
                    title=f"Latency Test {i}",
                    metadata={"test": "latency", "doc_id": i},
                )

        # Test storage latency
        storage_latencies = []

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            for i in range(10):
                start_time = time.time()

                doc_id = await qdrant_client.store_crawled_page(
                    url=f"https://example.com/latency-test/{i}",
                    content=f"Single operation latency test {i}.",
                    title=f"Latency Single {i}",
                    metadata={"test": "single_latency", "iteration": i},
                )

                latency = (time.time() - start_time) * 1000
                storage_latencies.append(latency)

                assert doc_id is not None

        # Test search latency
        search_latencies = []

        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            for i in range(10):
                start_time = time.time()

                results = await qdrant_client.search_crawled_pages(
                    query=f"latency test document {i}",
                    match_count=5,
                )

                latency = (time.time() - start_time) * 1000
                search_latencies.append(latency)

                assert len(results) > 0

        # Calculate statistics
        avg_storage_latency = sum(storage_latencies) / len(storage_latencies)
        p95_storage_latency = sorted(storage_latencies)[
            int(len(storage_latencies) * 0.95)
        ]

        avg_search_latency = sum(search_latencies) / len(search_latencies)
        p95_search_latency = sorted(search_latencies)[int(len(search_latencies) * 0.95)]

        # Performance validation
        assert avg_storage_latency < performance_thresholds["store_document_ms"]
        assert avg_search_latency < performance_thresholds["search_documents_ms"]
        assert p95_storage_latency < performance_thresholds["store_document_ms"] * 2
        assert p95_search_latency < performance_thresholds["search_documents_ms"] * 2

        print(
            f"✅ Latencies: Storage avg={avg_storage_latency:.1f}ms p95={p95_storage_latency:.1f}ms",
        )
        print(
            f"             Search avg={avg_search_latency:.1f}ms p95={p95_search_latency:.1f}ms",
        )

        return {
            "storage_avg_ms": avg_storage_latency,
            "storage_p95_ms": p95_storage_latency,
            "search_avg_ms": avg_search_latency,
            "search_p95_ms": p95_search_latency,
        }

    @pytest.mark.asyncio
    async def test_cold_start_performance(self, qdrant_client):
        """Benchmark cold start performance after service restart."""

        # Simulate cold start by creating a new client connection
        from database.qdrant_adapter import QdrantAdapter

        cold_client = QdrantAdapter(
            url="http://localhost:6333",
            api_key=None,
            collection_name="cold_start_test",
            vector_size=384,
        )

        # Measure initialization time
        start_time = time.time()
        await cold_client.initialize()
        init_time = (time.time() - start_time) * 1000

        # Measure first operation time
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()
            doc_id = await cold_client.store_crawled_page(
                url="https://example.com/cold-start",
                content="Cold start performance test document.",
                title="Cold Start Test",
                metadata={"test": "cold_start"},
            )
            first_op_time = (time.time() - start_time) * 1000

        # Measure second operation time (should be faster)
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            start_time = time.time()
            results = await cold_client.search_crawled_pages(
                query="cold start performance",
                match_count=5,
            )
            second_op_time = (time.time() - start_time) * 1000

        # Cleanup
        try:
            await cold_client.delete_collection()
        except:
            pass

        # Validation
        assert doc_id is not None
        assert len(results) >= 1
        assert init_time < 5000  # Should initialize in < 5 seconds
        assert first_op_time < 3000  # First operation < 3 seconds
        assert second_op_time < first_op_time  # Second operation should be faster

        print(
            f"✅ Cold start: init={init_time:.1f}ms, first_op={first_op_time:.1f}ms, second_op={second_op_time:.1f}ms",
        )

        return {
            "initialization_ms": init_time,
            "first_operation_ms": first_op_time,
            "second_operation_ms": second_op_time,
            "warmup_improvement_factor": first_op_time / second_op_time,
        }


@pytest.mark.integration
@pytest.mark.performance
class TestScalabilityBenchmarks:
    """Test system behavior under increasing load."""

    @pytest.mark.asyncio
    async def test_database_size_scaling(self, qdrant_client, performance_monitor):
        """Test performance as database size increases."""

        # Test different database sizes
        size_levels = [100, 500, 1000]  # Number of documents
        results = {}

        for size in size_levels:
            print(f"Testing with {size} documents...")

            # Populate database to target size
            with patch("src.utils.create_embedding") as mock_embeddings:
                mock_embeddings.return_value = [0.1] * 1536

                # Add documents in batches for efficiency
                batch_size = 50
                for batch_start in range(0, size, batch_size):
                    batch_end = min(batch_start + batch_size, size)
                    batch_tasks = []

                    for i in range(batch_start, batch_end):
                        task = qdrant_client.store_crawled_page(
                            url=f"https://example.com/scale/{size}/{i}",
                            content=f"Scaling test document {i} for size {size}. Contains topic {i % 20}.",
                            title=f"Scale Test {size}-{i}",
                            metadata={"size_test": size, "doc_id": i, "topic": i % 20},
                        )
                        batch_tasks.append(task)

                    await asyncio.gather(*batch_tasks)

            # Measure search performance at this size
            performance_monitor.start_monitoring()

            with patch("src.utils.create_embedding") as mock_embeddings:
                mock_embeddings.return_value = [0.1] * 1536

                search_times = []
                for i in range(10):  # 10 test searches
                    start_time = time.time()

                    search_results = await qdrant_client.search_crawled_pages(
                        query=f"scaling test topic {i % 20}",
                        match_count=10,
                    )

                    search_time = (time.time() - start_time) * 1000
                    search_times.append(search_time)

                    assert len(search_results) > 0

            metrics = performance_monitor.stop_monitoring(f"search_size_{size}")

            avg_search_time = sum(search_times) / len(search_times)

            results[size] = {
                "avg_search_time_ms": avg_search_time,
                "memory_usage_mb": metrics["memory_delta_mb"],
                "cpu_percent": metrics["cpu_percent"],
            }

            print(
                f"Size {size}: avg search {avg_search_time:.1f}ms, memory {metrics['memory_delta_mb']:.1f}MB",
            )

        # Analyze scaling behavior
        search_times = [results[size]["avg_search_time_ms"] for size in size_levels]

        # Search time should scale sub-linearly (logarithmically) with database size
        # Ratio should be less than the size ratio
        small_to_medium_ratio = search_times[1] / search_times[0]
        medium_to_large_ratio = search_times[2] / search_times[1]

        size_ratio_1 = size_levels[1] / size_levels[0]  # 5x
        size_ratio_2 = size_levels[2] / size_levels[1]  # 2x

        # Performance should scale better than linear
        assert small_to_medium_ratio < size_ratio_1
        assert medium_to_large_ratio < size_ratio_2

        print(
            f"✅ Scaling: {size_levels[0]}→{size_levels[1]} docs: {small_to_medium_ratio:.2f}x time vs {size_ratio_1:.1f}x size",
        )

        return results

    @pytest.mark.asyncio
    async def test_concurrent_user_simulation(self, qdrant_client, performance_monitor):
        """Simulate multiple concurrent users."""

        # Pre-populate database
        with patch("src.utils.create_embedding") as mock_embeddings:
            mock_embeddings.return_value = [0.1] * 1536

            for i in range(200):
                await qdrant_client.store_crawled_page(
                    url=f"https://example.com/concurrent/{i}",
                    content=f"Concurrent test document {i} about subject {i % 10}.",
                    title=f"Concurrent {i}",
                    metadata={"concurrent_test": True, "doc_id": i, "subject": i % 10},
                )

        # Simulate different numbers of concurrent users
        user_counts = [1, 5, 10, 20]
        results = {}

        for user_count in user_counts:
            print(f"Testing with {user_count} concurrent users...")

            performance_monitor.start_monitoring()

            async def simulate_user(user_id: int):
                """Simulate a single user's behavior."""
                user_results = []

                with patch("src.utils.create_embedding") as mock_embeddings:
                    mock_embeddings.return_value = [0.1] * 1536

                    # Each user performs multiple operations
                    for operation in range(5):
                        # Mix of searches and stores
                        if operation % 2 == 0:
                            # Search operation
                            start_time = time.time()
                            search_results = await qdrant_client.search_crawled_pages(
                                query=f"concurrent subject {(user_id + operation) % 10}",
                                match_count=5,
                            )
                            operation_time = (time.time() - start_time) * 1000

                            user_results.append(
                                {
                                    "type": "search",
                                    "time_ms": operation_time,
                                    "results": len(search_results),
                                },
                            )
                        else:
                            # Store operation
                            start_time = time.time()
                            doc_id = await qdrant_client.store_crawled_page(
                                url=f"https://example.com/user/{user_id}/op/{operation}",
                                content=f"User {user_id} operation {operation} document.",
                                title=f"User {user_id} Op {operation}",
                                metadata={"user_id": user_id, "operation": operation},
                            )
                            operation_time = (time.time() - start_time) * 1000

                            user_results.append(
                                {
                                    "type": "store",
                                    "time_ms": operation_time,
                                    "success": doc_id is not None,
                                },
                            )

                return user_results

            # Run concurrent user simulations
            start_time = time.time()
            user_tasks = [simulate_user(i) for i in range(user_count)]
            all_user_results = await asyncio.gather(*user_tasks)
            total_time = time.time() - start_time

            metrics = performance_monitor.stop_monitoring(
                f"concurrent_{user_count}_users",
            )

            # Analyze results
            all_operations = []
            for user_results in all_user_results:
                all_operations.extend(user_results)

            search_times = [
                op["time_ms"] for op in all_operations if op["type"] == "search"
            ]
            store_times = [
                op["time_ms"] for op in all_operations if op["type"] == "store"
            ]

            avg_search_time = (
                sum(search_times) / len(search_times) if search_times else 0
            )
            avg_store_time = sum(store_times) / len(store_times) if store_times else 0

            total_operations = len(all_operations)
            throughput = total_operations / total_time

            results[user_count] = {
                "total_operations": total_operations,
                "total_time_seconds": total_time,
                "throughput_ops_per_second": throughput,
                "avg_search_time_ms": avg_search_time,
                "avg_store_time_ms": avg_store_time,
                "memory_usage_mb": metrics["memory_delta_mb"],
                "cpu_percent": metrics["cpu_percent"],
            }

            print(
                f"Users {user_count}: {throughput:.2f} ops/sec, search {avg_search_time:.1f}ms, store {avg_store_time:.1f}ms",
            )

        # Validate scaling behavior
        throughputs = [
            results[count]["throughput_ops_per_second"] for count in user_counts
        ]

        # Throughput should generally increase with more users (up to a point)
        assert throughputs[1] > throughputs[0]  # 5 users > 1 user
        assert throughputs[2] > throughputs[0]  # 10 users > 1 user

        # Response times shouldn't degrade too much under load
        search_times = [results[count]["avg_search_time_ms"] for count in user_counts]
        max_search_time = max(search_times)
        min_search_time = min(search_times)

        assert max_search_time / min_search_time < 5  # < 5x degradation

        print(f"✅ Concurrent users: Peak throughput {max(throughputs):.2f} ops/sec")

        return results


@pytest.mark.integration
@pytest.mark.performance
class TestResourceUsageBenchmarks:
    """Test resource usage patterns."""

    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self, qdrant_client, performance_monitor):
        """Test memory usage under different workloads."""

        # Baseline memory usage
        gc.collect()
        baseline_memory = psutil.Process().memory_info().rss / 1024 / 1024

        workloads = {
            "small_docs": {
                "count": 100,
                "content_size": 500,
                "description": "Small documents",
            },
            "large_docs": {
                "count": 20,
                "content_size": 5000,
                "description": "Large documents",
            },
            "mixed_workload": {
                "count": 50,
                "content_size": "mixed",
                "description": "Mixed size documents",
            },
        }

        results = {}

        for workload_name, config in workloads.items():
            print(f"Testing {config['description']}...")

            performance_monitor.start_monitoring()

            # Generate test documents
            if config["content_size"] == "mixed":
                test_docs = []
                for i in range(config["count"]):
                    size = 500 if i % 2 == 0 else 5000
                    content = f"Mixed workload doc {i}. " + "Content. " * (size // 10)
                    test_docs.append(
                        {
                            "url": f"https://example.com/memory/{workload_name}/{i}",
                            "content": content,
                            "title": f"Memory Test {workload_name} {i}",
                            "metadata": {"workload": workload_name, "doc_id": i},
                        },
                    )
            else:
                test_docs = []
                for i in range(config["count"]):
                    content = f"Memory test doc {i}. " + "Content. " * (
                        config["content_size"] // 10
                    )
                    test_docs.append(
                        {
                            "url": f"https://example.com/memory/{workload_name}/{i}",
                            "content": content,
                            "title": f"Memory Test {workload_name} {i}",
                            "metadata": {"workload": workload_name, "doc_id": i},
                        },
                    )

            # Store documents and monitor memory
            memory_snapshots = []

            with patch("src.utils.create_embedding") as mock_embeddings:
                mock_embeddings.return_value = [0.1] * 1536

                for i, doc in enumerate(test_docs):
                    await qdrant_client.store_crawled_page(
                        url=doc["url"],
                        content=doc["content"],
                        title=doc["title"],
                        metadata=doc["metadata"],
                    )

                    # Take memory snapshot every 10 documents
                    if i % 10 == 0:
                        current_memory = (
                            psutil.Process().memory_info().rss / 1024 / 1024
                        )
                        memory_snapshots.append(current_memory - baseline_memory)

            metrics = performance_monitor.stop_monitoring(workload_name)

            # Analyze memory usage
            peak_memory_delta = max(memory_snapshots) if memory_snapshots else 0
            final_memory_delta = memory_snapshots[-1] if memory_snapshots else 0
            memory_growth = (
                (memory_snapshots[-1] - memory_snapshots[0])
                if len(memory_snapshots) > 1
                else 0
            )

            results[workload_name] = {
                "documents_processed": len(test_docs),
                "peak_memory_delta_mb": peak_memory_delta,
                "final_memory_delta_mb": final_memory_delta,
                "memory_growth_mb": memory_growth,
                "memory_per_doc_kb": (final_memory_delta * 1024) / len(test_docs)
                if test_docs
                else 0,
            }

            print(
                f"{config['description']}: {peak_memory_delta:.1f}MB peak, {final_memory_delta:.1f}MB final",
            )

            # Force garbage collection between workloads
            gc.collect()

        # Memory usage validation
        for workload_name, result in results.items():
            # Memory usage should be reasonable
            assert result["peak_memory_delta_mb"] < 200  # Less than 200MB peak
            assert result["memory_per_doc_kb"] < 500  # Less than 500KB per document

            # Memory shouldn't grow excessively during processing
            if result["memory_growth_mb"] > 0:
                growth_ratio = (
                    result["memory_growth_mb"] / result["final_memory_delta_mb"]
                )
                assert growth_ratio < 2.0  # Growth should be < 200% of final usage

        print("✅ Memory usage within acceptable bounds for all workloads")

        return results
