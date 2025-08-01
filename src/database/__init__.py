"""
Database adapter package for vector database operations.
Supports multiple backends: Supabase and Qdrant.
"""
from .base import VectorDatabase
from .factory import create_database_client

__all__ = ["VectorDatabase", "create_database_client"]