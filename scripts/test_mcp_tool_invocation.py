#!/usr/bin/env python3
"""
Test MCP tool invocation after initialization.
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
    
    # Load .env.test first with override=True
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
    
    print("=" * 80)
    print("MCP Tool Invocation Testing")
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
    
    # Read stderr in background
    async def read_stderr():
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            print(f"[STDERR] {line.decode().strip()}")
    
    stderr_task = asyncio.create_task(read_stderr())
    
    # Tool test definitions
    tools_to_test = [
        {
            "name": "get_available_sources",
            "args": {},
            "description": "List all sources (no params needed)",
            "expected": "Should return list of sources or empty array"
        },
        {
            "name": "scrape_urls", 
            "args": {"url": "https://example.com"},
            "description": "Scrape a simple test URL",
            "expected": "Should return scraped content"
        },
        {
            "name": "perform_rag_query",
            "args": {"query": "test", "match_count": 3},
            "description": "Test RAG search (may return empty)",
            "expected": "Should return search results or empty array"
        },
        {
            "name": "search",
            "args": {"query": "python programming", "num_results": 2},
            "description": "Test SearXNG search integration",
            "expected": "Should return search results or handle gracefully"
        }
    ]
    
    # Error test scenarios
    error_tests = [
        {
            "name": "invalid_tool_name",
            "request": {
                "name": "non_existent_tool",
                "arguments": {}
            },
            "description": "Test invalid tool name",
            "expected_error": "Tool not found"
        },
        {
            "name": "missing_required_param",
            "request": {
                "name": "scrape_urls",
                "arguments": {}  # Missing 'url' parameter
            },
            "description": "Test missing required parameter",
            "expected_error": "Missing required argument"
        },
        {
            "name": "invalid_param_type",
            "request": {
                "name": "perform_rag_query",
                "arguments": {"query": "test", "max_results": "not_a_number"}
            },
            "description": "Test invalid parameter type",
            "expected_error": "Invalid parameter type"
        }
    ]
    
    results = {
        "successful_tools": [],
        "failed_tools": [],
        "error_tests_passed": [],
        "error_tests_failed": []
    }
    
    try:
        # Step 1: Send initialization request
        print("[INIT] Sending initialization request...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test_tool_client",
                    "version": "1.0"
                }
            },
            "id": 1
        }
        
        request_json = json.dumps(init_request) + "\n"
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        # Read initialization response
        response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        if not response_line:
            print("[ERROR] No initialization response received")
            return results
            
        init_response = json.loads(response_line.decode().strip())
        print(f"[INIT] Response received: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        
        # Step 2: Send initialized notification
        initialized_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        notif_json = json.dumps(initialized_notif) + "\n"
        process.stdin.write(notif_json.encode())
        await process.stdin.drain()
        
        await asyncio.sleep(0.5)  # Let server process notification
        
        print("\n" + "=" * 80)
        print("Testing Tool Invocations")
        print("=" * 80)
        
        # Test each tool
        request_id = 2
        for tool_test in tools_to_test:
            print(f"\n[TEST {request_id-1}] {tool_test['name']}")
            print(f"Description: {tool_test['description']}")
            print(f"Arguments: {json.dumps(tool_test['args'])}")
            
            # Create tool call request
            tool_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_test['name'],
                    "arguments": tool_test['args']
                },
                "id": request_id
            }
            
            # Send request
            tool_json = json.dumps(tool_request) + "\n"
            process.stdin.write(tool_json.encode())
            await process.stdin.drain()
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                if response_line:
                    response_text = response_line.decode().strip()
                    if not response_text:
                        print("❌ ERROR: Empty response received")
                        results["failed_tools"].append({
                            "tool": tool_test['name'],
                            "error": "Empty response"
                        })
                        continue
                        
                    try:
                        response = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        print(f"❌ ERROR: Invalid JSON response: {e}")
                        print(f"Response text: {response_text[:200]}...")
                        results["failed_tools"].append({
                            "tool": tool_test['name'],
                            "error": f"JSON decode error: {e}"
                        })
                        continue
                    
                    if "result" in response:
                        print(f"✅ SUCCESS: Tool executed successfully")
                        # Extract text content if available
                        if isinstance(response["result"], dict) and "content" in response["result"]:
                            content = response["result"]["content"]
                            if isinstance(content, list) and len(content) > 0:
                                text = content[0].get("text", "")
                                print(f"Response preview: {text[:200]}...")
                        results["successful_tools"].append(tool_test['name'])
                    elif "error" in response:
                        print(f"❌ ERROR: {response['error'].get('message', 'Unknown error')}")
                        results["failed_tools"].append({
                            "tool": tool_test['name'],
                            "error": response['error']
                        })
                else:
                    print("❌ ERROR: No response received")
                    results["failed_tools"].append({
                        "tool": tool_test['name'],
                        "error": "No response"
                    })
                    
            except asyncio.TimeoutError:
                print("❌ ERROR: Timeout waiting for response")
                results["failed_tools"].append({
                    "tool": tool_test['name'],
                    "error": "Timeout"
                })
            
            request_id += 1
        
        # Test error scenarios
        print("\n" + "=" * 80)
        print("Testing Error Scenarios")
        print("=" * 80)
        
        for error_test in error_tests:
            print(f"\n[ERROR TEST] {error_test['name']}")
            print(f"Description: {error_test['description']}")
            
            # Create error test request
            error_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": error_test['request'],
                "id": request_id
            }
            
            # Send request
            error_json = json.dumps(error_request) + "\n"
            process.stdin.write(error_json.encode())
            await process.stdin.drain()
            
            # Read response
            try:
                response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
                if response_line:
                    response_text = response_line.decode().strip()
                    if not response_text:
                        print("❌ FAIL: Empty response received")
                        results["error_tests_failed"].append(error_test['name'])
                        continue
                        
                    try:
                        response = json.loads(response_text)
                    except json.JSONDecodeError as e:
                        print(f"❌ FAIL: Invalid JSON response: {e}")
                        results["error_tests_failed"].append(error_test['name'])
                        continue
                    
                    if "error" in response:
                        print(f"✅ PASS: Got expected error response")
                        print(f"Error: {response['error'].get('message', 'Unknown')}")
                        results["error_tests_passed"].append(error_test['name'])
                    else:
                        print(f"❌ FAIL: Expected error but got success")
                        results["error_tests_failed"].append(error_test['name'])
                else:
                    print("❌ FAIL: No response received")
                    results["error_tests_failed"].append(error_test['name'])
                    
            except asyncio.TimeoutError:
                print("❌ FAIL: Timeout (expected error response)")
                results["error_tests_failed"].append(error_test['name'])
            
            request_id += 1
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        print("\n[CLEANUP] Terminating server...")
        process.terminate()
        
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            print("[CLEANUP] Force killing server...")
            process.kill()
            await process.wait()
            
        stderr_task.cancel()
        try:
            await stderr_task
        except asyncio.CancelledError:
            pass
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Successful tools: {len(results['successful_tools'])}/{len(tools_to_test)}")
    for tool in results['successful_tools']:
        print(f"  ✅ {tool}")
    
    if results['failed_tools']:
        print(f"\nFailed tools: {len(results['failed_tools'])}")
        for failure in results['failed_tools']:
            print(f"  ❌ {failure['tool']}: {failure['error']}")
    
    print(f"\nError tests passed: {len(results['error_tests_passed'])}/{len(error_tests)}")
    for test in results['error_tests_passed']:
        print(f"  ✅ {test}")
        
    if results['error_tests_failed']:
        print(f"\nError tests failed: {len(results['error_tests_failed'])}")
        for test in results['error_tests_failed']:
            print(f"  ❌ {test}")
    
    # Overall result
    print("\n" + "=" * 80)
    total_success = len(results['successful_tools']) + len(results['error_tests_passed'])
    total_tests = len(tools_to_test) + len(error_tests)
    success_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"Overall Success Rate: {success_rate:.1f}% ({total_success}/{total_tests})")
    
    if success_rate >= 80:
        print("✅ Tool invocation testing PASSED")
    else:
        print("❌ Tool invocation testing FAILED")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_tool_invocation())
    
    # Exit with appropriate code
    success_rate = (len(results['successful_tools']) + len(results['error_tests_passed'])) / 7 * 100
    sys.exit(0 if success_rate >= 80 else 1)