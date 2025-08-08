#!/usr/bin/env python3
"""
Direct test of Neo4j functionality to verify the connection fix works.
This bypasses the MCP interface to test the core Neo4j integration.

Created: 2025-08-05
Purpose: Direct Neo4j connection testing for Fix 2 (Neo4j Connection)
Context: Part of MCP Tools Testing issue resolution to fix NEO4J_USER vs NEO4J_USERNAME mismatch

This script was created to test the Neo4j connection fix that standardized environment
variable names from NEO4J_USER to NEO4J_USERNAME across the codebase.

Related outcomes: See mcp_tools_test_results.md for resolution of Neo4j connection issues
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from neo4j import AsyncGraphDatabase


async def test_neo4j_connection():
    """Test basic Neo4j connectivity with fixed credentials."""
    print("Testing Neo4j Connection Fix")
    print("=" * 50)

    # Use environment variables
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "testpassword123")

    print(f"URI: {uri}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    print()

    try:
        # Test direct connection
        driver = AsyncGraphDatabase.driver(uri, auth=(username, password))

        async with driver.session() as session:
            # Test basic connectivity
            result = await session.run("RETURN 1 as test")
            record = await result.single()
            print(f"✅ Basic connection test: {record['test']}")

            # Check node count
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            print(f"✅ Current node count: {record['count']}")

            # Test write operation
            result = await session.run(
                "CREATE (t:TestNode {name: $name, timestamp: $timestamp}) RETURN t",
                name="connection_test",
                timestamp=42,
            )
            record = await result.single()
            print(f"✅ Created test node: {record['t']['name']}")

            # Verify write
            result = await session.run(
                "MATCH (t:TestNode {name: $name}) RETURN count(t) as count",
                name="connection_test",
            )
            record = await result.single()
            print(f"✅ Test node count: {record['count']}")

            # Clean up
            await session.run(
                "MATCH (t:TestNode {name: $name}) DELETE t", name="connection_test"
            )
            print("✅ Cleaned up test node")

        await driver.close()
        print("✅ Connection closed successfully")

        return True

    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_knowledge_graph_tools():
    """Test if the knowledge graph tools can be imported and initialized."""
    print("\nTesting Knowledge Graph Tools Import")
    print("=" * 50)

    try:
        # Test importing the main tools
        from crawl4ai_mcp import validate_neo4j_connection

        validation_result = validate_neo4j_connection()
        print(f"✅ validate_neo4j_connection(): {validation_result}")

        if not validation_result:
            print("❌ Validation failed - environment variables not properly set")
            return False

        # Try to import knowledge graph components
        try:
            from knowledge_graph_tools import (
                execute_cypher_query,
                validate_cypher_query,
            )

            print("✅ Knowledge graph tools imported successfully")
        except ImportError as e:
            print(f"⚠️  Knowledge graph tools import issue: {e}")

        return True

    except Exception as e:
        print(f"❌ Knowledge graph tools test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("Neo4j Connection Fix Verification")
    print("=" * 50)

    # Test 1: Basic connection
    connection_ok = await test_neo4j_connection()

    # Test 2: Tools import
    tools_ok = await test_knowledge_graph_tools()

    print("\nSummary")
    print("=" * 50)
    print(f"Neo4j Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    print(f"Tools Import: {'✅ PASS' if tools_ok else '❌ FAIL'}")

    if connection_ok and tools_ok:
        print("\n🎉 Neo4j connection fix verification SUCCESSFUL!")
        print("The MCP tools should now work correctly with Neo4j.")
    else:
        print("\n❌ Issues detected - further investigation needed.")

    return connection_ok and tools_ok


if __name__ == "__main__":
    asyncio.run(main())
