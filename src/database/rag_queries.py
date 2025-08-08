"""
RAG (Retrieval Augmented Generation) query functionality.

Handles vector search, hybrid search, and code example retrieval.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


async def get_available_sources(database_client: Any) -> str:
    """
    Get all available sources from the sources table.

    This returns a list of all unique sources (domains) that have been crawled and stored
    in the database, along with their summaries and statistics.

    Args:
        database_client: The database client instance

    Returns:
        JSON string with the list of available sources and their details
    """
    try:
        # Query the sources table
        source_data = await database_client.get_sources()

        # Format the sources with their details
        sources = []
        if source_data:
            for source in source_data:
                sources.append(
                    {
                        "source_id": source.get("source_id"),
                        "summary": source.get("summary"),
                        "total_chunks": source.get("total_chunks"),
                        "first_crawled": source.get("first_crawled"),
                        "last_crawled": source.get("last_crawled"),
                    },
                )

        return json.dumps(
            {
                "success": True,
                "sources": sources,
                "count": len(sources),
                "message": f"Found {len(sources)} unique sources.",
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in get_available_sources: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


async def perform_rag_query(
    database_client: Any,
    query: str,
    source: str | None = None,
    match_count: int = 5,
) -> str:
    """
    Perform a RAG (Retrieval Augmented Generation) query on the stored content.

    This searches the vector database for content relevant to the query and returns
    the matching documents. Optionally filter by source domain.

    Args:
        database_client: The database client instance
        query: The search query
        source: Optional source domain to filter results (e.g., 'example.com')
        match_count: Maximum number of results to return (default: 5)

    Returns:
        JSON string with the search results
    """
    try:
        # Check if hybrid search is enabled
        use_hybrid_search = os.getenv("USE_HYBRID_SEARCH", "false") == "true"

        # Prepare filter if source is provided and not empty
        filter_metadata = None
        if source and source.strip():
            filter_metadata = {"source": source}

        if use_hybrid_search:
            # Use hybrid search (vector + keyword)
            logger.info("Performing hybrid search")
            results = await database_client.hybrid_search(
                query,
                match_count=match_count,
                filter_metadata=filter_metadata,
            )
        else:
            # Use standard vector search
            logger.info("Performing standard vector search")
            results = await database_client.search(
                query,
                match_count=match_count,
                filter_metadata=filter_metadata,
            )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "content": result.get("content"),
                    "source": result.get("source"),
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "chunk_index": result.get("chunk_index"),
                    "similarity_score": result.get("score", 0),
                },
            )

        return json.dumps(
            {
                "success": True,
                "query": query,
                "source_filter": source,
                "match_count": len(formatted_results),
                "results": formatted_results,
                "search_type": "hybrid" if use_hybrid_search else "vector",
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in perform_rag_query: {e}")
        return json.dumps({"success": False, "query": query, "error": str(e)}, indent=2)


async def search_code_examples(
    database_client: Any,
    query: str,
    source_id: str | None = None,
    match_count: int = 5,
) -> str:
    """
    Search for code examples relevant to the query.

    This searches the vector database for code examples relevant to the query and returns
    the matching examples with their summaries. Optionally filter by source_id.

    Args:
        database_client: The database client instance
        query: The search query
        source_id: Optional source ID to filter results (e.g., 'example.com')
        match_count: Maximum number of results to return (default: 5)

    Returns:
        JSON string with the search results
    """
    # Check if code example extraction is enabled
    extract_code_examples_enabled = os.getenv("USE_AGENTIC_RAG", "false") == "true"

    if not extract_code_examples_enabled:
        return json.dumps(
            {
                "success": False,
                "error": "Code example extraction is disabled. Perform a normal RAG search.",
            },
            indent=2,
        )

    try:
        # Prepare filter if source_id is provided and not empty
        filter_metadata = None
        if source_id and source_id.strip():
            filter_metadata = {"source_id": source_id}

        # Search for code examples
        results = await database_client.search_code_examples(
            query,
            match_count=match_count,
            filter_metadata=filter_metadata,
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "code": result.get("code"),
                    "summary": result.get("summary"),
                    "source_id": result.get("source_id"),
                    "url": result.get("url"),
                    "programming_language": result.get("programming_language"),
                    "similarity_score": result.get("score", 0),
                },
            )

        return json.dumps(
            {
                "success": True,
                "query": query,
                "source_filter": source_id,
                "match_count": len(formatted_results),
                "results": formatted_results,
                "search_type": "code_examples",
            },
            indent=2,
        )
    except Exception as e:
        logger.error(f"Error in search_code_examples: {e}")
        return json.dumps({"success": False, "query": query, "error": str(e)}, indent=2)
