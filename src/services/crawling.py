"""Crawling services for the Crawl4AI MCP server."""

import json
import logging
from typing import Any

from crawl4ai import (
    AsyncWebCrawler,
    CacheMode,
    CrawlerRunConfig,
    MemoryAdaptiveDispatcher,
)
from fastmcp import Context

from core.logging import logger
from core.stdout_utils import SuppressStdout

# Import add_documents_to_database from utils package
from utils import add_documents_to_database
from utils.text_processing import smart_chunk_markdown
from utils.url_helpers import normalize_url


async def crawl_markdown_file(
    crawler: AsyncWebCrawler,
    url: str,
) -> list[dict[str, Any]]:
    """
    Crawl a .txt or markdown file.

    Args:
        crawler: AsyncWebCrawler instance
        url: URL of the file

    Returns:
        List of dictionaries with URL and markdown content
    """
    crawl_config = CrawlerRunConfig()

    with SuppressStdout():
        result = await crawler.arun(url=url, config=crawl_config)
    if result.success and result.markdown:
        return [{"url": url, "markdown": result.markdown}]
    logger.error(f"Failed to crawl {url}: {result.error_message}")
    return []


async def crawl_batch(
    crawler: AsyncWebCrawler,
    urls: list[str],
    max_concurrent: int = 10,
) -> list[dict[str, Any]]:
    """
    Batch crawl multiple URLs in parallel.

    Args:
        crawler: AsyncWebCrawler instance
        urls: List of URLs to crawl
        max_concurrent: Maximum number of concurrent browser sessions

    Returns:
        List of dictionaries with URL and markdown content

    Raises:
        ValueError: If URLs are invalid for crawl4ai
    """
    # Import validation functions
    from utils.validation import validate_urls_for_crawling

    # Enhanced debug logging - only log details in debug mode to avoid exposing sensitive data
    logger.info(f"crawl_batch received {len(urls)} URLs for processing")

    # Only log sensitive URL details in debug mode
    if logger.isEnabledFor(logging.DEBUG):
        # Don't log full URLs directly as they may contain auth tokens
        logger.debug(f"URL types: {[type(url).__name__ for url in urls]}")

    # Log details about each URL before validation
    for i, url in enumerate(urls):
        logger.debug(
            f"URL {i + 1}/{len(urls)}: {url!r} (type: {type(url).__name__}, length: {len(str(url))})"
        )
        if isinstance(url, str):
            logger.debug(f"  - Stripped: {url.strip()!r}")
            logger.debug(f"  - Contains whitespace: {url != url.strip()}")
            logger.debug(
                f"  - Starts with http: {url.strip().startswith(('http://', 'https://'))}"
            )

    # Validate URLs before passing to crawl4ai
    logger.debug("Starting URL validation...")
    validation_result = validate_urls_for_crawling(urls)
    logger.debug(f"URL validation completed. Result: {validation_result}")

    if not validation_result["valid"]:
        error_msg = f"URL validation failed: {validation_result['error']}"
        logger.error(error_msg)

        # Provide comprehensive debugging context
        if validation_result.get("invalid_urls"):
            logger.error(
                f"Invalid URLs that were rejected: {validation_result['invalid_urls']}"
            )
            # Log details about each invalid URL
            for invalid_url in validation_result["invalid_urls"]:
                logger.error(f"  - Invalid URL: {invalid_url!r}")

        if validation_result.get("valid_urls"):
            logger.info(
                f"Valid URLs that passed validation: {validation_result['valid_urls']}"
            )

        # Log the validation result structure for debugging
        logger.debug(f"Full validation result: {validation_result}")

        raise ValueError(f"Invalid URLs for crawling: {validation_result['error']}")

    # Use validated and normalized URLs
    validated_urls = validation_result["urls"]
    logger.info(
        f"URL validation successful! {len(validated_urls)} URLs ready for crawling"
    )

    # Log info about any URLs that were auto-fixed during validation
    if len(validated_urls) != len(urls):
        logger.info(
            f"URL count changed during validation: {len(urls)} -> {len(validated_urls)}"
        )
        logger.info(f"Original URLs: {urls}")
        logger.info(f"Validated URLs: {validated_urls}")

        # Log individual transformations
        for i, (orig, valid) in enumerate(zip(urls, validated_urls, strict=False)):
            if orig != valid:
                logger.info(f"URL {i + 1} transformed: {orig!r} -> {valid!r}")
    else:
        logger.debug("No URL transformations were needed during validation")

    logger.info(
        f"Starting crawl of {len(validated_urls)} validated URLs with max_concurrent={max_concurrent}"
    )
    logger.debug(f"Final URLs for crawling: {validated_urls}")

    # Initialize crawler configuration
    crawl_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent,
    )

    try:
        logger.debug("Starting crawler.arun_many...")
        with SuppressStdout():
            results = await crawler.arun_many(
                urls=validated_urls,
                config=crawl_config,
                dispatcher=dispatcher,
            )

        # Log crawling results summary
        successful_results = [
            {"url": r.url, "markdown": r.markdown, "links": r.links}
            for r in results
            if r.success and r.markdown
        ]

        failed_results = [r for r in results if not r.success or not r.markdown]

        logger.info(
            f"Crawling complete: {len(successful_results)} successful, {len(failed_results)} failed"
        )

        if successful_results:
            logger.debug(f"Successful URLs: {[r['url'] for r in successful_results]}")

        if failed_results:
            logger.warning("Failed URLs and reasons:")
            for failed_result in failed_results:
                logger.warning(
                    f"  - {failed_result.url}: success={failed_result.success}, "
                    f"has_markdown={bool(failed_result.markdown)}"
                )

        return successful_results

    except Exception as e:
        logger.error(f"Crawl4AI error with URLs {validated_urls}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {e!s}")

        # Log additional context for debugging
        logger.error(
            f"Crawler config: cache_mode={crawl_config.cache_mode}, stream={crawl_config.stream}"
        )
        logger.error(
            f"Dispatcher config: memory_threshold={dispatcher.memory_threshold_percent}%, "
            f"max_sessions={dispatcher.max_session_permit}"
        )

        # Re-raise with more context
        raise ValueError(f"Crawling failed for URLs {validated_urls}: {e}") from e


async def crawl_recursive_internal_links(
    crawler: AsyncWebCrawler,
    start_urls: list[str],
    max_depth: int = 3,
    max_concurrent: int = 10,
) -> list[dict[str, Any]]:
    """
    Recursively crawl internal links from start URLs up to a maximum depth.

    Args:
        crawler: AsyncWebCrawler instance
        start_urls: List of starting URLs
        max_depth: Maximum recursion depth
        max_concurrent: Maximum number of concurrent browser sessions

    Returns:
        List of dictionaries with URL and markdown content
    """
    run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=False)
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent,
    )

    visited = set()
    current_urls = set([normalize_url(u) for u in start_urls])
    results_all = []

    for depth in range(max_depth):
        urls_to_crawl = [
            normalize_url(url)
            for url in current_urls
            if normalize_url(url) not in visited
        ]
        if not urls_to_crawl:
            break

        with SuppressStdout():
            results = await crawler.arun_many(
                urls=urls_to_crawl,
                config=run_config,
                dispatcher=dispatcher,
            )
        next_level_urls = set()

        for result in results:
            norm_url = normalize_url(result.url)
            visited.add(norm_url)

            if result.success and result.markdown:
                results_all.append({"url": result.url, "markdown": result.markdown})
                for link in result.links.get("internal", []):
                    next_url = normalize_url(link["href"])
                    if next_url not in visited:
                        next_level_urls.add(next_url)

        current_urls = next_level_urls

    return results_all


async def process_urls_for_mcp(
    ctx: Context,
    urls: list[str],
    max_concurrent: int = 10,
    batch_size: int = 20,
    return_raw_markdown: bool = False,
) -> str:
    """
    Process URLs for MCP tools with context extraction and database storage.

    This is a bridge function that:
    1. Extracts the crawler from the MCP context
    2. Calls the low-level crawl_batch function
    3. Handles database storage and response formatting
    4. Supports return_raw_markdown option for direct content return

    Args:
        ctx: FastMCP context containing Crawl4AIContext
        urls: List of URLs to crawl
        max_concurrent: Maximum number of concurrent browser sessions
        batch_size: Batch size for database operations
        return_raw_markdown: If True, return raw markdown instead of storing

    Returns:
        JSON string with results
    """
    try:
        # Extract the Crawl4AI context from the FastMCP context
        if not hasattr(ctx, "crawl4ai_context") or not ctx.crawl4ai_context:
            # Get from global app context if available
            from core.context import get_app_context

            app_ctx = get_app_context()
            if not app_ctx:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Application context not available",
                    }
                )
            crawl4ai_ctx = app_ctx
        else:
            crawl4ai_ctx = ctx.crawl4ai_context

        # Validate that context has required attributes instead of strict type checking
        if not (
            hasattr(crawl4ai_ctx, "crawler")
            and hasattr(crawl4ai_ctx, "database_client")
        ):
            return json.dumps(
                {
                    "success": False,
                    "error": "Invalid Crawl4AI context: missing required attributes (crawler, database_client)",
                }
            )

        if not crawl4ai_ctx.crawler or not crawl4ai_ctx.database_client:
            return json.dumps(
                {
                    "success": False,
                    "error": "Invalid Crawl4AI context: crawler or database_client is None",
                }
            )

        # Call the low-level crawl_batch function
        crawl_results = await crawl_batch(
            crawler=crawl4ai_ctx.crawler,
            urls=urls,
            max_concurrent=max_concurrent,
        )

        if return_raw_markdown:
            # Return raw markdown content directly
            return json.dumps(
                {
                    "success": True,
                    "total_urls": len(urls),
                    "results": [
                        {
                            "url": result["url"],
                            "markdown": result["markdown"],
                            "success": True,
                        }
                        for result in crawl_results
                    ],
                }
            )

        # Store results in database
        stored_results = []
        for result in crawl_results:
            try:
                # Chunk the markdown content
                chunks = smart_chunk_markdown(result["markdown"], chunk_size=2000)

                if not chunks:
                    stored_results.append(
                        {
                            "url": result["url"],
                            "success": False,
                            "error": "No content to store",
                            "chunks_stored": 0,
                        }
                    )
                    continue

                # Prepare data for database storage
                urls = [result["url"]] * len(chunks)
                chunk_numbers = list(range(len(chunks)))
                contents = chunks
                metadatas = [
                    {"url": result["url"], "chunk": i} for i in range(len(chunks))
                ]
                url_to_full_document = {result["url"]: result["markdown"]}

                # Store in database
                await add_documents_to_database(
                    database=crawl4ai_ctx.database_client,
                    urls=urls,
                    chunk_numbers=chunk_numbers,
                    contents=contents,
                    metadatas=metadatas,
                    url_to_full_document=url_to_full_document,
                    batch_size=batch_size,
                )

                stored_results.append(
                    {
                        "url": result["url"],
                        "success": True,
                        "chunks_stored": len(chunks),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to store {result['url']}: {e}")
                stored_results.append(
                    {
                        "url": result["url"],
                        "success": False,
                        "error": str(e),
                        "chunks_stored": 0,
                    }
                )

        return json.dumps(
            {
                "success": True,
                "total_urls": len(urls),
                "results": stored_results,
            }
        )

    except Exception as e:
        logger.error(f"Error in process_urls_for_mcp: {e}")
        return json.dumps(
            {
                "success": False,
                "error": str(e),
            }
        )
