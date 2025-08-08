# Claude Desktop Integration Fix

## Current Situation

- Production Qdrant is running on port 6333
- Test SearXNG is running on port 8081
- The MCP server can use these existing services

## Solution

The test environment (`.env.test`) is already configured correctly:

- `TRANSPORT=stdio` (for Claude Desktop)
- `QDRANT_URL=http://localhost:6333` (using production Qdrant)
- `SEARXNG_URL=http://localhost:8081` (using test SearXNG)

## Testing the Integration

1. **Verify services are running:**

```bash
docker ps | grep -E "(qdrant|searxng)"
```

2. **Test the MCP server locally:**

```bash
export USE_TEST_ENV=true
uv run python src/crawl4ai_mcp.py
```

You should see:

- "Transport mode: stdio"
- "Running with STDIO transport"

3. **Send a test initialization:**

```json
{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "0.1.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}
```

## Claude Desktop Configuration

Use this configuration in `%APPDATA%\Claude\claude_desktop_config.json`:

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

## Troubleshooting

If the MCP server isn't working in Claude Desktop:

1. **Check the OpenAI API key in `.env.test`:**
   - Currently set to `test-mock-key-not-real`
   - You may need to add a real API key for embedding generation

2. **Check service connectivity:**

   ```bash
   curl http://localhost:6333/healthz  # Qdrant
   curl http://localhost:8081/healthz  # SearXNG
   ```

3. **Review logs:**
   - Check Claude Desktop developer console for errors
   - Run the MCP server manually to see detailed output

## Summary

You don't need to run `docker-compose.test.yml` if you're just using the MCP server with Claude Desktop. The existing services (production Qdrant on 6333 and test SearXNG on 8081) are sufficient.
