#!/usr/bin/env python3
"""Debug script to test batch URL processing issue."""

import json
from typing import Any

def debug_url_parameter_types():
    """Test how different URL parameter types are handled."""
    
    # Simulate what MCP might send
    test_cases = [
        # Single URL as string
        ("https://example.com", "single_url_string"),
        
        # JSON string representation of a list (what MCP sends)
        ('["https://example.com", "https://httpbin.org/html"]', "json_string_list"),
        
        # Actual Python list (what we want internally)
        (["https://example.com", "https://httpbin.org/html"], "python_list"),
    ]
    
    print("Testing URL parameter type handling:")
    print("=" * 60)
    
    for url_param, description in test_cases:
        print(f"\nTest case: {description}")
        print(f"Input: {url_param} (type: {type(url_param).__name__})")
        
        # Current logic from tools.py line 219
        if isinstance(url_param, str):
            if url_param.startswith('[') and url_param.endswith(']'):
                # This might be a JSON string list - try to parse it
                try:
                    parsed = json.loads(url_param)
                    if isinstance(parsed, list):
                        urls = parsed
                        print(f"Parsed as JSON list: {urls}")
                    else:
                        urls = [url_param]  # Single URL
                        print(f"Single URL: {urls}")
                except json.JSONDecodeError:
                    urls = [url_param]  # Single URL
                    print(f"Failed to parse as JSON, treating as single URL: {urls}")
            else:
                urls = [url_param]  # Single URL
                print(f"Single URL: {urls}")
        else:
            urls = url_param  # Assume it's already a list
            print(f"Already a list: {urls}")
        
        print(f"Result: {urls} (type: {type(urls).__name__})")
        print(f"Final URLs for validation: {urls}")

if __name__ == "__main__":
    debug_url_parameter_types()