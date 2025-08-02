@echo off
REM Test WSL MCP Server Command from Windows

echo Testing WSL access to MCP server...
echo.

echo Test 1: WSL Status
wsl --status
echo.

echo Test 2: UV Version via WSL
wsl --cd /home/krashnicov/crawl4aimcp -- /home/krashnicov/.local/bin/uv --version
echo.

echo Test 3: Python Version via WSL and UV
wsl --cd /home/krashnicov/crawl4aimcp -- /home/krashnicov/.local/bin/uv run python --version
echo.

echo Test 4: Test MCP Server Startup (2 second timeout)
echo Starting MCP server for 2 seconds...
timeout /t 1 /nobreak > nul
wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "timeout 2s /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py 2>&1 | head -10"
echo.

echo Test 5: Using wrapper script
wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "timeout 2s ./run_mcp_server.sh 2>&1 | head -10"
echo.

echo Tests completed!
echo.
echo If all tests passed, use this configuration in %%APPDATA%%\Claude\claude_desktop_config.json:
echo.
echo {
echo   "mcpServers": {
echo     "crawl4ai-rag": {
echo       "command": "wsl",
echo       "args": [
echo         "--cd",
echo         "/home/krashnicov/crawl4aimcp",
echo         "--",
echo         "/home/krashnicov/.local/bin/uv",
echo         "run",
echo         "python",
echo         "src/crawl4ai_mcp.py"
echo       ]
echo     }
echo   }
echo }
pause