# Claude Desktop MCP Integration - Troubleshooting Summary

## Quick Fix

If you're getting errors connecting Claude Desktop to the MCP server in WSL, use this configuration in `%APPDATA%\Claude\claude_desktop_config.json`:

```json
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
```

**Note:** Replace `/home/krashnicov` with your WSL username.

## Common Errors and Solutions

### Error 1: "spawn uv ENOENT"

**Cause**: Claude Desktop can't find the `uv` command  
**Solution**: Use full path to UV (e.g., `/home/krashnicov/.local/bin/uv`)

### Error 2: "spawn /home/krashnicov/.local/bin/uv ENOENT"

**Cause**: Windows can't access WSL paths directly  
**Solution**: Use `wsl` command as shown in the configuration above

### Error 3: "Could not attach to MCP server"

**Cause**: Server is using wrong transport (SSE instead of STDIO)  
**Solution**: Set `USE_TEST_ENV=true` to use `.env.test` with `TRANSPORT=stdio`

## Key Points

1. **Claude Desktop requires STDIO transport** - not SSE
2. **Windows needs `wsl` to access WSL** - can't use Linux paths directly
3. **Use `.env.test` for Claude Desktop** - keeps production config separate
4. **Full paths avoid PATH issues** - specify exact location of UV

## Testing

Before using Claude Desktop, test the command:

```powershell
wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "USE_TEST_ENV=true /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
```

You should see:

```
Using test environment: /home/krashnicov/crawl4aimcp/.env.test
Transport mode: stdio
Running with STDIO transport
```

## Prerequisites

1. Qdrant running: `docker compose -f docker-compose.test.yml up -d`
2. Dependencies installed: `uv sync`
3. `.env.test` exists with `TRANSPORT=stdio`
4. WSL2 installed and working

## Success

Once configured correctly, Claude Desktop will successfully connect to your MCP server running in WSL, allowing you to use all the Crawl4AI RAG tools directly from Claude Desktop.
