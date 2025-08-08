#!/usr/bin/env python3
"""Test script to verify MCP tools are working correctly."""

import asyncio
import json
import httpx


async def test_mcp_tools():
    """Test the MCP tools via HTTP API."""
    base_url = "http://localhost:8051/mcp"
    
    async with httpx.AsyncClient() as client:
        # Test 1: List available tools
        print("Testing list tools...")
        response = await client.post(
            f"{base_url}/",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 1
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Found {len(result.get('result', {}).get('tools', []))} tools")
            
            # Check if our problematic tools are present
            tools = result.get('result', {}).get('tools', [])
            tool_names = [tool['name'] for tool in tools]
            
            if 'scrape_urls' in tool_names:
                print("✓ scrape_urls tool is registered")
            else:
                print("✗ scrape_urls tool is NOT registered")
                
            if 'search_code_examples' in tool_names:
                print("✓ search_code_examples tool is registered")
            else:
                print("✗ search_code_examples tool is NOT registered")
        else:
            print(f"✗ Failed to list tools: {response.status_code}")
            
        # Test 2: Test scrape_urls with array parameter
        print("\nTesting scrape_urls with array parameter...")
        response = await client.post(
            f"{base_url}/",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "scrape_urls",
                    "arguments": {
                        "url": ["https://example.com", "https://example.org"],
                        "return_raw_markdown": True
                    }
                },
                "id": 2
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                print(f"✗ scrape_urls failed: {result['error']}")
            else:
                print("✓ scrape_urls succeeded with array parameter")
                # Parse the content to check if it worked
                try:
                    content = json.loads(result.get('result', {}).get('content', [{}])[0].get('text', '{}'))
                    if content.get('success'):
                        print(f"  - Processed {content.get('total_urls', 0)} URLs")
                except:
                    pass
        else:
            print(f"✗ scrape_urls request failed: {response.status_code}")
            
        # Test 3: Test search_code_examples
        print("\nTesting search_code_examples...")
        response = await client.post(
            f"{base_url}/",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_code_examples",
                    "arguments": {
                        "query": "test query",
                        "match_count": 5
                    }
                },
                "id": 3
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'error' in result:
                print(f"✗ search_code_examples failed: {result['error']}")
            else:
                print("✓ search_code_examples succeeded")
        else:
            print(f"✗ search_code_examples request failed: {response.status_code}")


if __name__ == "__main__":
    print("MCP Tools Test Script")
    print("=" * 50)
    asyncio.run(test_mcp_tools())
    print("\nTest complete!")