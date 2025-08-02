#!/usr/bin/env python3
"""
Basic MCP client connectivity test.
Tests tool discovery via stdio transport.
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add test utilities to path
sys.path.append(str(Path(__file__).parent.parent / "tests"))
from mcp_test_utils import MCPTestClient, MCPValidator

async def test_basic_connectivity():
    """Test basic MCP server connectivity and tool discovery"""
    client = MCPTestClient()
    
    # Set up environment
    env = os.environ.copy()
    env.update({
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")
    })
    
    # Server command
    server_command = [
        "uv", "run", "python", 
        "src/crawl4ai_mcp.py"
    ]
    
    print("Testing MCP server connectivity...")
    
    try:
        # Create tool discovery request
        request = client.create_tool_discovery_request()
        print(f"Sending request: {request.to_json()}")
        
        # Send request and get response
        response = await client.send_stdio_request(request, server_command)
        
        if response.is_error():
            print(f"Error response: {response.error}")
            return False
        
        # Validate response
        result = response.result
        errors = MCPValidator.validate_tool_list_response(result)
        
        if errors:
            print("Validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        # Check tools
        tools = result.get('tools', [])
        print(f"\nDiscovered {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description'][:50]}...")
        
        # Success criteria
        if len(tools) >= 10:
            print("\n✅ Test PASSED: Server is responding correctly")
            return True
        else:
            print(f"\n❌ Test FAILED: Expected at least 10 tools, got {len(tools)}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_connectivity())
    sys.exit(0 if success else 1)