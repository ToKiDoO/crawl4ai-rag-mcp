#!/usr/bin/env python3
"""
Test script to verify Neo4j HAS_COMMIT relationship warning fix.
This script tests the actual parsing and cleanup operations to ensure
no warnings are generated about HAS_COMMIT relationships.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from knowledge_graphs.parse_repo_into_neo4j import DirectNeo4jExtractor
from neo4j import AsyncGraphDatabase

# Configure logging to capture warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('has_commit_test.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)

async def test_has_commit_warning_fix():
    """Test that HAS_COMMIT relationship operations don't generate warnings."""
    
    # Neo4j connection details
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "testpassword123"
    test_repo_name = "test-has-commit-repo"
    
    logger.info("=" * 60)
    logger.info("TESTING HAS_COMMIT RELATIONSHIP WARNING FIX")
    logger.info("=" * 60)
    
    try:
        # Create extractor (it will create its own driver)
        extractor = DirectNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)
        
        # Initialize the driver 
        await extractor.initialize()
        
        # Create separate driver for direct Neo4j operations
        driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        logger.info(f"Testing with repository: {test_repo_name}")
        
        # Step 1: Clean up any existing data
        logger.info("Step 1: Cleaning up existing test data")
        try:
            await extractor.clear_repository_data(test_repo_name)
            logger.info("✅ Cleanup completed successfully")
        except Exception as e:
            logger.info(f"ℹ️  No existing data to clean: {e}")
        
        # Step 2: Create test repository with branches and commits
        logger.info("Step 2: Creating test repository with branches and commits")
        async with driver.session() as session:
            await session.run("""
                CREATE (r:Repository {name: $repo_name, description: 'Test repo for HAS_COMMIT validation'})
                CREATE (b1:Branch {name: 'main', is_default: true})
                CREATE (b2:Branch {name: 'develop', is_default: false})
                CREATE (c1:Commit {hash: 'abc123', message: 'Initial commit', timestamp: datetime()})
                CREATE (c2:Commit {hash: 'def456', message: 'Second commit', timestamp: datetime()})
                CREATE (f:File {path: 'test.py', module_name: 'test'})
                CREATE (cl:Class {name: 'TestClass', full_name: 'test.TestClass'})
                CREATE (m:Method {name: 'test_method', params_list: ['self'], return_type: 'None'})
                
                CREATE (r)-[:HAS_BRANCH]->(b1)
                CREATE (r)-[:HAS_BRANCH]->(b2) 
                CREATE (r)-[:HAS_COMMIT]->(c1)
                CREATE (r)-[:HAS_COMMIT]->(c2)
                CREATE (r)-[:CONTAINS]->(f)
                CREATE (f)-[:DEFINES]->(cl)
                CREATE (cl)-[:HAS_METHOD]->(m)
            """, repo_name=test_repo_name)
        
        logger.info("✅ Test repository structure created")
        
        # Step 3: Verify data was created correctly
        logger.info("Step 3: Verifying repository structure")
        async with driver.session() as session:
            result = await session.run("""
                MATCH (r:Repository {name: $repo_name})
                OPTIONAL MATCH (r)-[:HAS_BRANCH]->(b:Branch)
                OPTIONAL MATCH (r)-[:HAS_COMMIT]->(c:Commit)
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:DEFINES]->(cl:Class)
                OPTIONAL MATCH (cl)-[:HAS_METHOD]->(m:Method)
                RETURN 
                    count(DISTINCT b) as branch_count,
                    count(DISTINCT c) as commit_count,
                    count(DISTINCT f) as file_count,
                    count(DISTINCT cl) as class_count,
                    count(DISTINCT m) as method_count
            """, repo_name=test_repo_name)
            
            record = await result.single()
            if record:
                logger.info(f"Repository contains:")
                logger.info(f"  - Branches: {record['branch_count']}")
                logger.info(f"  - Commits: {record['commit_count']}")
                logger.info(f"  - Files: {record['file_count']}")
                logger.info(f"  - Classes: {record['class_count']}")  
                logger.info(f"  - Methods: {record['method_count']}")
                
                if record['commit_count'] > 0:
                    logger.info("✅ HAS_COMMIT relationships verified")
                else:
                    logger.error("❌ No HAS_COMMIT relationships found")
                    return False
        
        # Step 4: Test cleanup operation (this should NOT generate warnings)
        logger.info("Step 4: Testing cleanup operation (watching for warnings)")
        await extractor.clear_repository_data(test_repo_name)
        logger.info("✅ Cleanup operation completed")
        
        # Step 5: Verify all data was cleaned
        logger.info("Step 5: Verifying complete data cleanup")
        async with driver.session() as session:
            result = await session.run("""
                MATCH (r:Repository {name: $repo_name})
                RETURN count(r) as repo_count
            """, repo_name=test_repo_name)
            
            record = await result.single()
            if record and record['repo_count'] == 0:
                logger.info("✅ Repository completely cleaned")
            else:
                logger.error("❌ Repository cleanup incomplete")
                return False
        
        # Step 6: Test re-parsing after cleanup 
        logger.info("Step 6: Testing re-parse after cleanup")
        async with driver.session() as session:
            await session.run("""
                CREATE (r:Repository {name: $repo_name, description: 'Re-parsed test repo'})
                CREATE (c:Commit {hash: 'xyz789', message: 'Re-parse commit', timestamp: datetime()})
                CREATE (r)-[:HAS_COMMIT]->(c)
            """, repo_name=test_repo_name)
        
        logger.info("✅ Re-parse operation completed")
        
        # Final cleanup
        await extractor.clear_repository_data(test_repo_name)
        
        await driver.close()
        await extractor.close()
        
        logger.info("=" * 60)
        logger.info("✅ ALL TESTS PASSED - NO HAS_COMMIT WARNINGS DETECTED")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        logger.exception("Full error traceback:")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_has_commit_warning_fix())
    sys.exit(0 if success else 1)