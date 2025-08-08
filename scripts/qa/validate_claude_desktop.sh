#!/bin/bash

echo "=== Claude Desktop Integration Validation Script ==="
echo

# Check if running in WSL
if grep -qi microsoft /proc/version; then
    echo "✓ Running in WSL environment"
else
    echo "✗ Not running in WSL - this script is designed for WSL"
fi

# Check Python and UV
echo
echo "Checking Python and UV installation:"
python --version
uv --version

# Check environment files
echo
echo "Checking environment files:"
if [ -f ".env" ]; then
    echo "✓ .env file exists"
    echo "  Transport: $(grep TRANSPORT .env | head -1)"
else
    echo "✗ .env file missing"
fi

if [ -f ".env.test" ]; then
    echo "✓ .env.test file exists"
    echo "  Transport: $(grep TRANSPORT .env.test | head -1)"
else
    echo "✗ .env.test file missing"
fi

# Check Docker services
echo
echo "Checking Docker services:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(NAME|qdrant|searxng|valkey|mcp)"

# Test STDIO mode
echo
echo "Testing STDIO mode:"
echo "Starting MCP server in STDIO mode (press Ctrl+C after seeing 'Running with STDIO transport')..."
echo

# Create test script
cat > test_stdio.py << 'EOF'
import os
import sys
os.environ['USE_TEST_ENV'] = 'true'
sys.path.insert(0, 'src')

# Import and run the MCP server
import crawl4ai_mcp

# The server will run and wait for STDIO input
EOF

# Run test with timeout
timeout 5 uv run python test_stdio.py 2>&1 | grep -E "(Transport mode|Running with STDIO|TRANSPORT|Starting Crawl4AI)"

# Clean up
rm -f test_stdio.py

# Show Claude Desktop configuration
echo
echo "=== Recommended Claude Desktop Configuration ==="
echo
echo "Location: %APPDATA%\\Claude\\claude_desktop_config.json (Windows)"
echo "         ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)"
echo "         ~/.config/Claude/claude_desktop_config.json (Linux)"
echo
cat << 'EOF'
{
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
}
EOF

echo
echo "=== Validation Complete ==="
echo
echo "Next steps:"
echo "1. Ensure Qdrant is running: docker compose up -d qdrant"
echo "2. Copy the configuration above to your Claude Desktop config file"
echo "3. Restart Claude Desktop"
echo "4. Test by asking Claude: 'What MCP tools are available?'"