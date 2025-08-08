#!/usr/bin/env python3
"""
Simple script to trigger a tool call using the MCP client SDK or HTTP.
"""

import aiohttp
import asyncio
import json

async def test_tool_call():
    """Test calling a tool via HTTP."""
    url = "http://localhost:8051/mcp/"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    # First, create a session
    session_payload = {
        "jsonrpc": "2.0",
        "id": "create-session",
        "method": "session/create",
        "params": {}
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Create session
            async with session.post(url, headers=headers, json=session_payload) as response:
                result = await response.json()
                print(f"Session creation result: {result}")
                
                if 'result' in result and 'session_id' in result['result']:
                    session_id = result['result']['session_id']
                    print(f"Session ID: {session_id}")
                    
                    # Add session ID to headers
                    headers['X-MCP-Session-ID'] = session_id
                    
                    # Now try to call smart_crawl_url
                    tool_payload = {
                        "jsonrpc": "2.0",
                        "id": "test-call",
                        "method": "tools/call",
                        "params": {
                            "name": "smart_crawl_url",
                            "arguments": {
                                "url": "https://example.com",
                                "max_depth": 1,
                                "return_raw_markdown": True
                            }
                        }
                    }
                    
                    async with session.post(url, headers=headers, json=tool_payload) as tool_response:
                        tool_result = await tool_response.json()
                        print(f"Tool call result: {tool_result}")
                else:
                    print("Failed to create session")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tool_call())