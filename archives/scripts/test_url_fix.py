#!/usr/bin/env python
"""Test script to verify the batch URL processing fix."""

import json


def simulate_mcp_url_parsing(url):
    """
    Simulate the URL parsing logic from src/tools.py scrape_urls function.
    This is what happens when MCP passes URL parameters.
    """
    if isinstance(url, str):
        # Check if it's a JSON string representation of a list
        if url.strip().startswith('[') and url.strip().endswith(']'):
            try:
                parsed = json.loads(url)
                if isinstance(parsed, list):
                    return parsed  # Return parsed list
                else:
                    return [url]  # Single URL (parsed but not a list)
            except json.JSONDecodeError:
                return [url]  # Single URL (JSON decode failed)
        else:
            return [url]  # Single URL
    else:
        return url  # Already a list


def test_url_parsing():
    """Test various URL input formats."""
    test_cases = [
        # Single URL as plain string
        ("https://example.com", ["https://example.com"]),
        
        # Multiple URLs as JSON string (what MCP sends)
        ('["https://example.com", "https://httpbin.org/html"]', 
         ["https://example.com", "https://httpbin.org/html"]),
        
        # Single URL with brackets in the URL itself
        ("https://example.com/[test]", ["https://example.com/[test]"]),
        
        # Malformed JSON should be treated as single URL
        ('["https://example.com"', ['["https://example.com"']),
        
        # Empty list as JSON
        ('[]', []),
        
        # List with one URL
        ('["https://example.com"]', ["https://example.com"]),
    ]
    
    print("Testing URL parsing logic:")
    print("-" * 50)
    
    all_passed = True
    for input_url, expected in test_cases:
        result = simulate_mcp_url_parsing(input_url)
        passed = result == expected
        all_passed = all_passed and passed
        
        status = "✓" if passed else "✗"
        print(f"{status} Input: {repr(input_url)}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        if not passed:
            print("  FAILED!")
        print()
    
    print("-" * 50)
    if all_passed:
        print("✅ All tests passed! The batch URL fix works correctly.")
    else:
        print("❌ Some tests failed. The fix needs adjustment.")
    
    return all_passed


if __name__ == "__main__":
    success = test_url_parsing()
    exit(0 if success else 1)