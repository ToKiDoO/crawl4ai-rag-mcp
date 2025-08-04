"""
Knowledge graph tools for Neo4j integration.

Provides secure wrappers for Neo4j operations with injection prevention.
"""

import re
from typing import Dict, Any, List, Optional
from neo4j import AsyncSession
import logging

logger = logging.getLogger(__name__)


async def execute_cypher_query(
    query: str,
    params: Optional[Dict[str, Any]] = None,
    session: Optional[AsyncSession] = None
) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query with parameterized inputs to prevent injection.
    
    Args:
        query: Cypher query with parameter placeholders
        params: Query parameters
        session: Neo4j session (mocked in tests)
        
    Returns:
        Query results
        
    Raises:
        ValueError: If query contains dangerous patterns
    """
    # Validate query doesn't contain dangerous operations
    dangerous_patterns = [
        r'\bDETACH\s+DELETE\b',
        r'\bDROP\s+',
        r'\bCREATE\s+CONSTRAINT\b',
        r'\bCREATE\s+INDEX\b',
        r'\bCALL\s+dbms\.',
        r'\bCALL\s+apoc\.',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise ValueError(f"Dangerous Cypher pattern detected: {pattern}")
    
    # Ensure parameterized queries are used
    if params is None:
        params = {}
    
    # In production, this would execute against Neo4j
    # For testing, we just validate and return empty results
    logger.info(f"Executing Cypher query: {query} with params: {params}")
    
    if session:
        # Execute with session
        result = await session.run(query, params)
        return [record.data() for record in await result.fetch()]
    else:
        # Mock response for testing
        return []


def sanitize_cypher_input(value: str) -> str:
    """
    Sanitize input for Cypher queries.
    
    Args:
        value: Input value to sanitize
        
    Returns:
        Sanitized value
    """
    if not isinstance(value, str):
        return str(value)
    
    # Remove dangerous characters
    sanitized = re.sub(r'[;\'"\\]', '', value)
    
    # Remove Cypher keywords that could be dangerous
    dangerous_keywords = [
        'DELETE', 'DETACH', 'DROP', 'CREATE', 'MERGE',
        'SET', 'REMOVE', 'CALL', 'LOAD', 'USING'
    ]
    
    for keyword in dangerous_keywords:
        sanitized = re.sub(rf'\b{keyword}\b', '', sanitized, flags=re.IGNORECASE)
    
    return sanitized.strip()


def validate_cypher_query(query: str) -> bool:
    """
    Validate a Cypher query for safety.
    
    Args:
        query: Cypher query to validate
        
    Returns:
        True if query is safe
        
    Raises:
        ValueError: If query is unsafe
    """
    # Check for multiple statements
    if ';' in query:
        raise ValueError("Multiple statements not allowed")
    
    # Check for dangerous commands
    dangerous_commands = [
        'DETACH DELETE',
        'DROP DATABASE',
        'DROP CONSTRAINT',
        'DROP INDEX',
        'CALL dbms.shutdown',
    ]
    
    query_upper = query.upper()
    for cmd in dangerous_commands:
        if cmd in query_upper:
            raise ValueError(f"Dangerous command detected: {cmd}")
    
    # Ensure query uses parameters for user input
    if "'" in query or '"' in query:
        # Check if it's a parameter placeholder
        if not re.search(r'\$\w+', query):
            logger.warning("Query contains literal strings, consider using parameters")
    
    return True