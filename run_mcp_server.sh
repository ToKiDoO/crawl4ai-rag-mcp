#!/bin/bash
# MCP Server Wrapper Script for Claude Desktop
# This script ensures UV is in the PATH and runs the MCP server

# Add UV to PATH (adjust this path if UV is installed elsewhere)
export PATH="/home/krashnicov/.local/bin:$PATH"

# Set working directory
cd "$(dirname "$0")"

# Optional: Source .bashrc for any other environment setup
# source ~/.bashrc

# Run the MCP server with UV
# The exec ensures signals are properly forwarded to the Python process
exec uv run python src/crawl4ai_mcp.py