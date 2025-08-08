"""Service modules for the Crawl4AI MCP server."""

from .crawling import (
    crawl_batch,
    crawl_markdown_file,
    crawl_recursive_internal_links,
    process_urls_for_mcp,
)
from .search import search_and_process
from .smart_crawl import smart_crawl_url

__all__ = [
    # Crawling services
    "crawl_markdown_file",
    "crawl_batch",
    "crawl_recursive_internal_links",
    "process_urls_for_mcp",
    # Search services
    "search_and_process",
    # Smart crawl services
    "smart_crawl_url",
]
