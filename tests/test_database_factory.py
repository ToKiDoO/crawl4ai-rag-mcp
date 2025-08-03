"""
Unit tests for database factory.
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

from database.factory import create_database_client, create_and_initialize_database
from database.supabase_adapter import SupabaseAdapter
from database.qdrant_adapter import QdrantAdapter


class TestDatabaseFactory:
    """Test database factory functions"""
    
    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch('database.supabase_adapter.create_client')
    def test_create_supabase_client(self, mock_create_client):
        """Test creating Supabase client"""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Test
        client = create_database_client()
        
        # Verify
        assert isinstance(client, SupabaseAdapter)
        assert client.__class__.__name__ == "SupabaseAdapter"
    
    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant", "QDRANT_URL": "http://localhost:6333"})
    def test_create_qdrant_client(self):
        """Test creating Qdrant client"""
        # Test
        client = create_database_client()
        
        # Verify
        assert isinstance(client, QdrantAdapter)
        assert client.__class__.__name__ == "QdrantAdapter"
        assert client.url == "http://localhost:6333"
    
    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant", "QDRANT_URL": "http://custom:6333", "QDRANT_API_KEY": "test-key"})
    def test_create_qdrant_client_with_custom_config(self):
        """Test creating Qdrant client with custom configuration"""
        # Test
        client = create_database_client()
        
        # Verify
        assert isinstance(client, QdrantAdapter)
        assert client.url == "http://custom:6333"
        assert client.api_key == "test-key"
    
    @patch.dict(os.environ, {"VECTOR_DATABASE": ""})
    @patch('database.supabase_adapter.create_client')
    def test_create_client_default_to_supabase(self, mock_create_client):
        """Test default to Supabase when VECTOR_DATABASE is empty"""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Test
        client = create_database_client()
        
        # Verify
        assert isinstance(client, SupabaseAdapter)
    
    @patch.dict(os.environ, {"VECTOR_DATABASE": "invalid"})
    def test_create_client_invalid_type(self):
        """Test error for invalid database type"""
        # Test
        with pytest.raises(ValueError) as exc_info:
            create_database_client()
        
        # Verify
        assert "Unknown database type: invalid" in str(exc_info.value)
        assert "Supported types are: 'supabase', 'qdrant'" in str(exc_info.value)
    
    @patch.dict(os.environ, {"VECTOR_DATABASE": "SUPABASE"})
    @patch('database.supabase_adapter.create_client')
    def test_create_client_case_insensitive(self, mock_create_client):
        """Test database type is case insensitive"""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Test with uppercase
        client = create_database_client()
        
        # Verify
        assert isinstance(client, SupabaseAdapter)
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch('database.supabase_adapter.create_client')
    async def test_create_and_initialize_database(self, mock_create_client):
        """Test create and initialize helper function"""
        # Mock Supabase client
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client
        
        # Test
        with patch.object(SupabaseAdapter, 'initialize', new_callable=AsyncMock) as mock_init:
            client = await create_and_initialize_database()
        
        # Verify
        assert isinstance(client, SupabaseAdapter)
        mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"})
    async def test_create_and_initialize_qdrant(self):
        """Test create and initialize for Qdrant"""
        # Test
        with patch.object(QdrantAdapter, 'initialize', new_callable=AsyncMock) as mock_init:
            client = await create_and_initialize_database()
        
        # Verify
        assert isinstance(client, QdrantAdapter)
        mock_init.assert_called_once()
    
    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence"""
        # Set environment
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            client1 = create_database_client()
            assert isinstance(client1, QdrantAdapter)
        
        # Change environment
        with patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"}):
            with patch('database.supabase_adapter.create_client', return_value=MagicMock()):
                client2 = create_database_client()
                assert isinstance(client2, SupabaseAdapter)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])