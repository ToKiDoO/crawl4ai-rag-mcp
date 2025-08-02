#!/usr/bin/env python3
"""
Run the MCP server with stdio transport for testing.
This script overrides the .env file to force stdio transport.
"""
import os
import sys
from pathlib import Path

# Override environment variables before importing the server
os.environ["TRANSPORT"] = "stdio"

# Load other settings from .env.test
from dotenv import load_dotenv
env_test_path = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_test_path)

# Force stdio transport (override what was in .env.test)
os.environ["TRANSPORT"] = "stdio"

# Now import and run the server
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import after setting environment
from crawl4ai_mcp import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())