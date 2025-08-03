"""
Integration tests for Qdrant vector database implementation.
Tests real Qdrant operations with automated container management.
"""

import pytest
import asyncio
import os
import time
import json
import sys
from typing import List, Dict, Any
from testcontainers.compose import DockerCompose

from database.factory import create_database_client, create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter


class TestQdrantIntegration:
    """Fully automated Qdrant integration tests"""
    
    @classmethod
    def setup_class(cls):
        """Start Qdrant container for testing"""
        # Set environment for Qdrant
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
        
        # For CI environment, assume Qdrant is already running
        # For local testing, you can use docker-compose
        cls.qdrant_running = cls._check_qdrant_health()
        if not cls.qdrant_running:
            pytest.skip("Qdrant not running. Start with: docker run -p 6333:6333 qdrant/qdrant")
    
    @classmethod
    def _check_qdrant_health(cls) -> bool:
        """Check if Qdrant is healthy"""
        import requests
        try:
            response = requests.get("http://localhost:6333/healthz", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    @pytest.mark.asyncio
    async def test_qdrant_connection(self):
        """Test Qdrant connection and health"""
        client = create_database_client()
        assert isinstance(client, QdrantAdapter)
        
        # Test collection creation
        await client.ensure_collection_exists("test_collection")
        
        # Verify client is properly initialized
        assert client.client is not None
        assert client.collection_name == "crawled_pages"
    
    @pytest.mark.asyncio
    async def test_complete_crawl_workflow(self):
        """Test end-to-end crawl -> store -> search workflow"""
        client = create_database_client()
        
        # 1. Store test document
        test_doc = {
            "url": "https://example.com/test",
            "content": "This is a test document about Python programming and web crawling. "
                      "It contains information about async programming, web scraping, "
                      "and building robust crawlers with error handling.",
            "metadata": {
                "source": "example.com",
                "timestamp": "2024-01-01T00:00:00Z",
                "doc_type": "article"
            }
        }
        
        # Store the document
        await store_crawled_page(
            client,
            test_doc["url"],
            test_doc["content"],
            test_doc["metadata"]
        )
        
        # Allow time for indexing
        await asyncio.sleep(1)
        
        # 2. Search for content
        results = await search_crawled_pages(
            client,
            "Python programming web crawling",
            source="example.com",
            limit=5
        )
        
        # Verify results
        assert len(results) > 0
        assert results[0]["url"] == test_doc["url"]
        assert results[0]["similarity_score"] > 0.5
        assert "Python programming" in results[0]["content"]
        
        # 3. Test source filtering
        results_filtered = await search_crawled_pages(
            client,
            "Python programming",
            source="nonexistent.com"
        )
        assert len(results_filtered) == 0
    
    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """Test batch document operations"""
        client = create_database_client()
        
        # Create 100 test documents
        documents = []
        for i in range(100):
            documents.append({
                "url": f"https://batchtest.com/doc{i}",
                "content": f"Document {i} content with unique text pattern {i}. "
                          f"This document discusses topic {i % 10} in detail.",
                "metadata": {
                    "source": "batchtest.com",
                    "batch": "test",
                    "index": i,
                    "topic": f"topic_{i % 10}"
                }
            })
        
        # Batch store with timing
        start_time = time.time()
        
        # Store in batches of 10 for efficiency
        for i in range(0, len(documents), 10):
            batch = documents[i:i+10]
            batch_docs = []
            
            for doc in batch:
                # Create embedding
                embedding = await create_embedding(doc["content"])
                batch_docs.append({
                    "id": hash(doc["url"]) & 0x7FFFFFFF,  # Ensure positive ID
                    "url": doc["url"],
                    "content": doc["content"],
                    "content_hash": str(hash(doc["content"])),
                    "metadata": doc["metadata"],
                    "embedding": embedding
                })
            
            await client.store_documents(batch_docs)
        
        store_time = time.time() - start_time
        docs_per_second = len(documents) / store_time
        
        print(f"Stored {len(documents)} documents in {store_time:.2f}s ({docs_per_second:.2f} docs/sec)")
        
        # Allow indexing time
        await asyncio.sleep(2)
        
        # Verify all stored
        results = await client.search_documents_by_keyword("Document", limit=150)
        assert len(results) >= 50  # Should find many documents
        
        # Performance assertion
        assert store_time < 60  # Should complete in under 60 seconds
        assert docs_per_second > 1.5  # At least 1.5 docs/sec
        
        # Test batch retrieval by metadata
        topic_results = await search_crawled_pages(
            client,
            "topic 5",
            source="batchtest.com",
            limit=20
        )
        assert len(topic_results) > 0
    
    @pytest.mark.asyncio
    async def test_rag_strategies(self):
        """Test all RAG strategies work with Qdrant"""
        client = create_database_client()
        
        # Setup test data
        test_docs = [
            {
                "url": "https://ragtest.com/doc1",
                "content": "Advanced Python programming techniques for async web crawling",
                "metadata": {"source": "ragtest.com"}
            },
            {
                "url": "https://ragtest.com/doc2",
                "content": "Web scraping best practices and error handling strategies",
                "metadata": {"source": "ragtest.com"}
            },
            {
                "url": "https://ragtest.com/doc3",
                "content": "Building scalable crawlers with Python and asyncio",
                "metadata": {"source": "ragtest.com"}
            }
        ]
        
        # Store test documents
        for doc in test_docs:
            await store_crawled_page(client, doc["url"], doc["content"], doc["metadata"])
        
        await asyncio.sleep(1)
        
        # Test standard search
        os.environ["USE_HYBRID_SEARCH"] = "false"
        os.environ["USE_RERANKING"] = "false"
        
        results = await search_crawled_pages(
            client,
            "Python async programming",
            limit=5
        )
        assert len(results) > 0
        standard_score = results[0]["similarity_score"]
        
        # Test with hybrid search
        os.environ["USE_HYBRID_SEARCH"] = "true"
        results_hybrid = await search_crawled_pages(
            client,
            "Python async programming",
            limit=5
        )
        assert len(results_hybrid) > 0
        
        # Test with reranking (mock since we need cross-encoder)
        os.environ["USE_RERANKING"] = "true"
        results_reranked = await search_crawled_pages(
            client,
            "Python async programming",
            limit=5
        )
        assert len(results_reranked) > 0
        
        # Reset flags
        os.environ["USE_HYBRID_SEARCH"] = "false"
        os.environ["USE_RERANKING"] = "false"
    
    @pytest.mark.asyncio
    async def test_code_examples_workflow(self):
        """Test code example storage and retrieval"""
        client = create_database_client()
        
        # Store code examples
        code_examples = [
            {
                "code": """
import asyncio
import aiohttp

async def fetch_url(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    async with aiohttp.ClientSession() as session:
        html = await fetch_url(session, 'https://example.com')
        print(html)
""",
                "summary": "Async HTTP fetching with aiohttp",
                "language": "python",
                "source_url": "https://codetest.com/async-example",
                "metadata": {"topic": "async", "library": "aiohttp"}
            },
            {
                "code": """
from bs4 import BeautifulSoup
import requests

def scrape_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.find_all('a')
""",
                "summary": "Web scraping with BeautifulSoup",
                "language": "python",
                "source_url": "https://codetest.com/scraping-example",
                "metadata": {"topic": "scraping", "library": "beautifulsoup"}
            }
        ]
        
        # Store code examples
        for example in code_examples:
            await store_code_example(
                client,
                example["code"],
                example["summary"],
                example["language"],
                example["source_url"],
                example["metadata"]
            )
        
        await asyncio.sleep(1)
        
        # Search for code examples
        results = await search_code_examples(
            client,
            "async http fetching",
            limit=5
        )
        
        assert len(results) > 0
        assert "aiohttp" in results[0]["code"]
        assert results[0]["language"] == "python"
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test Qdrant error handling and recovery"""
        client = create_database_client()
        
        # Test with invalid data
        with pytest.raises(Exception):
            await client.store_documents([{"invalid": "data"}])
        
        # Test empty batch handling
        result = await client.store_documents([])
        assert result is None or result == []
        
        # Test search with empty query
        results = await search_crawled_pages(client, "")
        assert isinstance(results, list)
        
        # Test very long content (should chunk properly)
        long_content = "Test content. " * 1000  # ~13k chars
        await store_crawled_page(
            client,
            "https://longtest.com/doc",
            long_content,
            {"source": "longtest.com"}
        )
        
        # Verify it was stored and chunked
        await asyncio.sleep(1)
        results = await search_crawled_pages(
            client,
            "Test content",
            source="longtest.com"
        )
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent read/write operations"""
        client = create_database_client()
        
        async def writer(worker_id: int):
            """Simulate concurrent writes"""
            for i in range(5):
                await store_crawled_page(
                    client,
                    f"https://concurrent.com/w{worker_id}/d{i}",
                    f"Worker {worker_id} document {i} with test content",
                    {"source": "concurrent.com", "worker": worker_id}
                )
                await asyncio.sleep(0.1)
        
        async def reader(worker_id: int):
            """Simulate concurrent reads"""
            for i in range(5):
                await search_crawled_pages(
                    client,
                    f"Worker {worker_id}",
                    source="concurrent.com"
                )
                await asyncio.sleep(0.1)
        
        # Run 5 writers and 5 readers concurrently
        start_time = time.time()
        
        tasks = []
        for i in range(5):
            tasks.append(writer(i))
            tasks.append(reader(i))
        
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        print(f"Completed {len(tasks)} concurrent operations in {total_time:.2f}s")
        
        # Should complete reasonably quickly
        assert total_time < 10
        
        # Verify data integrity
        await asyncio.sleep(1)
        all_results = await search_crawled_pages(
            client,
            "Worker document",
            source="concurrent.com",
            limit=50
        )
        assert len(all_results) >= 20  # At least 20 documents stored
    
    @pytest.mark.asyncio
    async def test_source_management(self):
        """Test source listing and filtering"""
        client = create_database_client()
        
        # Store documents from different sources
        sources = ["source1.com", "source2.com", "source3.com"]
        for source in sources:
            await store_crawled_page(
                client,
                f"https://{source}/test",
                f"Test content from {source}",
                {"source": source}
            )
        
        await asyncio.sleep(1)
        
        # Get available sources
        available_sources = await client.get_available_sources()
        
        # Should include our test sources
        for source in sources:
            assert source in available_sources
        
        # Test filtering by each source
        for source in sources:
            results = await search_crawled_pages(
                client,
                "Test content",
                source=source
            )
            assert len(results) > 0
            assert all(r["metadata"]["source"] == source for r in results)