#!/usr/bin/env python3
"""
Test MCP tool invocation with explicit stdio transport.
Tests actual tool calls with minimal parameters.
"""
import asyncio
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Add test utilities to path
sys.path.append(str(Path(__file__).parent.parent / "tests"))

async def test_tool_invocation():
    """Test MCP tool calls after proper initialization"""
    
    # First load the real API key from .env.test
    from dotenv import load_dotenv
    env_test_path = Path(__file__).parent.parent / ".env.test"
    load_dotenv(env_test_path)
    api_key = os.getenv("OPENAI_API_KEY", "sk-test-key")
    
    # Create a temporary .env file for stdio testing
    temp_env_content = f"""TRANSPORT=stdio
VECTOR_DATABASE=qdrant
QDRANT_URL=http://localhost:6333
SEARXNG_URL=http://localhost:8081
OPENAI_API_KEY={api_key}
DEBUG=true
MCP_DEBUG=true
USE_KNOWLEDGE_GRAPH=false
"""
    
    temp_env_path = Path(__file__).parent.parent / ".env.stdio.tmp"
    temp_env_path.write_text(temp_env_content)
    
    # Set up environment
    env = os.environ.copy()
    env["TRANSPORT"] = "stdio"  # Ensure stdio is set
    env["VECTOR_DATABASE"] = "qdrant"
    env["QDRANT_URL"] = "http://localhost:6333"
    env["SEARXNG_URL"] = "http://localhost:8080"
    env["MCP_DEBUG"] = "true"
    
    # Server command - use our stdio wrapper
    server_command = ["uv", "run", "python", "scripts/run_mcp_stdio.py"]
    
    print("=" * 80)
    print("MCP Tool Invocation Testing (STDIO Transport)")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"TRANSPORT: {env.get('TRANSPORT')}")
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
            "name": "get_all_sources",
            "args": {},
            "description": "List all sources (no params needed)"
        },
        {
            "name": "scrape_url", 
            "args": {"url": "https://example.com"},
            "description": "Scrape a simple test URL"
        },
        {
            "name": "perform_rag_query",
            "args": {"query": "test", "max_results": 3},
            "description": "Test RAG search (may return empty)"
        },
        {
            "name": "search_sources",
            "args": {"query": "test", "max_results": 3},
            "description": "Search for sources (tests SearXNG)"
        }
    ]
    
    # Error test cases
    error_tests = [
        {
            "name": "invalid_tool_xyz",
            "args": {},
            "description": "Test invalid tool name",
            "expect_error": True
        },
        {
            "name": "scrape_url",
            "args": {},  # Missing required 'url' param
            "description": "Test missing required param",
            "expect_error": True
        },
        {
            "name": "perform_rag_query",
            "args": {"query": 123, "max_results": "not_a_number"},
            "description": "Test invalid param types",
            "expect_error": True
        }
    ]
    
    successful_tools = 0
    error_tests_passed = 0
    
    try:
        # Wait a bit for server to start
        await asyncio.sleep(2)
        
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
            init_response = json.loads(response_line.decode().strip())
            print(f"[INIT] Response: {json.dumps(init_response, indent=2)}")
            
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
            print("[CRITICAL ERROR] Server did not respond to initialization")
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
            
            print(f"[REQUEST] {json.dumps(request, indent=2)}")
            
            # Send request
            process.stdin.write((json.dumps(request) + "\n").encode())
            await process.stdin.drain()
            
            # Wait for response
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                response = json.loads(response_line.decode().strip())
                print(f"[RESPONSE] {json.dumps(response, indent=2)[:200]}...")
                
                if "result" in response:
                    print(f"[RESULT] ✅ Tool executed successfully")
                    successful_tools += 1
                else:
                    print(f"[ERROR] ❌ Tool returned error: {response.get('error', 'Unknown error')}")
                    
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
        
        # Test error handling
        print("\n\nTesting Error Handling:")
        print("-" * 80)
        
        for i, error_test in enumerate(error_tests):
            print(f"\n[ERROR TEST {i+1}] {error_test['description']}")
            
            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": error_test["name"],
                    "arguments": error_test["args"]
                },
                "id": i + 100
            }
            
            print(f"[REQUEST] {json.dumps(request, indent=2)}")
            
            # Send request
            process.stdin.write((json.dumps(request) + "\n").encode())
            await process.stdin.drain()
            
            # Wait for response
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
                response = json.loads(response_line.decode().strip())
                
                if "error" in response and error_test["expect_error"]:
                    print(f"[RESULT] ✅ Expected error received: {response['error']['message']}")
                    error_tests_passed += 1
                elif "result" in response and not error_test["expect_error"]:
                    print(f"[RESULT] ✅ Success as expected")
                    error_tests_passed += 1
                else:
                    print(f"[RESULT] ❌ Unexpected response type")
                    
            except asyncio.TimeoutError:
                print(f"[ERROR] ❌ Timeout waiting for response")
            except json.JSONDecodeError:
                print(f"[ERROR] ❌ Invalid JSON response")
        
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
        print(f"Error tests passed: {error_tests_passed}/{len(error_tests)}")
        print("\n" + "=" * 80)
        total_tests = len(tools_to_test) + len(error_tests)
        total_passed = successful_tools + error_tests_passed
        success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        print(f"Overall Success Rate: {success_rate:.1f}% ({total_passed}/{total_tests})")
        
        if success_rate >= 80:
            print("✅ Tool invocation testing PASSED")
        else:
            print("❌ Tool invocation testing FAILED")
        
        # Clean up temp env file
        try:
            temp_env_path.unlink()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_tool_invocation())
    sys.exit(0 if success else 1)