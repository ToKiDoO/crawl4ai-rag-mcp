"""
Main knowledge graph query functionality.

Provides the main query interface for the Neo4j knowledge graph.
"""

import json
import logging
import os

from neo4j import AsyncGraphDatabase

from .handlers import (
    handle_class_command,
    handle_classes_command,
    handle_explore_command,
    handle_method_command,
    handle_query_command,
    handle_repos_command,
)

logger = logging.getLogger(__name__)


async def query_knowledge_graph(command: str) -> str:
    """
    Query and explore the Neo4j knowledge graph containing repository data.

    This provides comprehensive access to the knowledge graph for exploring repositories,
    classes, methods, functions, and their relationships.

    Args:
        command: Command string to execute

    Returns:
        JSON string with query results, statistics, and metadata
    """
    # Check if Neo4j is configured
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_uri or not neo4j_password:
        return json.dumps(
            {
                "success": False,
                "error": "Neo4j is not configured. Please set NEO4J_URI and NEO4J_PASSWORD environment variables.",
            },
            indent=2,
        )

    driver = None
    try:
        # Import notification suppression (available in neo4j>=5.21.0)
        try:
            from neo4j import NotificationMinimumSeverity

            # Create Neo4j driver with notification suppression
            driver = AsyncGraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
                warn_notification_severity=NotificationMinimumSeverity.OFF,
            )
        except (ImportError, AttributeError):
            # Fallback for older versions - use logging suppression
            import logging

            logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
            driver = AsyncGraphDatabase.driver(
                neo4j_uri,
                auth=(neo4j_user, neo4j_password),
            )

        # Parse command
        command_lower = command.lower().strip()
        parts = command.split()

        async with driver.session() as session:
            # Handle different commands
            if command_lower == "repos":
                return await handle_repos_command(session, command)

            if command_lower.startswith("explore ") and len(parts) >= 2:
                repo_name = parts[1]
                return await handle_explore_command(session, command, repo_name)

            if command_lower == "classes":
                return await handle_classes_command(session, command)

            if command_lower.startswith("classes ") and len(parts) >= 2:
                repo_name = parts[1]
                return await handle_classes_command(session, command, repo_name)

            if command_lower.startswith("class ") and len(parts) >= 2:
                class_name = parts[1]
                return await handle_class_command(session, command, class_name)

            if command_lower.startswith("method "):
                if len(parts) >= 3:
                    method_name = parts[1]
                    class_name = parts[2]
                    return await handle_method_command(
                        session,
                        command,
                        method_name,
                        class_name,
                    )
                if len(parts) >= 2:
                    method_name = parts[1]
                    return await handle_method_command(session, command, method_name)
                return json.dumps(
                    {
                        "success": False,
                        "error": "Invalid method command. Use: method <method_name> [class_name]",
                    },
                    indent=2,
                )

            if command_lower.startswith("query ") and len(parts) >= 2:
                cypher_query = " ".join(parts[1:])
                return await handle_query_command(session, command, cypher_query)

            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown command: '{command}'. Use 'repos', 'explore <repo>', 'classes [repo]', 'class <name>', 'method <name> [class]', or 'query <cypher>'",
                },
                indent=2,
            )

    except Exception as e:
        logger.error(f"Error in query_knowledge_graph: {e}")
        return json.dumps(
            {
                "success": False,
                "error": f"Knowledge graph query failed: {e!s}",
            },
            indent=2,
        )
    finally:
        if driver:
            await driver.close()
