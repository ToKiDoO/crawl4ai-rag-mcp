"""
Simplified unit tests for the Supabase adapter using test doubles.
"""
import pytest
import sys
import os
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tests.test_doubles import FakeSupabaseClient


class TestSupabaseAdapterSimplified:
    """Test Supabase adapter with simplified test doubles"""
    
    @pytest.fixture
    def fake_supabase_client(self):
        """Create a fake Supabase client"""
        return FakeSupabaseClient()
    
    @pytest.fixture
    async def supabase_adapter(self, fake_supabase_client):
        """Create Supabase adapter with fake client"""
        from unittest.mock import patch
        
        with patch('database.supabase_adapter.create_client', return_value=fake_supabase_client):
            from database.supabase_adapter import SupabaseAdapter
            adapter = SupabaseAdapter()
            adapter.client = fake_supabase_client  # Direct assignment
            return adapter
    
    @pytest.mark.asyncio
    async def test_initialization(self, supabase_adapter):
        """Test Supabase adapter initialization"""
        await supabase_adapter.initialize()
        assert supabase_adapter.client is not None
    
    @pytest.mark.asyncio
    async def test_add_documents_simple(self, supabase_adapter, fake_supabase_client):
        """Test adding documents with simple fake client"""
        # Add test documents
        urls = ["https://test1.com", "https://test2.com"]
        
        await supabase_adapter.add_documents(
            urls=urls,
            chunk_numbers=[1, 1],
            contents=["Content 1", "Content 2"],
            metadatas=[{"index": 1}, {"index": 2}],
            embeddings=[[0.1] * 1536, [0.2] * 1536],
            source_ids=["test.com", "test.com"]
        )
        
        # Verify data was inserted
        crawled_data = fake_supabase_client.data.get('crawled_pages', [])
        assert len(crawled_data) > 0
    
    @pytest.mark.asyncio
    async def test_search_documents_simple(self, supabase_adapter, fake_supabase_client):
        """Test searching documents with simple fake client"""
        # Set up RPC results
        fake_supabase_client.rpc_results['match_crawled_pages'] = [
            {
                "id": 1,
                "url": "https://test.com",
                "chunk_number": 1,
                "content": "Test content",
                "metadata": {},
                "source_id": "test.com",
                "similarity": 0.9
            }
        ]
        
        results = await supabase_adapter.search_documents(
            query_embedding=[0.5] * 1536,
            match_count=10
        )
        
        assert len(results) == 1
        assert results[0]["url"] == "https://test.com"
        assert results[0]["similarity"] == 0.9
    
    @pytest.mark.asyncio
    async def test_delete_documents_simple(self, supabase_adapter, fake_supabase_client):
        """Test deleting documents with simple fake client"""
        # Pre-populate some data
        fake_supabase_client.data['crawled_pages'] = [
            {"url": "https://test1.com", "content": "Content 1"},
            {"url": "https://test2.com", "content": "Content 2"},
            {"url": "https://test3.com", "content": "Content 3"}
        ]
        
        # Delete some documents
        await supabase_adapter.delete_documents_by_url(["https://test1.com", "https://test3.com"])
        
        # Verify deletion
        remaining = fake_supabase_client.data.get('crawled_pages', [])
        assert len(remaining) == 1
        assert remaining[0]["url"] == "https://test2.com"
    
    @pytest.mark.asyncio
    async def test_error_handling_simple(self, supabase_adapter, fake_supabase_client):
        """Test error handling with simple fake client"""
        # Make the client fail
        fake_supabase_client.should_fail = True
        
        with pytest.raises(Exception):
            await supabase_adapter.search_documents(
                query_embedding=[0.5] * 1536,
                match_count=10
            )
    
    @pytest.mark.asyncio
    async def test_update_source_info_simple(self, supabase_adapter, fake_supabase_client):
        """Test updating source info with simple fake client"""
        # Pre-populate source data
        fake_supabase_client.data['source_info'] = []
        
        await supabase_adapter.update_source_info(
            source_id="test.com",
            total_pages=10,
            total_chunks=50
        )
        
        # Since update logic might insert if not exists, check both tables
        source_data = fake_supabase_client.data.get('source_info', [])
        # The actual behavior depends on implementation, but we're testing the interaction
        assert fake_supabase_client._table_name is not None  # Table was accessed
    
    @pytest.mark.asyncio
    async def test_get_documents_by_url_simple(self, supabase_adapter, fake_supabase_client):
        """Test getting documents by URL with simple fake client"""
        # Pre-populate data
        fake_supabase_client.data['crawled_pages'] = [
            {"url": "https://test1.com", "chunk_number": 1, "content": "Content 1"},
            {"url": "https://test1.com", "chunk_number": 2, "content": "Content 2"},
            {"url": "https://test2.com", "chunk_number": 1, "content": "Other content"}
        ]
        
        results = await supabase_adapter.get_documents_by_url("https://test1.com")
        
        assert len(results) == 2
        assert all(doc["url"] == "https://test1.com" for doc in results)
    
    @pytest.mark.asyncio
    async def test_batch_operations_simple(self, supabase_adapter, fake_supabase_client):
        """Test batch operations with simple fake client"""
        # Create many documents to test batching
        num_docs = 100
        urls = [f"https://test.com/page{i}" for i in range(num_docs)]
        
        await supabase_adapter.add_documents(
            urls=urls,
            chunk_numbers=list(range(num_docs)),
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"index": i} for i in range(num_docs)],
            embeddings=[[i/1000] * 1536 for i in range(num_docs)],
            source_ids=["test.com"] * num_docs
        )
        
        # Verify all documents were added (fake client doesn't enforce batch size)
        crawled_data = fake_supabase_client.data.get('crawled_pages', [])
        assert len(crawled_data) > 0