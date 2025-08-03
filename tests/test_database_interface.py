"""
Test suite for VectorDatabase interface contract.
Both Supabase and Qdrant adapters must pass these tests.
"""
import pytest
from typing import List, Dict, Any
import asyncio


class TestVectorDatabaseInterface:
    """Tests that both adapters implement the same interface"""
    
    @pytest.fixture
    async def sample_documents(self):
        """Sample data for testing document operations"""
        return {
            "urls": ["https://example.com/page1", "https://example.com/page2"],
            "chunk_numbers": [1, 2],
            "contents": ["This is the first document", "This is the second document"],
            "metadatas": [{"title": "Page 1"}, {"title": "Page 2"}],
            "embeddings": [[0.1] * 1536, [0.2] * 1536],  # OpenAI embedding size
            "source_ids": ["example.com", "example.com"]
        }
    
    @pytest.fixture
    async def sample_code_examples(self):
        """Sample data for testing code example operations"""
        return {
            "urls": ["https://example.com/docs"],
            "chunk_numbers": [1],
            "code_examples": ["def hello():\n    return 'world'"],
            "summaries": ["A simple hello world function"],
            "metadatas": [{"language": "python"}],
            "embeddings": [[0.3] * 1536],
            "source_ids": ["example.com"]
        }
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_adapter_initialization(self, adapter_name, get_adapter):
        """Test that adapters can be initialized properly"""
        adapter = await get_adapter(adapter_name)
        assert adapter is not None
        
        # Test initialization method exists
        await adapter.initialize()
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_add_and_search_documents(self, adapter_name, get_adapter, sample_documents):
        """Test document addition and searching"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Clean up any existing documents first
        await adapter.delete_documents_by_url(sample_documents["urls"])
        
        # Add documents
        await adapter.add_documents(
            urls=sample_documents["urls"],
            chunk_numbers=sample_documents["chunk_numbers"],
            contents=sample_documents["contents"],
            metadatas=sample_documents["metadatas"],
            embeddings=sample_documents["embeddings"],
            source_ids=sample_documents["source_ids"]
        )
        
        # Search for documents
        query_embedding = [0.15] * 1536
        results = await adapter.search_documents(
            query_embedding=query_embedding,
            match_count=10
        )
        
        # Verify results
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check result structure
        for result in results:
            assert "id" in result
            assert "url" in result
            assert "chunk_number" in result
            assert "content" in result
            assert "metadata" in result
            assert "source_id" in result
            assert "similarity" in result
            assert 0 <= result["similarity"] <= 1
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_search_with_filters(self, adapter_name, get_adapter, sample_documents):
        """Test searching with metadata filters"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Add documents with different metadata
        urls = ["https://test.com/1", "https://test.com/2"]
        await adapter.delete_documents_by_url(urls)
        
        await adapter.add_documents(
            urls=urls,
            chunk_numbers=[1, 1],
            contents=["Python content", "JavaScript content"],
            metadatas=[{"language": "python"}, {"language": "javascript"}],
            embeddings=[[0.4] * 1536, [0.5] * 1536],
            source_ids=["test.com", "test.com"]
        )
        
        # Search with filter
        results = await adapter.search_documents(
            query_embedding=[0.45] * 1536,
            match_count=10,
            filter_metadata={"language": "python"}
        )
        
        # Should only return Python content
        assert all(r["metadata"].get("language") == "python" for r in results)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_search_with_source_filter(self, adapter_name, get_adapter):
        """Test searching with source filter"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Add documents from different sources
        urls = ["https://source1.com/page", "https://source2.com/page"]
        await adapter.delete_documents_by_url(urls)
        
        await adapter.add_documents(
            urls=urls,
            chunk_numbers=[1, 1],
            contents=["Content from source 1", "Content from source 2"],
            metadatas=[{}, {}],
            embeddings=[[0.6] * 1536, [0.7] * 1536],
            source_ids=["source1.com", "source2.com"]
        )
        
        # Search with source filter
        results = await adapter.search_documents(
            query_embedding=[0.65] * 1536,
            match_count=10,
            source_filter="source1.com"
        )
        
        # Should only return results from source1
        assert all(r["source_id"] == "source1.com" for r in results)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_delete_documents(self, adapter_name, get_adapter):
        """Test document deletion"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Add a document
        url = "https://delete-test.com/page"
        await adapter.add_documents(
            urls=[url],
            chunk_numbers=[1],
            contents=["Content to be deleted"],
            metadatas=[{}],
            embeddings=[[0.8] * 1536],
            source_ids=["delete-test.com"]
        )
        
        # Verify it exists
        results = await adapter.search_documents(
            query_embedding=[0.8] * 1536,
            match_count=10
        )
        assert any(r["url"] == url for r in results)
        
        # Delete it
        await adapter.delete_documents_by_url([url])
        
        # Verify it's gone
        results = await adapter.search_documents(
            query_embedding=[0.8] * 1536,
            match_count=10
        )
        assert not any(r["url"] == url for r in results)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_code_examples_operations(self, adapter_name, get_adapter, sample_code_examples):
        """Test code example operations"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Clean up
        await adapter.delete_code_examples_by_url(sample_code_examples["urls"])
        
        # Add code examples
        await adapter.add_code_examples(
            urls=sample_code_examples["urls"],
            chunk_numbers=sample_code_examples["chunk_numbers"],
            code_examples=sample_code_examples["code_examples"],
            summaries=sample_code_examples["summaries"],
            metadatas=sample_code_examples["metadatas"],
            embeddings=sample_code_examples["embeddings"],
            source_ids=sample_code_examples["source_ids"]
        )
        
        # Search code examples
        results = await adapter.search_code_examples(
            query_embedding=[0.3] * 1536,
            match_count=10
        )
        
        # Verify results
        assert isinstance(results, list)
        assert len(results) > 0
        
        for result in results:
            assert "content" in result
            assert "summary" in result
            assert "metadata" in result
            assert "similarity" in result
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_source_operations(self, adapter_name, get_adapter):
        """Test source information operations"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        source_id = "test-source.com"
        
        # Update/create source
        await adapter.update_source_info(
            source_id=source_id,
            summary="A test source for unit tests",
            word_count=1000
        )
        
        # Get all sources
        sources = await adapter.get_sources()
        
        # Verify our source exists
        assert any(s["source_id"] == source_id for s in sources)
        
        # Find our source and verify data
        our_source = next(s for s in sources if s["source_id"] == source_id)
        assert our_source["summary"] == "A test source for unit tests"
        assert our_source["total_word_count"] == 1000
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_batch_operations(self, adapter_name, get_adapter):
        """Test that batch operations work efficiently"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Create many documents
        num_docs = 50
        urls = [f"https://batch-test.com/page{i}" for i in range(num_docs)]
        
        # Clean up
        await adapter.delete_documents_by_url(urls)
        
        # Add in batch
        await adapter.add_documents(
            urls=urls,
            chunk_numbers=list(range(num_docs)),
            contents=[f"Content {i}" for i in range(num_docs)],
            metadatas=[{"index": i} for i in range(num_docs)],
            embeddings=[[i/100] * 1536 for i in range(num_docs)],
            source_ids=["batch-test.com"] * num_docs
        )
        
        # Search should return results
        results = await adapter.search_documents(
            query_embedding=[0.25] * 1536,
            match_count=20
        )
        
        assert len(results) > 0
        assert len(results) <= 20
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("adapter_name", ["supabase", "qdrant"])
    async def test_error_handling(self, adapter_name, get_adapter):
        """Test that adapters handle errors gracefully"""
        adapter = await get_adapter(adapter_name)
        await adapter.initialize()
        
        # Test with invalid embedding size
        with pytest.raises(Exception):
            await adapter.add_documents(
                urls=["https://error-test.com"],
                chunk_numbers=[1],
                contents=["Test"],
                metadatas=[{}],
                embeddings=[[0.1] * 100],  # Wrong size
                source_ids=["error-test.com"]
            )
        
        # Test search with invalid embedding
        with pytest.raises(Exception):
            await adapter.search_documents(
                query_embedding=[0.1] * 100,  # Wrong size
                match_count=10
            )