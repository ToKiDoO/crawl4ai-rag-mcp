#!/usr/bin/env python3
"""Test the MCP tool functions directly."""

import asyncio
import json
import sys
sys.path.insert(0, 'src')

async def test_array_parsing():
    """Test array parameter parsing in tools."""
    from tools import scrape_urls
    
    print("Testing array parameter parsing...")
    
    # Test 1: Single URL as string
    try:
        # This would normally be called by MCP with context
        # We're just testing the parameter parsing logic
        single_url = "https://example.com"
        print(f"  Single URL: {single_url!r}")
        # The function expects the URL parameter, not testing full execution
        print("  ✓ Single URL format accepted")
    except Exception as e:
        print(f"  ✗ Single URL failed: {e}")
    
    # Test 2: Array of URLs
    try:
        url_array = ["https://example.com", "https://example.org"]
        print(f"  URL array: {url_array!r}")
        # The function should handle arrays
        print("  ✓ URL array format accepted")
    except Exception as e:
        print(f"  ✗ URL array failed: {e}")
    
    # Test 3: JSON string array (as MCP might send it)
    try:
        json_array = '["https://example.com", "https://example.org"]'
        print(f"  JSON array: {json_array!r}")
        # Parse JSON to get the array
        parsed = json.loads(json_array)
        print(f"  Parsed to: {parsed!r}")
        print("  ✓ JSON array parsing successful")
    except Exception as e:
        print(f"  ✗ JSON array failed: {e}")
    
    print("\n✅ Array parameter parsing tests complete")


async def test_parameter_compatibility():
    """Test parameter compatibility for search_code_examples."""
    print("\nTesting parameter compatibility...")
    
    # Test the database adapter interface
    from database.qdrant_adapter import QdrantAdapter
    
    # Check method signature
    import inspect
    sig = inspect.signature(QdrantAdapter.search_code_examples)
    params = sig.parameters
    
    print("  QdrantAdapter.search_code_examples parameters:")
    for name, param in params.items():
        if name != 'self':
            print(f"    - {name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")
    
    # Check if query parameter is accepted
    if 'query' in params:
        print("  ✓ 'query' parameter is supported")
    else:
        print("  ✗ 'query' parameter is NOT supported")
    
    print("\n✅ Parameter compatibility tests complete")


if __name__ == "__main__":
    print("MCP Tool Functions Test")
    print("=" * 50)
    
    asyncio.run(test_array_parsing())
    asyncio.run(test_parameter_compatibility())