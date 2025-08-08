"""
MCP Tool Definitions for Crawl4AI.

This module contains all the MCP tool implementations that were previously
in the monolithic crawl4ai_mcp.py file. Due to FastMCP's architecture,
tools must be registered in the same scope as the FastMCP instance.

The tools are implemented here and registered in main.py.
"""

import json
import logging

from fastmcp import Context

from core import MCPToolError, track_request
from database import (
    get_available_sources,
    perform_rag_query,
)
from database import (
    search_code_examples as search_code_examples_db,
)
from knowledge_graph import (
    query_knowledge_graph,
)
from knowledge_graph.repository import (
    parse_github_repository as parse_github_repository_impl,
)
from services import (
    process_urls_for_mcp,
    search_and_process,
)
from services import (
    smart_crawl_url as smart_crawl_url_service_impl,
)
from utils.validation import validate_github_url, validate_script_path

logger = logging.getLogger(__name__)

# Import global context functions from core.context
from core.context import get_app_context


async def parse_github_repository_wrapper(ctx: Context, repo_url: str) -> str:
    """
    Wrapper function to properly extract repo_extractor from context and call the implementation.
    """
    import json

    # Get the app context that was stored during lifespan
    app_ctx = get_app_context()

    if (
        not app_ctx
        or not hasattr(app_ctx, "repo_extractor")
        or not app_ctx.repo_extractor
    ):
        # Return a proper error message
        return json.dumps(
            {
                "success": False,
                "error": "Repository extractor not available. Neo4j may not be configured or the USE_KNOWLEDGE_GRAPH environment variable may be set to false.",
            },
            indent=2,
        )

    return await parse_github_repository_impl(app_ctx.repo_extractor, repo_url)


async def get_available_sources_wrapper(ctx: Context) -> str:
    """
    Wrapper function to properly extract database_client from context and call the implementation.
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

    return await get_available_sources(app_ctx.database_client)


async def perform_rag_query_wrapper(
    ctx: Context,
    query: str,
    source: str | None = None,
    match_count: int = 5,
) -> str:
    """
    Wrapper function to properly extract database_client from context and call the implementation.
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

    return await perform_rag_query(
        app_ctx.database_client,
        query=query,
        source=source,
        match_count=match_count,
    )


async def search_code_examples_wrapper(
    ctx: Context,
    query: str,
    source_id: str | None = None,
    match_count: int = 5,
) -> str:
    """
    Wrapper function to properly extract database_client from context and call the implementation.
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

    return await search_code_examples_db(
        app_ctx.database_client,
        query=query,
        source_id=source_id,
        match_count=match_count,
    )


async def query_knowledge_graph_wrapper(ctx: Context, command: str) -> str:
    """
    Wrapper function to call the knowledge graph query implementation.
    """
    # The query_knowledge_graph function doesn't need a context parameter
    # It creates its own Neo4j connection from environment variables
    return await query_knowledge_graph(command)


def register_tools(mcp):
    """
    Register all MCP tools with the FastMCP instance.

    Args:
        mcp: FastMCP instance to register tools with
    """

    @mcp.tool()
    @track_request("search")
    async def search(
        ctx: Context,
        query: str,
        return_raw_markdown: bool = False,
        num_results: int = 6,
        batch_size: int = 20,
        max_concurrent: int = 10,
    ) -> str:
        """
        Comprehensive search tool that integrates SearXNG search with scraping and RAG functionality.
        Optionally, use `return_raw_markdown=true` to return raw markdown for more detailed analysis.

        This tool performs a complete search, scrape, and RAG workflow:
        1. Searches SearXNG with the provided query, obtaining `num_results` URLs
        2. Extracts markdown from URLs, chunks embedding data into Supabase
        3. Scrapes all returned URLs using existing scraping functionality
        4. Returns organized results with comprehensive metadata

        Args:
            query: The search query for SearXNG
            return_raw_markdown: If True, skip embedding/RAG and return raw markdown content (default: False)
            num_results: Number of search results to return from SearXNG (default: 6)
            batch_size: Batch size for database operations (default: 20)
            max_concurrent: Maximum concurrent browser sessions for scraping (default: 10)

        Returns:
            JSON string with search results, or raw markdown of each URL if `return_raw_markdown=true`
        """
        try:
            return await search_and_process(
                ctx=ctx,
                query=query,
                return_raw_markdown=return_raw_markdown,
                num_results=num_results,
                batch_size=batch_size,
                max_concurrent=max_concurrent,
            )
        except Exception as e:
            logger.error(f"Error in search tool: {e}")
            raise MCPToolError(f"Search failed: {e!s}")

    @mcp.tool()
    @track_request("scrape_urls")
    async def scrape_urls(
        ctx: Context,
        url: str | list[str],
        max_concurrent: int = 10,
        batch_size: int = 20,
        return_raw_markdown: bool = False,
    ) -> str:
        """
        Scrape **one or more URLs** and store their contents as embedding chunks in Supabase.
        Optionally, use `return_raw_markdown=true` to return raw markdown content without storing.

        The content is scraped and stored in Supabase for later retrieval and querying via perform_rag_query tool, unless
        `return_raw_markdown=True` is specified, in which case raw markdown is returned directly.

        Args:
            url: URL to scrape, or list of URLs for batch processing
            max_concurrent: Maximum number of concurrent browser sessions for multi-URL mode (default: 10)
            batch_size: Size of batches for database operations (default: 20)
            return_raw_markdown: If True, skip database storage and return raw markdown content (default: False)

        Returns:
            Summary of the scraping operation and storage in Supabase, or raw markdown content if requested
        """
        try:
            # Security: Add input size limit to prevent JSON bomb attacks
            MAX_INPUT_SIZE = 50000  # 50KB limit for safety

            # Handle URL parameter which can be:
            # 1. Single URL string
            # 2. JSON string representation of a list (from MCP protocol)
            # 3. Actual Python list

            # Enhanced debug logging
            logger.debug(
                f"scrape_urls received url parameter (type: {type(url).__name__})"
            )

            urls = []
            if isinstance(url, str):
                # Security check: Limit input size
                if len(url) > MAX_INPUT_SIZE:
                    raise ValueError(
                        f"Input too large: {len(url)} bytes (max: {MAX_INPUT_SIZE})"
                    )
                # Clean whitespace and normalize the string
                cleaned_url = url.strip()
                logger.debug(f"Processing string URL, cleaned: {cleaned_url!r}")

                # Check if it's a JSON string representation of a list
                # Be more precise: must start with [ and end with ] and likely contain quotes
                if (
                    cleaned_url.startswith("[")
                    and cleaned_url.endswith("]")
                    and ('"' in cleaned_url or "'" in cleaned_url)
                ):
                    logger.debug("Detected JSON array format, attempting to parse...")
                    try:
                        # Handle common JSON escaping issues
                        # First, try to parse as-is
                        parsed = json.loads(cleaned_url)
                        if isinstance(parsed, list):
                            urls = parsed
                            logger.debug(
                                f"Successfully parsed JSON array with {len(urls)} URLs"
                            )
                        else:
                            urls = [
                                cleaned_url
                            ]  # Single URL that looks like JSON but isn't a list
                            logger.debug(
                                "JSON parsed but result is not a list, treating as single URL"
                            )
                    except json.JSONDecodeError as json_err:
                        logger.debug(
                            f"JSON parsing failed ({json_err}), treating as single URL"
                        )
                        # Don't attempt fallback parsing with comma split as it can break valid URLs
                        # URLs can contain commas in query parameters
                        urls = [cleaned_url]  # Treat as single URL
                else:
                    urls = [cleaned_url]  # Single URL
                    logger.debug("Single URL string detected")
            elif isinstance(url, list):
                urls = url  # Assume it's already a list
                logger.debug(f"List parameter received with {len(urls)} URLs")
            else:
                # Handle other types by converting to string
                logger.warning(
                    f"Unexpected URL parameter type {type(url)}, converting to string"
                )
                urls = [str(url)]

            # Clean and validate each URL in the final list
            from utils.url_helpers import clean_url

            cleaned_urls = []
            invalid_urls = []

            for i, raw_url in enumerate(urls):
                try:
                    # Convert to string if not already
                    url_str = str(raw_url).strip()
                    logger.debug(f"Processing URL {i + 1}/{len(urls)}: {url_str!r}")

                    if not url_str:
                        logger.warning(f"Empty URL at position {i + 1}, skipping")
                        continue

                    # Clean the URL using utility function
                    cleaned_url = clean_url(url_str)
                    if cleaned_url:
                        cleaned_urls.append(cleaned_url)
                        logger.debug(f"URL {i + 1} cleaned successfully: {cleaned_url}")
                    else:
                        invalid_urls.append(url_str)
                        logger.warning(f"URL {i + 1} failed cleaning: {url_str}")

                except Exception as url_err:
                    logger.error(
                        f"Error processing URL {i + 1} ({raw_url!r}): {url_err}"
                    )
                    invalid_urls.append(str(raw_url))

            # Log final results
            logger.info(
                f"URL processing complete: {len(cleaned_urls)} valid URLs, {len(invalid_urls)} invalid URLs"
            )
            if invalid_urls:
                logger.warning(f"Invalid URLs that were skipped: {invalid_urls}")

            if not cleaned_urls:
                error_msg = "No valid URLs found after processing and cleaning"
                logger.error(error_msg)
                raise MCPToolError(error_msg)

            # Use cleaned URLs for processing
            return await process_urls_for_mcp(
                ctx=ctx,
                urls=cleaned_urls,
                max_concurrent=max_concurrent,
                batch_size=batch_size,
                return_raw_markdown=return_raw_markdown,
            )
        except Exception as e:
            logger.error(f"Error in scrape_urls tool: {e}")
            raise MCPToolError(f"Scraping failed: {e!s}")

    @mcp.tool()
    @track_request("smart_crawl_url")
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
        Intelligently crawl a URL based on its type and store content in Supabase.
        Enhanced with raw markdown return and RAG query capabilities.

        This tool automatically detects the URL type and applies the appropriate crawling method:
        - For sitemaps: Extracts and crawls all URLs in parallel
        - For text files (llms.txt): Directly retrieves the content
        - For regular webpages: Recursively crawls internal links up to the specified depth

        All crawled content is chunked and stored in Supabase for later retrieval and querying.

        Args:
            url: URL to crawl (can be a regular webpage, sitemap.xml, or .txt file)
            max_depth: Maximum recursion depth for regular URLs (default: 3)
            max_concurrent: Maximum number of concurrent browser sessions (default: 10)
            chunk_size: Maximum size of each content chunk in characters (default: 5000)
            return_raw_markdown: If True, return raw markdown content instead of just storing (default: False)
            query: List of queries to perform RAG search on crawled content (default: None)

        Returns:
            JSON string with crawl summary, raw markdown (if requested), or RAG query results
        """
        try:
            # Handle query parameter which can be:
            # 1. None
            # 2. JSON string representation of a list (from MCP protocol)
            # 3. Actual Python list
            parsed_query = None
            if query is not None:
                if isinstance(query, str):
                    # Check if it's a JSON string representation of a list
                    if query.strip().startswith("[") and query.strip().endswith("]"):
                        try:
                            parsed = json.loads(query)
                            if isinstance(parsed, list):
                                parsed_query = parsed
                            else:
                                parsed_query = [query]  # Single query
                        except json.JSONDecodeError:
                            parsed_query = [query]  # Single query, JSON parsing failed
                    else:
                        parsed_query = [query]  # Single query
                else:
                    parsed_query = query  # Assume it's already a list

            # Call the implementation function with the correct aliased name
            return await smart_crawl_url_service_impl(
                ctx=ctx,
                url=url,
                max_depth=max_depth,
                max_concurrent=max_concurrent,
                chunk_size=chunk_size,
                return_raw_markdown=return_raw_markdown,
                query=parsed_query,
            )
        except Exception as e:
            logger.error(f"Error in smart_crawl_url tool: {e}")
            raise MCPToolError(f"Smart crawl failed: {e!s}")

    @mcp.tool()
    @track_request("get_available_sources")
    async def get_available_sources(ctx: Context) -> str:
        """
        Get all available sources from the sources table.

        This tool returns a list of all unique sources (domains) that have been crawled and stored
        in the database, along with their summaries and statistics. This is useful for discovering
        what content is available for querying.

        Always use this tool before calling the RAG query or code example query tool
        with a specific source filter!

        Args:
            NONE

        Returns:
            JSON string with the list of available sources and their details
        """
        try:
            return await get_available_sources_wrapper(ctx)
        except Exception as e:
            logger.error(f"Error in get_available_sources tool: {e}")
            raise MCPToolError(f"Failed to get sources: {e!s}")

    @mcp.tool()
    @track_request("perform_rag_query")
    async def perform_rag_query(
        ctx: Context,
        query: str,
        source: str | None = None,
        match_count: int = 5,
    ) -> str:
        """
        Perform a RAG (Retrieval Augmented Generation) query on the stored content.

        This tool searches the vector database for content relevant to the query and returns
        the matching documents. Optionally filter by source domain.
        Get the source by using the get_available_sources tool before calling this search!

        Args:
            query: The search query
            source: Optional source domain to filter results (e.g., 'example.com')
            match_count: Maximum number of results to return (default: 5)

        Returns:
            JSON string with the search results
        """
        try:
            return await perform_rag_query_wrapper(
                ctx=ctx,
                query=query,
                source=source,
                match_count=match_count,
            )
        except Exception as e:
            logger.error(f"Error in perform_rag_query tool: {e}")
            raise MCPToolError(f"RAG query failed: {e!s}")

    @mcp.tool()
    @track_request("search_code_examples")
    async def search_code_examples(
        ctx: Context,
        query: str,
        source_id: str | None = None,
        match_count: int = 5,
    ) -> str:
        """
        Search for code examples relevant to the query.

        This tool searches the vector database for code examples relevant to the query and returns
        the matching examples with their summaries. Optionally filter by source_id.
        Get the source_id by using the get_available_sources tool before calling this search!

        Use the get_available_sources tool first to see what sources are available for filtering.

        Args:
            query: The search query
            source_id: Optional source ID to filter results (e.g., 'example.com')
            match_count: Maximum number of results to return (default: 5)

        Returns:
            JSON string with the search results
        """
        try:
            return await search_code_examples_wrapper(
                ctx=ctx,
                query=query,
                source_id=source_id,
                match_count=match_count,
            )
        except Exception as e:
            logger.error(f"Error in search_code_examples tool: {e}")
            raise MCPToolError(f"Code example search failed: {e!s}")

    @mcp.tool()
    @track_request("check_ai_script_hallucinations")
    async def check_ai_script_hallucinations(
        ctx: Context,
        script_path: str,
    ) -> str:
        """
        Check an AI-generated Python script for hallucinations using the knowledge graph.

        This tool analyzes a Python script for potential AI hallucinations by validating
        imports, method calls, class instantiations, and function calls against a Neo4j
        knowledge graph containing real repository data.

        The tool performs comprehensive analysis including:
        - Import validation against known repositories
        - Method call validation on classes from the knowledge graph
        - Class instantiation parameter validation
        - Function call parameter validation
        - Attribute access validation

        Args:
            script_path: Absolute path to the Python script to analyze

        Returns:
            JSON string with hallucination detection results, confidence scores, and recommendations
        """
        try:
            # Validate script path
            validation_result = validate_script_path(script_path)
            if isinstance(validation_result, dict) and not validation_result.get(
                "valid", False
            ):
                return json.dumps(
                    {
                        "success": False,
                        "error": validation_result.get(
                            "error", "Script validation failed"
                        ),
                    },
                    indent=2,
                )

            # Get the app context that was stored during lifespan
            app_ctx = get_app_context()

            if not app_ctx:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Application context not available",
                    },
                    indent=2,
                )

            # Get database client (required)
            database_client = getattr(app_ctx, "database_client", None)

            # Get Neo4j driver (optional)
            neo4j_driver = None
            if hasattr(app_ctx, "repo_extractor") and app_ctx.repo_extractor:
                neo4j_driver = getattr(app_ctx.repo_extractor, "driver", None)

            # Use enhanced hallucination detection (which actually works)
            from knowledge_graph.enhanced_validation import (
                check_ai_script_hallucinations_enhanced as check_ai_script_hallucinations_enhanced_impl,
            )

            # Use the container path if available from validation
            actual_path = validation_result.get("container_path", script_path)
            return await check_ai_script_hallucinations_enhanced_impl(
                database_client=database_client,
                neo4j_driver=neo4j_driver,
                script_path=actual_path,
            )

        except Exception as e:
            logger.error(f"Error in check_ai_script_hallucinations tool: {e}")
            raise MCPToolError(f"Hallucination check failed: {e!s}")

    @mcp.tool()
    @track_request("query_knowledge_graph")
    async def query_knowledge_graph(
        ctx: Context,
        command: str,
    ) -> str:
        """
        Query and explore the Neo4j knowledge graph containing repository data.

        This tool provides comprehensive access to the knowledge graph for exploring repositories,
        classes, methods, functions, and their relationships. Perfect for understanding what data
        is available for hallucination detection and debugging validation results.

        **⚠️ IMPORTANT: Always start with the `repos` command first!**
        Before using any other commands, run `repos` to see what repositories are available
        in your knowledge graph. This will help you understand what data you can explore.

        ## Available Commands:

        **Repository Commands:**
        - `repos` - **START HERE!** List all repositories in the knowledge graph
        - `explore <repo_name>` - Get detailed overview of a specific repository

        **Class Commands:**
        - `classes` - List all classes across all repositories (limited to 20)
        - `classes <repo_name>` - List classes in a specific repository
        - `class <class_name>` - Get detailed information about a specific class including methods and attributes

        **Method Commands:**
        - `method <method_name>` - Search for methods by name across all classes
        - `method <method_name> <class_name>` - Search for a method within a specific class

        **Custom Query:**
        - `query <cypher_query>` - Execute a custom Cypher query (results limited to 20 records)

        ## Knowledge Graph Schema:

        **Node Types:**
        - Repository: `(r:Repository {name: string})`
        - File: `(f:File {path: string, module_name: string})`
        - Class: `(c:Class {name: string, full_name: string})`
        - Method: `(m:Method {name: string, params_list: [string], params_detailed: [string], return_type: string, args: [string]})`
        - Function: `(func:Function {name: string, params_list: [string], params_detailed: [string], return_type: string, args: [string]})`
        - Attribute: `(a:Attribute {name: string, type: string})`

        **Relationships:**
        - `(r:Repository)-[:CONTAINS]->(f:File)`
        - `(f:File)-[:DEFINES]->(c:Class)`
        - `(c:Class)-[:HAS_METHOD]->(m:Method)`
        - `(c:Class)-[:HAS_ATTRIBUTE]->(a:Attribute)`
        - `(f:File)-[:DEFINES]->(func:Function)`

        ## Example Workflow:
        ```
        1. repos                                    # See what repositories are available
        2. explore pydantic-ai                      # Explore a specific repository
        3. classes pydantic-ai                      # List classes in that repository
        4. class Agent                              # Explore the Agent class
        5. method run_stream                        # Search for run_stream method
        6. method __init__ Agent                    # Find Agent constructor
        7. query "MATCH (c:Class)-[:HAS_METHOD]->(m:Method) WHERE m.name = 'run' RETURN c.name, m.name LIMIT 5"
        ```

        Args:
            command: Command string to execute (see available commands above)

        Returns:
            JSON string with query results, statistics, and metadata
        """
        try:
            return await query_knowledge_graph_wrapper(ctx, command)
        except Exception as e:
            logger.error(f"Error in query_knowledge_graph tool: {e}")
            raise MCPToolError(f"Knowledge graph query failed: {e!s}")

    @mcp.tool()
    @track_request("parse_github_repository")
    async def parse_github_repository(
        ctx: Context,
        repo_url: str,
    ) -> str:
        """
        Parse a GitHub repository into the Neo4j knowledge graph.

        This tool clones a GitHub repository, analyzes its Python files, and stores
        the code structure (classes, methods, functions, imports) in Neo4j for use
        in hallucination detection. The tool:

        - Clones the repository to a temporary location
        - Analyzes Python files to extract code structure
        - Stores classes, methods, functions, and imports in Neo4j
        - Provides detailed statistics about the parsing results
        - Automatically handles module name detection for imports

        Args:
            repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo.git')

        Returns:
            JSON string with parsing results, statistics, and repository information
        """
        try:
            # Validate GitHub URL
            validation_result = validate_github_url(repo_url)
            if not validation_result["valid"]:
                raise MCPToolError(validation_result.get("error", "Invalid GitHub URL"))

            return await parse_github_repository_wrapper(ctx, repo_url)
        except Exception as e:
            logger.error(f"Error in parse_github_repository tool: {e}")
            raise MCPToolError(f"Repository parsing failed: {e!s}")

    @mcp.tool()
    @track_request("parse_repository_branch")
    async def parse_repository_branch(
        ctx: Context,
        repo_url: str,
        branch: str,
    ) -> str:
        """
        Parse a specific branch of a GitHub repository into the Neo4j knowledge graph.

        This enhanced tool allows parsing specific branches of a repository, useful for:
        - Analyzing feature branches before merging
        - Comparing different versions of code
        - Tracking code evolution across branches

        The tool extracts:
        - Code structure (classes, methods, functions, imports)
        - Git metadata (branches, tags, recent commits)
        - Repository statistics (contributors, file count, size)

        Args:
            repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo.git')
            branch: Branch name to parse (e.g., 'main', 'develop', 'feature/new-feature')

        Returns:
            JSON string with parsing results, statistics, and branch information
        """
        try:
            # Validate GitHub URL
            validation_result = validate_github_url(repo_url)
            if not validation_result["valid"]:
                raise MCPToolError(validation_result.get("error", "Invalid GitHub URL"))

            # Parse repository with branch support
            from knowledge_graph.repository import parse_github_repository_with_branch

            return await parse_github_repository_with_branch(ctx, repo_url, branch)
        except Exception as e:
            logger.error(f"Error in parse_repository_branch tool: {e}")
            raise MCPToolError(f"Repository branch parsing failed: {e!s}")

    @mcp.tool()
    @track_request("get_repository_info")
    async def get_repository_info(
        ctx: Context,
        repo_name: str,
    ) -> str:
        """
        Get detailed information about a parsed repository from the knowledge graph.

        This tool retrieves comprehensive metadata about a repository including:
        - Repository statistics (file count, contributors, size)
        - Branch information with recent commits
        - Tag information
        - Code structure summary (classes, methods, functions)
        - Git history insights

        Use this after parsing a repository to understand its structure and history.

        Args:
            repo_name: Name of the repository in the knowledge graph (without .git extension)

        Returns:
            JSON string with comprehensive repository information
        """
        try:
            from knowledge_graph.repository import get_repository_metadata_from_neo4j

            return await get_repository_metadata_from_neo4j(ctx, repo_name)
        except Exception as e:
            logger.error(f"Error in get_repository_info tool: {e}")
            raise MCPToolError(f"Failed to get repository info: {e!s}")

    @mcp.tool()
    @track_request("update_parsed_repository")
    async def update_parsed_repository(
        ctx: Context,
        repo_url: str,
    ) -> str:
        """
        Update an already parsed repository with latest changes.

        This tool performs an incremental update of a repository:
        - Pulls latest changes from the remote repository
        - Identifies modified files since last parse
        - Updates only the changed components in Neo4j
        - Preserves existing relationships and metadata

        More efficient than re-parsing the entire repository for large codebases.

        Args:
            repo_url: GitHub repository URL to update

        Returns:
            JSON string with update results and changed files
        """
        try:
            # Validate GitHub URL
            validation_result = validate_github_url(repo_url)
            if not validation_result["valid"]:
                raise MCPToolError(validation_result.get("error", "Invalid GitHub URL"))

            from knowledge_graph.repository import update_repository_in_neo4j

            return await update_repository_in_neo4j(ctx, repo_url)
        except Exception as e:
            logger.error(f"Error in update_parsed_repository tool: {e}")
            raise MCPToolError(f"Repository update failed: {e!s}")

    @mcp.tool()
    @track_request("extract_and_index_repository_code")
    async def extract_and_index_repository_code(
        ctx: Context,
        repo_name: str,
    ) -> str:
        """
        Extract code examples from Neo4j knowledge graph and index them in Qdrant.

        This tool creates a bridge between Neo4j (knowledge graph) and Qdrant (vector database)
        for code search and validation. It:
        - Extracts structured code examples from Neo4j
        - Generates embeddings for semantic search
        - Stores code with rich metadata in Qdrant
        - Enables AI hallucination detection and code validation

        Args:
            repo_name: Name of the repository in Neo4j to extract code from

        Returns:
            JSON string with indexing results and statistics
        """
        import json

        try:
            # Get the app context that was stored during lifespan
            app_ctx = get_app_context()

            if not app_ctx:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Application context not available",
                    },
                    indent=2,
                )

            # Check Neo4j availability
            if not hasattr(app_ctx, "repo_extractor") or not app_ctx.repo_extractor:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Repository extractor not available. Neo4j may not be configured or USE_KNOWLEDGE_GRAPH may be false.",
                    },
                    indent=2,
                )

            # Check database availability
            if not hasattr(app_ctx, "database_client") or not app_ctx.database_client:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Database client not available",
                    },
                    indent=2,
                )

            # Clean up any existing code examples for this repository
            logger.info(
                f"Cleaning up existing code examples for repository: {repo_name}"
            )
            try:
                await app_ctx.database_client.delete_repository_code_examples(repo_name)
            except Exception as cleanup_error:
                logger.warning(f"Error during cleanup: {cleanup_error}")

            # Extract code examples from Neo4j
            from knowledge_graph.code_extractor import extract_repository_code

            extraction_result = await extract_repository_code(
                app_ctx.repo_extractor, repo_name
            )

            if not extraction_result["success"]:
                return json.dumps(extraction_result, indent=2)

            code_examples = extraction_result["code_examples"]

            if not code_examples:
                return json.dumps(
                    {
                        "success": True,
                        "repository_name": repo_name,
                        "message": "No code examples found to index",
                        "indexed_count": 0,
                    },
                    indent=2,
                )

            # Generate embeddings for code examples
            from utils import create_embeddings_batch

            embedding_texts = [example["embedding_text"] for example in code_examples]
            logger.info(
                f"Generating embeddings for {len(embedding_texts)} code examples"
            )

            embeddings = create_embeddings_batch(embedding_texts)

            if len(embeddings) != len(code_examples):
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Embedding count mismatch: got {len(embeddings)}, expected {len(code_examples)}",
                    },
                    indent=2,
                )

            # Prepare data for Qdrant storage
            urls = []
            chunk_numbers = []
            code_texts = []
            summaries = []
            metadatas = []
            source_ids = []

            for i, example in enumerate(code_examples):
                # Create a pseudo-URL for the code example
                pseudo_url = f"neo4j://repository/{repo_name}/{example['code_type']}/{example['name']}"
                urls.append(pseudo_url)
                chunk_numbers.append(i)
                code_texts.append(example["code_text"])
                summaries.append(
                    f"{example['code_type'].title()}: {example['full_name']}"
                )
                metadatas.append(example["metadata"])
                source_ids.append(repo_name)

            # Store in Qdrant
            logger.info(f"Storing {len(code_examples)} code examples in Qdrant")

            await app_ctx.database_client.add_code_examples(
                urls=urls,
                chunk_numbers=chunk_numbers,
                code_examples=code_texts,
                summaries=summaries,
                metadatas=metadatas,
                embeddings=embeddings,
                source_ids=source_ids,
            )

            # Update source information
            await app_ctx.database_client.update_source_info(
                source_id=repo_name,
                summary=f"Code repository with {extraction_result['extraction_summary']['classes']} classes, "
                f"{extraction_result['extraction_summary']['methods']} methods, "
                f"{extraction_result['extraction_summary']['functions']} functions",
                word_count=sum(
                    len(example["code_text"].split()) for example in code_examples
                ),
            )

            return json.dumps(
                {
                    "success": True,
                    "repository_name": repo_name,
                    "indexed_count": len(code_examples),
                    "extraction_summary": extraction_result["extraction_summary"],
                    "storage_summary": {
                        "embeddings_generated": len(embeddings),
                        "examples_stored": len(code_examples),
                        "total_code_words": sum(
                            len(example["code_text"].split())
                            for example in code_examples
                        ),
                    },
                    "message": f"Successfully indexed {len(code_examples)} code examples from {repo_name}",
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Error in extract_and_index_repository_code tool: {e}")
            return json.dumps(
                {
                    "success": False,
                    "repository_name": repo_name,
                    "error": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    @track_request("smart_code_search")
    async def smart_code_search(
        ctx: Context,
        query: str,
        match_count: int = 5,
        source_filter: str | None = None,
        min_confidence: float = 0.6,
        validation_mode: str = "balanced",
        include_suggestions: bool = True,
    ) -> str:
        """
        Smart code search that intelligently combines Qdrant semantic search with Neo4j validation.

        This tool provides high-confidence code search results by:
        - Performing semantic search in Qdrant for relevant code examples
        - Validating each result against Neo4j knowledge graph structure
        - Adding confidence scores and validation metadata
        - Providing intelligent fallback when one system is unavailable
        - Options to control validation for speed vs accuracy trade-offs

        Args:
            query: Search query for semantic matching
            match_count: Maximum number of results to return (default: 5)
            source_filter: Optional source repository filter (e.g., 'repo-name')
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.6)
            validation_mode: Validation approach - "fast", "balanced", "thorough" (default: "balanced")
            include_suggestions: Whether to include correction suggestions (default: True)

        Returns:
            JSON string with validated search results, confidence scores, and metadata
        """
        import json

        try:
            # Get the app context
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

            # Initialize validated search service
            from services.validated_search import ValidatedCodeSearchService

            neo4j_driver = None
            if hasattr(app_ctx, "repo_extractor") and app_ctx.repo_extractor:
                # Extract Neo4j driver if available
                neo4j_driver = getattr(app_ctx.repo_extractor, "driver", None)

            validated_search = ValidatedCodeSearchService(
                app_ctx.database_client, neo4j_driver
            )

            # Configure validation based on mode
            parallel_validation = True
            if validation_mode == "fast":
                parallel_validation = True
                min_confidence = max(min_confidence, 0.4)  # Lower threshold for speed
            elif validation_mode == "thorough":
                parallel_validation = False  # Sequential for thoroughness
                min_confidence = max(
                    min_confidence, 0.7
                )  # Higher threshold for accuracy
            # balanced mode uses defaults

            # Perform validated search
            result = await validated_search.search_and_validate_code(
                query=query,
                match_count=match_count,
                source_filter=source_filter,
                min_confidence=min_confidence,
                include_suggestions=include_suggestions,
                parallel_validation=parallel_validation,
            )

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error in smart_code_search tool: {e}")
            return json.dumps(
                {
                    "success": False,
                    "query": query,
                    "error": str(e),
                },
                indent=2,
            )

    @mcp.tool()
    @track_request("check_ai_script_hallucinations_enhanced")
    async def check_ai_script_hallucinations_enhanced(
        ctx: Context,
        script_path: str,
        include_code_suggestions: bool = True,
        detailed_analysis: bool = True,
    ) -> str:
        """
        Enhanced AI script hallucination detection using both Neo4j and Qdrant validation.

        This tool provides comprehensive hallucination detection by:
        - Analyzing script structure and extracting code elements
        - Validating against Neo4j knowledge graph for structural correctness
        - Finding similar code examples in Qdrant for semantic validation
        - Providing detailed confidence scores and suggested corrections
        - Combining both validation approaches for maximum accuracy

        Improvements over basic hallucination detection:
        - Uses semantic search to find real code examples
        - Provides code suggestions from actual repositories
        - Combines structural and semantic validation
        - Better confidence scoring with multiple validation methods
        - Parallel validation for improved performance

        Args:
            script_path: Absolute path to the Python script to analyze
            include_code_suggestions: Whether to include code suggestions from real examples (default: True)
            detailed_analysis: Whether to include detailed validation results (default: True)

        Returns:
            JSON string with comprehensive hallucination detection results, confidence scores, and recommendations
        """
        try:
            # Validate script path
            validation_result = validate_script_path(script_path)
            if isinstance(validation_result, dict) and not validation_result.get(
                "valid", False
            ):
                return json.dumps(
                    {
                        "success": False,
                        "error": validation_result.get(
                            "error", "Script validation failed"
                        ),
                    },
                    indent=2,
                )

            # Get the app context
            app_ctx = get_app_context()

            if not app_ctx:
                return json.dumps(
                    {
                        "success": False,
                        "error": "Application context not available",
                    },
                    indent=2,
                )

            # Get database client (required)
            database_client = getattr(app_ctx, "database_client", None)

            # Get Neo4j driver (optional)
            neo4j_driver = None
            if hasattr(app_ctx, "repo_extractor") and app_ctx.repo_extractor:
                neo4j_driver = getattr(app_ctx.repo_extractor, "driver", None)

            # Use enhanced hallucination detection
            from knowledge_graph.enhanced_validation import (
                check_ai_script_hallucinations_enhanced as check_ai_script_hallucinations_enhanced_impl,
            )

            # Use the container path if available from validation
            actual_path = validation_result.get("container_path", script_path)
            return await check_ai_script_hallucinations_enhanced_impl(
                database_client=database_client,
                neo4j_driver=neo4j_driver,
                script_path=actual_path,
            )

        except Exception as e:
            logger.error(f"Error in enhanced hallucination detection tool: {e}")
            raise MCPToolError(f"Enhanced hallucination check failed: {e!s}")

    @mcp.tool()
    @track_request("get_script_analysis_info")
    async def get_script_analysis_info(ctx: Context) -> str:
        """
        Get information about script analysis setup and paths.

        This helper tool provides information about:
        - Available script directories
        - How to use the hallucination detection tools
        - Path mapping between host and container

        Returns:
            JSON string with setup information and usage examples
        """
        import os

        info = {
            "accessible_paths": {
                "user_scripts": "./analysis_scripts/user_scripts/",
                "test_scripts": "./analysis_scripts/test_scripts/",
                "validation_results": "./analysis_scripts/validation_results/",
                "temp_scripts": "/tmp/ (maps to /app/tmp_scripts/ in container)",
            },
            "usage_examples": [
                {
                    "description": "Analyze a script in user_scripts directory",
                    "host_path": "./analysis_scripts/user_scripts/my_script.py",
                    "tool_call": "check_ai_script_hallucinations(script_path='analysis_scripts/user_scripts/my_script.py')",
                },
                {
                    "description": "Analyze a script from /tmp",
                    "host_path": "/tmp/test.py",
                    "tool_call": "check_ai_script_hallucinations(script_path='/tmp/test.py')",
                },
                {
                    "description": "Analyze with just filename (defaults to user_scripts)",
                    "host_path": "./analysis_scripts/user_scripts/script.py",
                    "tool_call": "check_ai_script_hallucinations(script_path='script.py')",
                },
            ],
            "instructions": [
                "1. Place your Python scripts in ./analysis_scripts/user_scripts/ on your host machine",
                "2. Call the hallucination detection tools with the relative path",
                "3. Results will be saved to ./analysis_scripts/validation_results/",
                "4. The path translation is automatic - you can use convenient paths",
            ],
            "container_mappings": {
                "./analysis_scripts/": "/app/analysis_scripts/",
                "/tmp/": "/app/tmp_scripts/",
            },
            "available_tools": [
                "check_ai_script_hallucinations - Basic hallucination detection",
                "check_ai_script_hallucinations_enhanced - Enhanced detection with code suggestions",
            ],
        }

        # Check which directories actually exist
        for key, path in info["accessible_paths"].items():
            if "(" not in path:  # Skip paths with descriptions
                container_path = f"/app/analysis_scripts/{key.replace('_', '_')}/"
                if os.path.exists(container_path):
                    info["accessible_paths"][key] += " ✓ (exists)"
                else:
                    info["accessible_paths"][key] += " ✗ (not found)"

        return json.dumps(info, indent=2)
