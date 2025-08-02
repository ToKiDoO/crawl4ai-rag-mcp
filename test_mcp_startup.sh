#!/bin/bash
# Test MCP Server Startup

echo "Testing MCP server startup with full UV path..."
echo "UV location: $(which uv)"
echo ""

# Test 1: UV version
echo "Test 1: UV Version"
/home/krashnicov/.local/bin/uv --version
echo ""

# Test 2: Python version through UV
echo "Test 2: Python Version"
cd /home/krashnicov/crawl4aimcp
/home/krashnicov/.local/bin/uv run python --version
echo ""

# Test 3: Import test
echo "Test 3: Import Test"
/home/krashnicov/.local/bin/uv run python -c "import fastmcp; print('FastMCP imported successfully')"
echo ""

# Test 4: MCP server dry run (will exit immediately but shows if it starts)
echo "Test 4: MCP Server Startup Test"
timeout 2s /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py 2>&1 | head -20
echo ""

echo "Tests completed!"