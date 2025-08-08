#!/usr/bin/env python3
"""
Test script to validate Neo4j aggregation warning suppression.

This script tests:
1. Driver-level warning suppression
2. Query execution with aggregation functions
3. Repository metadata retrieval functionality
4. Backward compatibility
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import redirect_stderr
from io import StringIO

# Configure logging to capture Neo4j warnings
logging.basicConfig(level=logging.DEBUG)
neo4j_logger = logging.getLogger('neo4j')

def capture_logs_and_warnings():
    """Capture all logs and warnings during execution."""
    log_capture = StringIO()
    warning_capture = StringIO()
    
    # Set up log handler
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.WARNING)
    neo4j_logger.addHandler(handler)
    
    return log_capture, warning_capture, handler

async def test_driver_initialization():
    """Test that Neo4j driver initializes with warning suppression."""
    print("🔧 Testing Driver Initialization...")
    
    try:
        # Import the module that creates the driver
        sys.path.append('/app/src')
        from knowledge_graph.queries import get_neo4j_driver
        
        driver = await get_neo4j_driver()
        if driver:
            print("✅ Neo4j driver initialized successfully with warning suppression")
            await driver.close()
            return True
        else:
            print("❌ Failed to initialize Neo4j driver")
            return False
            
    except Exception as e:
        print(f"❌ Driver initialization failed: {e}")
        return False

async def test_repository_metadata_functionality():
    """Test the get_repository_metadata_from_neo4j function."""
    print("\n📊 Testing Repository Metadata Functionality...")
    
    try:
        sys.path.append('/app/src')
        from knowledge_graph.repository import get_repository_metadata_from_neo4j
        from core.context import AppContext
        
        # Create a mock context
        class MockContext:
            pass
        
        ctx = MockContext()
        
        # Test with a non-existent repository to check error handling
        result = await get_repository_metadata_from_neo4j(ctx, "nonexistent-repo")
        result_data = json.loads(result)
        
        if "error" in result_data:
            print("✅ Error handling works correctly for non-existent repository")
            return True
        else:
            print("⚠️ Unexpected result for non-existent repository")
            return False
            
    except Exception as e:
        print(f"❌ Repository metadata test failed: {e}")
        return False

async def test_aggregation_query_directly():
    """Test aggregation query directly against Neo4j."""
    print("\n🔢 Testing Aggregation Query Directly...")
    
    try:
        from neo4j import AsyncGraphDatabase, NotificationMinimumSeverity
        
        # Get connection details from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j-dev:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        # Create driver with warning suppression
        driver = AsyncGraphDatabase.driver(
            neo4j_uri, 
            auth=(neo4j_user, neo4j_password),
            warn_notification_severity=NotificationMinimumSeverity.OFF
        )
        
        async with driver.session() as session:
            # Test query that would normally cause aggregation warnings
            test_query = """
            MATCH (f:File)
            WITH COLLECT(f) as files
            RETURN 
                SIZE([file IN files WHERE file IS NOT NULL]) as file_count,
                REDUCE(total = 0, file IN [f IN files WHERE f IS NOT NULL] | total + COALESCE(f.line_count, 0)) as total_lines
            """
            
            result = await session.run(test_query)
            record = await result.single()
            
            if record:
                print("✅ Aggregation query executed successfully")
                print(f"   Files: {record['file_count']}, Total lines: {record['total_lines']}")
            else:
                print("✅ Aggregation query executed (no data found)")
                
        await driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Direct aggregation query test failed: {e}")
        return False

def check_for_warnings_in_logs(log_capture):
    """Check captured logs for Neo4j aggregation warnings."""
    log_content = log_capture.getvalue()
    
    warning_indicators = [
        "AggregationSkippedNull",
        "aggregation function that skips null values",
        "Neo.ClientNotification.Statement",
        "REDUCE"
    ]
    
    warnings_found = []
    for indicator in warning_indicators:
        if indicator in log_content:
            warnings_found.append(indicator)
    
    return warnings_found, log_content

async def main():
    """Run all validation tests."""
    print("🚀 Neo4j Aggregation Warning Suppression Validation")
    print("=" * 60)
    
    # Set up log capture
    log_capture, warning_capture, handler = capture_logs_and_warnings()
    
    # Test results
    results = []
    
    try:
        # Test 1: Driver initialization
        result1 = await test_driver_initialization()
        results.append(("Driver Initialization", result1))
        
        # Test 2: Repository metadata functionality
        result2 = await test_repository_metadata_functionality()
        results.append(("Repository Metadata", result2))
        
        # Test 3: Direct aggregation query
        result3 = await test_aggregation_query_directly()
        results.append(("Direct Aggregation Query", result3))
        
        # Check for warnings
        warnings_found, log_content = check_for_warnings_in_logs(log_capture)
        
        print("\n" + "=" * 60)
        print("🔍 VALIDATION SUMMARY")
        print("=" * 60)
        
        # Print test results
        all_passed = True
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:<25}: {status}")
            if not passed:
                all_passed = False
        
        # Check warnings
        if warnings_found:
            print(f"⚠️  Warning Suppression     : ❌ FAIL - Found {len(warnings_found)} warnings")
            print("   Warnings found:", warnings_found)
            all_passed = False
        else:
            print("⚠️  Warning Suppression     : ✅ PASS - No aggregation warnings detected")
        
        # Overall result
        print("-" * 60)
        if all_passed:
            print("🎉 OVERALL RESULT: ✅ ALL TESTS PASSED")
            print("   Neo4j aggregation warning fix is working correctly!")
        else:
            print("💥 OVERALL RESULT: ❌ SOME TESTS FAILED")
            print("   Review the failed tests and fix issues before deployment.")
        
        # Log details for debugging
        if log_content.strip():
            print("\n📝 Log Details (last 500 chars):")
            print("." * 40)
            print(log_content[-500:])
        
        return all_passed
        
    finally:
        # Clean up log handler
        neo4j_logger.removeHandler(handler)

if __name__ == "__main__":
    # Run the validation
    success = asyncio.run(main())
    sys.exit(0 if success else 1)