#!/usr/bin/env python3
"""Simple test to verify MCP server is working"""

import subprocess
import json
import time

def test_mcp_tools():
    """Test MCP server tools via subprocess"""
    
    # Start the MCP server process
    print("Starting MCP server...")
    proc = subprocess.Popen(
        ["/home/krashnicov/.local/bin/uv", "run", "python", "src/crawl4ai_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            "TRANSPORT": "stdio",
            "VECTOR_DATABASE": "qdrant",
            "QDRANT_URL": "http://localhost:6333",
            "SEARXNG_URL": "http://localhost:8081",
            "DEBUG": "true"
        }
    )
    
    # Give it a moment to start
    time.sleep(2)
    
    try:
        # Send initialize request
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-25",
                "capabilities": {}
            },
            "id": 1
        }
        
        print(f"Sending: {json.dumps(request)}")
        proc.stdin.write(json.dumps(request) + '\n')
        proc.stdin.flush()
        
        # Read response
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            print(f"Response: {json.dumps(response, indent=2)}")
            
            # Check if initialization was successful
            if "result" in response:
                print("\n✅ MCP Server initialized successfully!")
                print(f"Server name: {response['result'].get('serverInfo', {}).get('name', 'Unknown')}")
                print(f"Server version: {response['result'].get('serverInfo', {}).get('version', 'Unknown')}")
            else:
                print("\n❌ Server initialization failed")
                
        # List available tools
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        
        print(f"\nListing tools...")
        proc.stdin.write(json.dumps(request) + '\n')
        proc.stdin.flush()
        
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            if "result" in response and "tools" in response["result"]:
                print(f"\n📦 Available tools ({len(response['result']['tools'])}):")
                for tool in response['result']['tools']:
                    print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        # Print stderr if available
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"\nServer stderr:\n{stderr_output}")
    finally:
        # Cleanup
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    test_mcp_tools()