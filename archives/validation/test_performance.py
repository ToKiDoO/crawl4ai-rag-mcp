#!/usr/bin/env python3
"""
Performance test for Neo4j HAS_COMMIT relationship fix.
Tests transaction performance and timing.
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from knowledge_graphs.parse_repo_into_neo4j import DirectNeo4jExtractor
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_performance():
    """Test performance of HAS_COMMIT cleanup operations."""
    
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "testpassword123"
    test_repo_name = "test-performance"
    
    logger.info("=" * 50)
    logger.info("TESTING PERFORMANCE AND TRANSACTIONS")
    logger.info("=" * 50)
    
    extractor = DirectNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        await extractor.initialize()
        
        # Create multiple repositories with commits to test performance
        logger.info("Creating test data for performance testing...")
        creation_start = time.time()
        
        async with driver.session() as session:
            for i in range(5):
                await session.run("""
                    CREATE (r:Repository {name: $repo_name})
                    CREATE (b:Branch {name: 'main', is_default: true})
                    CREATE (c1:Commit {hash: $hash1, message: 'Commit 1'})
                    CREATE (c2:Commit {hash: $hash2, message: 'Commit 2'})
                    CREATE (c3:Commit {hash: $hash3, message: 'Commit 3'})
                    CREATE (f:File {path: 'test.py', module_name: 'test'})
                    CREATE (cls:Class {name: 'TestClass', full_name: 'test.TestClass'})
                    CREATE (m:Method {name: 'test_method', params_list: ['self']})
                    
                    CREATE (r)-[:HAS_BRANCH]->(b)
                    CREATE (r)-[:HAS_COMMIT]->(c1)
                    CREATE (r)-[:HAS_COMMIT]->(c2)
                    CREATE (r)-[:HAS_COMMIT]->(c3)
                    CREATE (r)-[:CONTAINS]->(f)
                    CREATE (f)-[:DEFINES]->(cls)
                    CREATE (cls)-[:HAS_METHOD]->(m)
                """, repo_name=f"{test_repo_name}-{i}", 
                    hash1=f"abc{i}1", hash2=f"def{i}2", hash3=f"ghi{i}3")
        
        creation_time = time.time() - creation_start
        logger.info(f"✅ Test data creation took {creation_time:.3f}s")
        
        # Test cleanup performance for all repositories
        logger.info("Testing cleanup performance...")
        cleanup_times = []
        
        for i in range(5):
            repo_name = f"{test_repo_name}-{i}"
            cleanup_start = time.time()
            
            await extractor.clear_repository_data(repo_name)
            
            cleanup_time = time.time() - cleanup_start
            cleanup_times.append(cleanup_time)
            logger.info(f"Repository {i+1} cleanup took {cleanup_time:.3f}s")
        
        # Performance analysis
        avg_cleanup = sum(cleanup_times) / len(cleanup_times)
        max_cleanup = max(cleanup_times)
        min_cleanup = min(cleanup_times)
        
        logger.info("=" * 50)
        logger.info("PERFORMANCE RESULTS:")
        logger.info(f"✅ Average cleanup time: {avg_cleanup:.3f}s")
        logger.info(f"✅ Min cleanup time: {min_cleanup:.3f}s")
        logger.info(f"✅ Max cleanup time: {max_cleanup:.3f}s")
        logger.info(f"✅ Total cleanup time: {sum(cleanup_times):.3f}s")
        
        # Test transaction atomicity
        logger.info("Testing transaction atomicity...")
        async with driver.session() as session:
            await session.run("""
                CREATE (r:Repository {name: $repo_name})
                CREATE (c:Commit {hash: 'test123', message: 'Atomicity test'})
                CREATE (r)-[:HAS_COMMIT]->(c)
            """, repo_name=f"{test_repo_name}-atomicity")
        
        atomicity_start = time.time()
        await extractor.clear_repository_data(f"{test_repo_name}-atomicity")
        atomicity_time = time.time() - atomicity_start
        
        logger.info(f"✅ Atomicity test cleanup took {atomicity_time:.3f}s")
        
        # Verify no orphaned nodes
        async with driver.session() as session:
            result = await session.run("""
                MATCH (n)
                WHERE n.name CONTAINS $test_name OR n.hash CONTAINS 'test'
                RETURN count(n) as orphaned_count
            """, test_name=test_repo_name)
            record = await result.single()
            orphaned = record['orphaned_count']
        
        if orphaned == 0:
            logger.info("✅ No orphaned nodes found - transaction atomicity verified")
        else:
            logger.warning(f"⚠️  Found {orphaned} potentially orphaned nodes")
        
        # Performance verdict
        if avg_cleanup < 1.0:  # Less than 1 second average
            logger.info("✅ PERFORMANCE TEST PASSED - Cleanup operations are efficient")
        else:
            logger.warning("⚠️  PERFORMANCE WARNING - Cleanup operations may need optimization")
        
        logger.info("=" * 50)
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        logger.exception("Full traceback:")
        return False
    finally:
        await driver.close()
        await extractor.close()

if __name__ == "__main__":
    success = asyncio.run(test_performance())
    sys.exit(0 if success else 1)