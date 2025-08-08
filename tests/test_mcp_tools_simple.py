#!/usr/bin/env python3
"""Simple test script to verify MCP tools fixes."""

import os
import sys
from pathlib import Path

# Add src to path and change working directory
sys.path.insert(0, str(Path(__file__).parent / "src"))
os.chdir(str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")

    try:
        from src.tools import register_tools

        print("✅ src.tools.register_tools imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import register_tools: {e}")
        return False

    try:
        from src.main import create_mcp_server

        print("✅ src.main.create_mcp_server imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import create_mcp_server: {e}")
        return False

    return True


def test_mcp_server_creation():
    """Test MCP server creation and tool registration."""
    print("\nTesting MCP server creation...")

    try:
        from src.main import create_mcp_server
        from src.tools import register_tools

        # Create server
        server = create_mcp_server()
        print("✅ MCP server created successfully")

        # Register tools
        register_tools(server)
        print("✅ Tools registered successfully")

        # Check if tools are registered
        tools = getattr(server, "_tools", {})
        expected_tools = [
            "search",
            "scrape_urls",
            "smart_crawl_url",
            "get_available_sources",
            "perform_rag_query",
            "search_code_examples",
            "check_ai_script_hallucinations",
            "query_knowledge_graph",
            "parse_github_repository",
        ]

        print(f"✅ Found {len(tools)} registered tools")

        missing_tools = []
        for tool_name in expected_tools:
            if tool_name not in tools:
                missing_tools.append(tool_name)

        if missing_tools:
            print(f"❌ Missing tools: {missing_tools}")
            return False
        print("✅ All expected tools are registered")

        return True

    except Exception as e:
        print(f"❌ Error creating MCP server or registering tools: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_smart_crawl_import():
    """Test that smart_crawl_url import is fixed (no infinite recursion)."""
    print("\nTesting smart_crawl_url import fix...")

    try:
        from services.smart_crawl import smart_crawl_url

        print("✅ services.smart_crawl.smart_crawl_url imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import smart_crawl_url: {e}")
        return False
    except Exception as e:
        print(f"❌ Error importing smart_crawl_url: {e}")
        return False


def test_validation_functions():
    """Test that validation functions work correctly."""
    print("\nTesting validation functions...")

    try:
        from utils.validation import validate_github_url, validate_script_path

        # Test script path validation with invalid path
        result = validate_script_path("/nonexistent/path.py")
        if isinstance(result, dict) and not result.get("valid", True):
            print("✅ validate_script_path works correctly for invalid paths")
        else:
            print(f"❌ validate_script_path returned unexpected result: {result}")
            return False

        # Test GitHub URL validation
        result = validate_github_url("https://github.com/user/repo.git")
        if isinstance(result, dict) and result.get("valid", False):
            print("✅ validate_github_url works correctly for valid URLs")
        else:
            print(f"❌ validate_github_url returned unexpected result: {result}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error testing validation functions: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Tools Fix Verification")
    print("=" * 60)

    tests = [
        test_imports,
        test_mcp_server_creation,
        test_smart_crawl_import,
        test_validation_functions,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"❌ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED with exception: {e}")

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
