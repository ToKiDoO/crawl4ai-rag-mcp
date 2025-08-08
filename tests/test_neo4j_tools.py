#!/usr/bin/env python3
"""Test script to verify Neo4j knowledge graph tools are working"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Set USE_TEST_ENV before importing anything
os.environ['USE_TEST_ENV'] = 'true'

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment from .env.test
from dotenv import load_dotenv
load_dotenv(".env.test", override=True)

# Import the MCP server functions
from crawl4ai_mcp import (
    parse_github_repository,
    query_knowledge_graph,
    check_ai_script_hallucinations,
    Context,
    crawl4ai_lifespan,
    mcp
)

class MockContext:
    """Mock context for testing"""
    def __init__(self, lifespan_context):
        self.request_context = MockRequestContext(lifespan_context)

class MockRequestContext:
    """Mock request context"""
    def __init__(self, lifespan_context):
        self.lifespan_context = lifespan_context

async def test_neo4j_tools():
    """Test the Neo4j knowledge graph tools"""
    print("Testing Neo4j Knowledge Graph Tools")
    print("=" * 50)
    
    # Initialize the lifespan context
    print("\n1. Initializing Neo4j components...")
    async with crawl4ai_lifespan(mcp) as lifespan_context:
        # Create mock context
        ctx = MockContext(lifespan_context)
        
        # Check if knowledge graph is enabled
        if not lifespan_context.knowledge_validator:
            print("❌ Knowledge graph validator not initialized!")
            print("   Check USE_KNOWLEDGE_GRAPH and Neo4j credentials in .env.test")
            return
        
        if not lifespan_context.repo_extractor:
            print("❌ Repository extractor not initialized!")
            return
            
        print("✅ Neo4j components initialized successfully!")
        
        # Test 1: Query knowledge graph for existing repos
        print("\n2. Testing query_knowledge_graph - listing repositories...")
        try:
            result = await query_knowledge_graph(ctx, "repos")
            result_data = json.loads(result)
            if result_data["success"]:
                print(f"✅ Found {len(result_data.get('repositories', []))} repositories")
                for repo in result_data.get('repositories', [])[:3]:
                    print(f"   - {repo}")
            else:
                print(f"❌ Query failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Error querying knowledge graph: {e}")
        
        # Test 2: Parse a small test repository
        print("\n3. Testing parse_github_repository...")
        test_repo = "https://github.com/octocat/Hello-World.git"
        try:
            result = await parse_github_repository(ctx, test_repo)
            result_data = json.loads(result)
            if result_data["success"]:
                print(f"✅ Successfully parsed {result_data['repo_name']}")
                stats = result_data.get('statistics', {})
                print(f"   - Files: {stats.get('total_files', 0)}")
                print(f"   - Classes: {stats.get('total_classes', 0)}")
                print(f"   - Functions: {stats.get('total_functions', 0)}")
            else:
                print(f"❌ Parsing failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Error parsing repository: {e}")
        
        # Test 3: Query the parsed repository
        print("\n4. Testing query_knowledge_graph - exploring repository...")
        try:
            result = await query_knowledge_graph(ctx, "explore Hello-World")
            result_data = json.loads(result)
            if result_data["success"]:
                print("✅ Successfully explored repository")
                overview = result_data.get('overview', {})
                print(f"   - Total files: {overview.get('total_files', 0)}")
                print(f"   - Python files: {overview.get('python_files', 0)}")
            else:
                print(f"❌ Exploration failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Error exploring repository: {e}")
        
        # Test 4: Create a test script and check for hallucinations
        print("\n5. Creating test script for hallucination detection...")
        test_script_path = "/tmp/test_ai_script.py"
        test_script_content = """
# Test script with potential hallucinations
import json
from hello_world import NonExistentClass  # This should be flagged

def main():
    # This class doesn't exist in the repo
    obj = NonExistentClass()
    obj.fake_method()  # This method doesn't exist
    
    # Valid Python but might not exist in knowledge graph
    data = json.loads('{}')
    
if __name__ == "__main__":
    main()
"""
        
        with open(test_script_path, 'w') as f:
            f.write(test_script_content)
        
        print(f"   Created test script at {test_script_path}")
        
        print("\n6. Testing check_ai_script_hallucinations...")
        try:
            result = await check_ai_script_hallucinations(ctx, test_script_path)
            result_data = json.loads(result)
            if result_data["success"]:
                print("✅ Hallucination check completed")
                hallucinations = result_data.get('hallucinations', {})
                print(f"   - Import hallucinations: {len(hallucinations.get('imports', []))}")
                print(f"   - Method call hallucinations: {len(hallucinations.get('method_calls', []))}")
                print(f"   - Class instantiation hallucinations: {len(hallucinations.get('class_instantiations', []))}")
                
                # Show some examples
                if hallucinations.get('imports'):
                    print("\n   Import hallucinations found:")
                    for imp in hallucinations['imports'][:2]:
                        print(f"     - {imp['import']} (line {imp['line']})")
            else:
                print(f"❌ Hallucination check failed: {result_data.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Error checking hallucinations: {e}")
        
        print("\n" + "=" * 50)
        print("Neo4j Knowledge Graph Tools Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_neo4j_tools())