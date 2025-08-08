#!/usr/bin/env python3
"""
Check if the app context is available in the running server.
"""

import asyncio
import aiohttp
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.context import get_app_context

def check_local_context():
    """Check if context is available locally."""
    print("Checking local context...")
    ctx = get_app_context()
    if ctx:
        print(f"✓ Context found: {type(ctx)}")
        print(f"  - Has crawler: {hasattr(ctx, 'crawler') and ctx.crawler is not None}")
        print(f"  - Has database_client: {hasattr(ctx, 'database_client') and ctx.database_client is not None}")
    else:
        print("✗ No context found")

async def check_via_simple_tool():
    """Try to call a simple tool that doesn't require context."""
    url = "http://localhost:8051/mcp/"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    # Try to call get_script_analysis_info which shouldn't require context
    tool_payload = {
        "jsonrpc": "2.0",
        "id": "test-info",
        "method": "tools/call",
        "params": {
            "name": "get_script_analysis_info"
        }
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=tool_payload) as response:
                result = await response.json()
                print(f"Simple tool result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error calling simple tool: {e}")

if __name__ == "__main__":
    check_local_context()
    print("\nTrying simple tool call...")
    asyncio.run(check_via_simple_tool())