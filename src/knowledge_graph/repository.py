"""
Repository parsing functionality for the knowledge graph.

Handles GitHub repository cloning, code analysis, and storage in Neo4j.
"""

import json
import logging
import os
from typing import Any
from urllib.parse import urlparse

from fastmcp import Context

logger = logging.getLogger(__name__)


# Import for getting app context
def get_app_context():
    """Get the stored app context."""
    from core.context import get_app_context as _get_app_context

    return _get_app_context()


def validate_github_url(url: str) -> dict[str, Any]:
    """
    Validate that a URL is a valid GitHub repository URL.

    Args:
        url: URL to validate

    Returns:
        Dictionary with 'valid' boolean and 'error' message if invalid
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return {"valid": False, "error": "URL must use http or https protocol"}

        if parsed.hostname not in ["github.com", "www.github.com"]:
            return {"valid": False, "error": "URL must be from github.com"}

        # Check path format: /owner/repo or /owner/repo.git
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) != 2:
            return {
                "valid": False,
                "error": "URL must be in format: https://github.com/owner/repo",
            }

        owner, repo = path_parts
        if not owner or not repo:
            return {
                "valid": False,
                "error": "URL must include both owner and repository name",
            }

        # Remove .git extension if present
        if repo.endswith(".git"):
            repo = repo[:-4]

        return {"valid": True, "owner": owner, "repo": repo}
    except Exception as e:
        return {"valid": False, "error": f"Invalid URL format: {e!s}"}


async def parse_github_repository(repo_extractor: Any, repo_url: str) -> str:
    """
    Parse a GitHub repository into the Neo4j knowledge graph.

    This clones a GitHub repository, analyzes its Python files, and stores
    the code structure (classes, methods, functions, imports) in Neo4j for use
    in hallucination detection.

    Args:
        repo_extractor: Repository extractor instance from context
        repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo.git')

    Returns:
        JSON string with parsing results, statistics, and repository information
    """
    try:
        # Check if knowledge graph functionality is enabled
        knowledge_graph_enabled = os.getenv("USE_KNOWLEDGE_GRAPH", "false") == "true"
        if not knowledge_graph_enabled:
            return json.dumps(
                {
                    "success": False,
                    "error": "Knowledge graph functionality is disabled. Set USE_KNOWLEDGE_GRAPH=true in environment.",
                },
                indent=2,
            )

        if not repo_extractor:
            return json.dumps(
                {
                    "success": False,
                    "error": "Repository extractor not available. Check Neo4j configuration in environment variables.",
                },
                indent=2,
            )

        # Validate repository URL
        validation = validate_github_url(repo_url)
        if not validation["valid"]:
            return json.dumps(
                {"success": False, "repo_url": repo_url, "error": validation["error"]},
                indent=2,
            )

        # Extract repository name from URL
        repo_name = repo_url.rstrip(".git").split("/")[-1]

        logger.info(f"Starting repository parsing for: {repo_url}")

        # Clone and analyze the repository
        # The repo_extractor handles:
        # 1. Cloning the repository to a temporary location
        # 2. Analyzing Python files to extract code structure
        # 3. Storing classes, methods, functions, and imports in Neo4j
        # 4. Cleaning up temporary files
        result = await repo_extractor.analyze_repository(repo_url)

        # Query Neo4j to get statistics about what was stored
        stats_query = """
        MATCH (r:Repository {name: $repo_name})
        OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
        OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (f)-[:DEFINES]->(func:Function)
        WITH r,
             COLLECT(DISTINCT f) as files,
             COLLECT(DISTINCT c) as classes,
             COLLECT(DISTINCT m) as methods,
             COLLECT(DISTINCT func) as functions
        RETURN 
            SIZE([f IN files WHERE f IS NOT NULL]) as file_count,
            SIZE([c IN classes WHERE c IS NOT NULL]) as class_count,
            SIZE([m IN methods WHERE m IS NOT NULL]) as method_count,
            SIZE([func IN functions WHERE func IS NOT NULL]) as function_count
        """

        # Get statistics from the extractor's driver
        async with repo_extractor.driver.session() as session:
            stats_result = await session.run(stats_query, repo_name=repo_name)
            stats = await stats_result.single()

        return json.dumps(
            {
                "success": True,
                "repo_url": repo_url,
                "repository_name": repo_name,
                "statistics": {
                    "files_processed": stats["file_count"] if stats else 0,
                    "classes_created": stats["class_count"] if stats else 0,
                    "methods_created": stats["method_count"] if stats else 0,
                    "functions_created": stats["function_count"] if stats else 0,
                },
                "message": f"Successfully parsed repository '{repo_name}' into the knowledge graph",
                "next_steps": [
                    "Use 'query_knowledge_graph' tool with 'explore <repo_name>' to see detailed statistics",
                    "Use 'check_ai_script_hallucinations' tool to validate AI-generated code against this repository",
                ],
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error parsing repository {repo_url}: {e}")
        return json.dumps(
            {
                "success": False,
                "repo_url": repo_url,
                "error": f"Repository parsing failed: {e!s}",
            },
            indent=2,
        )


async def parse_github_repository_with_branch(
    ctx: Context,
    repo_url: str,
    branch: str,
) -> str:
    """Parse a specific branch of a GitHub repository."""
    # Get the app context that was stored during lifespan
    app_ctx = get_app_context()

    if not app_ctx:
        return json.dumps(
            {
                "error": "Application context not available",
                "details": "The application is not properly initialized",
            }
        )

    repo_extractor = getattr(app_ctx, "repo_extractor", None)
    knowledge_graph_enabled = getattr(app_ctx, "knowledge_validator", None) is not None

    if not knowledge_graph_enabled or not repo_extractor:
        return json.dumps(
            {
                "error": "Knowledge graph functionality is not enabled",
                "details": "Set USE_KNOWLEDGE_GRAPH=true and configure Neo4j credentials",
            }
        )

    try:
        # Validate the URL format
        validation = validate_github_url(repo_url)
        if validation:
            return json.dumps(
                {
                    "error": "Invalid GitHub URL",
                    "details": validation,
                }
            )

        # Extract repository name
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        logger.info(f"Parsing repository {repo_name} on branch {branch}")

        # Parse the repository with branch specification
        await repo_extractor.analyze_repository(repo_url, branch=branch)

        # Get statistics from Neo4j
        stats_query = """
        MATCH (r:Repository {name: $repo_name})
        OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
        OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        OPTIONAL MATCH (f)-[:DEFINES]->(func:Function)
        OPTIONAL MATCH (r)-[:HAS_BRANCH]->(b:Branch)
        OPTIONAL MATCH (r)-[:HAS_COMMIT]->(commit:Commit)
        WITH r,
             COLLECT(DISTINCT f) as files,
             COLLECT(DISTINCT c) as classes,
             COLLECT(DISTINCT m) as methods,
             COLLECT(DISTINCT func) as functions,
             COLLECT(DISTINCT b) as branches,
             COLLECT(DISTINCT commit) as commits
        RETURN 
            r.remote_url as remote_url,
            r.current_branch as current_branch,
            r.file_count as total_files,
            r.contributor_count as contributors,
            r.size as repo_size,
            SIZE([f IN files WHERE f IS NOT NULL]) as files_analyzed,
            SIZE([c IN classes WHERE c IS NOT NULL]) as classes,
            SIZE([m IN methods WHERE m IS NOT NULL]) as methods,
            SIZE([func IN functions WHERE func IS NOT NULL]) as functions,
            SIZE([b IN branches WHERE b IS NOT NULL]) as branches,
            SIZE([commit IN commits WHERE commit IS NOT NULL]) as recent_commits
        """

        async with repo_extractor.driver.session() as session:
            result = await session.run(stats_query, repo_name=repo_name)
            stats = await result.single()

            if stats:
                return json.dumps(
                    {
                        "status": "success",
                        "repository": repo_name,
                        "branch": branch,
                        "remote_url": stats["remote_url"] or repo_url,
                        "current_branch": stats["current_branch"] or branch,
                        "statistics": {
                            "total_files": stats["total_files"] or 0,
                            "files_analyzed": stats["files_analyzed"],
                            "classes": stats["classes"],
                            "methods": stats["methods"],
                            "functions": stats["functions"],
                            "branches": stats["branches"],
                            "recent_commits": stats["recent_commits"],
                            "contributors": stats["contributors"] or 0,
                            "repository_size": stats["repo_size"] or "unknown",
                        },
                        "message": f"Successfully parsed {repo_name} branch {branch} into knowledge graph",
                    }
                )
            return json.dumps(
                {
                    "status": "error",
                    "message": "Failed to retrieve statistics after parsing",
                }
            )

    except Exception as e:
        logger.error(f"Error parsing repository branch: {e}")
        return json.dumps(
            {
                "error": "Failed to parse repository branch",
                "details": str(e),
            }
        )


async def get_repository_metadata_from_neo4j(ctx: Context, repo_name: str) -> str:
    """Get comprehensive repository information from Neo4j."""
    # Get the app context that was stored during lifespan
    app_ctx = get_app_context()

    if not app_ctx:
        return json.dumps(
            {
                "error": "Application context not available",
                "details": "The application is not properly initialized",
            }
        )

    repo_extractor = getattr(app_ctx, "repo_extractor", None)

    if not repo_extractor:
        return json.dumps(
            {
                "error": "Knowledge graph functionality is not enabled",
            }
        )

    try:
        async with repo_extractor.driver.session() as session:
            # Get repository info
            repo_query = """
            MATCH (r:Repository {name: $repo_name})
            RETURN r
            """
            result = await session.run(repo_query, repo_name=repo_name)
            repo_node = await result.single()

            if not repo_node:
                return json.dumps(
                    {
                        "error": f"Repository {repo_name} not found in knowledge graph",
                    }
                )

            repo_data = dict(repo_node["r"])

            # Get branches - fix missing property warnings with COALESCE
            branches_query = """
            MATCH (r:Repository {name: $repo_name})-[:HAS_BRANCH]->(b:Branch)
            RETURN b.name as name, 
                   COALESCE(b.last_commit_date, '') as last_commit_date, 
                   COALESCE(b.last_commit_message, '') as last_commit_message
            LIMIT 20
            """
            result = await session.run(branches_query, repo_name=repo_name)
            branches = [dict(record) async for record in result]

            # Get recent commits - fix missing property warnings with COALESCE
            commits_query = """
            MATCH (r:Repository {name: $repo_name})-[:HAS_COMMIT]->(c:Commit)
            RETURN COALESCE(c.hash, '') as hash, 
                   COALESCE(c.author_name, '') as author, 
                   COALESCE(c.date, '') as date, 
                   COALESCE(c.message, '') as message
            ORDER BY c.date DESC
            LIMIT 20
            """
            result = await session.run(commits_query, repo_name=repo_name)
            commits = [dict(record) async for record in result]

            # Get file statistics - CORRECTED QUERY
            stats_query = """
            MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
            OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
            OPTIONAL MATCH (f)-[:DEFINES]->(func:Function)
            WITH r,
                 COLLECT(DISTINCT f) as files,
                 COLLECT(DISTINCT c) as classes,
                 COLLECT(DISTINCT m) as methods,
                 COLLECT(DISTINCT func) as functions
            RETURN 
                SIZE([f IN files WHERE f IS NOT NULL]) as file_count,
                SIZE([c IN classes WHERE c IS NOT NULL]) as class_count,
                SIZE([m IN methods WHERE m IS NOT NULL]) as method_count,
                SIZE([func IN functions WHERE func IS NOT NULL]) as function_count,
                REDUCE(total = 0, f IN [file IN files WHERE file IS NOT NULL] | total + COALESCE(f.line_count, 0)) as total_lines
            """
            result = await session.run(stats_query, repo_name=repo_name)
            stats = await result.single()

            return json.dumps(
                {
                    "repository": repo_name,
                    "metadata": {
                        "remote_url": repo_data.get("remote_url"),
                        "current_branch": repo_data.get("current_branch"),
                        "size": repo_data.get("size"),
                        "contributor_count": repo_data.get("contributor_count", 0),
                        "file_count": repo_data.get("file_count", 0),
                    },
                    "branches": branches,
                    "recent_commits": commits,
                    "code_statistics": {
                        "files_analyzed": stats["file_count"] if stats else 0,
                        "total_classes": stats["class_count"] if stats else 0,
                        "total_methods": stats["method_count"] if stats else 0,
                        "total_functions": stats["function_count"] if stats else 0,
                        "total_lines": stats["total_lines"] if stats else 0,
                    },
                },
                indent=2,
            )

    except Exception as e:
        logger.error(f"Error getting repository metadata: {e}")
        return json.dumps(
            {
                "error": "Failed to get repository metadata",
                "details": str(e),
            }
        )


async def update_repository_in_neo4j(ctx: Context, repo_url: str) -> str:
    """Update an existing repository with latest changes."""
    # Get the app context that was stored during lifespan
    app_ctx = get_app_context()

    if not app_ctx:
        return json.dumps(
            {
                "error": "Application context not available",
                "details": "The application is not properly initialized",
            }
        )

    repo_extractor = getattr(app_ctx, "repo_extractor", None)

    if not repo_extractor or not getattr(repo_extractor, "git_manager", None):
        return json.dumps(
            {
                "error": "Git manager not available for incremental updates",
                "suggestion": "Re-parse the entire repository using parse_github_repository",
            }
        )

    try:
        repo_name = repo_url.split("/")[-1].replace(".git", "")

        # Check if repository exists in Neo4j
        async with repo_extractor.driver.session() as session:
            result = await session.run(
                "MATCH (r:Repository {name: $name}) RETURN r.remote_url as url",
                name=repo_name,
            )
            existing = await result.single()

            if not existing:
                return json.dumps(
                    {
                        "error": f"Repository {repo_name} not found",
                        "suggestion": "Parse the repository first using parse_github_repository",
                    }
                )

        # For now, just re-parse the repository
        # TODO: Implement incremental updates using GitRepositoryManager
        await repo_extractor.analyze_repository(repo_url)

        return json.dumps(
            {
                "status": "success",
                "repository": repo_name,
                "message": "Repository updated successfully",
                "note": "Full re-parse performed (incremental updates coming soon)",
            }
        )

    except Exception as e:
        logger.error(f"Error updating repository: {e}")
        return json.dumps(
            {
                "error": "Failed to update repository",
                "details": str(e),
            }
        )
