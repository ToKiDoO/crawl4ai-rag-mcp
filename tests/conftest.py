"""
Pytest configuration and fixtures for database adapter tests.
"""
import pytest
import asyncio
import os
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
async def get_adapter():
    """Factory fixture to get database adapters by name"""
    adapters = {}
    
    async def _get_adapter(adapter_name: str):
        if adapter_name in adapters:
            return adapters[adapter_name]
            
        if adapter_name == "supabase":
            # Import will be available after we create the adapter
            from database.supabase_adapter import SupabaseAdapter
            adapter = SupabaseAdapter()
            # Mock the Supabase client for testing
            adapter.client = MagicMock()
            adapter.client.table = MagicMock(return_value=MagicMock())
            adapter.client.rpc = MagicMock(return_value=MagicMock())
        elif adapter_name == "qdrant":
            # Import will be available after we create the adapter
            from database.qdrant_adapter import QdrantAdapter
            adapter = QdrantAdapter(url="http://localhost:6333")
            # Mock the Qdrant client for testing
            adapter.client = AsyncMock()
        else:
            raise ValueError(f"Unknown adapter: {adapter_name}")
            
        adapters[adapter_name] = adapter
        return adapter
    
    yield _get_adapter
    
    # Cleanup
    adapters.clear()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_openai_embeddings():
    """Mock OpenAI embeddings for testing"""
    import openai
    
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    
    openai.embeddings.create = MagicMock(return_value=mock_response)
    yield openai.embeddings.create


@pytest.fixture
async def clean_test_data():
    """Cleanup test data before and after tests"""
    # This will be implemented when we have real adapters
    yield
    # Cleanup after test