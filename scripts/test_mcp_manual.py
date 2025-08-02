#!/usr/bin/env python3
"""
Manual test to check if MCP server responds to stdin input.
"""
import subprocess
import json
import time

# Start the server
print("Starting MCP server...")
process = subprocess.Popen(
    ["uv", "run", "python", "src/crawl4ai_mcp.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env={
        **subprocess.os.environ,
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333"
    }
)

# Give it time to start
print("Waiting for server to initialize...")
time.sleep(3)

# Send a request
request = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
}

print(f"Sending request: {json.dumps(request)}")
process.stdin.write(json.dumps(request) + "\n")
process.stdin.flush()

# Read response
print("Waiting for response...")
try:
    # Try to read a line
    response = process.stdout.readline()
    if response:
        print(f"Response: {response}")
        try:
            data = json.loads(response)
            if "result" in data and "tools" in data["result"]:
                print(f"✅ Success! Found {len(data['result']['tools'])} tools")
            else:
                print("❌ Unexpected response format")
        except json.JSONDecodeError:
            print("❌ Failed to parse JSON response")
    else:
        print("❌ No response received")
        
    # Check stderr for errors
    stderr_output = process.stderr.read()
    if stderr_output:
        print("\nServer stderr output:")
        print(stderr_output)
        
except Exception as e:
    print(f"❌ Error: {e}")
    
finally:
    print("\nTerminating server...")
    process.terminate()
    process.wait()