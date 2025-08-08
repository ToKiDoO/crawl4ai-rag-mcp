# Claude Desktop Final Configuration

## The Working Configuration

Edit `%APPDATA%\Claude\claude_desktop_config.json` and use this configuration:

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

## What This Configuration Does

1. **Uses WSL** to bridge Windows → Linux
2. **Sets `USE_TEST_ENV=true`** which makes the server:
   - Load `.env.test` instead of `.env`
   - Use `TRANSPORT=stdio` (required for Claude Desktop)
   - Keep production `.env` with `TRANSPORT=sse` unchanged
3. **Uses full path to UV** to avoid PATH issues
4. **Runs in correct directory** with `--cd` flag

## Alternative Configurations

### Option 1: With Environment Variables in args

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
        "export USE_TEST_ENV=true && /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

### Option 2: Using env property (if supported by your Claude Desktop version)

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "wsl",
      "args": [
        "--cd",
        "/home/krashnicov/crawl4aimcp",
        "--",
        "/home/krashnicov/.local/bin/uv",
        "run",
        "python",
        "src/crawl4ai_mcp.py"
      ],
      "env": {
        "USE_TEST_ENV": "true"
      }
    }
  }
}
```

## Testing Before Using Claude Desktop

1. **Test the exact command from PowerShell:**

```powershell
wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "USE_TEST_ENV=true /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
```

You should see:

```
Starting Crawl4AI MCP server...
Using test environment: /home/krashnicov/crawl4aimcp/.env.test
Transport mode: stdio
Running with STDIO transport
```

Then send a test JSON-RPC message:

```json
{"jsonrpc": "2.0", "method": "initialize", "params": {"protocolVersion": "0.1.0", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}, "id": 1}
```

2. **Ensure Qdrant is running in WSL:**

```bash
docker compose -f docker-compose.test.yml up -d
```

3. **Verify Qdrant health:**

```bash
curl http://localhost:6333/healthz
```

## Troubleshooting

### If "Could not attach" error persists

1. **Check server starts correctly:**
   - Open PowerShell
   - Run the test command above
   - Look for any error messages
   - Ensure it says "Running with STDIO transport"

2. **Check Claude Desktop logs:**
   - Look for more detailed error messages
   - Check if the server is crashing immediately

3. **Try simplified test:**

```json
{
  "mcpServers": {
    "test-echo": {
      "command": "wsl",
      "args": ["--", "echo", "Hello from WSL"]
    }
  }
}
```

4. **Common issues:**
   - Qdrant not running (server needs it to start)
   - Python dependencies not installed (`uv sync` in WSL)
   - Firewall blocking WSL communication

## Why This Works

- **Production** uses `.env` with `TRANSPORT=sse` for web clients
- **Claude Desktop** uses `.env.test` with `TRANSPORT=stdio` for desktop integration
- **USE_TEST_ENV=true** switches between these configurations
- No need to modify production settings

## Final Steps

1. Copy the configuration above
2. Open `%APPDATA%\Claude\claude_desktop_config.json`
3. Replace the content
4. Save the file
5. Restart Claude Desktop
6. The MCP server should now connect successfully
