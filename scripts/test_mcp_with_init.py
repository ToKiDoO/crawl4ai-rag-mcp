#!/usr/bin/env python3
"""
Test MCP server with proper initialization handshake.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add test utilities to path
sys.path.append(str(Path(__file__).parent.parent / "tests"))

async def test_with_initialization():
    """Test MCP server with proper initialization sequence"""
    
    # Load .env.test first
    from dotenv import load_dotenv
    env_test_path = Path(__file__).parent.parent / ".env.test"
    load_dotenv(env_test_path, override=True)
    
    # Set up environment
    env = os.environ.copy()
    env.update({
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "SEARXNG_URL": "http://localhost:8080",
        "OPENAI_API_KEY": env.get("OPENAI_API_KEY", ""),
        "MCP_DEBUG": "true"
    })
    
    # Server command
    server_command = ["uv", "run", "python", "src/crawl4ai_mcp.py"]
    
    print("Starting MCP server with initialization handshake...")
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
        # Step 1: Send initialization request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test_client",
                    "version": "1.0"
                }
            },
            "id": 1
        }
        
        request_json = json.dumps(init_request) + "\n"
        print(f"\n[CLIENT] Sending initialization: {json.dumps(init_request, indent=2)}")
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        # Read initialization response
        print("[CLIENT] Waiting for initialization response...")
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        
        if response_line:
            response_json = response_line.decode().strip()
            response = json.loads(response_json)
            print(f"\n[CLIENT] Initialization response: {json.dumps(response, indent=2)}")
            
            # Step 2: Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            
            notif_json = json.dumps(initialized_notif) + "\n"
            print(f"\n[CLIENT] Sending initialized notification...")
            process.stdin.write(notif_json.encode())
            await process.stdin.drain()
            
            # Small delay to ensure server processes the notification
            await asyncio.sleep(0.5)
            
            # Step 3: Now send the tools/list request
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            
            tools_json = json.dumps(tools_request) + "\n"
            print(f"\n[CLIENT] Sending tools/list request...")
            process.stdin.write(tools_json.encode())
            await process.stdin.drain()
            
            # Read tools response
            print("[CLIENT] Waiting for tools response...")
            tools_response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            
            if tools_response_line:
                tools_response_json = tools_response_line.decode().strip()
                tools_response = json.loads(tools_response_json)
                
                if "result" in tools_response and "tools" in tools_response["result"]:
                    tools = tools_response["result"]["tools"]
                    print(f"\n✅ Success! Found {len(tools)} tools:")
                    for tool in tools[:10]:
                        print(f"  - {tool['name']}: {tool['description'][:50]}...")
                    if len(tools) > 10:
                        print(f"  ... and {len(tools) - 10} more")
                else:
                    print("\n❌ Response missing expected fields")
                    print(json.dumps(tools_response, indent=2))
            else:
                print("\n❌ No tools response received")
        else:
            print("\n❌ No initialization response received")
            
    except asyncio.TimeoutError:
        print("\n❌ Timeout waiting for response")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
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
    asyncio.run(test_with_initialization())