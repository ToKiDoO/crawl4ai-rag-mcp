#!/usr/bin/env python3
"""
List available MCP tools and their schemas
"""

import asyncio
import json
import subprocess


async def list_mcp_tools():
    """List available MCP tools"""

    # Create MCP request to list tools
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
    }

    # Start MCP server process
    process = subprocess.Popen(
        ["docker", "exec", "-i", "mcp-crawl4ai-dev", "python", "src/crawl4ai_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Send initialization handshake first
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0",
                },
            },
        }

        # Send init request
        init_json = json.dumps(init_request) + "\n"
        process.stdin.write(init_json)
        process.stdin.flush()

        # Read init response
        init_response_line = process.stdout.readline()
        print(f"Init response: {init_response_line.strip()}")

        # Send tools/list request
        request_json = json.dumps(request) + "\n"
        print("Sending tools/list request...")
        process.stdin.write(request_json)
        process.stdin.flush()

        # Close stdin
        process.stdin.close()

        # Read response
        response_line = process.stdout.readline()
        print(f"Tools response: {response_line.strip()}")

        if response_line:
            response = json.loads(response_line)

            if "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                print(f"\nFound {len(tools)} available tools:")

                for tool in tools:
                    print(f"\n📋 Tool: {tool['name']}")
                    print(
                        f"   Description: {tool.get('description', 'No description')}"
                    )

                    if "inputSchema" in tool:
                        schema = tool["inputSchema"]
                        print("   Input Schema:")
                        print(f"     Type: {schema.get('type', 'unknown')}")

                        if "properties" in schema:
                            print("     Properties:")
                            for prop_name, prop_info in schema["properties"].items():
                                prop_type = prop_info.get("type", "unknown")
                                required = prop_name in schema.get("required", [])
                                description = prop_info.get(
                                    "description", "No description"
                                )

                                print(
                                    f"       - {prop_name} ({prop_type}): {description}"
                                )
                                if required:
                                    print("         [REQUIRED]")

                                # Show enum values if present
                                if "enum" in prop_info:
                                    print(
                                        f"         Allowed values: {prop_info['enum']}"
                                    )

                                # Show array item types if present
                                if prop_type == "array" and "items" in prop_info:
                                    items_type = prop_info["items"].get(
                                        "type", "unknown"
                                    )
                                    print(f"         Array items: {items_type}")

                return tools
            print(f"❌ Unexpected tools response format: {response}")
            return []
        stderr_output = process.stderr.read()
        print(f"❌ No response received. Stderr: {stderr_output}")
        return []

    finally:
        # Clean up process
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    print("Listing available MCP tools...")
    asyncio.run(list_mcp_tools())
