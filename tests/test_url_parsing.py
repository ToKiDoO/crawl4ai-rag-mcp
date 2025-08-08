#!/usr/bin/env python3
"""
Test script for the _parse_url_input function.

Created: 2025-08-05
Purpose: Validate the URL input parsing functionality for Fix 3 (Array Parameter Handling)
Context: Part of MCP Tools Testing issue resolution to support multiple URL inputs via JSON strings

This script was created to test the smart array parameter handling implementation that allows
the scrape_urls tool to accept both single URLs and arrays of URLs through MCP protocol,
which only supports string parameters.

Related outcomes: See mcp_tools_test_results.md for test results showing successful JSON array parsing
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from crawl4ai_mcp import MCPToolError, _parse_url_input


def test_url_parsing():
    """Test the _parse_url_input function with various inputs."""

    print("Testing _parse_url_input function...")

    # Test 1: Single URL string
    try:
        result = _parse_url_input("https://example.com")
        print(f"✅ Single URL: {result}")
        assert result == ["https://example.com"]
    except Exception as e:
        print(f"❌ Single URL failed: {e}")

    # Test 2: JSON array string
    try:
        result = _parse_url_input('["https://example.com", "https://test.com"]')
        print(f"✅ JSON array: {result}")
        assert result == ["https://example.com", "https://test.com"]
    except Exception as e:
        print(f"❌ JSON array failed: {e}")

    # Test 3: Python list
    try:
        result = _parse_url_input(["https://example.com", "https://test.com"])
        print(f"✅ Python list: {result}")
        assert result == ["https://example.com", "https://test.com"]
    except Exception as e:
        print(f"❌ Python list failed: {e}")

    # Test 4: Invalid scheme
    try:
        result = _parse_url_input("ftp://example.com")
        print(f"❌ Invalid scheme should have failed: {result}")
    except MCPToolError as e:
        print(f"✅ Invalid scheme correctly rejected: {e}")

    # Test 5: Empty input
    try:
        result = _parse_url_input("")
        print(f"❌ Empty input should have failed: {result}")
    except MCPToolError as e:
        print(f"✅ Empty input correctly rejected: {e}")

    # Test 6: Too many URLs
    try:
        large_list = ["https://example.com"] * 101
        result = _parse_url_input(large_list)
        print(f"❌ Too many URLs should have failed: got {len(result)} URLs")
    except MCPToolError as e:
        print(f"✅ Too many URLs correctly rejected: {e}")

    # Test 7: Malformed JSON
    try:
        result = _parse_url_input('["https://example.com"')  # Missing closing bracket
        print(f"❌ Malformed JSON should have failed: {result}")
    except MCPToolError as e:
        print(f"✅ Malformed JSON correctly rejected: {e}")

    print("\nAll tests completed!")


if __name__ == "__main__":
    test_url_parsing()
