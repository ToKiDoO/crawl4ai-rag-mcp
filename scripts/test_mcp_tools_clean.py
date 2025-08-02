#!/usr/bin/env python3
"""
Clean MCP tool test - loads from .env.test and overrides only what's needed
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

async def test_tool_invocation():
    """Test MCP tool calls with stdio transport"""
    
    # Load .env.test but don't override existing env vars
    env_test_path = Path(__file__).parent.parent / ".env.test"
    load_dotenv(env_test_path, override=False)
    
    # Set up environment - start with current environment
    env = os.environ.copy()
    
    # Tell server to use .env.test
    env["USE_TEST_ENV"] = "true"
    
    # Override only what's needed for local testing
    env["TRANSPORT"] = "stdio"
    env["QDRANT_URL"] = "http://localhost:6333"
    env["SEARXNG_URL"] = "http://localhost:8081"
    
    # Server command
    server_command = ["uv", "run", "python", "src/crawl4ai_mcp.py"]
    
    print("=" * 80)
    print("MCP Tool Invocation Testing (STDIO Transport)")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Using .env.test with overrides:")
    print(f"  TRANSPORT=stdio (override)")
    print(f"  QDRANT_URL=http://localhost:6333 (override)")
    print(f"  SEARXNG_URL=http://localhost:8081 (override)")
    print()
    
    # Start MCP server process
    process = await asyncio.create_subprocess_exec(
        *server_command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    # Capture stderr in background
    stderr_lines = []
    async def capture_stderr():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            stderr_line = line.decode().rstrip()
            stderr_lines.append(stderr_line)
            print(f"[STDERR] {stderr_line}")
    
    stderr_task = asyncio.create_task(capture_stderr())
    
    # Tools to test
    tools_to_test = [
        {
            "name": "get_available_sources",
            "args": {},
            "description": "List all sources"
        },
        {
            "name": "scrape_urls", 
            "args": {"url": "https://example.com"},
            "description": "Scrape a test URL"
        },
        {
            "name": "perform_rag_query",
            "args": {"query": "test", "max_results": 3},
            "description": "Test RAG search"
        },
        {
            "name": "search",
            "args": {"query": "test", "num_results": 3},
            "description": "Search for sources"
        }
    ]
    
    successful_tools = 0
    
    try:
        # Wait for server to start and show transport mode
        print("[STARTUP] Waiting for server to start...")
        for i in range(10):  # Wait up to 10 seconds
            await asyncio.sleep(1)
            if any("Transport mode:" in line for line in stderr_lines):
                break
        
        # Check if server started with STDIO
        stdio_started = any("Running with STDIO transport" in line for line in stderr_lines)
        if not stdio_started:
            print("❌ Server did not start with STDIO transport")
            print("\nDiagnostic info:")
            for line in stderr_lines:
                if "Transport mode:" in line or "Using test environment:" in line:
                    print(f"  {line}")
            return False
        
        print("✅ Server started with STDIO transport")
        
        # Send initialization handshake
        print("\n[INIT] Sending initialization request...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        process.stdin.write((json.dumps(init_request) + "\n").encode())
        await process.stdin.drain()
        
        # Wait for initialization response
        try:
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            if not response_line:
                print("[INIT] ❌ No response received")
                return False
                
            init_response = json.loads(response_line.decode().strip())
            print(f"[INIT] ✅ Server initialized: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
            
            # Send initialized notification
            initialized_notif = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            process.stdin.write((json.dumps(initialized_notif) + "\n").encode())
            await process.stdin.drain()
            
        except asyncio.TimeoutError:
            print("[INIT] ❌ Timeout waiting for initialization")
            return False
        except json.JSONDecodeError as e:
            print(f"[INIT] ❌ Invalid JSON: {e}")
            return False
        
        # Test each tool
        print("\nTesting Tools:")
        print("-" * 80)
        
        for i, tool_test in enumerate(tools_to_test):
            print(f"\n[TOOL {i+1}] Testing: {tool_test['name']}")
            print(f"         Description: {tool_test['description']}")
            
            # Create tool call request
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_test["name"],
                    "arguments": tool_test["args"]
                },
                "id": i + 10
            }
            
            # Send request
            process.stdin.write((json.dumps(request) + "\n").encode())
            await process.stdin.drain()
            
            # Wait for response
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                response = json.loads(response_line.decode().strip())
                
                if "result" in response:
                    print(f"[RESULT] ✅ Tool executed successfully")
                    successful_tools += 1
                else:
                    error_msg = response.get('error', {}).get('message', 'Unknown error')
                    print(f"[ERROR] ❌ Tool error: {error_msg}")
                    
            except asyncio.TimeoutError:
                print(f"[ERROR] ❌ Timeout (30s)")
            except json.JSONDecodeError as e:
                print(f"[ERROR] ❌ Invalid JSON: {e}")
        
    finally:
        print("\n[CLEANUP] Terminating server...")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            process.kill()
        
        stderr_task.cancel()
        try:
            await stderr_task
        except asyncio.CancelledError:
            pass
        
        print("\n" + "=" * 80)
        print("Test Summary")
        print("=" * 80)
        print(f"Successful tools: {successful_tools}/{len(tools_to_test)}")
        
        success_rate = (successful_tools / len(tools_to_test)) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("✅ ALL TOOLS WORKING - 100% SUCCESS!")
        elif success_rate >= 75:
            print("✅ Tool invocation testing PASSED")
        else:
            print("❌ Tool invocation testing FAILED")
        
        return success_rate == 100

if __name__ == "__main__":
    success = asyncio.run(test_tool_invocation())
    sys.exit(0 if success else 1)