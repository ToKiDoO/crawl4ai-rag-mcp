#!/usr/bin/env python3
"""Simple MCP client to test the server"""

import json
import sys
import asyncio
from typing import Any, Dict

async def send_request(method: str, params: Dict[str, Any] = None):
    """Send a JSON-RPC request to the MCP server via stdio"""
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1
    }
    
    # Write request to stdout
    sys.stdout.write(json.dumps(request) + '\n')
    sys.stdout.flush()
    
    # Read response from stdin
    response_line = sys.stdin.readline()
    if response_line:
        return json.loads(response_line)
    return None

async def test_mcp_server():
    """Test basic MCP server functionality"""
    print("Testing MCP Server...", file=sys.stderr)
    
    # Test 1: Initialize
    print("\n1. Testing initialize...", file=sys.stderr)
    response = await send_request("initialize", {
        "protocolVersion": "2024-11-25",
        "capabilities": {}
    })
    print(f"Response: {json.dumps(response, indent=2)}", file=sys.stderr)
    
    # Test 2: List tools
    print("\n2. Testing tools/list...", file=sys.stderr)
    response = await send_request("tools/list")
    print(f"Available tools: {json.dumps(response, indent=2)}", file=sys.stderr)
    
    # Test 3: Call crawl tool
    print("\n3. Testing crawl tool...", file=sys.stderr)
    response = await send_request("tools/call", {
        "name": "crawl",
        "arguments": {"url": "https://example.com"}
    })
    print(f"Crawl response: {json.dumps(response, indent=2)}", file=sys.stderr)
    
    # Test 4: List stored pages
    print("\n4. Testing list_stored_pages...", file=sys.stderr)
    response = await send_request("tools/call", {
        "name": "list_stored_pages",
        "arguments": {}
    })
    print(f"Stored pages: {json.dumps(response, indent=2)}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(test_mcp_server())