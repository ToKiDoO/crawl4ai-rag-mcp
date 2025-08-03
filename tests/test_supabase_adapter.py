"""
Unit tests specific to the Supabase adapter implementation.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os


class TestSupabaseAdapter:
    """Test Supabase-specific functionality"""
    
    @pytest.fixture
    async def mock_supabase_client(self):
        """Mock Supabase client for testing"""
        client = MagicMock()
        
        # Mock table operations
        table_mock = MagicMock()
        table_mock.insert = MagicMock(return_value=table_mock)
        table_mock.delete = MagicMock(return_value=table_mock)
        table_mock.select = MagicMock(return_value=table_mock)
        table_mock.eq = MagicMock(return_value=table_mock)
        table_mock.in_ = MagicMock(return_value=table_mock)
        table_mock.execute = MagicMock(return_value=MagicMock(data=[]))
        
        client.table = MagicMock(return_value=table_mock)
        
        # Mock RPC operations
        rpc_mock = MagicMock()
        rpc_mock.execute = MagicMock(return_value=MagicMock(data=[]))
        client.rpc = MagicMock(return_value=rpc_mock)
        
        return client
    
    @pytest.fixture
    async def supabase_adapter(self, mock_supabase_client):
        """Create Supabase adapter with mocked client"""
        with patch('database.supabase_adapter.create_client', return_value=mock_supabase_client):
            from database.supabase_adapter import SupabaseAdapter
            adapter = SupabaseAdapter()
            return adapter
    
    @pytest.mark.asyncio
    async def test_initialization(self, supabase_adapter):
        """Test Supabase adapter initialization"""
        await supabase_adapter.initialize()
        assert supabase_adapter.client is not None
    
    @pytest.mark.asyncio
    async def test_add_documents_with_batch_processing(self, supabase_adapter, mock_supabase_client):
        """Test that documents are added in batches"""
        # Create 50 documents to test batching
        num_docs = 50
        urls = [f"https://test.com/page{i}" for i in range(num_docs)]
        
        await supabase_adapter.add_documents(
            urls=urls,
            chunk_numbers=list(range(num_docs)),
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"index": i} for i in range(num_docs)],
            embeddings=[[i/100] * 1536 for i in range(num_docs)],
            source_ids=["test.com"] * num_docs
        )
        
        # Verify batch deletion was called
        table_mock = mock_supabase_client.table.return_value
        assert table_mock.delete.called
        
        # Verify insert was called (multiple times for batches)
        assert table_mock.insert.called
    
    @pytest.mark.asyncio
    async def test_search_uses_match_crawled_pages_function(self, supabase_adapter, mock_supabase_client):
        """Test that search uses the correct Supabase RPC function"""
        query_embedding = [0.5] * 1536
        
        # Mock search results
        mock_results = [
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
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(data=mock_results)
        
        results = await supabase_adapter.search_documents(
            query_embedding=query_embedding,
            match_count=10
        )
        
        # Verify RPC was called with correct function
        mock_supabase_client.rpc.assert_called_with('match_crawled_pages', {
            'query_embedding': query_embedding,
            'match_count': 10
        })
        
        assert results == mock_results
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, supabase_adapter, mock_supabase_client):
        """Test search with metadata and source filters"""
        query_embedding = [0.5] * 1536
        filter_metadata = {"language": "python"}
        source_filter = "docs.python.org"
        
        await supabase_adapter.search_documents(
            query_embedding=query_embedding,
            match_count=5,
            filter_metadata=filter_metadata,
            source_filter=source_filter
        )
        
        # Verify RPC was called with all parameters
        expected_params = {
            'query_embedding': query_embedding,
            'match_count': 5,
            'filter': filter_metadata,
            'source_filter': source_filter
        }
        mock_supabase_client.rpc.assert_called_with('match_crawled_pages', expected_params)
    
    @pytest.mark.asyncio
    async def test_delete_documents_batch_operation(self, supabase_adapter, mock_supabase_client):
        """Test batch deletion of documents"""
        urls = ["https://test1.com", "https://test2.com", "https://test3.com"]
        
        await supabase_adapter.delete_documents_by_url(urls)
        
        # Verify batch delete was attempted
        table_mock = mock_supabase_client.table.return_value
        table_mock.delete.assert_called()
        table_mock.in_.assert_called_with("url", urls)
    
    @pytest.mark.asyncio
    async def test_update_source_info(self, supabase_adapter, mock_supabase_client):
        """Test source information update"""
        # Mock update that returns empty (no existing record)
        table_mock = mock_supabase_client.table.return_value
        table_mock.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        
        await supabase_adapter.update_source_info(
            source_id="test.com",
            summary="Test source",
            word_count=1000
        )
        
        # Should try update first
        table_mock.update.assert_called_with({
            'summary': 'Test source',
            'total_word_count': 1000,
            'updated_at': 'now()'
        })
        
        # Since update returned empty, should insert
        table_mock.insert.assert_called_with({
            'source_id': 'test.com',
            'summary': 'Test source',
            'total_word_count': 1000
        })
    
    @pytest.mark.asyncio
    async def test_code_examples_operations(self, supabase_adapter, mock_supabase_client):
        """Test code example specific operations"""
        # Test add code examples
        await supabase_adapter.add_code_examples(
            urls=["https://test.com/docs"],
            chunk_numbers=[1],
            code_examples=["print('hello')"],
            summaries=["Print hello"],
            metadatas=[{"language": "python"}],
            embeddings=[[0.1] * 1536],
            source_ids=["test.com"]
        )
        
        # Verify delete was called for existing examples
        table_mock = mock_supabase_client.table.return_value
        assert table_mock.delete.called
        
        # Verify insert was called
        assert table_mock.insert.called
        
        # Test search code examples
        mock_supabase_client.rpc.return_value.execute.return_value = MagicMock(data=[])
        
        await supabase_adapter.search_code_examples(
            query_embedding=[0.1] * 1536,
            match_count=5
        )
        
        # Verify correct RPC function was called
        mock_supabase_client.rpc.assert_called_with('match_code_examples', {
            'query_embedding': [0.1] * 1536,
            'match_count': 5
        })
    
    @pytest.mark.asyncio
    async def test_error_handling_with_retry(self, supabase_adapter, mock_supabase_client):
        """Test that operations retry on failure"""
        # Make insert fail first time, succeed second time
        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.return_value.execute.side_effect = [
            Exception("Connection error"),
            MagicMock(data=[])
        ]
        
        # Should retry and eventually succeed
        await supabase_adapter.add_documents(
            urls=["https://test.com"],
            chunk_numbers=[1],
            contents=["Test"],
            metadatas=[{}],
            embeddings=[[0.1] * 1536],
            source_ids=["test.com"]
        )
        
        # Verify insert was called twice (retry)
        assert table_mock.insert.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_empty_input_handling(self, supabase_adapter):
        """Test handling of empty inputs"""
        # Empty lists should not cause errors
        await supabase_adapter.add_documents(
            urls=[],
            chunk_numbers=[],
            contents=[],
            metadatas=[],
            embeddings=[],
            source_ids=[]
        )
        
        # Empty URL list for deletion
        await supabase_adapter.delete_documents_by_url([])
        
        # Search with invalid embedding size should handle gracefully
        try:
            await supabase_adapter.search_documents(
                query_embedding=[0.1] * 100,  # Wrong size
                match_count=10
            )
        except Exception:
            pass  # Expected to handle invalid embedding
    
    @pytest.mark.asyncio
    async def test_large_batch_handling(self, supabase_adapter, mock_supabase_client):
        """Test handling of large batches"""
        # Create 200 documents to test multiple batch processing
        num_docs = 200
        urls = [f"https://test.com/page{i}" for i in range(num_docs)]
        
        await supabase_adapter.add_documents(
            urls=urls,
            chunk_numbers=list(range(num_docs)),
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"index": i} for i in range(num_docs)],
            embeddings=[[i/1000] * 1536 for i in range(num_docs)],
            source_ids=["test.com"] * num_docs
        )
        
        # Verify multiple batch calls were made
        table_mock = mock_supabase_client.table.return_value
        # With batch size of 50, should have 4 insert calls
        assert table_mock.insert.call_count >= 4
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self, supabase_adapter, mock_supabase_client):
        """Test handling of special characters in content"""
        special_content = "Test with 'quotes' and \"double quotes\" and \n newlines \t tabs"
        
        await supabase_adapter.add_documents(
            urls=["https://test.com/special"],
            chunk_numbers=[0],
            contents=[special_content],
            metadatas=[{"special": True}],
            embeddings=[[0.1] * 1536],
            source_ids=["test.com"]
        )
        
        # Should complete without errors
        table_mock = mock_supabase_client.table.return_value
        table_mock.insert.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_documents_by_url(self, supabase_adapter, mock_supabase_client):
        """Test retrieving documents by URL"""
        # Mock response
        mock_docs = [
            {"id": 1, "content": "Chunk 1", "chunk_number": 0},
            {"id": 2, "content": "Chunk 2", "chunk_number": 1}
        ]
        table_mock = mock_supabase_client.table.return_value
        table_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_docs)
        
        # Test
        results = await supabase_adapter.get_documents_by_url("https://test.com")
        
        # Verify
        assert len(results) == 2
        assert results[0]["content"] == "Chunk 1"
        table_mock.select.assert_called_with('*')
        table_mock.select.return_value.eq.assert_called_with('url', 'https://test.com')
    
    @pytest.mark.asyncio 
    async def test_keyword_search_documents(self, supabase_adapter, mock_supabase_client):
        """Test keyword search functionality"""
        # Mock response
        mock_results = [
            {"id": 1, "content": "Python programming", "url": "https://test.com"}
        ]
        table_mock = mock_supabase_client.table.return_value
        query_mock = MagicMock()
        query_mock.limit.return_value.execute.return_value = MagicMock(data=mock_results)
        query_mock.eq.return_value = query_mock
        table_mock.select.return_value.ilike.return_value = query_mock
        
        # Test without source filter
        results = await supabase_adapter.search_documents_by_keyword(
            keyword="Python",
            match_count=10
        )
        
        assert len(results) == 1
        table_mock.select.return_value.ilike.assert_called_with('content', '%Python%')
        
        # Test with source filter
        await supabase_adapter.search_documents_by_keyword(
            keyword="Python",
            match_count=10,
            source_filter="test.com"
        )
        
        query_mock.eq.assert_called_with('source_id', 'test.com')
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, supabase_adapter, mock_supabase_client):
        """Test handling of connection errors"""
        # Simulate connection error
        mock_supabase_client.table.side_effect = Exception("Connection refused")
        
        # Should handle error gracefully
        with pytest.raises(Exception) as exc_info:
            await supabase_adapter.add_documents(
                urls=["https://test.com"],
                chunk_numbers=[0],
                contents=["Test"],
                metadatas=[{}],
                embeddings=[[0.1] * 1536],
                source_ids=["test.com"]
            )
        
        assert "Connection refused" in str(exc_info.value)