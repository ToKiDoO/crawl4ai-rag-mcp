"""
Comprehensive Qdrant database integration tests for crawl4ai_mcp.py.
Tests real Qdrant operations with proper environment handling and concurrent operations.
"""

import pytest
import asyncio
import os
import sys
import json
import time
import requests
from typing import List, Dict, Any, Optional
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from contextlib import asynccontextmanager

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.factory import create_database_client, create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter
from database.base import VectorDatabase
from utils_refactored import (
    add_documents_to_database, 
    search_documents,
    create_embedding,
    create_embeddings_batch
)


class TestQdrantIntegrationComprehensive:
    """Comprehensive Qdrant integration tests with proper environment handling"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment with proper Qdrant URL handling"""
        # Detect environment: Docker or localhost
        cls.is_docker_env = os.getenv("DOCKER_ENV", "false").lower() == "true"
        
        if cls.is_docker_env:
            cls.qdrant_url = "http://qdrant:6333"
            cls.test_environment = "docker"
        else:
            cls.qdrant_url = "http://localhost:6333"
            cls.test_environment = "localhost"
        
        # Set environment variables
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = cls.qdrant_url
        os.environ["QDRANT_API_KEY"] = ""
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
        os.environ["USE_RERANKING"] = "false"
        os.environ["USE_HYBRID_SEARCH"] = "false"
        os.environ["USE_CONTEXTUAL_EMBEDDINGS"] = "false"
        os.environ["USE_AGENTIC_RAG"] = "false"
        
        # Check Qdrant health
        cls.qdrant_healthy = cls._check_qdrant_health()
        if not cls.qdrant_healthy:
            pytest.skip(f"Qdrant not available at {cls.qdrant_url}. Start with: docker run -p 6333:6333 qdrant/qdrant")
    
    @classmethod
    def _check_qdrant_health(cls) -> bool:
        """Check if Qdrant is healthy and responsive"""
        try:
            health_url = f"{cls.qdrant_url}/healthz"
            response = requests.get(health_url, timeout=10)
            if response.status_code == 200:
                print(f"✓ Qdrant healthy at {cls.qdrant_url}")
                return True
            else:
                print(f"✗ Qdrant health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Qdrant connection failed: {e}")
            return False
    
    @pytest.fixture
    async def qdrant_adapter(self):
        """Create and initialize a real Qdrant adapter"""
        adapter = QdrantAdapter(url=self.qdrant_url, api_key=None)
        await adapter.initialize()
        
        # Clean up test collections before each test
        await self._cleanup_test_data(adapter)
        
        yield adapter
        
        # Clean up after test
        await self._cleanup_test_data(adapter)
    
    async def _cleanup_test_data(self, adapter: QdrantAdapter):
        """Clean up test data from Qdrant collections"""
        try:
            # Delete all test documents by URL pattern
            test_urls = [
                "https://test.example.com",
                "https://batch.test.com", 
                "https://concurrent.test.com",
                "https://large.test.com",
                "https://error.test.com"
            ]
            
            for url in test_urls:
                try:
                    await adapter.delete_documents_by_url(url)
                except Exception:
                    pass  # Ignore cleanup errors
                    
            # Also clean up any documents that might be left from previous tests
            for i in range(100):
                try:
                    await adapter.delete_documents_by_url(f"https://test.example.com/page{i}")
                    await adapter.delete_documents_by_url(f"https://batch.test.com/doc{i}")
                    await adapter.delete_documents_by_url(f"https://concurrent.test.com/w{i}")
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"Cleanup warning: {e}", file=sys.stderr)
    
    @pytest.mark.asyncio
    async def test_qdrant_connection_initialization(self, qdrant_adapter):
        """Test Qdrant connection and collection initialization"""
        adapter = qdrant_adapter
        
        # Verify adapter is properly initialized
        assert adapter.client is not None
        assert adapter.url == self.qdrant_url
        assert adapter.CRAWLED_PAGES == "crawled_pages"
        assert adapter.CODE_EXAMPLES == "code_examples"
        assert adapter.SOURCES == "sources"
        
        # Test collection creation
        await adapter._ensure_collections()
        
        # Verify collections exist by attempting operations
        try:
            # Test empty search on each collection
            results = await adapter.search_documents(
                query_embedding=[0.1] * 1536,
                match_count=1
            )
            assert isinstance(results, list)
        except Exception as e:
            pytest.fail(f"Collection initialization failed: {e}")
    
    @pytest.mark.asyncio
    async def test_factory_qdrant_creation(self):
        """Test database factory creates Qdrant adapter correctly"""
        # Test factory method
        client = create_database_client()
        assert isinstance(client, QdrantAdapter)
        assert client.url == self.qdrant_url
        
        # Test initialization
        await client.initialize()
        assert client.client is not None
        
        # Test that create_and_initialize_database works
        initialized_client = await create_and_initialize_database()
        assert isinstance(initialized_client, QdrantAdapter)
        assert initialized_client.client is not None
    
    @pytest.mark.asyncio
    async def test_store_and_search_single_document(self, qdrant_adapter):
        """Test storing and searching a single document"""
        adapter = qdrant_adapter
        
        # Mock OpenAI embeddings
        test_embedding = [0.1] * 1536
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[test_embedding]):
            # Store document
            await add_documents_to_database(
                database=adapter,
                urls=["https://test.example.com/doc1"],
                chunk_numbers=[1],
                contents=["This is a test document about Python async programming and web crawling."],
                metadatas=[{"title": "Test Document", "author": "Test Author"}],
                url_to_full_document={"https://test.example.com/doc1": "Full document content here"},
                batch_size=10
            )
        
        # Allow time for indexing
        await asyncio.sleep(1)
        
        # Mock search embedding
        with patch('utils_refactored.create_embedding', return_value=test_embedding):
            # Search for content
            results = await search_documents(
                database=adapter,
                query="Python async programming",
                match_count=5
            )
        
        # Verify results
        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
        
        result = results[0]
        assert result["url"] == "https://test.example.com/doc1"
        assert "Python async programming" in result["content"]
        assert result["metadata"]["title"] == "Test Document"
        assert "score" in result
        assert result["score"] > 0
    
    @pytest.mark.asyncio
    async def test_store_multiple_chunks_same_url(self, qdrant_adapter):
        """Test storing multiple chunks from the same URL"""
        adapter = qdrant_adapter
        
        # Mock embeddings for 3 chunks
        test_embeddings = [
            [0.1] * 1536,  # Chunk 1
            [0.2] * 1536,  # Chunk 2  
            [0.3] * 1536   # Chunk 3
        ]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=["https://test.example.com/long-doc"] * 3,
                chunk_numbers=[1, 2, 3],
                contents=[
                    "Introduction: This document covers async programming fundamentals.",
                    "Main content: Here we dive deep into asyncio and event loops.", 
                    "Conclusion: Best practices for production async applications."
                ],
                metadatas=[
                    {"title": "Long Document", "section": "intro"},
                    {"title": "Long Document", "section": "main"},
                    {"title": "Long Document", "section": "conclusion"}
                ],
                url_to_full_document={"https://test.example.com/long-doc": "Complete document content"},
                batch_size=10
            )
        
        await asyncio.sleep(1)
        
        # Get all chunks for this URL
        url_results = await adapter.get_documents_by_url("https://test.example.com/long-doc")
        
        # Verify all chunks stored
        assert len(url_results) == 3
        
        # Verify chunks are in correct order
        chunk_numbers = [doc["chunk_number"] for doc in url_results]
        assert chunk_numbers == [1, 2, 3]
        
        # Verify different content in each chunk
        contents = [doc["content"] for doc in url_results]
        assert "Introduction" in contents[0]
        assert "Main content" in contents[1]
        assert "Conclusion" in contents[2]
    
    @pytest.mark.asyncio
    async def test_batch_processing_large_dataset(self, qdrant_adapter):
        """Test batch processing with a large dataset"""
        adapter = qdrant_adapter
        
        # Create 50 documents to test batching
        num_docs = 50
        urls = [f"https://batch.test.com/doc{i}" for i in range(num_docs)]
        chunk_numbers = [1] * num_docs
        contents = [f"Document {i} contains information about topic {i % 5}. This is detailed content for testing batch operations." for i in range(num_docs)]
        metadatas = [{"doc_id": i, "topic": f"topic_{i % 5}", "batch": "test"} for i in range(num_docs)]
        url_to_full_document = {url: f"Full content for {url}" for url in urls}
        
        # Mock embeddings
        test_embeddings = [[0.1 + (i * 0.001)] * 1536 for i in range(num_docs)]
        
        start_time = time.time()
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=urls,
                chunk_numbers=chunk_numbers,
                contents=contents,
                metadatas=metadatas,
                url_to_full_document=url_to_full_document,
                batch_size=10  # Force multiple batches
            )
        
        store_time = time.time() - start_time
        print(f"Stored {num_docs} documents in {store_time:.2f}s")
        
        await asyncio.sleep(2)  # Allow indexing
        
        # Verify all documents stored by searching
        with patch('utils_refactored.create_embedding', return_value=[0.1] * 1536):
            results = await search_documents(
                database=adapter,
                query="Document topic testing",
                match_count=num_docs
            )
        
        # Should find many of our test documents
        assert len(results) >= num_docs // 2, f"Expected at least {num_docs // 2} results, got {len(results)}"
        
        # Verify performance
        assert store_time < 30, f"Batch storage took too long: {store_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, qdrant_adapter):
        """Test concurrent read/write operations"""
        adapter = qdrant_adapter
        
        async def concurrent_writer(worker_id: int):
            """Simulate concurrent write operations"""
            for i in range(3):
                test_embedding = [0.1 + worker_id * 0.01 + i * 0.001] * 1536
                
                with patch('utils_refactored.create_embeddings_batch', return_value=[test_embedding]):
                    await add_documents_to_database(
                        database=adapter,
                        urls=[f"https://concurrent.test.com/w{worker_id}/d{i}"],
                        chunk_numbers=[1],
                        contents=[f"Worker {worker_id} document {i} with concurrent test content"],
                        metadatas=[{"worker": worker_id, "doc": i, "test": "concurrent"}],
                        url_to_full_document={f"https://concurrent.test.com/w{worker_id}/d{i}": f"Full content {worker_id}-{i}"},
                        batch_size=10
                    )
                await asyncio.sleep(0.1)
        
        async def concurrent_reader(worker_id: int):
            """Simulate concurrent read operations"""
            for i in range(3):
                with patch('utils_refactored.create_embedding', return_value=[0.1] * 1536):
                    results = await search_documents(
                        database=adapter,
                        query=f"Worker {worker_id} concurrent",
                        match_count=10
                    )
                await asyncio.sleep(0.1)
        
        # Run 3 writers and 3 readers concurrently
        start_time = time.time()
        
        tasks = []
        for i in range(3):
            tasks.append(concurrent_writer(i))
            tasks.append(concurrent_reader(i))
        
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        print(f"Completed {len(tasks)} concurrent operations in {total_time:.2f}s")
        
        # Verify reasonable performance
        assert total_time < 15, f"Concurrent operations took too long: {total_time:.2f}s"
        
        # Verify data integrity
        await asyncio.sleep(1)
        with patch('utils_refactored.create_embedding', return_value=[0.1] * 1536):
            results = await search_documents(
                database=adapter,
                query="Worker document concurrent",
                match_count=20
            )
        
        # Should find documents from all workers
        assert len(results) >= 6, f"Expected at least 6 results from concurrent operations, got {len(results)}"
    
    @pytest.mark.asyncio
    async def test_error_handling_connection_failure(self):
        """Test handling of Qdrant connection failures"""
        # Test with invalid URL
        invalid_adapter = QdrantAdapter(url="http://invalid-host:6333", api_key=None)
        
        # Connection should fail gracefully
        with pytest.raises(Exception):
            await invalid_adapter.initialize()
    
    @pytest.mark.asyncio
    async def test_error_handling_malformed_data(self, qdrant_adapter):
        """Test handling of malformed data"""
        adapter = qdrant_adapter
        
        # Test with mismatched list lengths
        with pytest.raises((ValueError, IndexError, Exception)):
            await add_documents_to_database(
                database=adapter,
                urls=["https://error.test.com/doc1"],
                chunk_numbers=[1, 2],  # Wrong length
                contents=["Content"],
                metadatas=[{"test": "error"}],
                url_to_full_document={"https://error.test.com/doc1": "Full content"},
                batch_size=10
            )
    
    @pytest.mark.asyncio
    async def test_error_handling_embedding_failure(self, qdrant_adapter):
        """Test handling of embedding creation failures"""
        adapter = qdrant_adapter
        
        # Mock embedding failure
        with patch('utils_refactored.create_embeddings_batch', side_effect=Exception("OpenAI API failure")):
            with pytest.raises(Exception, match="OpenAI API failure"):
                await add_documents_to_database(
                    database=adapter,
                    urls=["https://error.test.com/doc1"],
                    chunk_numbers=[1],
                    contents=["Test content"],
                    metadatas=[{"test": "embedding_error"}],
                    url_to_full_document={"https://error.test.com/doc1": "Full content"},
                    batch_size=10
                )
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, qdrant_adapter):
        """Test search with metadata and source filters"""
        adapter = qdrant_adapter
        
        # Store documents with different metadata
        test_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=[
                    "https://test.example.com/doc1",
                    "https://test.example.com/doc2", 
                    "https://other.example.com/doc3"
                ],
                chunk_numbers=[1, 1, 1],
                contents=[
                    "Python programming tutorial",
                    "JavaScript programming guide",
                    "Python advanced concepts"
                ],
                metadatas=[
                    {"language": "python", "level": "beginner"},
                    {"language": "javascript", "level": "beginner"},
                    {"language": "python", "level": "advanced"}
                ],
                url_to_full_document={
                    "https://test.example.com/doc1": "Full Python tutorial",
                    "https://test.example.com/doc2": "Full JavaScript guide",
                    "https://other.example.com/doc3": "Full Python advanced guide"
                },
                batch_size=10
            )
        
        await asyncio.sleep(1)
        
        # Test search with metadata filter
        with patch('utils_refactored.create_embedding', return_value=[0.1] * 1536):
            # Search for Python documents only
            python_results = await search_documents(
                database=adapter,
                query="programming tutorial",
                filter_metadata={"language": "python"},
                match_count=10
            )
        
        # Should only return Python documents
        assert len(python_results) >= 1
        for result in python_results:
            if "metadata" in result and "language" in result["metadata"]:
                assert result["metadata"]["language"] == "python"
        
        # Test search with source filter
        with patch('utils_refactored.create_embedding', return_value=[0.1] * 1536):
            source_results = await search_documents(
                database=adapter,
                query="programming",
                source_filter="test.example.com",
                match_count=10
            )
        
        # Should only return documents from test.example.com
        assert len(source_results) >= 1
    
    @pytest.mark.asyncio
    async def test_document_cleanup_and_replacement(self, qdrant_adapter):
        """Test that documents are properly cleaned up and replaced"""
        adapter = qdrant_adapter
        
        test_url = "https://test.example.com/replacement-test"
        
        # Store initial document
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536]):
            await add_documents_to_database(
                database=adapter,
                urls=[test_url],
                chunk_numbers=[1],
                contents=["Original content"],
                metadatas=[{"version": "v1"}],
                url_to_full_document={test_url: "Original full content"},
                batch_size=10
            )
        
        await asyncio.sleep(1)
        
        # Verify original document exists
        original_docs = await adapter.get_documents_by_url(test_url)
        assert len(original_docs) == 1
        assert "Original content" in original_docs[0]["content"]
        
        # Store replacement document
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.2] * 1536]):
            await add_documents_to_database(
                database=adapter,
                urls=[test_url],
                chunk_numbers=[1],
                contents=["Updated content"],
                metadatas=[{"version": "v2"}],
                url_to_full_document={test_url: "Updated full content"},
                batch_size=10
            )
        
        await asyncio.sleep(1)
        
        # Verify old document was replaced
        updated_docs = await adapter.get_documents_by_url(test_url)
        assert len(updated_docs) == 1
        assert "Updated content" in updated_docs[0]["content"]
        assert updated_docs[0]["metadata"]["version"] == "v2"
    
    @pytest.mark.asyncio
    async def test_environment_configuration(self):
        """Test that environment configuration is properly handled"""
        # Verify environment variables are set correctly
        assert os.getenv("VECTOR_DATABASE") == "qdrant"
        assert os.getenv("QDRANT_URL") == self.qdrant_url
        
        # Test that factory respects environment
        client = create_database_client()
        assert isinstance(client, QdrantAdapter)
        assert client.url == self.qdrant_url
        
        # Test environment detection
        print(f"Test environment: {self.test_environment}")
        print(f"Qdrant URL: {self.qdrant_url}")
        
        if self.is_docker_env:
            assert "qdrant:6333" in self.qdrant_url
        else:
            assert "localhost:6333" in self.qdrant_url
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, qdrant_adapter):
        """Test performance benchmarks for various operations"""
        adapter = qdrant_adapter
        
        # Benchmark document storage
        num_docs = 20
        test_embeddings = [[0.1 + i * 0.001] * 1536 for i in range(num_docs)]
        
        start_time = time.time()
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=[f"https://bench.test.com/doc{i}" for i in range(num_docs)],
                chunk_numbers=[1] * num_docs,
                contents=[f"Benchmark document {i} content" for i in range(num_docs)],
                metadatas=[{"bench": i} for i in range(num_docs)],
                url_to_full_document={f"https://bench.test.com/doc{i}": f"Full {i}" for i in range(num_docs)},
                batch_size=5
            )
        
        storage_time = time.time() - start_time
        storage_rate = num_docs / storage_time
        
        await asyncio.sleep(1)
        
        # Benchmark search
        search_start = time.time()
        
        with patch('utils_refactored.create_embedding', return_value=[0.1] * 1536):
            for _ in range(10):  # 10 search operations
                await search_documents(
                    database=adapter,
                    query="Benchmark document content",
                    match_count=5
                )
        
        search_time = time.time() - search_start
        search_rate = 10 / search_time
        
        print(f"Storage rate: {storage_rate:.2f} docs/sec")
        print(f"Search rate: {search_rate:.2f} searches/sec")
        
        # Performance assertions (adjust based on your requirements)
        assert storage_rate > 1.0, f"Storage too slow: {storage_rate:.2f} docs/sec"
        assert search_rate > 2.0, f"Search too slow: {search_rate:.2f} searches/sec"
    
    @pytest.mark.asyncio
    async def test_code_examples_storage_and_search(self, qdrant_adapter):
        """Test code examples storage and retrieval functionality"""
        adapter = qdrant_adapter
        
        # Test code examples
        code_examples = [
            {
                "url": "https://test.example.com/code1",
                "chunk_number": 1,
                "code": "async def fetch_data():\n    return await api_call()",
                "summary": "Async function for fetching data",
                "metadata": {"language": "python", "topic": "async"}
            },
            {
                "url": "https://test.example.com/code2",
                "chunk_number": 1,
                "code": "function fetchData() {\n    return fetch('/api/data')\n}",
                "summary": "JavaScript function for fetching data",
                "metadata": {"language": "javascript", "topic": "api"}
            }
        ]
        
        # Mock embeddings for code examples
        test_embeddings = [[0.1] * 1536, [0.2] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await adapter.add_code_examples(
                urls=[ex["url"] for ex in code_examples],
                chunk_numbers=[ex["chunk_number"] for ex in code_examples],
                codes=[ex["code"] for ex in code_examples],
                summaries=[ex["summary"] for ex in code_examples],
                metadatas=[ex["metadata"] for ex in code_examples],
                embeddings=test_embeddings
            )
        
        await asyncio.sleep(1)
        
        # Search for code examples
        search_results = await adapter.search_code_examples(
            query_embedding=[0.1] * 1536,
            match_count=5
        )
        
        # Verify results
        assert len(search_results) >= 1
        result = search_results[0]
        assert "code" in result
        assert "summary" in result
        assert "async def" in result["code"] or "function" in result["code"]
    
    @pytest.mark.asyncio
    async def test_source_management(self, qdrant_adapter):
        """Test source information storage and retrieval"""
        adapter = qdrant_adapter
        
        # Add source information
        await adapter.update_source_info(
            source_id="test.example.com",
            summary="Test website for integration testing",
            word_count=1500
        )
        
        await asyncio.sleep(1)
        
        # Get all sources
        sources = await adapter.get_sources()
        
        # Verify source was added
        test_sources = [s for s in sources if s["source_id"] == "test.example.com"]
        assert len(test_sources) == 1
        
        test_source = test_sources[0]
        assert test_source["summary"] == "Test website for integration testing"
        assert test_source["total_word_count"] == 1500
        assert "created_at" in test_source
        assert "updated_at" in test_source
    
    @pytest.mark.asyncio
    async def test_large_content_chunking(self, qdrant_adapter):
        """Test handling of large content that needs chunking"""
        adapter = qdrant_adapter
        
        # Create very large content (>10KB)
        large_content = "This is a very long document. " * 500  # ~15KB
        
        test_embedding = [0.1] * 1536
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[test_embedding]):
            await add_documents_to_database(
                database=adapter,
                urls=["https://large.test.com/big-doc"],
                chunk_numbers=[1],
                contents=[large_content],
                metadatas=[{"size": "large", "test": "chunking"}],
                url_to_full_document={"https://large.test.com/big-doc": large_content},
                batch_size=10
            )
        
        await asyncio.sleep(1)
        
        # Verify document was stored
        docs = await adapter.get_documents_by_url("https://large.test.com/big-doc")
        assert len(docs) >= 1
        
        # Verify content integrity
        assert "very long document" in docs[0]["content"]
        assert docs[0]["metadata"]["size"] == "large"