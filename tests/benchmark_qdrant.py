"""
Performance benchmarks for Qdrant vector database.
Measures insertion rate, search latency, and concurrent operation performance.
"""

import asyncio
import time
import statistics
import os
import sys
import random
import string
from typing import List, Dict, Any, Tuple

from database.factory import create_database_client, create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter


class QdrantBenchmark:
    """Automated performance benchmarks for Qdrant"""
    
    def __init__(self):
        # Ensure Qdrant configuration
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = os.getenv("QDRANT_URL", "http://localhost:6333")
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
        
        self.results = {
            "insertion": {},
            "search": {},
            "concurrent": {}
        }
    
    def generate_test_content(self, index: int, size: int = 500) -> str:
        """Generate realistic test content"""
        topics = [
            "web crawling", "data extraction", "machine learning",
            "natural language processing", "vector databases",
            "information retrieval", "search engines", "AI systems"
        ]
        
        topic = topics[index % len(topics)]
        content = f"Document {index} about {topic}. "
        
        # Add random but realistic content
        sentences = [
            f"This document discusses advanced techniques in {topic}.",
            f"Modern approaches to {topic} involve sophisticated algorithms.",
            f"The field of {topic} has evolved significantly in recent years.",
            f"Best practices for {topic} include proper error handling.",
            f"Performance optimization is crucial for {topic} applications.",
            f"Scalability challenges in {topic} require careful consideration.",
            f"Security aspects of {topic} cannot be overlooked.",
            f"Future developments in {topic} look promising."
        ]
        
        # Build content to approximately desired size
        while len(content) < size:
            content += " " + random.choice(sentences)
        
        return content[:size]
    
    async def benchmark_insertion(self, num_docs: int = 1000) -> float:
        """Benchmark document insertion performance"""
        print(f"\n📊 Starting Insertion Benchmark ({num_docs} documents)")
        
        client = create_database_client()
        
        # Generate test documents
        documents = []
        for i in range(num_docs):
            documents.append({
                "url": f"https://benchmark.com/insertion/doc{i}",
                "content": self.generate_test_content(i),
                "metadata": {
                    "source": "benchmark.com",
                    "batch": "insertion_test",
                    "index": i,
                    "timestamp": time.time()
                }
            })
        
        # Measure insertion time
        start_time = time.time()
        successful_inserts = 0
        failed_inserts = 0
        
        # Insert in batches for efficiency
        batch_size = 10
        for i in range(0, num_docs, batch_size):
            batch = documents[i:i+batch_size]
            try:
                # Store documents in parallel within batch
                tasks = []
                for doc in batch:
                    tasks.append(store_crawled_page(
                        client,
                        doc["url"],
                        doc["content"],
                        doc["metadata"]
                    ))
                
                await asyncio.gather(*tasks)
                successful_inserts += len(batch)
            except Exception as e:
                print(f"   ⚠️  Batch insertion failed: {e}")
                failed_inserts += len(batch)
        
        insertion_time = time.time() - start_time
        docs_per_second = successful_inserts / insertion_time if insertion_time > 0 else 0
        
        # Store results
        self.results["insertion"] = {
            "total_documents": num_docs,
            "successful": successful_inserts,
            "failed": failed_inserts,
            "total_time": insertion_time,
            "docs_per_second": docs_per_second
        }
        
        print(f"   ✅ Insertion Complete:")
        print(f"      - Documents: {successful_inserts}/{num_docs}")
        print(f"      - Total time: {insertion_time:.2f}s")
        print(f"      - Rate: {docs_per_second:.2f} docs/sec")
        print(f"      - Success rate: {(successful_inserts/num_docs)*100:.1f}%")
        
        # Assert minimum performance
        assert docs_per_second > 5, f"Insertion too slow: {docs_per_second:.2f} docs/sec (minimum: 5)"
        assert successful_inserts >= num_docs * 0.95, f"Too many failures: {failed_inserts}"
        
        return docs_per_second
    
    async def benchmark_search(self, num_queries: int = 100) -> Tuple[float, float]:
        """Benchmark search performance"""
        print(f"\n🔍 Starting Search Benchmark ({num_queries} queries)")
        
        client = create_database_client()
        
        # Ensure we have documents to search
        await self._ensure_test_data(client)
        
        # Prepare diverse queries
        query_terms = [
            "web crawling techniques",
            "data extraction methods",
            "machine learning algorithms",
            "natural language processing",
            "vector database optimization",
            "information retrieval systems",
            "search engine architecture",
            "AI system design",
            "performance optimization",
            "scalability challenges"
        ]
        
        queries = []
        for i in range(num_queries):
            # Mix single terms and phrases
            if i % 2 == 0:
                queries.append(random.choice(query_terms))
            else:
                # Combine two terms
                terms = random.sample(query_terms, 2)
                queries.append(f"{terms[0]} {terms[1]}")
        
        # Measure search latencies
        latencies = []
        successful_searches = 0
        start_time = time.time()
        
        for query in queries:
            query_start = time.time()
            try:
                results = await search_crawled_pages(client, query, limit=10)
                latencies.append(time.time() - query_start)
                successful_searches += 1
            except Exception as e:
                print(f"   ⚠️  Search failed for '{query}': {e}")
        
        total_time = time.time() - start_time
        
        if latencies:
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else max(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            avg_latency = p95_latency = p99_latency = min_latency = max_latency = 0
        
        # Store results
        self.results["search"] = {
            "total_queries": num_queries,
            "successful": successful_searches,
            "avg_latency_ms": avg_latency * 1000,
            "p95_latency_ms": p95_latency * 1000,
            "p99_latency_ms": p99_latency * 1000,
            "min_latency_ms": min_latency * 1000,
            "max_latency_ms": max_latency * 1000,
            "queries_per_second": num_queries / total_time if total_time > 0 else 0
        }
        
        print(f"   ✅ Search Complete:")
        print(f"      - Queries: {successful_searches}/{num_queries}")
        print(f"      - Avg latency: {avg_latency*1000:.2f}ms")
        print(f"      - P95 latency: {p95_latency*1000:.2f}ms")
        print(f"      - P99 latency: {p99_latency*1000:.2f}ms")
        print(f"      - Min/Max: {min_latency*1000:.2f}ms / {max_latency*1000:.2f}ms")
        print(f"      - Throughput: {num_queries/total_time:.2f} queries/sec")
        
        # Assert performance requirements
        assert avg_latency < 0.1, f"Average latency too high: {avg_latency*1000:.2f}ms (max: 100ms)"
        assert p95_latency < 0.2, f"P95 latency too high: {p95_latency*1000:.2f}ms (max: 200ms)"
        assert successful_searches >= num_queries * 0.95, f"Too many search failures"
        
        return avg_latency, p95_latency
    
    async def benchmark_concurrent_load(self, num_workers: int = 10) -> float:
        """Benchmark concurrent operations"""
        print(f"\n🔄 Starting Concurrent Load Benchmark ({num_workers} workers)")
        
        client = create_database_client()
        
        # Ensure test data exists
        await self._ensure_test_data(client)
        
        operation_times = []
        errors = []
        
        async def worker(worker_id: int) -> List[Tuple[str, float]]:
            """Simulate concurrent user with mixed operations"""
            worker_operations = []
            
            for i in range(10):
                try:
                    # Mix of operations (70% reads, 30% writes)
                    if random.random() < 0.7:
                        # Read operation
                        start = time.time()
                        query = f"worker {worker_id} document {i % 5}"
                        await search_crawled_pages(client, query, limit=5)
                        operation_time = time.time() - start
                        worker_operations.append(("read", operation_time))
                    else:
                        # Write operation
                        start = time.time()
                        await store_crawled_page(
                            client,
                            f"https://concurrent.com/w{worker_id}/d{i}",
                            f"Concurrent test document from worker {worker_id} iteration {i}",
                            {"source": "concurrent.com", "worker": worker_id}
                        )
                        operation_time = time.time() - start
                        worker_operations.append(("write", operation_time))
                    
                    # Small delay to simulate realistic load
                    await asyncio.sleep(random.uniform(0.01, 0.05))
                    
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {str(e)}")
            
            return worker_operations
        
        # Run concurrent workers
        start_time = time.time()
        
        # Create worker tasks
        tasks = [worker(i) for i in range(num_workers)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_operations = []
        for result in results:
            if isinstance(result, list):
                all_operations.extend(result)
            else:
                errors.append(str(result))
        
        if all_operations:
            write_times = [t for op, t in all_operations if op == "write"]
            read_times = [t for op, t in all_operations if op == "read"]
            
            write_avg = statistics.mean(write_times) if write_times else 0
            read_avg = statistics.mean(read_times) if read_times else 0
            
            # Store results
            self.results["concurrent"] = {
                "num_workers": num_workers,
                "total_operations": len(all_operations),
                "write_operations": len(write_times),
                "read_operations": len(read_times),
                "total_time": total_time,
                "avg_write_time_ms": write_avg * 1000,
                "avg_read_time_ms": read_avg * 1000,
                "operations_per_second": len(all_operations) / total_time if total_time > 0 else 0,
                "errors": len(errors)
            }
            
            print(f"   ✅ Concurrent Load Complete:")
            print(f"      - Workers: {num_workers}")
            print(f"      - Total operations: {len(all_operations)}")
            print(f"      - Write operations: {len(write_times)} (avg: {write_avg*1000:.2f}ms)")
            print(f"      - Read operations: {len(read_times)} (avg: {read_avg*1000:.2f}ms)")
            print(f"      - Completion time: {total_time:.2f}s")
            print(f"      - Throughput: {len(all_operations)/total_time:.2f} ops/sec")
            print(f"      - Errors: {len(errors)}")
            
            # Assert performance requirements
            assert total_time < 30, f"Concurrent operations too slow: {total_time:.2f}s"
            assert len(errors) < len(all_operations) * 0.05, f"Too many errors: {len(errors)}"
            assert write_avg < 0.5, f"Write operations too slow: {write_avg*1000:.2f}ms"
            assert read_avg < 0.2, f"Read operations too slow: {read_avg*1000:.2f}ms"
        
        return total_time
    
    async def _ensure_test_data(self, client) -> None:
        """Ensure there's data to search"""
        # Check if we already have test data
        try:
            results = await search_crawled_pages(client, "document", limit=1)
            if len(results) > 0:
                return
        except:
            pass
        
        # Insert some test data
        print("   📝 Inserting test data for search benchmark...")
        for i in range(100):
            await store_crawled_page(
                client,
                f"https://searchtest.com/doc{i}",
                self.generate_test_content(i),
                {"source": "searchtest.com", "index": i}
            )
        
        # Allow indexing
        await asyncio.sleep(2)
    
    def generate_report(self) -> str:
        """Generate a comprehensive benchmark report"""
        report = [
            "\n" + "="*60,
            "📊 QDRANT PERFORMANCE BENCHMARK REPORT",
            "="*60,
            ""
        ]
        
        # Insertion results
        if self.results["insertion"]:
            r = self.results["insertion"]
            report.extend([
                "1. INSERTION PERFORMANCE",
                f"   Documents inserted: {r['successful']}/{r['total_documents']}",
                f"   Time taken: {r['total_time']:.2f}s",
                f"   Rate: {r['docs_per_second']:.2f} docs/sec",
                f"   ✅ PASSED (minimum: 5 docs/sec)" if r['docs_per_second'] > 5 else "❌ FAILED",
                ""
            ])
        
        # Search results
        if self.results["search"]:
            r = self.results["search"]
            report.extend([
                "2. SEARCH PERFORMANCE",
                f"   Queries executed: {r['successful']}/{r['total_queries']}",
                f"   Average latency: {r['avg_latency_ms']:.2f}ms",
                f"   P95 latency: {r['p95_latency_ms']:.2f}ms",
                f"   P99 latency: {r['p99_latency_ms']:.2f}ms",
                f"   Throughput: {r['queries_per_second']:.2f} queries/sec",
                f"   ✅ PASSED (avg<100ms, p95<200ms)" if r['avg_latency_ms'] < 100 and r['p95_latency_ms'] < 200 else "❌ FAILED",
                ""
            ])
        
        # Concurrent results
        if self.results["concurrent"]:
            r = self.results["concurrent"]
            report.extend([
                "3. CONCURRENT OPERATIONS",
                f"   Workers: {r['num_workers']}",
                f"   Total operations: {r['total_operations']}",
                f"   Write latency: {r['avg_write_time_ms']:.2f}ms",
                f"   Read latency: {r['avg_read_time_ms']:.2f}ms",
                f"   Total time: {r['total_time']:.2f}s",
                f"   Throughput: {r['operations_per_second']:.2f} ops/sec",
                f"   Errors: {r['errors']}",
                f"   ✅ PASSED (time<30s)" if r['total_time'] < 30 else "❌ FAILED",
                ""
            ])
        
        report.extend([
            "="*60,
            "OVERALL RESULT: " + (
                "✅ ALL BENCHMARKS PASSED" 
                if all(self._check_benchmark_passed(k) for k in self.results if self.results[k])
                else "❌ SOME BENCHMARKS FAILED"
            ),
            "="*60
        ])
        
        return "\n".join(report)
    
    def _check_benchmark_passed(self, benchmark_type: str) -> bool:
        """Check if a benchmark passed its criteria"""
        r = self.results.get(benchmark_type, {})
        if not r:
            return False
        
        if benchmark_type == "insertion":
            return r.get('docs_per_second', 0) > 5
        elif benchmark_type == "search":
            return r.get('avg_latency_ms', 1000) < 100 and r.get('p95_latency_ms', 1000) < 200
        elif benchmark_type == "concurrent":
            return r.get('total_time', 100) < 30
        
        return False


async def run_benchmarks():
    """Run all benchmarks with proper setup"""
    benchmark = QdrantBenchmark()
    
    print("🚀 Starting Qdrant Performance Benchmarks")
    print("   Qdrant URL:", os.getenv("QDRANT_URL", "http://localhost:6333"))
    print()
    
    try:
        # 1. Insertion benchmark
        await benchmark.benchmark_insertion(1000)
        
        # 2. Search benchmark
        await benchmark.benchmark_search(100)
        
        # 3. Concurrent load benchmark
        await benchmark.benchmark_concurrent_load(10)
        
        # Generate and print report
        report = benchmark.generate_report()
        print(report)
        
        # Save report to file
        with open("benchmark_results.txt", "w") as f:
            f.write(report)
        print("\n📄 Report saved to benchmark_results.txt")
        
        # Return success if all benchmarks passed
        all_passed = all(benchmark._check_benchmark_passed(k) for k in benchmark.results if benchmark.results[k])
        return 0 if all_passed else 1
        
    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(run_benchmarks())
    sys.exit(exit_code)