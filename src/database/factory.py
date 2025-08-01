"""
Factory for creating database adapters based on configuration.
"""
import os
from typing import Union
from .base import VectorDatabase
from .supabase_adapter import SupabaseAdapter
from .qdrant_adapter import QdrantAdapter


def create_database_client() -> VectorDatabase:
    """
    Create a database client based on the VECTOR_DATABASE environment variable.
    
    Returns:
        VectorDatabase: An instance of either SupabaseAdapter or QdrantAdapter
        
    Raises:
        ValueError: If an unknown database type is specified
    """
    db_type = os.getenv("VECTOR_DATABASE", "supabase").lower()
    
    # Handle empty string as default
    if not db_type:
        db_type = "supabase"
    
    if db_type == "supabase":
        return SupabaseAdapter()
    elif db_type == "qdrant":
        url = os.getenv("QDRANT_URL", "http://qdrant:6333")
        api_key = os.getenv("QDRANT_API_KEY")
        return QdrantAdapter(url=url, api_key=api_key)
    else:
        raise ValueError(
            f"Unknown database type: {db_type}. "
            f"Supported types are: 'supabase', 'qdrant'"
        )


async def create_and_initialize_database() -> VectorDatabase:
    """
    Create and initialize a database client.
    This is a convenience function that creates the client and calls initialize().
    
    Returns:
        VectorDatabase: An initialized database adapter
    """
    client = create_database_client()
    await client.initialize()
    return client