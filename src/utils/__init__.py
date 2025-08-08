"""Utility functions for the Crawl4AI MCP server."""

from .reranking import rerank_results
from .text_processing import extract_section_info, process_code_example, smart_chunk_markdown
from .url_helpers import is_sitemap, is_txt, normalize_url, parse_sitemap
from .validation import (
    validate_github_url,
    validate_neo4j_connection,
    validate_script_path,
)

# Import functions from parent utils.py module
try:
    # Import from parent directory's utils.py
    from ..utils import create_embedding, add_documents_to_database, create_embeddings_batch
except ImportError:
    try:
        # Fallback: try direct import if we're running from src
        import sys
        from pathlib import Path
        src_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(src_dir))
        from utils import create_embedding, add_documents_to_database, create_embeddings_batch
        sys.path.remove(str(src_dir))
    except ImportError:
        # If import fails, create stubs
        def create_embedding(text: str) -> list[float]:
            """Stub implementation when create_embedding is not available."""
            import warnings
            warnings.warn("create_embedding function not available, using stub")
            return [0.0] * 1536
        
        def create_embeddings_batch(texts: list[str]) -> list[list[float]]:
            """Stub implementation when create_embeddings_batch is not available."""
            import warnings
            warnings.warn("create_embeddings_batch function not available, using stub")
            return [[0.0] * 1536 for _ in texts]
        
        async def add_documents_to_database(*args, **kwargs):
            """Stub implementation when add_documents_to_database is not available."""
            import warnings
            warnings.warn("add_documents_to_database function not available, using stub")
            return None

__all__ = [
    # Validation
    "validate_neo4j_connection",
    "validate_script_path",
    "validate_github_url",
    # Text processing
    "smart_chunk_markdown",
    "extract_section_info",
    "process_code_example",
    # URL helpers
    "is_sitemap",
    "is_txt",
    "parse_sitemap",
    "normalize_url",
    # Reranking
    "rerank_results",
    # Embedding and database
    "create_embedding",
    "create_embeddings_batch",
    "add_documents_to_database",
]