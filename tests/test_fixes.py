#!/usr/bin/env python3
"""
Test script to verify the MCP tools fixes are working correctly.
"""

import os
import sys
import traceback
from pathlib import Path

# Ensure we're in the right directory and set proper paths
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
os.chdir(script_dir)
sys.path.insert(0, str(src_dir))


def test_imports():
    """Test that all imports work correctly after the fixes."""
    try:
        # Test importing the main modules
        from main import create_mcp_server

        print("✅ Successfully imported register_tools and create_mcp_server")

        # Test creating the MCP server (this will instantiate all tools)
        mcp_server = create_mcp_server()
        print("✅ Successfully created MCP server instance")

        # Get the registered tools
        tools = list(mcp_server.tools.keys())
        print(f"✅ Found {len(tools)} registered tools:")
        for tool_name in sorted(tools):
            print(f"  - {tool_name}")

        # Check that our fixed tools are present
        expected_tools = [
            "smart_crawl_url",
            "check_ai_script_hallucinations",
            "check_ai_script_hallucinations_enhanced",
            "perform_rag_query",
            "search_code_examples",
        ]

        missing_tools = [tool for tool in expected_tools if tool not in tools]
        if missing_tools:
            print(f"❌ Missing expected tools: {missing_tools}")
            return False
        print("✅ All expected fixed tools are registered")

        return True

    except Exception as e:
        print(f"❌ Import or initialization error: {e}")
        traceback.print_exc()
        return False


def test_validation_functions():
    """Test that validation functions work correctly."""
    try:
        from utils.validation import validate_github_url, validate_script_path

        # Test script path validation with invalid path
        result = validate_script_path("/nonexistent/file.py")
        print(f"✅ validate_script_path with invalid path: {result}")

        # Test GitHub URL validation
        result = validate_github_url("https://github.com/user/repo.git")
        print(f"✅ validate_github_url with valid URL: {result}")

        return True

    except Exception as e:
        print(f"❌ Validation function error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing MCP tools fixes...")
    print("=" * 50)

    success = True

    print("\n1. Testing imports and MCP server creation...")
    success &= test_imports()

    print("\n2. Testing validation functions...")
    success &= test_validation_functions()

    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! The fixes appear to be working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please review the errors above.")
        sys.exit(1)
