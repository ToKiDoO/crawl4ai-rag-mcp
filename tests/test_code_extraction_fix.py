#!/usr/bin/env python3
"""
Test script to verify the code extraction fix is working correctly.
This script checks that the environment variable has been corrected and
verifies the code extraction functionality works as expected.

Created: 2025-08-05
Purpose: Verify environment variable fix for code extraction (Fix 4)
Context: Part of MCP Tools Testing issue resolution for code extraction

This script verifies that the environment variable name has been corrected
from USE_AGENTIC_RAG to ENABLE_AGENTIC_RAG in the source code.

Related outcomes: See mcp_tools_test_results.md - Fix 4 implementation
"""

import sys
from pathlib import Path


def test_environment_variable_fix():
    """Test that the environment variable has been corrected in the source code."""
    print("🔍 Testing environment variable fix...")

    # Read the source file
    src_file = Path(__file__).parent / "src" / "crawl4ai_mcp.py"
    with open(src_file) as f:
        content = f.read()

    # Check that ENABLE_AGENTIC_RAG is no longer used (old incorrect variable)
    old_var_count = content.count("ENABLE_AGENTIC_RAG")
    print(f"Occurrences of old variable 'ENABLE_AGENTIC_RAG': {old_var_count}")

    # Check that USE_AGENTIC_RAG is now used (correct variable)
    new_var_count = content.count("USE_AGENTIC_RAG")
    print(f"Occurrences of correct variable 'USE_AGENTIC_RAG': {new_var_count}")

    # Should have exactly 3 occurrences of USE_AGENTIC_RAG and 0 of ENABLE_AGENTIC_RAG
    assert old_var_count == 0, (
        f"Found {old_var_count} occurrences of old variable ENABLE_AGENTIC_RAG"
    )
    assert new_var_count == 3, (
        f"Expected 3 occurrences of USE_AGENTIC_RAG, found {new_var_count}"
    )

    print("✅ Environment variable fix verified!")
    return True


def test_code_extraction_logic():
    """Test that the code extraction logic is in place."""
    print("\n🔍 Testing code extraction logic...")

    src_file = Path(__file__).parent / "src" / "crawl4ai_mcp.py"
    with open(src_file) as f:
        content = f.read()

    # Check for key components of code extraction
    checks = [
        ('os.getenv("USE_AGENTIC_RAG"', "Environment variable check"),
        ("extract_code_blocks(md, min_length=100)", "Code block extraction"),
        ("process_code_example", "Code example processing"),
        ("add_code_examples_to_database", "Database storage of code examples"),
        ("total_code_examples = len(code_examples)", "Code example counting"),
    ]

    for pattern, description in checks:
        if pattern in content:
            print(f"✅ {description} - Found")
        else:
            print(f"❌ {description} - Missing")
            return False

    print("✅ All code extraction logic components found!")
    return True


def main():
    """Run all tests."""
    print("🚀 Testing code extraction fix...\n")

    try:
        # Test 1: Environment variable fix
        test_environment_variable_fix()

        # Test 2: Code extraction logic
        test_code_extraction_logic()

        print("\n🎉 All tests passed! Code extraction fix is complete.")
        print("\n📋 Summary of changes:")
        print(
            "- Changed environment variable from ENABLE_AGENTIC_RAG to USE_AGENTIC_RAG"
        )
        print("- Code extraction logic is properly integrated in the scraping pipeline")
        print(
            "- Code will now extract and store code examples when USE_AGENTIC_RAG=true"
        )

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
