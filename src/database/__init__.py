"""
Database adapter package for vector database operations.
Supports multiple backends: Supabase and Qdrant.
"""

from .base import VectorDatabase
from .factory import create_database_client
from .rag_queries import get_available_sources, perform_rag_query, search_code_examples
from .sources import update_source_summary, get_source_statistics, list_all_sources

__all__ = [
    "VectorDatabase",
    "create_database_client",
    "get_available_sources",
    "perform_rag_query",
    "search_code_examples",
    "update_source_summary",
    "get_source_statistics",
    "list_all_sources",
]
