#!/usr/bin/env python3
"""
Test which environment variables the MCP server would use
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

print("=== MCP Server Environment Test ===", file=sys.stderr)

# Show current shell environment
print(f"\nShell OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'NOT SET')[:20]}...", file=sys.stderr)

# Simulate MCP server loading (from .env, not .env.test)
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / '.env'
print(f"\nLoading from: {dotenv_path}", file=sys.stderr)
print(f"File exists: {dotenv_path.exists()}", file=sys.stderr)

# Load with override=False (like MCP server does)
load_dotenv(dotenv_path, override=False)

# Show what the MCP server would see
api_key = os.getenv('OPENAI_API_KEY', 'NOT SET')
print(f"\nMCP server would use OPENAI_API_KEY: {api_key[:20]}...", file=sys.stderr)
print(f"Key length: {len(api_key) if api_key != 'NOT SET' else 0}", file=sys.stderr)

# Also check .env.test
env_test_path = project_root / '.env.test'
print(f"\n.env.test exists: {env_test_path.exists()}", file=sys.stderr)

# Show recommendation
print("\n=== Recommendation ===", file=sys.stderr)
if len(api_key) == 56:
    print("❌ MCP server would use the invalid shell environment key", file=sys.stderr)
    print("   Solution: Either unset OPENAI_API_KEY in shell or update MCP to use override=True", file=sys.stderr)
else:
    print("✅ MCP server would use the valid key from .env file", file=sys.stderr)