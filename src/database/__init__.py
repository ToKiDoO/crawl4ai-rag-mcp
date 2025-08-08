"""
Database adapter package for vector database operations.
Supports multiple backends: Supabase and Qdrant.
"""

from .base import VectorDatabase
from .factory import create_database_client
from .rag_queries import get_available_sources, perform_rag_query, search_code_examples
from .sources import get_source_statistics, list_all_sources, update_source_summary

__all__ = [
    "VectorDatabase",
    "create_database_client",
    "get_available_sources",
    "get_source_statistics",
    "list_all_sources",
    "perform_rag_query",
    "search_code_examples",
    "update_source_summary",
]
