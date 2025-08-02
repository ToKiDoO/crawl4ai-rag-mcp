#!/usr/bin/env python3
"""
Test MCP initialization handshake.
"""
import subprocess
import json
import time
from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env.test
env_test_path = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_test_path, override=True)

# Start the server
print("Starting MCP server...")
env = os.environ.copy()
env.update({
    "TRANSPORT": "stdio",
    "VECTOR_DATABASE": "qdrant",
    "QDRANT_URL": "http://localhost:6333",
    "SEARXNG_URL": "http://localhost:8080",
})

process = subprocess.Popen(
    ["uv", "run", "python", "src/crawl4ai_mcp.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env
)

# Give it time to start
print("Waiting for server to initialize...")
time.sleep(2)

# Try initialize request first
print("\nTrying initialize request...")
init_request = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "0.1.0",
        "capabilities": {
            "roots": {}
        },
        "clientInfo": {
            "name": "test-client",
            "version": "0.1.0"
        }
    },
    "id": 1
}

print(f"Sending: {json.dumps(init_request)}")
process.stdin.write(json.dumps(init_request) + "\n")
process.stdin.flush()

# Try to read response
print("Waiting for initialize response...")
try:
    response = process.stdout.readline()
    if response:
        print(f"Response: {response}")
        
        # Now try tools/list
        print("\nTrying tools/list request...")
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2
        }
        
        print(f"Sending: {json.dumps(tools_request)}")
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        response = process.stdout.readline()
        if response:
            print(f"Response: {response[:200]}...")
            data = json.loads(response)
            if "result" in data and "tools" in data["result"]:
                print(f"✅ Success! Found {len(data['result']['tools'])} tools")
        else:
            print("❌ No tools/list response")
    else:
        print("❌ No initialize response")
        
except Exception as e:
    print(f"❌ Error: {e}")
    
finally:
    # Check stderr
    stderr = process.stderr.read()
    if stderr:
        print("\nServer stderr (last 20 lines):")
        lines = stderr.strip().split('\n')
        for line in lines[-20:]:
            print(f"  {line}")
    
    print("\nTerminating server...")
    process.terminate()
    process.wait()