"""
Compatibility module for tests that import from the old crawl4ai_mcp module.

This module re-exports the tools from the new modular structure to maintain
backward compatibility with existing tests.
"""

import logging
from fastmcp import FastMCP, Context
from tools import register_tools
from core import crawl4ai_lifespan

logger = logging.getLogger(__name__)

# Create a FastMCP instance for tool registration
_mcp = FastMCP("Crawl4AI MCP Test Server", lifespan=crawl4ai_lifespan)

# Register all tools
register_tools(_mcp)

# Extract tool functions from registered tools and expose them
search = _mcp._tools["search"]
scrape_urls = _mcp._tools["scrape_urls"] 
smart_crawl_url = _mcp._tools["smart_crawl_url"]
get_available_sources = _mcp._tools["get_available_sources"]
perform_rag_query = _mcp._tools["perform_rag_query"]
search_code_examples = _mcp._tools["search_code_examples"]
check_ai_script_hallucinations = _mcp._tools["check_ai_script_hallucinations"]
query_knowledge_graph = _mcp._tools["query_knowledge_graph"]
parse_github_repository = _mcp._tools["parse_github_repository"]
parse_repository_branch = _mcp._tools["parse_repository_branch"]
get_repository_info = _mcp._tools["get_repository_info"]
update_parsed_repository = _mcp._tools["update_parsed_repository"]
extract_and_index_repository_code = _mcp._tools["extract_and_index_repository_code"]
smart_code_search = _mcp._tools["smart_code_search"]
check_ai_script_hallucinations_enhanced = _mcp._tools["check_ai_script_hallucinations_enhanced"]
get_script_analysis_info = _mcp._tools["get_script_analysis_info"]

# For backward compatibility, also expose any legacy classes/functions that tests might expect
try:
    # Import any classes that might be needed by tests
    from core.context import AppContext as Crawl4AIContext
except ImportError:
    # Define a minimal context class for tests if it doesn't exist
    class Crawl4AIContext:
        def __init__(self):
            self.database_client = None
            self.crawler = None
            self.repo_extractor = None

logger.info("Compatibility module crawl4ai_mcp loaded successfully")