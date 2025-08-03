"""
Comprehensive Qdrant database integration tests for crawl4ai_mcp.py
Tests Qdrant-specific database operations with proper environment handling.
"""

import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.factory import create_and_initialize_database
from src.database.qdrant_adapter import QdrantAdapter
from src.utils_refactored import add_documents_to_database, search_documents


class TestQdrantDatabaseIntegration:
    """Test Qdrant database integration with crawl4ai_mcp.py"""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Set up test environment for Qdrant"""
        # Determine if running in Docker or locally
        qdrant_host = "qdrant" if os.path.exists("/.dockerenv") else "localhost"
        
        # Set test environment variables
        test_env = {
            "VECTOR_DATABASE": "qdrant",
            "QDRANT_URL": f"http://{qdrant_host}:6333",
            "QDRANT_API_KEY": "test_key",
            "DATABASE_COLLECTION": "test_crawled_pages",
            "OPENAI_API_KEY": "test-key-123",
        }
        
        with patch.dict(os.environ, test_env, clear=False):
            yield
    
    @pytest.mark.asyncio
    async def test_qdrant_initialization(self):
        """Test Qdrant database initialization"""
        # Mock Qdrant client to avoid actual connection
        with patch("src.database.qdrant_adapter.QdrantClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            
            # Initialize database
            db = await create_and_initialize_database()
            
            # Verify initialization
            assert db is not None
            mock_client.assert_called_once()
            
            # Check URL was parsed correctly
            call_args = mock_client.call_args
            if "localhost" in os.environ.get("QDRANT_URL", ""):
                assert "localhost" in str(call_args)
            else:
                assert "qdrant" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_add_documents_with_qdrant(self):
        """Test adding documents to Qdrant database"""
        # Mock dependencies
        with patch("src.database.qdrant_adapter.QdrantClient") as mock_client, \
             patch("openai.embeddings.create") as mock_create:
            
            # Set up mocks
            mock_qdrant_instance = MagicMock()
            mock_client.return_value = mock_qdrant_instance
            
            # Mock collection exists
            mock_qdrant_instance.collection_exists.return_value = True
            
            # Mock OpenAI embeddings
            mock_embedding_response = MagicMock()
            mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_create.return_value = mock_embedding_response
            
            # Create database instance
            db = QdrantAdapter(mock_qdrant_instance, "test_collection")
            
            # Test data
            test_docs = {
                "urls": ["http://example.com/test"],
                "chunk_numbers": [1],
                "contents": ["Test content for Qdrant"],
                "metadatas": [{"source": "test"}],
                "url_to_full_document": {"http://example.com/test": "Full document content"}
            }
            
            # Add documents
            await add_documents_to_database(
                db,
                test_docs["urls"],
                test_docs["chunk_numbers"],
                test_docs["contents"],
                test_docs["metadatas"],
                test_docs["url_to_full_document"]
            )
            
            # Verify Qdrant operations were called
            assert mock_qdrant_instance.upsert.called
    
    @pytest.mark.asyncio
    async def test_search_documents_with_qdrant(self):
        """Test searching documents in Qdrant database"""
        # Mock dependencies
        with patch("src.database.qdrant_adapter.QdrantClient") as mock_client, \
             patch("openai.embeddings.create") as mock_create:
            
            # Set up mocks
            mock_qdrant_instance = MagicMock()
            mock_client.return_value = mock_qdrant_instance
            
            # Mock search results
            mock_search_results = [
                MagicMock(
                    id="test-id-1",
                    score=0.9,
                    payload={
                        "content": "Test result 1",
                        "url": "http://example.com/1",
                        "metadata": {"source": "test"}
                    }
                )
            ]
            mock_qdrant_instance.search.return_value = mock_search_results
            
            # Mock OpenAI embeddings
            mock_embedding_response = MagicMock()
            mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_create.return_value = mock_embedding_response
            
            # Search
            results = await search_documents("test query", top_k=5)
            
            # Verify results
            assert len(results) == 1
            assert results[0]["content"] == "Test result 1"
            assert results[0]["score"] == 0.9
    
    @pytest.mark.asyncio
    async def test_qdrant_connection_error_handling(self):
        """Test error handling for Qdrant connection failures"""
        with patch("src.database.qdrant_adapter.QdrantClient") as mock_client:
            # Simulate connection error
            mock_client.side_effect = Exception("Connection refused to Qdrant")
            
            # Attempt to initialize database
            with pytest.raises(Exception) as exc_info:
                await create_and_initialize_database()
            
            assert "Connection refused" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_concurrent_qdrant_operations(self):
        """Test concurrent operations with Qdrant"""
        # Mock dependencies
        with patch("src.database.qdrant_adapter.QdrantClient") as mock_client, \
             patch("openai.embeddings.create") as mock_create:
            
            # Set up mocks
            mock_qdrant_instance = MagicMock()
            mock_client.return_value = mock_qdrant_instance
            mock_qdrant_instance.collection_exists.return_value = True
            
            # Mock OpenAI
            mock_embedding_response = MagicMock()
            mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
            mock_create.return_value = mock_embedding_response
            
            # Create concurrent tasks
            async def add_docs(idx):
                await add_documents_to_database(
                    [f"http://example.com/{idx}"],
                    [f"Content {idx}"],
                    [{"idx": idx}]
                )
            
            # Run concurrent operations
            tasks = [add_docs(i) for i in range(5)]
            await asyncio.gather(*tasks)
            
            # Verify all operations completed
            assert mock_qdrant_instance.upsert.call_count == 5
    
    @pytest.mark.asyncio
    async def test_qdrant_batch_operations(self):
        """Test batch operations with Qdrant"""
        # Mock dependencies
        with patch("src.database.qdrant_adapter.QdrantClient") as mock_client, \
             patch("openai.embeddings.create") as mock_create:
            
            # Set up mocks
            mock_qdrant_instance = MagicMock()
            mock_client.return_value = mock_qdrant_instance
            mock_qdrant_instance.collection_exists.return_value = True
            
            # Create batch test data
            batch_size = 25
            urls = [f"http://example.com/{i}" for i in range(batch_size)]
            contents = [f"Content {i}" for i in range(batch_size)]
            metadatas = [{"idx": i} for i in range(batch_size)]
            
            # Mock embedding responses
            mock_embeddings = [MagicMock(embedding=[0.1] * 1536) for _ in range(batch_size)]
            mock_embedding_response = MagicMock()
            mock_embedding_response.data = mock_embeddings
            mock_create.return_value = mock_embedding_response
            
            # Add batch
            await add_documents_to_database(urls, contents, metadatas)
            
            # Verify batch was processed
            assert mock_qdrant_instance.upsert.called
            upsert_call = mock_qdrant_instance.upsert.call_args[0]
            assert len(upsert_call[1]) == batch_size  # Check points count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])