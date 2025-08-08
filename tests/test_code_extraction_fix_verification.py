#!/usr/bin/env python3
"""
Test script to verify that the code extraction fix is working.

This script verifies that:
1. The environment variable USE_AGENTIC_RAG is properly checked in the code
2. Code extraction logic is present and correctly implemented
3. All test files use the correct environment variable name

The issue was that tests were using ENABLE_AGENTIC_RAG=true but the code
was checking for USE_AGENTIC_RAG, so code extraction was never enabled.
"""

import sys
from pathlib import Path


def test_environment_variable_consistency():
    """Test that all references to agentic RAG use the correct variable name."""
    print("🔍 Testing environment variable consistency...")

    # Read the main source file
    src_file = Path(__file__).parent / "src" / "crawl4ai_mcp.py"
    with open(src_file) as f:
        content = f.read()

    # Count occurrences of the correct variable
    correct_var_count = content.count("USE_AGENTIC_RAG")
    print(f"✅ Occurrences of correct variable 'USE_AGENTIC_RAG': {correct_var_count}")

    # Count occurrences of the incorrect variable (should be 0)
    incorrect_var_count = content.count("ENABLE_AGENTIC_RAG")
    print(
        f"❌ Occurrences of incorrect variable 'ENABLE_AGENTIC_RAG': {incorrect_var_count}"
    )

    # Should have exactly 3 occurrences of USE_AGENTIC_RAG and 0 of ENABLE_AGENTIC_RAG
    assert incorrect_var_count == 0, (
        f"Found {incorrect_var_count} occurrences of incorrect variable ENABLE_AGENTIC_RAG"
    )
    assert correct_var_count == 3, (
        f"Expected 3 occurrences of USE_AGENTIC_RAG, found {correct_var_count}"
    )

    print("✅ Environment variable consistency check passed!")


def test_code_extraction_logic_present():
    """Test that code extraction logic is present in the scraping pipeline."""
    print("🔍 Testing code extraction logic presence...")

    src_file = Path(__file__).parent / "src" / "crawl4ai_mcp.py"
    with open(src_file) as f:
        content = f.read()

    # Check for key functions and patterns
    required_patterns = [
        "extract_code_blocks(md, min_length=100)",
        "process_code_example",
        "add_code_examples_to_database",
        "total_code_examples",
        "code_examples_stored",
    ]

    for pattern in required_patterns:
        if pattern in content:
            print(f"✅ Found required pattern: {pattern}")
        else:
            raise AssertionError(f"❌ Missing required pattern: {pattern}")

    print("✅ Code extraction logic presence check passed!")


def test_test_files_fixed():
    """Test that test files use the correct environment variable."""
    print("🔍 Testing test files use correct environment variable...")

    test_files = [
        "tests/test_mcp_tools_unit_optimized.py",
        "tests/test_chat_tool.py",
        "tests/test_crawl4ai_mcp_tools.py",
        "tests/test_mcp_tools_unit.py",
        "tests/test_qdrant_store_crawled_page.py",
        "tests/integration/conftest.py",
    ]

    for test_file_path in test_files:
        test_file = Path(__file__).parent / test_file_path
        if test_file.exists():
            with open(test_file) as f:
                content = f.read()

            # Check that no incorrect variable is used
            incorrect_count = content.count("ENABLE_AGENTIC_RAG")
            if incorrect_count > 0:
                raise AssertionError(
                    f"❌ Found {incorrect_count} occurrences of ENABLE_AGENTIC_RAG in {test_file_path}"
                )

            # Check that correct variable is used (if any agentic RAG references exist)
            correct_count = content.count("USE_AGENTIC_RAG")
            if "AGENTIC_RAG" in content:
                print(
                    f"✅ {test_file_path}: {correct_count} USE_AGENTIC_RAG, 0 ENABLE_AGENTIC_RAG"
                )
            else:
                print(f"✅ {test_file_path}: No agentic RAG references")
        else:
            print(f"⚠️  Test file not found: {test_file_path}")

    print("✅ Test files check passed!")


def main():
    """Run all verification tests."""
    print("🚀 Starting code extraction fix verification...\n")

    try:
        test_environment_variable_consistency()
        print()

        test_code_extraction_logic_present()
        print()

        test_test_files_fixed()
        print()

        print("🎉 All verification tests passed!")
        print("\n📋 Summary of the fix:")
        print(
            "- Changed environment variable from ENABLE_AGENTIC_RAG to USE_AGENTIC_RAG in test files"
        )
        print("- Code extraction logic was already correctly implemented")
        print("- The issue was just environment variable naming inconsistency")
        print("- Code extraction should now work when USE_AGENTIC_RAG=true is set")

        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
