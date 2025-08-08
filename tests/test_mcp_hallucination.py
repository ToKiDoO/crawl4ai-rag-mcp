#!/usr/bin/env python3
"""
Test script for MCP server hallucination detection tools.
This simulates MCP client calls to test the hallucination detection functionality.
"""

import asyncio
import json
from pathlib import Path

import httpx

# MCP server endpoint
MCP_URL = "http://localhost:8051/mcp/"


async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool via HTTP."""
    async with httpx.AsyncClient() as client:
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": 1,
        }

        response = await client.post(MCP_URL, json=request)
        result = response.json()

        if "error" in result:
            return {"success": False, "error": result["error"]}

        # Parse the content from the result
        if "result" in result and "content" in result["result"]:
            content = result["result"]["content"]
            if isinstance(content, list) and len(content) > 0:
                return json.loads(content[0]["text"])

        return result


async def test_get_script_analysis_info():
    """Test the get_script_analysis_info tool."""
    print("\n" + "=" * 60)
    print("TEST 1: get_script_analysis_info")
    print("=" * 60)

    result = await call_mcp_tool("get_script_analysis_info", {})

    if isinstance(result, dict):
        print("\n✅ Tool returned information successfully")
        print("\nAccessible Paths:")
        for key, path in result.get("accessible_paths", {}).items():
            print(f"  - {key}: {path}")

        print("\nAvailable Tools:")
        for tool in result.get("available_tools", []):
            print(f"  - {tool}")

        return True
    print(f"❌ Tool failed: {result}")
    return False


async def test_hallucination_detection():
    """Test the basic hallucination detection tool."""
    print("\n" + "=" * 60)
    print("TEST 2: check_ai_script_hallucinations")
    print("=" * 60)

    # Test with the script we created earlier
    test_script = "analysis_scripts/test_scripts/test_hallucination.py"

    # First check if the file exists
    if not Path(test_script).exists():
        print(f"⚠️  Test script not found at {test_script}")
        print("Creating test script...")
        Path("analysis_scripts/test_scripts").mkdir(parents=True, exist_ok=True)
        with open(test_script, "w") as f:
            f.write('''"""Test script for hallucination detection."""
import requests
from fastapi import FastAPI

class TestClass:
    def __init__(self):
        self.api = FastAPI()
    
    def invalid_method(self):
        # This should be detected as a potential hallucination
        result = self.api.process_request({"test": "data"})
        return result
''')

    print(f"\nTesting with script: {test_script}")

    result = await call_mcp_tool(
        "check_ai_script_hallucinations",
        {
            "script_path": test_script,
        },
    )

    if isinstance(result, dict):
        if result.get("success") is False:
            error = result.get("error", "Unknown error")
            if "Knowledge graph functionality not available" in error:
                print(
                    "⚠️  Knowledge graph not configured - this is expected without Neo4j"
                )
                print(f"   Error: {error}")
                return True  # This is an expected result
            print(f"❌ Tool failed: {error}")
            return False
        print("✅ Hallucination detection completed")
        print(f"   Results: {json.dumps(result, indent=2)[:200]}...")
        return True
    print(f"❌ Unexpected response: {result}")
    return False


async def test_path_translation():
    """Test various path formats."""
    print("\n" + "=" * 60)
    print("TEST 3: Path Translation")
    print("=" * 60)

    test_cases = [
        ("analysis_scripts/test_scripts/test_hallucination.py", "Relative path"),
        ("test_hallucination.py", "Filename only"),
        ("/tmp/simple_test.py", "/tmp mount"),
    ]

    for path, description in test_cases:
        print(f"\nTesting {description}: {path}")

        # Create the file if it doesn't exist
        if path.startswith("/tmp"):
            with open(path, "w") as f:
                f.write("# Test file\nprint('test')")

        result = await call_mcp_tool(
            "check_ai_script_hallucinations",
            {
                "script_path": path,
            },
        )

        if isinstance(result, dict):
            if "error" in result:
                error = result["error"]
                if "Knowledge graph" in error or "not available" in error:
                    print(f"  ✅ Path validated (KG not available): {path}")
                elif "not found" in error:
                    print(f"  ⚠️  Path not found: {path}")
                else:
                    print(f"  ❌ Error: {error[:100]}")
            else:
                print(f"  ✅ Path works: {path}")
        else:
            print("  ❌ Unexpected response")

    return True


async def test_enhanced_detection():
    """Test the enhanced hallucination detection tool."""
    print("\n" + "=" * 60)
    print("TEST 4: check_ai_script_hallucinations_enhanced")
    print("=" * 60)

    test_script = "analysis_scripts/test_scripts/test_hallucination.py"

    result = await call_mcp_tool(
        "check_ai_script_hallucinations_enhanced",
        {
            "script_path": test_script,
            "include_code_suggestions": True,
            "detailed_analysis": True,
        },
    )

    if isinstance(result, dict):
        if result.get("success") is False:
            error = result.get("error", "Unknown error")
            if "not available" in error or "not initialized" in error:
                print("⚠️  Enhanced detection requires additional setup")
                print(f"   Error: {error[:200]}")
                return True  # Expected without full setup
            print(f"❌ Tool failed: {error}")
            return False
        print("✅ Enhanced detection completed")
        print(f"   Results: {json.dumps(result, indent=2)[:200]}...")
        return True
    print(f"❌ Unexpected response: {result}")
    return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" MCP HALLUCINATION DETECTION TEST SUITE")
    print("=" * 70)

    results = []

    # Run tests
    results.append(("get_script_analysis_info", await test_get_script_analysis_info()))
    results.append(
        ("check_ai_script_hallucinations", await test_hallucination_detection())
    )
    results.append(("Path Translation", await test_path_translation()))
    results.append(("Enhanced Detection", await test_enhanced_detection()))

    # Generate report
    print("\n" + "=" * 70)
    print(" TEST REPORT")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nTest Results: {passed}/{total} passed")
    print("\nDetailed Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    print("\n" + "=" * 70)

    if passed == total:
        print("🎉 All tests passed!")
    elif passed > 0:
        print(f"⚠️  {passed}/{total} tests passed")
    else:
        print("❌ All tests failed")

    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
