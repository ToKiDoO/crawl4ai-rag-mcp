#!/usr/bin/env python3
"""
Test script to verify the code extraction search fix.
Created: 2025-01-05
Purpose: Verify that search_code_examples now uses the correct utils_refactored implementation
Context: Fix 4.2.3 - Debug code example search issue
References: mcp_tools_test_results.md

The issue was that search_code_examples was importing from utils.py (Supabase-specific)
instead of utils.py (database adapter pattern).
"""

import sys
from pathlib import Path


def test_import_fix():
    """Test that the correct import is now being used."""
    print("🔍 Testing search_code_examples import fix...")

    # Read the main source file
    src_file = Path(__file__).parent / "src" / "crawl4ai_mcp.py"
    with open(src_file) as f:
        content = f.read()

    # Check for the old incorrect import
    old_import_count = content.count("from utils import search_code_examples")
    print(f"❌ Old import occurrences (should be 0): {old_import_count}")

    # Check for the new correct import
    new_import_count = content.count("from utils import search_code_examples")
    print(f"✅ New import occurrences (should be 2): {new_import_count}")

    # Verify the async calls
    async_call_count = content.count("await search_code_examples_impl(")
    print(f"✅ Async call occurrences (should be 2): {async_call_count}")

    # Check that database parameter is used for code examples search
    # Extract just the search_code_examples function part
    search_code_func_start = content.find("async def search_code_examples(")
    search_code_func_end = content.find("@mcp.tool()", search_code_func_start + 1)
    if search_code_func_end == -1:
        search_code_func_end = len(content)
    search_code_func_content = content[search_code_func_start:search_code_func_end]

    # Count database parameter usage in search_code_examples function
    database_param_in_func = search_code_func_content.count("database=database_client")
    print(
        f"✅ Database parameter usage in search_code_examples (should be 2): {database_param_in_func}"
    )

    # Assertions
    assert old_import_count == 0, f"Found {old_import_count} occurrences of old import"
    assert new_import_count == 2, (
        f"Expected 2 occurrences of new import, found {new_import_count}"
    )
    assert async_call_count == 2, f"Expected 2 async calls, found {async_call_count}"
    assert database_param_in_func == 2, (
        f"Expected 2 database parameter usages in search_code_examples, found {database_param_in_func}"
    )

    print("✅ Import fix verification passed!")


def test_utils_refactored_implementation():
    """Test that utils_refactored has the proper implementation."""
    print("\n🔍 Testing utils_refactored implementation...")

    utils_file = Path(__file__).parent / "src" / "utils.py"
    with open(utils_file) as f:
        content = f.read()

    # Check for the async search_code_examples function
    if "async def search_code_examples(" in content:
        print("✅ Found async search_code_examples in utils_refactored")
    else:
        raise AssertionError(
            "❌ Missing async search_code_examples in utils_refactored"
        )

    # Check that it uses the database adapter pattern
    if "database.search_code_examples(" in content:
        print("✅ Uses database adapter pattern")
    else:
        raise AssertionError("❌ Does not use database adapter pattern")

    # Check for proper parameters
    if "database: VectorDatabase" in content:
        print("✅ Uses VectorDatabase type for database parameter")
    else:
        raise AssertionError("❌ Missing VectorDatabase type for database parameter")

    print("✅ utils_refactored implementation check passed!")


def main():
    """Run all verification tests."""
    print("🚀 Starting code extraction search fix verification...\n")

    try:
        test_import_fix()
        test_utils_refactored_implementation()

        print("\n🎉 All verification tests passed!")
        print("\n📋 Summary of the fix:")
        print("- Changed import from 'utils' to 'utils'")
        print(
            "- Updated function calls to use 'database' parameter instead of 'client'"
        )
        print("- Made function calls async with 'await'")
        print("- Added source_filter parameter to match the new signature")
        print("- Code example search should now work with Qdrant adapter")

        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
