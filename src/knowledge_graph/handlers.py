"""
Command handlers for Neo4j knowledge graph queries.

Provides handlers for different query commands like repos, explore, classes, etc.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_repos_command(session: Any, command: str) -> str:
    """Handle 'repos' command - list all repositories"""
    query = "MATCH (r:Repository) RETURN r.name as name ORDER BY r.name"
    result = await session.run(query)
    repos = []
    async for record in result:
        repos.append(record["name"])

    return json.dumps(
        {
            "success": True,
            "command": command,
            "data": {"repositories": repos},
            "metadata": {"total_results": len(repos), "limited": False},
        },
        indent=2,
    )


async def handle_explore_command(session: Any, command: str, repo_name: str) -> str:
    """Handle 'explore <repo>' command - get repository overview"""
    # Check if repository exists
    repo_check_query = "MATCH (r:Repository {name: $repo_name}) RETURN r.name as name"
    result = await session.run(repo_check_query, repo_name=repo_name)
    repo_record = await result.single()

    if not repo_record:
        return json.dumps(
            {
                "success": False,
                "command": command,
                "error": f"Repository '{repo_name}' not found in knowledge graph",
            },
            indent=2,
        )

    # Get repository stats
    stats_query = """
    MATCH (r:Repository {name: $repo_name})
    OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
    OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
    OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
    OPTIONAL MATCH (f)-[:DEFINES]->(func:Function)
    OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(a:Attribute)
    WITH r, 
         COLLECT(DISTINCT f) as files,
         COLLECT(DISTINCT c) as classes,
         COLLECT(DISTINCT m) as methods,
         COLLECT(DISTINCT func) as functions,
         COLLECT(DISTINCT a) as attributes
    RETURN 
        SIZE([f IN files WHERE f IS NOT NULL]) as file_count,
        SIZE([c IN classes WHERE c IS NOT NULL]) as class_count,
        SIZE([m IN methods WHERE m IS NOT NULL]) as method_count,
        SIZE([func IN functions WHERE func IS NOT NULL]) as function_count,
        SIZE([a IN attributes WHERE a IS NOT NULL]) as attribute_count
    """

    result = await session.run(stats_query, repo_name=repo_name)
    stats = await result.single()

    # Get sample classes
    sample_classes_query = """
    MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
    RETURN c.name as name, count{(c)-[:HAS_METHOD]->(:Method)} as methods
    ORDER BY methods DESC
    LIMIT 10
    """

    result = await session.run(sample_classes_query, repo_name=repo_name)
    sample_classes = []
    async for record in result:
        sample_classes.append(
            {"name": record["name"], "method_count": record["methods"]},
        )

    return json.dumps(
        {
            "success": True,
            "command": command,
            "data": {
                "repository": repo_name,
                "statistics": {
                    "files": stats["file_count"],
                    "classes": stats["class_count"],
                    "methods": stats["method_count"],
                    "functions": stats["function_count"],
                    "attributes": stats["attribute_count"],
                },
                "sample_classes": sample_classes,
            },
        },
        indent=2,
    )


async def handle_classes_command(
    session: Any, command: str, repo_name: str | None = None
) -> str:
    """Handle 'classes [repo]' command - list classes"""
    limit = 20

    if repo_name:
        query = """
        MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
        RETURN c.name as name, c.full_name as full_name
        ORDER BY c.name
        LIMIT $limit
        """
        result = await session.run(query, repo_name=repo_name, limit=limit)
    else:
        query = """
        MATCH (c:Class)
        RETURN c.name as name, c.full_name as full_name
        ORDER BY c.name
        LIMIT $limit
        """
        result = await session.run(query, limit=limit)

    classes = []
    async for record in result:
        classes.append({"name": record["name"], "full_name": record["full_name"]})

    return json.dumps(
        {
            "success": True,
            "command": command,
            "data": {"classes": classes},
            "metadata": {
                "total_results": len(classes),
                "limited": len(classes) == limit,
                "repository": repo_name,
            },
        },
        indent=2,
    )


async def handle_class_command(session: Any, command: str, class_name: str) -> str:
    """Handle 'class <name>' command - explore specific class"""
    # Find the class
    class_query = """
    MATCH (c:Class)
    WHERE c.name = $class_name OR c.full_name = $class_name
    RETURN c.name as name, c.full_name as full_name
    LIMIT 1
    """
    result = await session.run(class_query, class_name=class_name)
    class_record = await result.single()

    if not class_record:
        return json.dumps(
            {
                "success": False,
                "command": command,
                "error": f"Class '{class_name}' not found in knowledge graph",
            },
            indent=2,
        )

    # Get methods
    methods_query = """
    MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
    WHERE c.name = $class_name OR c.full_name = $class_name
    RETURN m.name as name, m.params_list as params, m.return_type as return_type
    ORDER BY m.name
    """
    result = await session.run(methods_query, class_name=class_name)
    methods = []
    async for record in result:
        methods.append(
            {
                "name": record["name"],
                "params": record["params"],
                "return_type": record["return_type"],
            },
        )

    # Get attributes
    attributes_query = """
    MATCH (c:Class)-[:HAS_ATTRIBUTE]->(a:Attribute)
    WHERE c.name = $class_name OR c.full_name = $class_name
    RETURN a.name as name, a.type as type
    ORDER BY a.name
    """
    result = await session.run(attributes_query, class_name=class_name)
    attributes = []
    async for record in result:
        attributes.append({"name": record["name"], "type": record["type"]})

    return json.dumps(
        {
            "success": True,
            "command": command,
            "data": {
                "class": {
                    "name": class_record["name"],
                    "full_name": class_record["full_name"],
                },
                "methods": methods,
                "attributes": attributes,
            },
        },
        indent=2,
    )


async def handle_method_command(
    session: Any,
    command: str,
    method_name: str,
    class_name: str | None = None,
) -> str:
    """Handle 'method <name> [class]' command - search for methods"""
    if class_name:
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE (c.name = $class_name OR c.full_name = $class_name)
          AND m.name = $method_name
        RETURN c.name as class_name, c.full_name as class_full_name,
               m.name as method_name, m.params_list as params_list, 
               m.params_detailed as params_detailed, m.return_type as return_type, m.args as args
        """
        result = await session.run(
            query,
            class_name=class_name,
            method_name=method_name,
        )
    else:
        query = """
        MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
        WHERE m.name = $method_name
        RETURN c.name as class_name, c.full_name as class_full_name,
               m.name as method_name, m.params_list as params_list, 
               m.params_detailed as params_detailed, m.return_type as return_type, m.args as args
        LIMIT 20
        """
        result = await session.run(query, method_name=method_name)

    methods = []
    async for record in result:
        methods.append(
            {
                "class_name": record["class_name"],
                "class_full_name": record["class_full_name"],
                "method_name": record["method_name"],
                "params_list": record["params_list"],
                "params_detailed": record["params_detailed"],
                "return_type": record["return_type"],
                "args": record["args"],
            },
        )

    return json.dumps(
        {
            "success": True,
            "command": command,
            "data": {"methods": methods},
            "metadata": {"total_results": len(methods), "class_filter": class_name},
        },
        indent=2,
    )


async def handle_query_command(session: Any, command: str, cypher_query: str) -> str:
    """Handle 'query <cypher>' command - execute custom Cypher query"""
    try:
        # Execute the query with a limit to prevent overwhelming responses
        result = await session.run(cypher_query)
        records = []
        count = 0
        async for record in result:
            records.append(dict(record))
            count += 1
            if count >= 20:  # Limit results to prevent overwhelming responses
                break

        return json.dumps(
            {
                "success": True,
                "command": command,
                "data": {"results": records},
                "metadata": {
                    "query": cypher_query,
                    "total_results": count,
                    "limited": count >= 20,
                },
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "command": command,
                "error": f"Query execution failed: {e!s}",
                "query": cypher_query,
            },
            indent=2,
        )
