"""
Focused tests for store_crawled_page function behavior with Qdrant database.
Tests the complete flow from crawl4ai_mcp.py through Qdrant operations.
"""

import pytest
import asyncio
import os
import sys
import json
from typing import List, Dict, Any
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from contextlib import asynccontextmanager

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from .test_doubles import FakeQdrantClient
from database.qdrant_adapter import QdrantAdapter
from utils_refactored import add_documents_to_database, search_documents
from crawl4ai_mcp import Crawl4AIContext
from fastmcp import Context


class TestQdrantStoreCrawledPage:
    """Test store_crawled_page specific behavior with Qdrant"""
    
    @pytest.fixture(autouse=True)
    def setup_qdrant_env(self):
        """Setup Qdrant environment variables"""
        with patch.dict(os.environ, {
            'VECTOR_DATABASE': 'qdrant',
            'QDRANT_URL': 'http://localhost:6333',
            'QDRANT_API_KEY': '',
            'OPENAI_API_KEY': 'test-key',
            'USE_RERANKING': 'false',
            'USE_HYBRID_SEARCH': 'false',
            'ENHANCED_CONTEXT': 'false',
            'ENABLE_AGENTIC_RAG': 'false'
        }):
            yield
    
    @pytest.fixture
    def enhanced_fake_qdrant_client(self):
        """Enhanced fake Qdrant client that tracks operations more accurately"""
        
        class EnhancedFakeQdrantClient(FakeQdrantClient):
            def __init__(self):
                super().__init__()
                self.upsert_calls = []
                self.delete_calls = []
                self.search_calls = []
                self.get_collection_calls = []
                self.create_collection_calls = []
            
            def get_collection(self, collection_name: str):
                self.get_collection_calls.append(collection_name)
                if self.should_fail:
                    raise Exception(f"Collection {collection_name} not found")
                return Mock()  # Simulate existing collection
            
            def create_collection(self, collection_name: str, vectors_config):
                self.create_collection_calls.append((collection_name, vectors_config))
                if self.should_fail:
                    raise Exception(f"Failed to create collection {collection_name}")
                return Mock()
            
            def upsert(self, collection_name: str, points: List):
                self.upsert_calls.append((collection_name, len(points)))
                if self.should_fail:
                    raise Exception("Upsert failed")
                
                # Store points in collections for verification
                if collection_name not in self.collections:
                    self.collections[collection_name] = []
                
                # Convert PointStruct-like objects to dicts for storage
                for point in points:
                    point_dict = {
                        "id": getattr(point, 'id', point.get('id', 'unknown')),
                        "vector": getattr(point, 'vector', point.get('vector', [])),
                        "payload": getattr(point, 'payload', point.get('payload', {}))
                    }
                    self.collections[collection_name].append(point_dict)
                
                return {"status": "ok"}
            
            def delete(self, collection_name: str, points_selector):
                self.delete_calls.append((collection_name, points_selector))
                if self.should_fail:
                    raise Exception("Delete failed")
                return {"status": "ok"}
            
            def search(self, collection_name: str, query_vector: List[float], limit: int = 10, query_filter=None):
                self.search_calls.append((collection_name, len(query_vector), limit, query_filter))
                if self.should_fail:
                    raise Exception("Search failed")
                return self.search_results[:limit]
        
        return EnhancedFakeQdrantClient()
    
    @pytest.fixture
    async def qdrant_adapter_with_enhanced_client(self, enhanced_fake_qdrant_client):
        """Create Qdrant adapter with enhanced fake client"""
        adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
        adapter.client = enhanced_fake_qdrant_client
        return adapter
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_single_document(self, qdrant_adapter_with_enhanced_client):
        """Test storing a single document page with Qdrant"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Mock embeddings
        test_embeddings = [[0.1] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=["https://example.com/page1"],
                chunk_numbers=[1],
                contents=["This is test content for page 1"],
                metadatas=[{"title": "Test Page 1", "author": "Test Author"}],
                url_to_full_document={"https://example.com/page1": "Full document content"},
                batch_size=10
            )
        
        # Verify delete was called first (cleanup existing docs)
        assert len(client.delete_calls) >= 1
        
        # Verify upsert was called
        assert len(client.upsert_calls) == 1
        collection_name, point_count = client.upsert_calls[0]
        assert collection_name == "crawled_pages"
        assert point_count == 1
        
        # Verify document was stored correctly
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == 1
        
        doc = stored_docs[0]
        assert doc["payload"]["url"] == "https://example.com/page1"
        assert doc["payload"]["content"] == "This is test content for page 1"
        assert doc["payload"]["chunk_number"] == 1
        assert doc["payload"]["metadata"]["title"] == "Test Page 1"
        assert len(doc["vector"]) == 1536
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_multiple_chunks(self, qdrant_adapter_with_enhanced_client):
        """Test storing multiple chunks from the same page"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Mock embeddings for multiple chunks
        test_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=["https://example.com/long-page"] * 3,
                chunk_numbers=[1, 2, 3],
                contents=[
                    "First chunk of content",
                    "Second chunk of content", 
                    "Third chunk of content"
                ],
                metadatas=[
                    {"title": "Long Page", "chunk_type": "intro"},
                    {"title": "Long Page", "chunk_type": "body"},
                    {"title": "Long Page", "chunk_type": "conclusion"}
                ],
                url_to_full_document={"https://example.com/long-page": "Complete page content"},
                batch_size=10
            )
        
        # Verify all chunks were stored
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == 3
        
        # Verify chunk numbers are correct
        chunk_numbers = [doc["payload"]["chunk_number"] for doc in stored_docs]
        assert sorted(chunk_numbers) == [1, 2, 3]
        
        # Verify different embeddings for each chunk
        vectors = [doc["vector"] for doc in stored_docs]
        assert vectors[0] != vectors[1] != vectors[2]
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_batch_processing(self, qdrant_adapter_with_enhanced_client):
        """Test batch processing with multiple documents"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Create data for 5 documents with 2 chunks each = 10 total chunks
        urls = []
        chunk_numbers = []
        contents = []
        metadatas = []
        url_to_full_document = {}
        
        for i in range(5):
            for chunk in [1, 2]:
                urls.append(f"https://example.com/page{i}")
                chunk_numbers.append(chunk)
                contents.append(f"Content for page {i}, chunk {chunk}")
                metadatas.append({"title": f"Page {i}", "chunk": chunk})
            url_to_full_document[f"https://example.com/page{i}"] = f"Full content for page {i}"
        
        # Mock embeddings
        test_embeddings = [[0.1 * (i+1)] * 1536 for i in range(10)]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=urls,
                chunk_numbers=chunk_numbers,
                contents=contents,
                metadatas=metadatas,
                url_to_full_document=url_to_full_document,
                batch_size=3  # Force multiple batches
            )
        
        # Should have multiple upsert calls due to batching
        assert len(client.upsert_calls) > 1
        
        # Verify total documents stored
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == 10
        
        # Verify all pages are represented
        unique_urls = set(doc["payload"]["url"] for doc in stored_docs)
        assert len(unique_urls) == 5
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_with_source_ids(self, qdrant_adapter_with_enhanced_client):
        """Test storing documents with source IDs"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        test_embeddings = [[0.1] * 1536, [0.2] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            # Mock source storage (simulate sources being added first)
            await add_documents_to_database(
                database=adapter,
                urls=["https://docs.example.com/api", "https://docs.example.com/guide"],
                chunk_numbers=[1, 1],
                contents=["API documentation", "User guide"],
                metadatas=[{"type": "api"}, {"type": "guide"}],
                url_to_full_document={
                    "https://docs.example.com/api": "Full API docs",
                    "https://docs.example.com/guide": "Full user guide"
                },
                batch_size=10
            )
        
        # Verify documents were stored with source information
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == 2
        
        # Check that documents contain the expected content
        api_doc = next(doc for doc in stored_docs if "API" in doc["payload"]["content"])
        guide_doc = next(doc for doc in stored_docs if "guide" in doc["payload"]["content"])
        
        assert api_doc["payload"]["metadata"]["type"] == "api"
        assert guide_doc["payload"]["metadata"]["type"] == "guide"
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_cleanup_existing(self, qdrant_adapter_with_enhanced_client):
        """Test that existing documents are cleaned up before storing new ones"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Pre-populate with existing document
        client.collections["crawled_pages"] = [
            {
                "id": "existing_doc",
                "payload": {"url": "https://example.com/page1", "content": "Old content"}
            }
        ]
        
        test_embeddings = [[0.1] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=["https://example.com/page1"],
                chunk_numbers=[1],
                contents=["New content"],
                metadatas=[{"title": "Updated Page"}],
                url_to_full_document={"https://example.com/page1": "New full content"},
                batch_size=10
            )
        
        # Verify delete was called for cleanup
        assert len(client.delete_calls) >= 1
        
        # Verify new document was stored
        assert len(client.upsert_calls) == 1
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_embedding_failure(self, qdrant_adapter_with_enhanced_client):
        """Test handling of embedding creation failures"""
        adapter = qdrant_adapter_with_enhanced_client
        
        # Mock embedding failure
        with patch('utils_refactored.create_embeddings_batch', side_effect=Exception("Embedding API failed")):
            with pytest.raises(Exception, match="Embedding API failed"):
                await add_documents_to_database(
                    database=adapter,
                    urls=["https://example.com/page1"],
                    chunk_numbers=[1],
                    contents=["Test content"],
                    metadatas=[{"title": "Test Page"}],
                    url_to_full_document={"https://example.com/page1": "Full content"},
                    batch_size=10
                )
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_qdrant_upsert_failure(self, qdrant_adapter_with_enhanced_client):
        """Test handling of Qdrant upsert failures"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Make upsert fail
        client.should_fail = True
        
        test_embeddings = [[0.1] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            with pytest.raises(Exception, match="Upsert failed"):
                await add_documents_to_database(
                    database=adapter,
                    urls=["https://example.com/page1"],
                    chunk_numbers=[1],
                    contents=["Test content"],
                    metadatas=[{"title": "Test Page"}],
                    url_to_full_document={"https://example.com/page1": "Full content"},
                    batch_size=10
                )
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_point_id_generation(self, qdrant_adapter_with_enhanced_client):
        """Test that point IDs are generated deterministically"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        test_embeddings = [[0.1] * 1536, [0.2] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=["https://example.com/page1", "https://example.com/page1"],
                chunk_numbers=[1, 2],
                contents=["Chunk 1", "Chunk 2"],
                metadatas=[{"chunk": 1}, {"chunk": 2}],
                url_to_full_document={"https://example.com/page1": "Full content"},
                batch_size=10
            )
        
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == 2
        
        # Verify IDs are different for different chunk numbers
        ids = [doc["id"] for doc in stored_docs]
        assert len(set(ids)) == 2  # All IDs should be unique
        
        # Verify IDs are deterministic (test by generating the same ID manually)
        expected_id_1 = adapter._generate_point_id("https://example.com/page1", 1)
        expected_id_2 = adapter._generate_point_id("https://example.com/page1", 2)
        
        assert expected_id_1 in ids
        assert expected_id_2 in ids
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_empty_data(self, qdrant_adapter_with_enhanced_client):
        """Test handling of empty data inputs"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Test with empty lists
        with patch('utils_refactored.create_embeddings_batch', return_value=[]):
            await add_documents_to_database(
                database=adapter,
                urls=[],
                chunk_numbers=[],
                contents=[],
                metadatas=[],
                url_to_full_document={},
                batch_size=10
            )
        
        # Should not have made any upsert calls
        assert len(client.upsert_calls) == 0
        assert len(client.collections.get("crawled_pages", [])) == 0
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_large_batch(self, qdrant_adapter_with_enhanced_client):
        """Test storing a large batch that exceeds the default batch size"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        # Create data for 150 documents (exceeds default batch size of 100)
        num_docs = 150
        urls = [f"https://example.com/page{i}" for i in range(num_docs)]
        chunk_numbers = [1] * num_docs
        contents = [f"Content for page {i}" for i in range(num_docs)]
        metadatas = [{"page_num": i} for i in range(num_docs)]
        url_to_full_document = {url: f"Full content {i}" for i, url in enumerate(urls)}
        
        # Mock embeddings
        test_embeddings = [[0.1] * 1536 for _ in range(num_docs)]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=urls,
                chunk_numbers=chunk_numbers,
                contents=contents,
                metadatas=metadatas,
                url_to_full_document=url_to_full_document,
                batch_size=50  # Smaller batch size to force multiple batches
            )
        
        # Should have multiple upsert calls due to batching
        assert len(client.upsert_calls) >= 3  # 150 docs / 50 batch size = 3 batches
        
        # Verify all documents were stored
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == num_docs
        
        # Verify total points across all upsert calls equals expected
        total_points_upserted = sum(count for _, count in client.upsert_calls)
        assert total_points_upserted == num_docs
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_metadata_handling(self, qdrant_adapter_with_enhanced_client):
        """Test proper handling of metadata including None values"""
        adapter = qdrant_adapter_with_enhanced_client
        client = adapter.client
        
        test_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings):
            await add_documents_to_database(
                database=adapter,
                urls=["https://example1.com", "https://example2.com", "https://example3.com"],
                chunk_numbers=[1, 1, 1],
                contents=["Content 1", "Content 2", "Content 3"],
                metadatas=[
                    {"title": "Page 1", "author": "Author 1"},  # Normal metadata
                    {},  # Empty metadata
                    None  # None metadata
                ],
                url_to_full_document={
                    "https://example1.com": "Full 1",
                    "https://example2.com": "Full 2", 
                    "https://example3.com": "Full 3"
                },
                batch_size=10
            )
        
        stored_docs = client.collections["crawled_pages"]
        assert len(stored_docs) == 3
        
        # Verify metadata handling
        doc1 = next(doc for doc in stored_docs if "Content 1" in doc["payload"]["content"])
        doc2 = next(doc for doc in stored_docs if "Content 2" in doc["payload"]["content"])
        doc3 = next(doc for doc in stored_docs if "Content 3" in doc["payload"]["content"])
        
        # Normal metadata should be preserved
        assert doc1["payload"]["metadata"]["title"] == "Page 1"
        assert doc1["payload"]["metadata"]["author"] == "Author 1"
        
        # Empty metadata should be empty dict
        assert doc2["payload"]["metadata"] == {}
        
        # None metadata should be converted to empty dict
        assert doc3["payload"]["metadata"] == {}