"""Smart crawling service with intelligent URL type detection."""

import json
import logging

import aiohttp
from fastmcp import Context

from core import MCPToolError
from core.context import get_app_context

# Import will be done in the function to avoid circular imports
from utils import is_sitemap, is_txt, normalize_url, parse_sitemap

from .crawling import (
    crawl_markdown_file,
    crawl_recursive_internal_links,
    process_urls_for_mcp,
)

logger = logging.getLogger(__name__)


async def _perform_rag_query_with_context(
    ctx: Context,
    query: str,
    source: str | None = None,
    match_count: int = 5,
) -> str:
    """
    Helper function to properly extract database_client from context and call perform_rag_query.
    """
    import json

    # Get the app context that was stored during lifespan
    app_ctx = get_app_context()

    if (
        not app_ctx
        or not hasattr(app_ctx, "database_client")
        or not app_ctx.database_client
    ):
        return json.dumps(
            {
                "success": False,
                "error": "Database client not available",
            },
            indent=2,
        )

    from database.rag_queries import perform_rag_query

    return await perform_rag_query(
        app_ctx.database_client,
        query=query,
        source=source,
        match_count=match_count,
    )


async def smart_crawl_url(
    ctx: Context,
    url: str,
    max_depth: int = 3,
    max_concurrent: int = 10,
    chunk_size: int = 5000,
    return_raw_markdown: bool = False,
    query: list[str] | None = None,
) -> str:
    """
    Intelligently crawl a URL based on its type.

    Detects URL type and applies appropriate crawling strategy:
    - Sitemaps: Extract and crawl all URLs
    - Text files: Direct retrieval
    - Regular pages: Recursive crawling

    Args:
        ctx: FastMCP context
        url: URL to crawl
        max_depth: Max recursion depth for regular URLs
        max_concurrent: Max concurrent operations
        chunk_size: Chunk size for content
        return_raw_markdown: Return raw markdown
        query: Optional RAG queries to run

    Returns:
        JSON string with results
    """
    try:
        normalized_url = normalize_url(url)

        # Detect URL type and crawl accordingly
        if is_sitemap(normalized_url):
            logger.info(f"Detected sitemap: {normalized_url}")
            return await _crawl_sitemap(
                ctx,
                normalized_url,
                max_concurrent,
                chunk_size,
                return_raw_markdown,
                query,
            )
        if is_txt(normalized_url):
            logger.info(f"Detected text file: {normalized_url}")
            return await _crawl_text_file(
                ctx,
                normalized_url,
                chunk_size,
                return_raw_markdown,
            )
        logger.info(f"Regular URL, crawling recursively: {normalized_url}")
        return await _crawl_recursive(
            ctx,
            normalized_url,
            max_depth,
            max_concurrent,
            chunk_size,
            return_raw_markdown,
            query,
        )

    except Exception as e:
        logger.error(f"Error in smart_crawl_url: {e}")
        raise MCPToolError(f"Smart crawl failed: {e!s}")


async def _crawl_sitemap(
    ctx: Context,
    url: str,
    max_concurrent: int,
    chunk_size: int,
    return_raw_markdown: bool,
    query: list[str] | None,
) -> str:
    """Crawl a sitemap URL."""
    try:
        # Fetch and parse sitemap
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise MCPToolError(
                        f"Failed to fetch sitemap: HTTP {response.status}"
                    )
                content = await response.text()

        # Parse sitemap URLs
        urls = parse_sitemap(content)
        if not urls:
            return json.dumps(
                {
                    "success": False,
                    "type": "sitemap",
                    "message": "No URLs found in sitemap",
                    "url": url,
                }
            )

        logger.info(f"Found {len(urls)} URLs in sitemap")

        # Crawl all URLs
        result = await process_urls_for_mcp(
            ctx=ctx,
            urls=urls,
            max_concurrent=max_concurrent,
            batch_size=20,
            return_raw_markdown=return_raw_markdown,
        )

        # Parse result and add metadata
        data = json.loads(result)
        data["type"] = "sitemap"
        data["sitemap_url"] = url
        data["total_urls"] = len(urls)

        # Run RAG queries if requested
        if query and not return_raw_markdown and data.get("success"):
            data["query_results"] = {}
            for q in query:
                try:
                    rag_result = await _perform_rag_query_with_context(
                        ctx, q, source=None, match_count=5
                    )
                    data["query_results"][q] = json.loads(rag_result)
                except Exception as e:
                    logger.error(f"RAG query failed for '{q}': {e}")
                    data["query_results"][q] = {"error": str(e)}

        return json.dumps(data)

    except Exception as e:
        logger.error(f"Sitemap crawl error: {e}")
        return json.dumps(
            {
                "success": False,
                "type": "sitemap",
                "error": str(e),
                "url": url,
            }
        )


async def _crawl_text_file(
    ctx: Context,
    url: str,
    chunk_size: int,
    return_raw_markdown: bool,
) -> str:
    """Crawl a text file directly."""
    try:
        result = await crawl_markdown_file(
            ctx=ctx,
            url=url,
            chunk_size=chunk_size,
            return_raw_markdown=return_raw_markdown,
        )

        # Parse and add metadata
        data = json.loads(result)
        data["type"] = "text_file"

        return json.dumps(data)

    except Exception as e:
        logger.error(f"Text file crawl error: {e}")
        return json.dumps(
            {
                "success": False,
                "type": "text_file",
                "error": str(e),
                "url": url,
            }
        )


async def _crawl_recursive(
    ctx: Context,
    url: str,
    max_depth: int,
    max_concurrent: int,
    chunk_size: int,
    return_raw_markdown: bool,
    query: list[str] | None,
) -> str:
    """Crawl a regular URL recursively."""
    try:
        # Get the app context to access the crawler
        from core.context import get_app_context

        app_ctx = get_app_context()

        if not app_ctx or not hasattr(app_ctx, "crawler"):
            raise MCPToolError("Crawler not available in application context")

        # Call crawl_recursive_internal_links with correct parameters
        crawl_results = await crawl_recursive_internal_links(
            crawler=app_ctx.crawler,
            start_urls=[url],  # Note: expects a list
            max_depth=max_depth,
            max_concurrent=max_concurrent,
        )

        # Process results - it returns a list of dicts
        if return_raw_markdown:
            # Return raw markdown from all crawled pages
            markdown_content = "\n\n---\n\n".join(
                [
                    f"# {result.get('url', 'Unknown URL')}\n\n{result.get('markdown', '')}"
                    for result in crawl_results
                ]
            )
            return json.dumps(
                {
                    "success": True,
                    "type": "recursive",
                    "raw_markdown": markdown_content,
                    "urls_crawled": len(crawl_results),
                }
            )

        # Store results in database if not returning raw
        app_ctx = get_app_context()
        if not app_ctx or not app_ctx.database_client:
            raise MCPToolError("Database client not available in application context")
        db_client = app_ctx.database_client

        stored_count = 0
        for result in crawl_results:
            if result.get("success") and result.get("markdown"):
                try:
                    await db_client.store_crawled_page(
                        url=result["url"],
                        content=result["markdown"],
                        chunk_size=chunk_size,
                    )
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store {result['url']}: {e}")

        # Create response data
        data = {
            "success": True,
            "type": "recursive",
            "urls_crawled": len(crawl_results),
            "urls_stored": stored_count,
            "max_depth": max_depth,
        }

        # Run RAG queries if requested
        if query and not return_raw_markdown and data.get("success"):
            data["query_results"] = {}
            for q in query:
                try:
                    rag_result = await _perform_rag_query_with_context(
                        ctx, q, source=None, match_count=5
                    )
                    data["query_results"][q] = json.loads(rag_result)
                except Exception as e:
                    logger.error(f"RAG query failed for '{q}': {e}")
                    data["query_results"][q] = {"error": str(e)}

        return json.dumps(data)

    except Exception as e:
        logger.error(f"Recursive crawl error: {e}")
        return json.dumps(
            {
                "success": False,
                "type": "recursive",
                "error": str(e),
                "url": url,
            }
        )
