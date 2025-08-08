# Claude Desktop MCP Integration Guide

This guide explains how to integrate the Crawl4AI MCP server with Claude Desktop, including common issues and their solutions.

## Prerequisites

### In WSL/Linux

- UV package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker or Docker Desktop running
- Project dependencies installed (`uv sync`)
- Qdrant running (`docker compose -f docker-compose.test.yml up -d`)

### In Windows

- Claude Desktop installed
- WSL2 with Ubuntu (or similar distribution)
- Access to `%APPDATA%\Claude\claude_desktop_config.json`

## Configuration

### Step 1: Verify UV Installation Path

In WSL, check where UV is installed:

```bash
which uv
# Expected output: /home/krashnicov/.local/bin/uv
```

### Step 2: Configure Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` with the following configuration:

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

**Important:** Replace `/home/krashnicov` with your actual WSL username if different.

### Step 3: Understanding the Configuration

- `"command": "wsl"` - Uses Windows Subsystem for Linux to run the server
- `"--cd", "/home/krashnicov/crawl4aimcp"` - Changes to your project directory
- `"USE_TEST_ENV=true"` - Uses `.env.test` which has `TRANSPORT=stdio` (required for Claude Desktop)
- Full path to UV - Avoids PATH issues when spawning from Windows

## Environment Setup

### Production vs Claude Desktop

The MCP server supports two transport modes:

- **SSE (Server-Sent Events)**: Used for web-based production deployments
- **STDIO (Standard I/O)**: Required for Claude Desktop integration

Your setup uses:

- `.env` - Production configuration with `TRANSPORT=sse`
- `.env.test` - Test/Claude Desktop configuration with `TRANSPORT=stdio`

The `USE_TEST_ENV=true` environment variable switches between these configurations.

### Required Environment Variables

Ensure your `.env.test` contains:

```env
TRANSPORT=stdio
VECTOR_DATABASE=qdrant
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-api-key-here
```

## Testing the Setup

### Step 1: Test from PowerShell

```powershell
wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "USE_TEST_ENV=true /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
```

You should see:

```
Using test environment: /home/krashnicov/crawl4aimcp/.env.test
Transport mode: stdio
Running with STDIO transport
```

### Step 2: Test with the Provided Script

In WSL:

```bash
cd /home/krashnicov/crawl4aimcp
./test_stdio_mode.sh
```

### Step 3: Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the new settings.

## Troubleshooting

### Common Errors and Solutions

#### 1. "spawn uv ENOENT"

**Problem**: Claude Desktop cannot find the `uv` command.
**Solution**: Use the full path to UV (e.g., `/home/krashnicov/.local/bin/uv`)

#### 2. "spawn /home/krashnicov/.local/bin/uv ENOENT"

**Problem**: Running Claude Desktop on Windows but using Linux path directly.
**Solution**: Use `wsl` command as shown in the configuration above.

#### 3. "Could not attach to MCP server"

**Problem**: Server is using wrong transport mode (SSE instead of STDIO).
**Solution**: Set `USE_TEST_ENV=true` to use `.env.test` with `TRANSPORT=stdio`.

#### 4. Server starts but no tools appear

**Problem**: Qdrant is not running or not accessible.
**Solution**:

```bash
# In WSL
docker compose -f docker-compose.test.yml up -d
curl http://localhost:6333/healthz
```

### Debugging Steps

1. **Check WSL is working**:

   ```powershell
   wsl --status
   ```

2. **Verify UV installation**:

   ```powershell
   wsl -- /home/krashnicov/.local/bin/uv --version
   ```

3. **Check Docker/Qdrant status**:

   ```powershell
   wsl -- docker ps
   ```

4. **View Claude Desktop logs**:
   - Check for detailed error messages
   - Look for server startup issues

## Alternative Configurations

### Using Environment Variables in Config

Some versions of Claude Desktop support an `env` property:

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

### Using a Wrapper Script

If you prefer, use the provided wrapper script:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "wsl",
      "args": [
        "--cd",
        "/home/krashnicov/crawl4aimcp",
        "--",
        "./run_mcp_server.sh"
      ]
    }
  }
}
```

## Best Practices

1. **Always use full paths** to avoid PATH issues
2. **Keep production and test configs separate** using `.env` and `.env.test`
3. **Test commands in PowerShell first** before adding to Claude Desktop
4. **Ensure Docker services are running** before starting the MCP server
5. **Check logs** when troubleshooting issues

## Support

If you encounter issues not covered here:

1. Check the server logs in stderr output
2. Verify all prerequisites are met
3. Test each component individually
4. Review the MCP server test documentation in `mcp_test.md`
