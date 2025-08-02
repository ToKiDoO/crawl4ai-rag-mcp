#!/bin/bash
# Simple test script for MCP server via stdio

echo "Testing MCP Server via stdio transport..."

# Create a test request
cat << 'EOF' > test_request.json
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-25","capabilities":{}},"id":1}
EOF

echo "Starting MCP server and sending initialize request..."

# Run the server with the test request
/home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py < test_request.json

echo -e "\n\nNow testing tools/list..."

# Create tools list request
cat << 'EOF' > test_tools.json
{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-25","capabilities":{}},"id":1}
{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}
EOF

# Run with multiple requests
/home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py < test_tools.json | jq .