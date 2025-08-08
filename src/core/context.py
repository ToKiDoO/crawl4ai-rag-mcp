"""Application context and lifecycle management for the Crawl4AI MCP server."""

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig
from fastmcp import FastMCP
from sentence_transformers import CrossEncoder

from config import get_settings
from database.base import VectorDatabase
from database.factory import create_and_initialize_database

from .logging import logger

# Get settings instance
settings = get_settings()

# Global context storage
_app_context: Optional["Crawl4AIContext"] = None


def set_app_context(context: "Crawl4AIContext") -> None:
    """Store the application context globally."""
    global _app_context
    _app_context = context


def get_app_context() -> Optional["Crawl4AIContext"]:
    """Get the stored application context."""
    return _app_context


# These imports are conditional based on Neo4j availability
try:
    # Add knowledge_graphs directory to path for imports
    import sys

    sys.path.append("/app/knowledge_graphs")
    from knowledge_graph_validator import KnowledgeGraphValidator
    from parse_repo_into_neo4j import DirectNeo4jExtractor

    KNOWLEDGE_GRAPH_AVAILABLE = True
except ImportError:
    KNOWLEDGE_GRAPH_AVAILABLE = False
    KnowledgeGraphValidator = None
    DirectNeo4jExtractor = None


@dataclass
class Crawl4AIContext:
    """Context for the Crawl4AI MCP server."""

    crawler: AsyncWebCrawler
    database_client: VectorDatabase
    reranking_model: CrossEncoder | None = None
    knowledge_validator: Any | None = None  # KnowledgeGraphValidator when available
    repo_extractor: Any | None = None  # DirectNeo4jExtractor when available


def format_neo4j_error(error: Exception) -> str:
    """Format Neo4j errors for user-friendly display."""
    error_str = str(error).lower()

    if "authentication" in error_str or "unauthorized" in error_str:
        return "Authentication failed. Please check your Neo4j username and password."
    if (
        "failed to establish connection" in error_str
        or "connection refused" in error_str
    ):
        return "Connection failed. Please ensure Neo4j is running and accessible at the specified URI."
    if "unable to retrieve routing information" in error_str:
        return "Connection failed. The Neo4j URI may be incorrect or the database may not be accessible."
    return f"Neo4j error: {error!s}"


@asynccontextmanager
async def crawl4ai_lifespan(server: FastMCP) -> AsyncIterator[Crawl4AIContext]:
    """
    Manages the Crawl4AI client lifecycle.

    Args:
        server: The FastMCP server instance

    Yields:
        Crawl4AIContext: The context containing the Crawl4AI crawler and database client
    """
    # Create browser configuration
    browser_config = BrowserConfig(headless=True, verbose=False)

    # Initialize the crawler
    crawler = AsyncWebCrawler(config=browser_config)
    await crawler.__aenter__()

    # Initialize database client (Supabase or Qdrant based on config)
    database_client = await create_and_initialize_database()

    # Initialize cross-encoder model for reranking if enabled
    reranking_model = None
    if settings.use_reranking:
        try:
            reranking_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            logger.error(f"Failed to load reranking model: {e}")
            reranking_model = None

    # Initialize Neo4j components if configured and enabled
    knowledge_validator = None
    repo_extractor = None

    # Check if knowledge graph functionality is enabled
    knowledge_graph_enabled = settings.use_knowledge_graph

    if knowledge_graph_enabled and KNOWLEDGE_GRAPH_AVAILABLE:
        neo4j_uri = settings.neo4j_uri
        neo4j_user = settings.neo4j_username
        neo4j_password = settings.neo4j_password

        if neo4j_uri and neo4j_user and neo4j_password:
            try:
                logger.info("Initializing knowledge graph components...")

                # Initialize knowledge graph validator
                knowledge_validator = KnowledgeGraphValidator(
                    neo4j_uri,
                    neo4j_user,
                    neo4j_password,
                )
                await knowledge_validator.initialize()
                logger.info("✓ Knowledge graph validator initialized")

                # Initialize repository extractor
                repo_extractor = DirectNeo4jExtractor(
                    neo4j_uri,
                    neo4j_user,
                    neo4j_password,
                )
                await repo_extractor.initialize()
                logger.info("✓ Repository extractor initialized")

            except Exception as e:
                logger.error(
                    f"Failed to initialize Neo4j components: {format_neo4j_error(e)}",
                )
                knowledge_validator = None
                repo_extractor = None
        else:
            logger.warning(
                "Neo4j credentials not configured - knowledge graph tools will be unavailable",
            )
    elif not knowledge_graph_enabled:
        logger.info(
            "Knowledge graph functionality disabled - set USE_KNOWLEDGE_GRAPH=true to enable",
        )
    else:
        logger.warning(
            "Knowledge graph dependencies not available - install neo4j dependencies",
        )

    try:
        context = Crawl4AIContext(
            crawler=crawler,
            database_client=database_client,
            reranking_model=reranking_model,
            knowledge_validator=knowledge_validator,
            repo_extractor=repo_extractor,
        )

        # Store the context globally for tool access
        set_app_context(context)

        yield context
    finally:
        # Clean up all components
        await crawler.__aexit__(None, None, None)
        if knowledge_validator:
            try:
                await knowledge_validator.close()
                logger.info("✓ Knowledge graph validator closed")
            except Exception as e:
                logger.error(f"Error closing knowledge validator: {e}")
        if repo_extractor:
            try:
                await repo_extractor.close()
                logger.info("✓ Repository extractor closed")
            except Exception as e:
                logger.error(f"Error closing repository extractor: {e}")
