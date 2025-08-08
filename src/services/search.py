"""Search service implementation for SearXNG integration."""

import json
import logging

import aiohttp
from bs4 import BeautifulSoup
from fastmcp import Context

from config import get_settings
from core import MCPToolError

from .crawling import process_urls_for_mcp

logger = logging.getLogger(__name__)
settings = get_settings()


async def search_and_process(
    ctx: Context,
    query: str,
    return_raw_markdown: bool = False,
    num_results: int = 6,
    batch_size: int = 20,
    max_concurrent: int = 10,
) -> str:
    """
    Perform search using SearXNG and process results.

    Args:
        ctx: FastMCP context
        query: Search query
        return_raw_markdown: Return raw markdown instead of storing
        num_results: Number of results to return
        batch_size: Batch size for processing
        max_concurrent: Max concurrent operations

    Returns:
        JSON string with results
    """
    if not settings.searxng_url:
        raise MCPToolError(
            "SearXNG URL not configured. Please set SEARXNG_URL in your environment."
        )

    try:
        # Perform SearXNG search
        search_results = await _search_searxng(query, num_results)

        if not search_results:
            return json.dumps(
                {
                    "success": False,
                    "message": "No search results found",
                    "results": [],
                }
            )

        # Extract URLs from search results
        urls = [result["url"] for result in search_results]

        # Process URLs with process_urls_for_mcp
        crawl_result = await process_urls_for_mcp(
            ctx=ctx,
            urls=urls,
            max_concurrent=max_concurrent,
            batch_size=batch_size,
            return_raw_markdown=return_raw_markdown,
        )

        # Parse crawl result
        crawl_data = json.loads(crawl_result)

        # Combine search metadata with crawl results
        combined_results = []
        for i, search_result in enumerate(search_results):
            combined_result = {
                "title": search_result["title"],
                "url": search_result["url"],
                "snippet": search_result.get("snippet", ""),
            }

            # Find corresponding crawl result
            if crawl_data.get("success") and i < len(crawl_data.get("results", [])):
                crawl_info = crawl_data["results"][i]
                if return_raw_markdown:
                    combined_result["markdown"] = crawl_info.get("markdown", "")
                else:
                    combined_result["stored"] = crawl_info.get("success", False)
                    combined_result["chunks"] = crawl_info.get("chunks_stored", 0)

            combined_results.append(combined_result)

        return json.dumps(
            {
                "success": True,
                "query": query,
                "total_results": len(combined_results),
                "results": combined_results,
            }
        )

    except Exception as e:
        logger.error(f"Error in search_and_process: {e}")
        raise MCPToolError(f"Search processing failed: {e!s}")


async def _search_searxng(query: str, num_results: int) -> list[dict]:
    """
    Search using SearXNG instance.

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        List of search results
    """
    searxng_url = settings.searxng_url.rstrip("/")
    search_url = f"{searxng_url}/search"

    params = {
        "q": query,
        "format": "html",
        "categories": "general",
        "engines": settings.searxng_default_engines or "",
        "safesearch": "1",
        "limit": num_results,
    }

    headers = {
        "User-Agent": settings.searxng_user_agent,
        "Accept": "text/html",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                search_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=settings.searxng_timeout),
            ) as response:
                if response.status != 200:
                    logger.error(f"SearXNG returned status {response.status}")
                    return []

                html = await response.text()

        # Parse HTML results
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Find result articles
        for article in soup.find_all("article", class_="result", limit=num_results):
            result = {}

            # Extract title and URL
            title_elem = article.find("h3")
            if title_elem and title_elem.find("a"):
                link = title_elem.find("a")
                result["title"] = link.get_text(strip=True)
                result["url"] = link.get("href", "")

            # Extract snippet
            content_elem = article.find("p", class_="content")
            if content_elem:
                result["snippet"] = content_elem.get_text(strip=True)

            if result.get("url"):
                results.append(result)

        return results

    except Exception as e:
        logger.error(f"SearXNG search error: {e}")
        return []
