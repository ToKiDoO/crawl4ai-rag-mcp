"""Configuration settings for Crawl4AI MCP Server."""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Settings:
    """Central configuration management for the application."""

    def __init__(self):
        """Initialize settings by loading environment variables."""
        self._load_environment()
        self._validate_configuration()

    def _load_environment(self) -> None:
        """Load environment variables from .env file."""
        # Determine which .env file to load
        dotenv_path = Path(__file__).parent.parent.parent / ".env"

        if os.getenv("USE_TEST_ENV", "").lower() in ("true", "1", "yes"):
            test_env_path = dotenv_path.with_suffix(".test")
            if test_env_path.exists():
                dotenv_path = test_env_path
                logger.info(f"Using test environment: {dotenv_path}")

        # Load environment variables
        if dotenv_path.exists():
            if os.getenv("USE_TEST_ENV", "").lower() in ("true", "1", "yes"):
                # Test mode: .env.test values override environment
                load_dotenv(dotenv_path, override=True)
            else:
                # Normal mode: .env file values override environment
                load_dotenv(dotenv_path, override=True)

    def _validate_configuration(self) -> None:
        """Validate critical configuration values."""
        # Validate OpenAI API key
        if not self.openai_api_key:
            logger.error(
                "OPENAI_API_KEY is missing or empty. Please check your .env file."
            )

        # Log current database configuration
        logger.info(f"VECTOR_DATABASE: {self.vector_database}")
        logger.debug(f"QDRANT_URL: {self.qdrant_url}")

    # Debug settings
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled."""
        return os.getenv("MCP_DEBUG", "").lower() in ("true", "1", "yes")

    # API Keys
    @property
    def openai_api_key(self) -> str | None:
        """Get OpenAI API key."""
        return os.getenv("OPENAI_API_KEY")

    # Server settings
    @property
    def host(self) -> str:
        """Get server host."""
        return os.getenv("HOST", "0.0.0.0")

    @property
    def port(self) -> str:
        """Get server port."""
        return os.getenv("PORT", "8051")

    # Database settings
    @property
    def vector_database(self) -> str:
        """Get vector database type."""
        return os.getenv("VECTOR_DATABASE", "qdrant")

    @property
    def qdrant_url(self) -> str | None:
        """Get Qdrant URL."""
        return os.getenv("QDRANT_URL")

    @property
    def qdrant_api_key(self) -> str | None:
        """Get Qdrant API key."""
        return os.getenv("QDRANT_API_KEY")

    # Neo4j settings
    @property
    def neo4j_uri(self) -> str | None:
        """Get Neo4j URI."""
        return os.getenv("NEO4J_URI")

    @property
    def neo4j_username(self) -> str | None:
        """Get Neo4j username."""
        return os.getenv("NEO4J_USERNAME")

    @property
    def neo4j_password(self) -> str | None:
        """Get Neo4j password."""
        return os.getenv("NEO4J_PASSWORD")

    @property
    def use_knowledge_graph(self) -> bool:
        """Check if knowledge graph is enabled."""
        return os.getenv("USE_KNOWLEDGE_GRAPH", "false").lower() == "true"

    # SearXNG settings
    @property
    def searxng_url(self) -> str | None:
        """Get SearXNG URL."""
        return os.getenv("SEARXNG_URL")

    @property
    def searxng_user_agent(self) -> str:
        """Get SearXNG user agent."""
        return os.getenv("SEARXNG_USER_AGENT", "MCP-Crawl4AI-RAG-Server/1.0")

    @property
    def searxng_timeout(self) -> int:
        """Get SearXNG timeout."""
        return int(os.getenv("SEARXNG_TIMEOUT", "30"))

    @property
    def searxng_default_engines(self) -> str:
        """Get SearXNG default engines."""
        return os.getenv("SEARXNG_DEFAULT_ENGINES", "")

    # Feature flags
    @property
    def use_reranking(self) -> bool:
        """Check if reranking is enabled."""
        return os.getenv("USE_RERANKING", "false").lower() == "true"

    @property
    def use_test_env(self) -> bool:
        """Check if test environment is enabled."""
        return os.getenv("USE_TEST_ENV", "").lower() in ("true", "1", "yes")

    @property
    def use_agentic_rag(self) -> bool:
        """Check if agentic RAG is enabled."""
        return os.getenv("USE_AGENTIC_RAG", "false").lower() == "true"

    # Transport settings
    @property
    def transport(self) -> str:
        """Get transport mode."""
        return os.getenv("TRANSPORT", "http")

    # Knowledge graph validation
    def has_neo4j_config(self) -> bool:
        """Check if Neo4j environment variables are configured."""
        return all(
            [
                self.neo4j_uri,
                self.neo4j_username,
                self.neo4j_password,
            ]
        )

    def get_neo4j_config(self) -> dict[str, str]:
        """Get Neo4j configuration as a dictionary."""
        return {
            "uri": self.neo4j_uri or "",
            "auth": (self.neo4j_username or "", self.neo4j_password or ""),
        }

    def to_dict(self) -> dict[str, Any]:
        """Export settings as a dictionary."""
        return {
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "vector_database": self.vector_database,
            "use_knowledge_graph": self.use_knowledge_graph,
            "use_reranking": self.use_reranking,
            "use_test_env": self.use_test_env,
            "has_neo4j": self.has_neo4j_config(),
            "has_searxng": bool(self.searxng_url),
            "has_openai": bool(self.openai_api_key),
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
