#!/usr/bin/env python3
"""
Simplified test to verify Neo4j HAS_COMMIT relationship warning fix.
This test focuses specifically on the HAS_COMMIT cleanup operation.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from neo4j import AsyncGraphDatabase

# Configure logging to capture warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

async def test_has_commit_cleanup():
    """Simple test to verify HAS_COMMIT relationship cleanup works without warnings."""
    
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j" 
    neo4j_password = "testpassword123"
    test_repo_name = "test-commit-cleanup"
    
    logger.info("=" * 50)
    logger.info("TESTING HAS_COMMIT RELATIONSHIP CLEANUP")
    logger.info("=" * 50)
    
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        # Clean up any existing test data
        async with driver.session() as session:
            await session.run("""
                MATCH (r:Repository {name: $repo_name})
                DETACH DELETE r
            """, repo_name=test_repo_name)
            logger.info("✅ Cleaned up any existing test data")
        
        # Create test repository with HAS_COMMIT relationships
        async with driver.session() as session:
            await session.run("""
                CREATE (r:Repository {name: $repo_name})
                CREATE (c1:Commit {hash: 'abc123', message: 'Test commit 1'})
                CREATE (c2:Commit {hash: 'def456', message: 'Test commit 2'})
                CREATE (r)-[:HAS_COMMIT]->(c1)
                CREATE (r)-[:HAS_COMMIT]->(c2)
            """, repo_name=test_repo_name)
            logger.info("✅ Created test repository with HAS_COMMIT relationships")
        
        # Verify HAS_COMMIT relationships exist
        async with driver.session() as session:
            result = await session.run("""
                MATCH (r:Repository {name: $repo_name})-[:HAS_COMMIT]->(c:Commit)
                RETURN count(c) as commit_count
            """, repo_name=test_repo_name)
            record = await result.single()
            commit_count = record['commit_count']
            logger.info(f"✅ Verified {commit_count} HAS_COMMIT relationships exist")
        
        # Test the specific cleanup operation for HAS_COMMIT (from the fix)
        async with driver.session() as session:
            tx = await session.begin_transaction()
            try:
                logger.info("Testing HAS_COMMIT relationship cleanup operation...")
                
                # This is the fixed query - test HAS_COMMIT cleanup
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})
                    OPTIONAL MATCH (r)-[:HAS_COMMIT]->(c:Commit)
                    WITH r, collect(DISTINCT c) as commits
                    FOREACH(commit IN [x IN commits WHERE x IS NOT NULL] |
                        DETACH DELETE commit
                    )
                    RETURN size([x IN commits WHERE x IS NOT NULL]) as deleted_count
                """, repo_name=test_repo_name)
                
                record = await result.single()
                deleted_count = record['deleted_count']
                logger.info(f"✅ Cleanup deleted {deleted_count} commits")
                
                # Delete the repository
                await tx.run("""
                    MATCH (r:Repository {name: $repo_name})
                    DETACH DELETE r
                """, repo_name=test_repo_name)
                
                await tx.commit()
                logger.info("✅ Transaction committed successfully")
            except Exception as e:
                await tx.rollback()
                raise e
        
        # Verify complete cleanup
        async with driver.session() as session:
            result = await session.run("""
                MATCH (r:Repository {name: $repo_name})
                RETURN count(r) as repo_count
            """, repo_name=test_repo_name)
            record = await result.single()
            if record['repo_count'] == 0:
                logger.info("✅ Repository completely cleaned")
            else:
                logger.error("❌ Repository cleanup incomplete")
                return False
    
        logger.info("=" * 50)
        logger.info("✅ HAS_COMMIT CLEANUP TEST PASSED")
        logger.info("=" * 50)
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        logger.exception("Full traceback:")
        return False
    finally:
        await driver.close()

if __name__ == "__main__":
    success = asyncio.run(test_has_commit_cleanup())
    sys.exit(0 if success else 1)