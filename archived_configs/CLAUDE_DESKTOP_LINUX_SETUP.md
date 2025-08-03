# Claude Desktop MCP Integration Guide - Linux Native

This guide explains how to integrate the Crawl4AI MCP server with Claude Desktop on native Linux systems.

## Prerequisites

- UV package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker or Docker Desktop running
- Project dependencies installed (`uv sync`)
- Qdrant running (`docker compose -f docker-compose.test.yml up -d`)
- Claude Desktop installed on your Linux system

## Configuration

### Step 1: Locate Claude Desktop Config

The configuration file is typically located at:
- `~/.config/Claude/claude_desktop_config.json`
- Or `~/.claude/claude_desktop_config.json`

### Step 2: Configure Claude Desktop

Edit the configuration file with the following:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "/home/krashnicov/.local/bin/uv",
      "args": [
        "run",
        "python",
        "src/crawl4ai_mcp.py"
      ],
      "cwd": "/home/krashnicov/crawl4aimcp",
      "env": {
        "USE_TEST_ENV": "true"
      }
    }
  }
}
```

**Important:** Replace `/home/krashnicov` with your actual home directory path.

### Alternative Configuration (using bash wrapper)

If the above doesn't work, try this configuration:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "bash",
      "args": [
        "-c",
        "cd /home/krashnicov/crawl4aimcp && USE_TEST_ENV=true /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

## Environment Setup

The server uses two configurations:
- `.env` - Production configuration with `TRANSPORT=sse`
- `.env.test` - Claude Desktop configuration with `TRANSPORT=stdio`

The `USE_TEST_ENV=true` environment variable ensures the correct configuration is used.

### Required Environment Variables in .env.test

```env
TRANSPORT=stdio
VECTOR_DATABASE=qdrant
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=your-api-key-here
```

## Testing the Setup

### Step 1: Test the Command Directly

```bash
cd /home/krashnicov/crawl4aimcp
USE_TEST_ENV=true /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py
```

Expected output:
```
Using test environment: /home/krashnicov/crawl4aimcp/.env.test
Transport mode: stdio
Running with STDIO transport
```

### Step 2: Test with the Provided Script

```bash
cd /home/krashnicov/crawl4aimcp
./test_stdio_mode.sh
```

### Step 3: Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the new settings.

## Troubleshooting

### Common Issues

#### 1. "Could not attach to MCP server"
**Problem**: Server configuration or transport mode issue.
**Solutions**:
- Verify `.env.test` has `TRANSPORT=stdio`
- Check that Qdrant is running: `docker ps`
- Ensure the path to UV is correct: `which uv`

#### 2. Permission Denied
**Problem**: Executable permissions missing.
**Solution**: 
```bash
chmod +x /home/krashnicov/.local/bin/uv
chmod +x /home/krashnicov/crawl4aimcp/src/crawl4ai_mcp.py
```

#### 3. Server starts but no tools appear
**Problem**: Qdrant not accessible.
**Solution**:
```bash
# Start Qdrant
docker compose -f docker-compose.test.yml up -d

# Verify it's running
curl http://localhost:6333/healthz
```

### Debugging Steps

1. **Check UV installation**:
   ```bash
   which uv
   uv --version
   ```

2. **Verify Docker/Qdrant status**:
   ```bash
   docker ps
   docker compose -f docker-compose.test.yml ps
   ```

3. **Test the MCP server manually**:
   ```bash
   cd /home/krashnicov/crawl4aimcp
   USE_TEST_ENV=true uv run python src/crawl4ai_mcp.py
   ```

4. **Check Claude Desktop logs**:
   - Look for startup errors
   - Verify the server path is correct

## Using the Wrapper Script

If you prefer, create a wrapper script for easier configuration:

1. Create `/home/krashnicov/crawl4aimcp/run_claude_desktop.sh`:
```bash
#!/bin/bash
cd /home/krashnicov/crawl4aimcp
USE_TEST_ENV=true exec /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py
```

2. Make it executable:
```bash
chmod +x run_claude_desktop.sh
```

3. Use in Claude Desktop config:
```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "/home/krashnicov/crawl4aimcp/run_claude_desktop.sh"
    }
  }
}
```

## Best Practices

1. **Use absolute paths** to avoid path resolution issues
2. **Keep test and production configs separate** using `.env.test`
3. **Test commands in terminal first** before adding to Claude Desktop
4. **Ensure Docker services are running** before starting the MCP server
5. **Check file permissions** if you encounter access issues

## Quick Checklist

- [ ] UV installed and accessible
- [ ] Docker running with Qdrant container
- [ ] `.env.test` exists with `TRANSPORT=stdio`
- [ ] Dependencies installed with `uv sync`
- [ ] Configuration file updated with correct paths
- [ ] Claude Desktop restarted after config changes

## Support

If issues persist:
1. Run the test script: `./test_stdio_mode.sh`
2. Check server logs for detailed error messages
3. Verify all paths are correct for your system
4. Ensure all required services are running