#!/bin/bash
# Test MCP Server in STDIO mode

echo "Testing MCP Server with STDIO transport..."
echo ""

# Check if Qdrant is running
echo "Checking Qdrant status..."
if curl -s http://localhost:6333/healthz | grep -q "healthz check passed"; then
    echo "✓ Qdrant is running"
else
    echo "✗ Qdrant is NOT running. Starting it..."
    docker compose -f docker-compose.test.yml up -d
    sleep 5
fi
echo ""

# Test server startup with USE_TEST_ENV
echo "Starting MCP server with USE_TEST_ENV=true..."
echo "This should use STDIO transport from .env.test"
echo ""

# Create a test input file with initialization
cat > /tmp/mcp_test_input.json << 'EOF'
{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "0.1.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}
{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}, "id": 2}
{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 3}
EOF

# Run the server with test input
echo "Sending initialization and tool list requests..."
USE_TEST_ENV=true timeout 5s /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py < /tmp/mcp_test_input.json 2>&1 | head -50

echo ""
echo "Test completed!"
echo ""
echo "If you see JSON responses above, the server is working correctly with STDIO."
echo "Use this configuration in Claude Desktop:"
echo ""
echo '{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "wsl",
      "args": [
        "--cd",
        "/home/krashnicov/crawl4aimcp",
        "--",
        "bash",
        "-c",
        "USE_TEST_ENV=true /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}'