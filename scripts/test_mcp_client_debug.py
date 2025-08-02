#!/usr/bin/env python3
"""
Basic MCP client connectivity test with debug output.
Tests tool discovery via stdio transport and captures stderr.
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add test utilities to path
sys.path.append(str(Path(__file__).parent.parent / "tests"))
from mcp_test_utils import MCPRequest, MCPResponse

async def test_with_debug():
    """Test basic MCP server connectivity with full debug output"""
    
    # Load .env.test first
    from dotenv import load_dotenv
    env_test_path = Path(__file__).parent.parent / ".env.test"
    load_dotenv(env_test_path, override=True)
    
    # Set up environment - override specific values for stdio testing
    env = os.environ.copy()
    env.update({
        "TRANSPORT": "stdio",  # Override to stdio for this test
        "VECTOR_DATABASE": "qdrant", 
        "QDRANT_URL": "http://localhost:6333",  # Use localhost for local testing
        "SEARXNG_URL": "http://localhost:8080",  # Use localhost for local testing
        "OPENAI_API_KEY": env.get("OPENAI_API_KEY", ""),  # Keep from .env.test
        "MCP_DEBUG": "true"  # Enable debug logging
    })
    
    # Server command
    server_command = [
        "uv", "run", "python", 
        "src/crawl4ai_mcp.py"
    ]
    
    print("Starting MCP server with debug output...")
    print(f"Command: {' '.join(server_command)}")
    print(f"Environment: TRANSPORT={env['TRANSPORT']}, VECTOR_DATABASE={env['VECTOR_DATABASE']}")
    print("=" * 60)
    
    # Start MCP server process
    process = await asyncio.create_subprocess_exec(
        *server_command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    # Read stderr in background
    async def read_stderr():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            print(f"[STDERR] {line.decode().strip()}")
    
    stderr_task = asyncio.create_task(read_stderr())
    
    try:
        # Create and send request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        request_json = json.dumps(request) + "\n"
        
        print(f"\n[CLIENT] Sending: {request_json.strip()}")
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        print("[CLIENT] Waiting for response...")
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(), 
                timeout=30.0  # Increased timeout
            )
            
            if response_line:
                response_json = response_line.decode().strip()
                print(f"\n[CLIENT] Received: {response_json[:200]}...")
                
                # Parse and display tools
                try:
                    response = json.loads(response_json)
                    if "result" in response and "tools" in response["result"]:
                        tools = response["result"]["tools"]
                        print(f"\n✅ Success! Found {len(tools)} tools:")
                        for tool in tools[:5]:  # Show first 5
                            print(f"  - {tool['name']}")
                        if len(tools) > 5:
                            print(f"  ... and {len(tools) - 5} more")
                    else:
                        print("\n❌ Response missing expected fields")
                        print(json.dumps(response, indent=2))
                except json.JSONDecodeError as e:
                    print(f"\n❌ Failed to parse response: {e}")
            else:
                print("\n❌ No response received")
                
        except asyncio.TimeoutError:
            print("\n❌ Timeout waiting for response (30s)")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        # Clean up
        print("\n[CLIENT] Terminating server...")
        process.terminate()
        
        # Give it time to shut down gracefully
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            print("[CLIENT] Force killing server...")
            process.kill()
            await process.wait()
            
        stderr_task.cancel()
        try:
            await stderr_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    asyncio.run(test_with_debug())