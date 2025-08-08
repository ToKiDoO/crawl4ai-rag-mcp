"""
Main entry point for the refactored Crawl4AI MCP server.

This demonstrates how the monolithic crawl4ai_mcp.py file can be refactored
into a modular structure following best practices.
"""

import asyncio
import sys
import traceback

from fastmcp import FastMCP

from config import get_settings
from core import crawl4ai_lifespan, logger
from tools import register_tools

# Get settings instance
settings = get_settings()

# Initialize FastMCP server with lifespan management
try:
    logger.info("Initializing FastMCP server...")
    # Get host and port from settings
    host = settings.host
    port = settings.port
    # Ensure port has a valid default even if empty string
    if not port:
        port = "8051"
    logger.info(f"Host: {host}, Port: {port}")

    mcp = FastMCP("Crawl4AI MCP Server", lifespan=crawl4ai_lifespan)
    logger.info("FastMCP server initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize FastMCP server: {e}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)


# Register all MCP tools
register_tools(mcp)


def create_mcp_server():
    """
    Create and return an MCP server instance for testing purposes.
    """
    test_mcp = FastMCP("Crawl4AI MCP Server Test")
    return test_mcp


async def main():
    """
    Main async function to run the MCP server.
    """
    try:
        logger.info("Main function started")
        transport = settings.transport.lower()
        logger.info(f"Transport mode: {transport}")

        # Flush output before starting server
        sys.stdout.flush()
        sys.stderr.flush()

        # Run server with appropriate transport
        if transport == "http":
            # For HTTP transport, manually initialize the lifespan context
            # because HTTP mode doesn't automatically call lifespan managers
            logger.info("Initializing application context for HTTP transport...")
            async with crawl4ai_lifespan(mcp) as context:
                logger.info("✓ Application context initialized successfully")
                logger.info(f"  - Crawler: {type(context.crawler).__name__}")
                logger.info(f"  - Database: {type(context.database_client).__name__}")
                logger.info(
                    f"  - Reranking model: {'✓' if context.reranking_model else '✗'}"
                )
                logger.info(
                    f"  - Knowledge validator: {'✓' if context.knowledge_validator else '✗'}"
                )
                logger.info(
                    f"  - Repository extractor: {'✓' if context.repo_extractor else '✗'}"
                )

                # Run the HTTP server with the context active
                await mcp.run_async(transport="http", host=host, port=int(port))
        elif transport == "sse":
            await mcp.run_sse_async()
        else:  # Default to stdio for Claude Desktop compatibility
            await mcp.run_stdio_async()

    except Exception as e:
        logger.error(f"Error in main function: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    try:
        logger.info("Starting main function...")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error in main: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
