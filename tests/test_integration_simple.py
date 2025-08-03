"""
Simple integration tests that can run without Docker.
These tests use mock data and focus on the integration between components.
"""
import pytest
import asyncio
import os
from typing import List, Dict, Any
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

from database.factory import create_database_client
from database.base import VectorDatabase
from utils_refactored import (
    add_documents_to_database,
    search_documents,
    add_code_examples_to_database,
    search_code_examples
)

# Load environment variables
load_dotenv()


class TestSimpleIntegration:
    """Simple integration tests without external dependencies"""
    
    @pytest.fixture
    def mock_embedding(self):
        """Mock embedding generation"""
        def _mock_embedding(text):
            # Return a fake embedding vector
            return [0.1] * 1536
        
        with patch('utils_refactored.create_embedding', side_effect=_mock_embedding):
            with patch('utils_refactored.create_embeddings_batch', 
                      side_effect=lambda texts: [[0.1] * 1536 for _ in texts]):
                yield
    
    async def test_database_factory(self):
        """Test database factory creates correct adapter"""
        # Test Supabase creation
        os.environ["VECTOR_DATABASE"] = "supabase"
        supabase_client = create_database_client()
        assert supabase_client.__class__.__name__ == "SupabaseAdapter"
        
        # Test Qdrant creation
        os.environ["VECTOR_DATABASE"] = "qdrant"
        qdrant_client = create_database_client()
        assert qdrant_client.__class__.__name__ == "QdrantAdapter"
        
        # Test invalid database type
        os.environ["VECTOR_DATABASE"] = "invalid"
        with pytest.raises(ValueError, match="Unknown database type"):
            create_database_client()
    
    async def test_utils_integration_with_mock(self, mock_embedding):
        """Test utility functions integrate correctly with database adapters"""
        # Create a mock database adapter
        mock_db = MagicMock(spec=VectorDatabase)
        mock_db.add_documents = AsyncMock()
        mock_db.search_documents = AsyncMock(return_value=[
            {
                "id": "1",
                "url": "https://example.com/doc1",
                "chunk_number": 0,
                "content": "Test content",
                "metadata": {"title": "Test"},
                "source_id": "example.com",
                "similarity": 0.9
            }
        ])
        
        # Test document addition through utils
        await add_documents_to_database(
            database=mock_db,
            urls=["https://example.com/doc1"],
            chunk_numbers=[0],
            contents=["Test content"],
            metadatas=[{"title": "Test"}],
            url_to_full_document={"https://example.com/doc1": "Test content"}
        )
        
        # Verify the database method was called
        mock_db.add_documents.assert_called_once()
        call_args = mock_db.add_documents.call_args[1]
        assert call_args["urls"] == ["https://example.com/doc1"]
        assert call_args["contents"][0] == "Test content"
        assert len(call_args["embeddings"][0]) == 1536
        
        # Test search through utils
        results = await search_documents(
            database=mock_db,
            query="test query",
            match_count=5
        )
        
        assert len(results) == 1
        assert results[0]["content"] == "Test content"
    
    async def test_code_examples_integration(self, mock_embedding):
        """Test code example functions integrate correctly"""
        # Create a mock database adapter
        mock_db = MagicMock(spec=VectorDatabase)
        mock_db.add_code_examples = AsyncMock()
        mock_db.search_code_examples = AsyncMock(return_value=[
            {
                "id": "1",
                "url": "https://example.com/code1",
                "chunk_number": 0,
                "content": "def test(): pass",
                "summary": "Test function",
                "metadata": {"language": "python"},
                "source_id": "example.com",
                "similarity": 0.95
            }
        ])
        
        # Test code example addition
        await add_code_examples_to_database(
            database=mock_db,
            urls=["https://example.com/code1"],
            chunk_numbers=[0],
            code_examples=["def test(): pass"],
            summaries=["Test function"],
            metadatas=[{"language": "python"}]
        )
        
        # Verify the database method was called
        mock_db.add_code_examples.assert_called_once()
        
        # Test code example search
        results = await search_code_examples(
            database=mock_db,
            query="test function",
            match_count=5
        )
        
        assert len(results) == 1
        assert results[0]["summary"] == "Test function"
    
    async def test_contextual_embeddings_flag(self, mock_embedding):
        """Test contextual embeddings feature flag"""
        mock_db = MagicMock(spec=VectorDatabase)
        mock_db.add_documents = AsyncMock()
        
        # Test with contextual embeddings disabled
        os.environ["USE_CONTEXTUAL_EMBEDDINGS"] = "false"
        await add_documents_to_database(
            database=mock_db,
            urls=["https://example.com/doc1"],
            chunk_numbers=[0],
            contents=["Test content"],
            metadatas=[{"title": "Test"}],
            url_to_full_document={"https://example.com/doc1": "Full document content"}
        )
        
        # Content should be unchanged
        call_args = mock_db.add_documents.call_args[1]
        assert call_args["contents"][0] == "Test content"
        
        # Test with contextual embeddings enabled
        os.environ["USE_CONTEXTUAL_EMBEDDINGS"] = "true"
        with patch('utils_refactored.generate_contextual_embedding', 
                  return_value=("Contextualized: Test content", True)):
            await add_documents_to_database(
                database=mock_db,
                urls=["https://example.com/doc2"],
                chunk_numbers=[0],
                contents=["Test content 2"],
                metadatas=[{"title": "Test 2"}],
                url_to_full_document={"https://example.com/doc2": "Full document content 2"}
            )
        
        # Content should be contextualized
        call_args = mock_db.add_documents.call_args[1]
        assert "Contextualized:" in call_args["contents"][0]
    
    async def test_error_handling(self, mock_embedding):
        """Test error handling in integration"""
        # Create a mock database that raises errors
        mock_db = MagicMock(spec=VectorDatabase)
        mock_db.add_documents = AsyncMock(side_effect=Exception("Database error"))
        
        # Test that errors propagate correctly
        with pytest.raises(Exception, match="Database error"):
            await add_documents_to_database(
                database=mock_db,
                urls=["https://example.com/doc1"],
                chunk_numbers=[0],
                contents=["Test content"],
                metadatas=[{"title": "Test"}],
                url_to_full_document={"https://example.com/doc1": "Test content"}
            )


class AsyncMock(MagicMock):
    """Helper class for async mock methods"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])