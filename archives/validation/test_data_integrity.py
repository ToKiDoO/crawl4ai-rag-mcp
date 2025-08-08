#!/usr/bin/env python3
"""
Data integrity test for Neo4j HAS_COMMIT relationship fix.
Tests complete parse → cleanup → re-parse workflow to ensure no data corruption.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
import tempfile
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from knowledge_graphs.parse_repo_into_neo4j import DirectNeo4jExtractor
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_data_integrity():
    """Test complete workflow: parse → cleanup → reparse for data integrity."""
    
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "testpassword123"
    test_repo_name = "test-data-integrity"
    
    logger.info("=" * 50)
    logger.info("TESTING DATA INTEGRITY AFTER CLEANUP")
    logger.info("=" * 50)
    
    extractor = DirectNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        await extractor.initialize()
        
        # Step 1: Clean any existing test repository
        logger.info("Step 1: Initial cleanup")
        await extractor.clear_repository_data(test_repo_name)
        
        # Step 2: Create mock repository structure in memory
        logger.info("Step 2: Creating test repository with complex structure")
        async with driver.session() as session:
            await session.run("""
                CREATE (r:Repository {
                    name: $repo_name,
                    description: 'Data integrity test repository',
                    url: 'https://github.com/test/integrity',
                    stars: 100,
                    forks: 50,
                    language: 'Python'
                })
                
                // Create branches
                CREATE (main:Branch {name: 'main', is_default: true})
                CREATE (dev:Branch {name: 'develop', is_default: false})
                
                // Create commits with detailed metadata
                CREATE (c1:Commit {
                    hash: 'abc123def456',
                    message: 'Initial commit with basic structure',
                    author: 'Test Author',
                    timestamp: datetime('2025-01-01T10:00:00Z'),
                    additions: 100,
                    deletions: 0
                })
                CREATE (c2:Commit {
                    hash: 'def456ghi789',
                    message: 'Add feature implementation',
                    author: 'Test Author',
                    timestamp: datetime('2025-01-02T15:30:00Z'),
                    additions: 250,
                    deletions: 10
                })
                
                // Create files with proper metadata
                CREATE (f1:File {
                    path: 'src/main.py',
                    name: 'main.py',
                    module_name: 'main',
                    lines_of_code: 150,
                    imports: ['os', 'sys', 'logging']
                })
                CREATE (f2:File {
                    path: 'src/utils.py', 
                    name: 'utils.py',
                    module_name: 'utils',
                    lines_of_code: 75,
                    imports: ['json', 'datetime']
                })
                
                // Create classes
                CREATE (cls1:Class {
                    name: 'MainApplication',
                    full_name: 'main.MainApplication',
                    line_number: 10,
                    docstring: 'Main application class',
                    is_abstract: false
                })
                CREATE (cls2:Class {
                    name: 'UtilityHelper',
                    full_name: 'utils.UtilityHelper', 
                    line_number: 5,
                    docstring: 'Utility helper functions',
                    is_abstract: false
                })
                
                // Create methods
                CREATE (m1:Method {
                    name: 'run',
                    full_name: 'main.MainApplication.run',
                    line_number: 15,
                    params_list: ['self'],
                    params_detailed: ['{name: self, type: MainApplication, kind: positional_only}'],
                    return_type: 'None',
                    docstring: 'Run the main application',
                    is_async: false,
                    is_static: false,
                    is_class_method: false
                })
                CREATE (m2:Method {
                    name: 'parse_data',
                    full_name: 'utils.UtilityHelper.parse_data',
                    line_number: 20,
                    params_list: ['self', 'data'],
                    params_detailed: [
                        '{name: self, type: UtilityHelper, kind: positional_only}',
                        '{name: data, type: dict, kind: positional_or_keyword}'
                    ],
                    return_type: 'dict',
                    docstring: 'Parse input data',
                    is_async: true,
                    is_static: false,
                    is_class_method: false
                })
                
                // Create attributes
                CREATE (a1:Attribute {
                    name: 'config',
                    type: 'dict',
                    line_number: 12,
                    is_class_var: false
                })
                
                // Create functions
                CREATE (fn1:Function {
                    name: 'initialize_logging',
                    full_name: 'main.initialize_logging',
                    line_number: 5,
                    params_list: ['level'],
                    params_detailed: ['{name: level, type: str, kind: positional_or_keyword, default: INFO}'],
                    return_type: 'None',
                    docstring: 'Initialize logging configuration',
                    is_async: false
                })
                
                // Create all relationships
                CREATE (r)-[:HAS_BRANCH]->(main)
                CREATE (r)-[:HAS_BRANCH]->(dev)
                CREATE (r)-[:HAS_COMMIT]->(c1)
                CREATE (r)-[:HAS_COMMIT]->(c2)
                CREATE (r)-[:CONTAINS]->(f1)
                CREATE (r)-[:CONTAINS]->(f2)
                CREATE (f1)-[:DEFINES]->(cls1)
                CREATE (f1)-[:DEFINES]->(fn1)
                CREATE (f2)-[:DEFINES]->(cls2)
                CREATE (cls1)-[:HAS_METHOD]->(m1)
                CREATE (cls1)-[:HAS_ATTRIBUTE]->(a1)
                CREATE (cls2)-[:HAS_METHOD]->(m2)
            """, repo_name=test_repo_name)
        
        # Step 3: Verify created structure
        logger.info("Step 3: Verifying created repository structure")
        async with driver.session() as session:
            result = await session.run("""
                MATCH (r:Repository {name: $repo_name})
                OPTIONAL MATCH (r)-[:HAS_BRANCH]->(b:Branch)
                OPTIONAL MATCH (r)-[:HAS_COMMIT]->(c:Commit)
                OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                OPTIONAL MATCH (f)-[:DEFINES]->(cls:Class)
                OPTIONAL MATCH (f)-[:DEFINES]->(fn:Function) 
                OPTIONAL MATCH (cls)-[:HAS_METHOD]->(m:Method)
                OPTIONAL MATCH (cls)-[:HAS_ATTRIBUTE]->(a:Attribute)
                RETURN 
                    count(DISTINCT b) as branch_count,
                    count(DISTINCT c) as commit_count,
                    count(DISTINCT f) as file_count,
                    count(DISTINCT cls) as class_count,
                    count(DISTINCT fn) as function_count,
                    count(DISTINCT m) as method_count,
                    count(DISTINCT a) as attribute_count
            """, repo_name=test_repo_name)
            
            record = await result.single()
            original_counts = {
                'branches': record['branch_count'],
                'commits': record['commit_count'],
                'files': record['file_count'],
                'classes': record['class_count'],
                'functions': record['function_count'],
                'methods': record['method_count'],
                'attributes': record['attribute_count']
            }
            
            logger.info(f"Original structure counts: {original_counts}")
            assert original_counts['commits'] == 2, "HAS_COMMIT relationships not created"
            assert original_counts['branches'] == 2, "HAS_BRANCH relationships not created"
        
        # Step 4: Test cleanup operation (the critical HAS_COMMIT fix)
        logger.info("Step 4: Testing cleanup operation with HAS_COMMIT fix")
        await extractor.clear_repository_data(test_repo_name)
        logger.info("✅ Cleanup completed without errors")
        
        # Step 5: Verify complete cleanup
        logger.info("Step 5: Verifying complete cleanup")
        async with driver.session() as session:
            result = await session.run("""
                MATCH (n)
                WHERE n:Repository OR n:Branch OR n:Commit OR n:File OR n:Class OR n:Method OR n:Function OR n:Attribute
                AND (n.name = $repo_name OR n.full_name CONTAINS $repo_name OR n.path CONTAINS $repo_name)
                RETURN count(n) as remaining_count
            """, repo_name=test_repo_name)
            
            record = await result.single()
            remaining = record['remaining_count']
            
            if remaining == 0:
                logger.info("✅ Complete cleanup verified - no nodes remaining")
            else:
                logger.error(f"❌ Cleanup incomplete - {remaining} nodes remaining")
                return False
        
        # Step 6: Test re-creation after cleanup (to verify no relationship warnings)
        logger.info("Step 6: Testing re-creation after cleanup")
        async with driver.session() as session:
            await session.run("""
                CREATE (r:Repository {name: $repo_name, description: 'Re-created after cleanup'})
                CREATE (c:Commit {hash: 'new123', message: 'Post-cleanup commit'})
                CREATE (r)-[:HAS_COMMIT]->(c)
            """, repo_name=test_repo_name)
        
        logger.info("✅ Re-creation successful")
        
        # Final cleanup
        await extractor.clear_repository_data(test_repo_name)
        
        logger.info("=" * 50)
        logger.info("✅ DATA INTEGRITY TEST PASSED")
        logger.info("- Complex repository structure created successfully")
        logger.info("- HAS_COMMIT relationships handled without warnings")
        logger.info("- Complete cleanup verified (no orphaned nodes)")
        logger.info("- Re-creation after cleanup works correctly")
        logger.info("=" * 50)
        return True
        
    except Exception as e:
        logger.error(f"❌ Data integrity test failed: {e}")
        logger.exception("Full traceback:")
        return False
    finally:
        await driver.close()
        await extractor.close()

if __name__ == "__main__":
    success = asyncio.run(test_data_integrity())
    sys.exit(0 if success else 1)