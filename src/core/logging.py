"""Logging configuration for the Crawl4AI MCP server."""

import logging
import os
import sys


def configure_logging() -> logging.Logger:
    """Configure and return the logger for the application."""
    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    logger = logging.getLogger("crawl4ai-mcp")

    # Enable debug mode from environment
    if os.getenv("MCP_DEBUG", "").lower() in ("true", "1", "yes"):
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    return logger


# Initialize logger
logger = configure_logging()
