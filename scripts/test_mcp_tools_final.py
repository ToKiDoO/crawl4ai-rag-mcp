#!/usr/bin/env python3
"""
Final MCP tool test - uses .env.test with temporary stdio modification
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
        # Temporarily modify .env.test to use stdio and localhost
        modified_content = original_content.replace("TRANSPORT=sse", "TRANSPORT=stdio")
        modified_content = modified_content.replace("http://qdrant:6333", "http://localhost:6333")
        modified_content = modified_content.replace("http://searxng:8080", "http://localhost:8081")
        env_test_path.write_text(modified_content)
        
        # Set up environment to use .env.test
        env = os.environ.copy()
        env["USE_TEST_ENV"] = "true"  # This tells server to use .env.test
        
        # Server command
        server_command = ["uv", "run", "python", "src/crawl4ai_mcp.py"]
        
        print("=" * 80)
        print("MCP Tool Invocation Testing (STDIO Transport)")
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
        stderr_lines = []
        async def capture_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                stderr_line = line.decode().rstrip()
                stderr_lines.append(stderr_line)
                if "[STDERR]" not in stderr_line:  # Avoid double prefix
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
                # Show diagnostic info
                print("\nDiagnostic info:")
                for line in stderr_lines:
                    if "Transport mode:" in line or "Using test environment:" in line or "Loading .env from:" in line:
                        print(f"  {line}")
                return False
            
            # Send initialization handshake
            print("[INIT] Sending initialization request...")
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
                # First check if there's any stdout output
                print("[DEBUG] Checking for any stdout output...")
                try:
                    peek = await asyncio.wait_for(process.stdout.read(1), timeout=2.0)
                    if peek:
                        # Put it back and read the line
                        remaining = await process.stdout.readline()
                        response_line = peek + remaining
                    else:
                        response_line = None
                except asyncio.TimeoutError:
                    print("[DEBUG] No stdout output detected")
                    response_line = None
                
                if not response_line:
                    print("[INIT] ❌ No response received")
                    # Check if process is still running
                    if process.returncode is not None:
                        print(f"[DEBUG] Process exited with code: {process.returncode}")
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
    
    finally:
        # Restore original .env.test
        print("\n[CLEANUP] Restoring original .env.test...")
        env_test_path.write_text(original_content)

if __name__ == "__main__":
    success = asyncio.run(test_tool_invocation())
    sys.exit(0 if success else 1)