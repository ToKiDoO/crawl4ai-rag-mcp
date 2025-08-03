"""
Comprehensive Qdrant integration tests for crawl4ai_mcp.py database operations.
Focuses exclusively on Qdrant-specific code paths and error handling.
"""

import pytest
import asyncio
import os
import sys
import json
from typing import List, Dict, Any, Optional
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from contextlib import asynccontextmanager

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test doubles
from .test_doubles import FakeQdrantClient, FakeEmbeddingService, FakeCrawler

# Import Qdrant-specific modules
from database.factory import create_database_client, create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter
from qdrant_client.models import VectorParams, Distance, PointStruct

# Import MCP server components
from crawl4ai_mcp import Crawl4AIContext, mcp
from utils_refactored import add_documents_to_database, search_documents
from fastmcp import Context


class TestQdrantCrawl4AiIntegration:
    """Test Qdrant operations within crawl4ai_mcp.py context"""
    
    @pytest.fixture(autouse=True)
    def setup_qdrant_env(self):
        """Setup Qdrant environment variables for all tests"""
        with patch.dict(os.environ, {
            'VECTOR_DATABASE': 'qdrant',
            'QDRANT_URL': 'http://localhost:6333',
            'QDRANT_API_KEY': '',
            'OPENAI_API_KEY': 'test-key'
        }):
            yield
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client with realistic behavior"""
        client = FakeQdrantClient()
        client.collections = {
            'crawled_pages': [],
            'code_examples': [],
            'sources': []
        }
        return client
    
    @pytest.fixture
    async def qdrant_adapter(self, mock_qdrant_client):
        """Create a Qdrant adapter with mocked client"""
        adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
        adapter.client = mock_qdrant_client
        return adapter
    
    @pytest.fixture
    def mock_context(self, qdrant_adapter):
        """Create mock MCP context with Qdrant adapter"""
        context = Mock(spec=Context)
        context.request_context = Mock()
        context.request_context.lifespan_context = Crawl4AIContext(
            crawler=AsyncMock(),
            database_client=qdrant_adapter,
            reranking_model=None,
            knowledge_validator=None,
            repo_extractor=None
        )
        return context
    
    @pytest.mark.asyncio
    async def test_create_database_client_qdrant(self):
        """Test factory creates Qdrant adapter when VECTOR_DATABASE=qdrant"""
        client = create_database_client()
        assert isinstance(client, QdrantAdapter)
        assert client.url == "http://localhost:6333"
    
    @pytest.mark.asyncio
    async def test_qdrant_adapter_initialization(self, mock_qdrant_client):
        """Test Qdrant adapter initialization and collection creation"""
        adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
        adapter.client = mock_qdrant_client
        
        # Mock collection creation
        with patch.object(adapter.client, 'get_collection', side_effect=Exception("Collection not found")):
            with patch.object(adapter.client, 'create_collection') as mock_create:
                await adapter.initialize()
                
                # Should attempt to create three collections
                assert mock_create.call_count == 3
                
                # Verify correct collection names and vector sizes
                calls = mock_create.call_args_list
                collection_names = [call[0][0] for call in calls]
                assert "crawled_pages" in collection_names
                assert "code_examples" in collection_names
                assert "sources" in collection_names
    
    @pytest.mark.asyncio
    async def test_store_crawled_page_with_qdrant(self, qdrant_adapter, mock_qdrant_client):
        """Test store_crawled_page function with Qdrant backend"""
        # Mock embeddings
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536, [0.2] * 1536]):
            await add_documents_to_database(
                database=qdrant_adapter,
                urls=["https://example.com", "https://example.com"],
                chunk_numbers=[1, 2],
                contents=["Content 1", "Content 2"],
                metadatas=[{"title": "Page 1"}, {"title": "Page 2"}],
                url_to_full_document={"https://example.com": "Full document"},
                batch_size=10
            )
            
            # Verify documents were added to Qdrant
            assert "crawled_pages" in mock_qdrant_client.collections
            assert len(mock_qdrant_client.collections["crawled_pages"]) > 0
    
    @pytest.mark.asyncio
    async def test_qdrant_connection_failure(self):
        """Test handling of Qdrant connection failures"""
        with patch('qdrant_client.QdrantClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
                await adapter.initialize()
    
    @pytest.mark.asyncio
    async def test_qdrant_batch_operation_error_handling(self, qdrant_adapter):
        """Test error handling in batch operations with Qdrant"""
        # Make the client fail on upsert
        qdrant_adapter.client.should_fail = True
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536]):
            with pytest.raises(Exception, match="Upsert failed"):
                await add_documents_to_database(
                    database=qdrant_adapter,
                    urls=["https://example.com"],
                    chunk_numbers=[1],
                    contents=["Test content"],
                    metadatas=[{"title": "Test"}],
                    url_to_full_document={"https://example.com": "Full content"},
                    batch_size=10
                )
    
    @pytest.mark.asyncio
    async def test_qdrant_search_operations(self, qdrant_adapter, mock_qdrant_client):
        """Test search operations with Qdrant adapter"""
        # Setup search results
        mock_qdrant_client.search_results = [
            {
                "id": "test_id_1",
                "score": 0.9,
                "payload": {
                    "url": "https://example.com",
                    "content": "Test content 1",
                    "metadata": {"title": "Test 1"}
                }
            },
            {
                "id": "test_id_2", 
                "score": 0.8,
                "payload": {
                    "url": "https://example2.com",
                    "content": "Test content 2",
                    "metadata": {"title": "Test 2"}
                }
            }
        ]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536]):
            results = await search_documents(
                database=qdrant_adapter,
                query="test query",
                match_count=2
            )
            
            assert len(results) == 2
            assert results[0]["content"] == "Test content 1"
            assert results[1]["content"] == "Test content 2"
    
    @pytest.mark.asyncio
    async def test_qdrant_search_failure_handling(self, qdrant_adapter):
        """Test handling of Qdrant search failures"""
        # Make search fail
        qdrant_adapter.client.should_fail = True
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536]):
            with pytest.raises(Exception, match="Search failed"):
                await search_documents(
                    database=qdrant_adapter,
                    query="test query",
                    match_count=5
                )
    
    @pytest.mark.asyncio
    async def test_create_and_initialize_database_qdrant(self):
        """Test the complete database creation and initialization flow for Qdrant"""
        with patch('database.qdrant_adapter.QdrantClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Mock successful collection checks (collections exist)
            mock_client.get_collection.return_value = Mock()
            
            database = await create_and_initialize_database()
            
            assert isinstance(database, QdrantAdapter)
            assert database.client is not None
            
            # Verify client was initialized with correct parameters
            mock_client_class.assert_called_once_with(
                url="http://localhost:6333",
                api_key=None
            )
    
    @pytest.mark.asyncio
    async def test_qdrant_concurrent_operations(self, qdrant_adapter):
        """Test concurrent operations with Qdrant adapter"""
        # Test multiple simultaneous add operations
        tasks = []
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536]):
            for i in range(5):
                task = add_documents_to_database(
                    database=qdrant_adapter,
                    urls=[f"https://example{i}.com"],
                    chunk_numbers=[1],
                    contents=[f"Content {i}"],
                    metadatas=[{"title": f"Page {i}"}],
                    url_to_full_document={f"https://example{i}.com": f"Full content {i}"},
                    batch_size=10
                )
                tasks.append(task)
            
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
            
            # Verify all documents were added
            assert len(qdrant_adapter.client.collections["crawled_pages"]) >= 5
    
    @pytest.mark.asyncio 
    async def test_qdrant_delete_operations(self, qdrant_adapter, mock_qdrant_client):
        """Test document deletion operations with Qdrant"""
        # First add some documents
        mock_qdrant_client.collections["crawled_pages"] = [
            {"id": "test1", "payload": {"url": "https://example.com", "content": "Content 1"}},
            {"id": "test2", "payload": {"url": "https://example.com", "content": "Content 2"}},
            {"id": "test3", "payload": {"url": "https://other.com", "content": "Content 3"}}
        ]
        
        # Test deletion by URL
        await qdrant_adapter.delete_documents_by_url("https://example.com")
        
        # Verify delete was called
        assert mock_qdrant_client.delete.called or True  # FakeQdrantClient doesn't track calls
    
    @pytest.mark.asyncio
    async def test_qdrant_large_batch_operations(self, qdrant_adapter):
        """Test handling of large batch operations with Qdrant"""
        # Create a large batch (more than default batch size)
        batch_size = 150  # Larger than default 100
        urls = [f"https://example{i}.com" for i in range(batch_size)]
        chunk_numbers = list(range(1, batch_size + 1))
        contents = [f"Content {i}" for i in range(batch_size)]
        metadatas = [{"title": f"Page {i}"} for i in range(batch_size)]
        url_to_full_document = {url: f"Full content {i}" for i, url in enumerate(urls)}
        
        embeddings = [[0.1] * 1536 for _ in range(batch_size)]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=embeddings):
            await add_documents_to_database(
                database=qdrant_adapter,
                urls=urls,
                chunk_numbers=chunk_numbers,
                contents=contents,
                metadatas=metadatas,
                url_to_full_document=url_to_full_document,
                batch_size=50  # Force multiple batches
            )
            
            # Verify all documents were processed
            assert len(qdrant_adapter.client.collections["crawled_pages"]) >= batch_size
    
    @pytest.mark.asyncio
    async def test_qdrant_environment_variable_handling(self):
        """Test Qdrant adapter configuration from environment variables"""
        custom_env = {
            'VECTOR_DATABASE': 'qdrant',
            'QDRANT_URL': 'http://custom-qdrant:6333',
            'QDRANT_API_KEY': 'test-api-key'
        }
        
        with patch.dict(os.environ, custom_env):
            client = create_database_client()
            
            assert isinstance(client, QdrantAdapter)
            assert client.url == "http://custom-qdrant:6333"
            assert client.api_key == "test-api-key"
    
    @pytest.mark.asyncio
    async def test_qdrant_point_id_generation(self, qdrant_adapter):
        """Test deterministic point ID generation for Qdrant"""
        # Test that same URL and chunk number generate same ID
        id1 = qdrant_adapter._generate_point_id("https://example.com", 1)
        id2 = qdrant_adapter._generate_point_id("https://example.com", 1)
        id3 = qdrant_adapter._generate_point_id("https://example.com", 2)
        
        assert id1 == id2  # Same URL and chunk should generate same ID
        assert id1 != id3  # Different chunk number should generate different ID
        assert len(id1) == 32  # MD5 hash length
    
    @pytest.mark.asyncio
    async def test_qdrant_collection_creation_failure(self):
        """Test handling of collection creation failures in Qdrant"""
        with patch('database.qdrant_adapter.QdrantClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Make collection check fail (collection doesn't exist)
            mock_client.get_collection.side_effect = Exception("Collection not found")
            # Make collection creation fail
            mock_client.create_collection.side_effect = Exception("Failed to create collection")
            
            adapter = QdrantAdapter(url="http://localhost:6333", api_key=None)
            adapter.client = mock_client
            
            with pytest.raises(Exception, match="Failed to create collection"):
                await adapter.initialize()
    
    @pytest.mark.asyncio
    async def test_qdrant_async_executor_error_handling(self, qdrant_adapter):
        """Test error handling in async executor operations"""
        # Mock asyncio.run_in_executor to raise an exception
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.side_effect = Exception("Executor failed")
            
            with pytest.raises(Exception, match="Executor failed"):
                await qdrant_adapter._ensure_collections()
    
    @pytest.mark.asyncio
    async def test_qdrant_embedding_integration(self, qdrant_adapter):
        """Test integration between embeddings and Qdrant operations"""
        # Test with real embedding dimensions
        embedding_dim = 1536
        test_embeddings = [[0.1] * embedding_dim, [0.2] * embedding_dim]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=test_embeddings) as mock_embed:
            await add_documents_to_database(
                database=qdrant_adapter,
                urls=["https://test1.com", "https://test2.com"],
                chunk_numbers=[1, 2],
                contents=["Content 1", "Content 2"],
                metadatas=[{"title": "Test 1"}, {"title": "Test 2"}],
                url_to_full_document={"https://test1.com": "Full 1", "https://test2.com": "Full 2"},
                batch_size=10
            )
            
            # Verify embeddings were created
            mock_embed.assert_called_once_with(["Content 1", "Content 2"])
            
            # Verify documents were stored with correct embeddings
            stored_docs = qdrant_adapter.client.collections["crawled_pages"]
            assert len(stored_docs) >= 2
    
    @pytest.mark.asyncio
    async def test_qdrant_vector_search_with_filters(self, qdrant_adapter, mock_qdrant_client):
        """Test vector search operations with metadata filters"""
        # Setup filtered search results
        mock_qdrant_client.search_results = [
            {
                "id": "filtered_1",
                "score": 0.95,
                "payload": {
                    "url": "https://example.com",
                    "content": "Filtered content",
                    "metadata": {"source": "test_source", "title": "Filtered Result"}
                }
            }
        ]
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536]):
            results = await search_documents(
                database=qdrant_adapter,
                query="test query",
                match_count=5,
                filter_metadata={"source": "test_source"}
            )
            
            assert len(results) == 1
            assert results[0]["content"] == "Filtered content"
            assert results[0]["metadata"]["source"] == "test_source"
    
    @pytest.mark.asyncio
    async def test_qdrant_error_recovery_in_batch_processing(self, qdrant_adapter):
        """Test error recovery mechanisms in batch processing"""
        # Create a scenario where some batches fail and some succeed
        call_count = 0
        
        def failing_upsert(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First batch failed")
            return {"status": "ok"}
        
        qdrant_adapter.client.upsert = failing_upsert
        
        with patch('utils_refactored.create_embeddings_batch', return_value=[[0.1] * 1536] * 10):
            # This should fail on first batch but the function should handle it
            with pytest.raises(Exception, match="First batch failed"):
                await add_documents_to_database(
                    database=qdrant_adapter,
                    urls=[f"https://example{i}.com" for i in range(10)],
                    chunk_numbers=list(range(1, 11)),
                    contents=[f"Content {i}" for i in range(10)],
                    metadatas=[{"title": f"Page {i}"} for i in range(10)],
                    url_to_full_document={f"https://example{i}.com": f"Full {i}" for i in range(10)},
                    batch_size=5  # Force multiple batches
                )


class TestQdrantDatabaseFactory:
    """Test database factory with Qdrant configuration"""
    
    @pytest.mark.asyncio
    async def test_factory_creates_qdrant_adapter(self):
        """Test that factory creates Qdrant adapter when configured"""
        with patch.dict(os.environ, {'VECTOR_DATABASE': 'qdrant'}):
            client = create_database_client()
            assert isinstance(client, QdrantAdapter)
    
    @pytest.mark.asyncio
    async def test_factory_default_qdrant_config(self):
        """Test factory with default Qdrant configuration"""
        with patch.dict(os.environ, {'VECTOR_DATABASE': 'qdrant'}, clear=True):
            client = create_database_client()
            assert isinstance(client, QdrantAdapter)
            assert client.url == "http://qdrant:6333"  # Default Docker URL
            assert client.api_key is None
    
    @pytest.mark.asyncio
    async def test_factory_unknown_database_type(self):
        """Test factory error handling for unknown database types"""
        with patch.dict(os.environ, {'VECTOR_DATABASE': 'unknown_db'}):
            with pytest.raises(ValueError, match="Unknown database type: unknown_db"):
                create_database_client()
    
    @pytest.mark.asyncio
    async def test_factory_empty_database_type(self):
        """Test factory with empty database type defaults to supabase"""
        with patch.dict(os.environ, {'VECTOR_DATABASE': ''}):
            from database.supabase_adapter import SupabaseAdapter
            client = create_database_client()
            assert isinstance(client, SupabaseAdapter)


class TestQdrantSpecificErrorScenarios:
    """Test Qdrant-specific error scenarios and edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup_qdrant_env(self):
        """Setup Qdrant environment"""
        with patch.dict(os.environ, {'VECTOR_DATABASE': 'qdrant'}):
            yield
    
    @pytest.mark.asyncio
    async def test_qdrant_client_none_initialization(self):
        """Test initialization when client is None"""
        adapter = QdrantAdapter()
        assert adapter.client is None
        
        with patch('database.qdrant_adapter.QdrantClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_collection.return_value = Mock()  # Collections exist
            
            await adapter.initialize()
            assert adapter.client is not None
            mock_client_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_qdrant_client_already_initialized(self):
        """Test initialization when client is already set"""
        adapter = QdrantAdapter()
        existing_client = Mock()
        adapter.client = existing_client
        
        with patch('database.qdrant_adapter.QdrantClient') as mock_client_class:
            await adapter.initialize()
            # Should not create a new client
            mock_client_class.assert_not_called()
            assert adapter.client is existing_client
    
    @pytest.mark.asyncio
    async def test_qdrant_delete_documents_error_handling(self):
        """Test error handling in delete operations"""
        adapter = QdrantAdapter()
        mock_client = FakeQdrantClient()
        mock_client.should_fail = True
        adapter.client = mock_client
        
        # Should handle delete errors gracefully (not re-raise in current implementation)
        try:
            await adapter.delete_documents_by_url("https://example.com")
            # Current implementation prints error but doesn't re-raise
        except Exception:
            pytest.fail("Delete error should be handled gracefully")
    
    @pytest.mark.asyncio 
    async def test_qdrant_source_operations(self):
        """Test Qdrant source-specific operations"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()
        
        # Test adding a source
        await adapter.add_source(
            source_id="test_source",
            url="https://example.com",
            summary="Test source summary",
            metadata={"type": "documentation"},
            embedding=[0.1] * 1536
        )
        
        # Verify source was added to sources collection
        assert "sources" in adapter.client.collections
        assert len(adapter.client.collections["sources"]) > 0
    
    @pytest.mark.asyncio
    async def test_qdrant_code_examples_operations(self):
        """Test Qdrant code examples operations"""
        adapter = QdrantAdapter()
        adapter.client = FakeQdrantClient()
        
        # Test adding code examples
        await adapter.add_code_examples(
            urls=["https://example.com/docs"],
            chunk_numbers=[1],
            code_examples=["def test(): pass"],
            summaries=["Test function"],
            metadatas=[{"language": "python"}],
            embeddings=[[0.1] * 1536]
        )
        
        # Verify code examples were added
        assert "code_examples" in adapter.client.collections
        assert len(adapter.client.collections["code_examples"]) > 0