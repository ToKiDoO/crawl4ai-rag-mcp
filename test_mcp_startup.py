#!/usr/bin/env python
import sys
import os

print("Python executable:", sys.executable, file=sys.stderr)
print("Python version:", sys.version, file=sys.stderr)
print("Current directory:", os.getcwd(), file=sys.stderr)
print("VECTOR_DATABASE:", os.getenv('VECTOR_DATABASE'), file=sys.stderr)

try:
    print("Importing mcp...", file=sys.stderr)
    from fastmcp import FastMCP
    print("FastMCP imported successfully", file=sys.stderr)
    
    print("Creating minimal MCP server...", file=sys.stderr)
    mcp = FastMCP("test-server")
    print("MCP server created", file=sys.stderr)
    
    # Just exit instead of running
    print("Test complete - would run server here", file=sys.stderr)
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)