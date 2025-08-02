#!/usr/bin/env python3
"""
Test MCP tool invocation with stdio transport using .env.test.
This version temporarily modifies .env.test to use stdio transport.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

async def test_tool_invocation():
    """Test MCP tool calls with stdio transport"""
    
    # Path to .env.test
    env_test_path = Path(__file__).parent.parent / ".env.test"
    
    # Read original content
    original_content = env_test_path.read_text()
    
    try:
        # Temporarily modify .env.test to use stdio
        modified_content = original_content.replace("TRANSPORT=sse", "TRANSPORT=stdio")
        env_test_path.write_text(modified_content)
        
        # Set up environment to use .env.test
        env = os.environ.copy()
        env["USE_TEST_ENV"] = "true"
        
        # Server command
        server_command = ["uv", "run", "python", "src/crawl4ai_mcp.py"]
        
        print("=" * 80)
        print("MCP Tool Invocation Testing (STDIO Transport via .env.test)")
        print("=" * 80)
        print(f"Started at: {datetime.now().isoformat()}")
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
        async def capture_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                print(f"[STDERR] {line.decode().rstrip()}")
        
        stderr_task = asyncio.create_task(capture_stderr())
        
        # Tools to test
        tools_to_test = [
            {
                "name": "get_available_sources",
                "args": {},
                "description": "List all sources (no params needed)"
            },
            {
                "name": "scrape_urls", 
                "args": {"url": "https://example.com"},
                "description": "Scrape a simple test URL"
            },
            {
                "name": "perform_rag_query",
                "args": {"query": "test", "max_results": 3},
                "description": "Test RAG search (may return empty)"
            },
            {
                "name": "search",
                "args": {"query": "test", "num_results": 3},
                "description": "Search for sources (tests SearXNG)"
            }
        ]
        
        successful_tools = 0
        
        try:
            # Wait a bit for server to start
            await asyncio.sleep(2)
            
            # Check if there's any initial output
            try:
                initial_output = await asyncio.wait_for(process.stdout.read(100), timeout=0.5)
                if initial_output:
                    print(f"[DEBUG] Initial stdout output: {initial_output.decode()}")
            except asyncio.TimeoutError:
                print("[DEBUG] No initial stdout output")
            
            # Send initialization handshake
            print("[INIT] Sending initialization request...")
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
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
                if response_line:
                    print(f"[DEBUG] Raw response: {response_line.decode().strip()}")
                    init_response = json.loads(response_line.decode().strip())
                    print(f"[INIT] Response received")
                    print(f"[INIT] Server name: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
                else:
                    print("[INIT] ❌ Empty response received")
                
                # Send initialized notification
                initialized_notif = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                process.stdin.write((json.dumps(initialized_notif) + "\n").encode())
                await process.stdin.drain()
                
                print("[INIT] ✅ Initialization complete")
                print()
                
            except asyncio.TimeoutError:
                print("[INIT] ❌ Timeout waiting for initialization response")
                return False
            
            # Test each tool
            print("Testing Tools:")
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
                        # Show first 200 chars of result
                        result_text = json.dumps(response["result"])[:200]
                        print(f"[RESULT] {result_text}...")
                        successful_tools += 1
                    else:
                        print(f"[ERROR] ❌ Tool returned error: {response.get('error', {}).get('message', 'Unknown error')}")
                        
                except asyncio.TimeoutError:
                    print(f"[ERROR] ❌ Timeout waiting for response")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] ❌ Invalid JSON response: {e}")
                    # Try to read any additional output
                    try:
                        extra = await asyncio.wait_for(process.stdout.read(1000), timeout=1.0)
                        print(f"[DEBUG] Extra output: {extra.decode()[:200]}...")
                    except:
                        pass
            
            return True
            
        except Exception as e:
            print(f"\n[CRITICAL ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            print("\n[CLEANUP] Terminating server...")
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                print("[CLEANUP] Force killing server...")
                process.kill()
            
            # Cancel stderr task
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass
            
            print("\n" + "=" * 80)
            print("Test Summary")
            print("=" * 80)
            print(f"Successful tools: {successful_tools}/{len(tools_to_test)}")
            
            success_rate = (successful_tools / len(tools_to_test)) * 100 if len(tools_to_test) > 0 else 0
            print(f"Success Rate: {success_rate:.1f}%")
            
            if success_rate >= 75:
                print("✅ Tool invocation testing PASSED")
            else:
                print("❌ Tool invocation testing FAILED")
    
    finally:
        # Restore original .env.test
        print("\n[CLEANUP] Restoring original .env.test...")
        env_test_path.write_text(original_content)

if __name__ == "__main__":
    success = asyncio.run(test_tool_invocation())
    sys.exit(0 if success else 1)