# Claude Desktop Configuration for Windows with WSL

## Configuration for WSL-based Development

When your development environment is in WSL and you're running Claude Desktop on Windows, use this configuration:

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crawl4ai-rag-qdrant": {
      "command": "wsl",
      "args": [
        "--cd",
        "/home/krashnicov/crawl4aimcp",
        "--",
        "bash",
        "-c",
        "export TRANSPORT=stdio VECTOR_DATABASE=qdrant QDRANT_URL=http://localhost:6333 && /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

## Alternative: Using bash -l for login shell

If the above doesn't work, try this configuration that uses a login shell to ensure all environment variables are loaded:

```json
{
  "mcpServers": {
    "crawl4ai-rag-qdrant": {
      "command": "wsl",
      "args": [
        "--cd",
        "/home/krashnicov/crawl4aimcp",
        "--",
        "bash",
        "-l",
        "-c",
        "uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

## Troubleshooting Steps

1. **Test WSL access from Windows PowerShell**:
   ```powershell
   wsl --cd /home/krashnicov/crawl4aimcp -- ls
   ```

2. **Verify UV is installed in WSL**:
   ```powershell
   wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "source ~/.bashrc && uv --version"
   ```

3. **Test the MCP server directly**:
   ```powershell
   wsl --cd /home/krashnicov/crawl4aimcp -- bash -c "source ~/.bashrc && uv run python src/crawl4ai_mcp.py"
   ```

4. **Check the logs in Claude Desktop**:
   - The stderr logging we added will show:
     - Import success/failures
     - Environment variable values
     - Database configuration
     - Connection details

## Expected Log Output

When working correctly, you should see in Claude Desktop logs:
```
Starting Crawl4AI MCP server...
Importing dependencies...
Basic imports successful
Importing Crawl4AI...
Crawl4AI imported successfully
Loading .env from: /home/krashnicov/crawl4aimcp/.env
.env exists: True
VECTOR_DATABASE: qdrant
QDRANT_URL: http://localhost:6333
Initializing FastMCP server...
Host: 0.0.0.0, Port: 8051
FastMCP server initialized successfully
Main function started
Transport mode: sse
Running with SSE transport
```

## Prerequisites

1. **In WSL**:
   - Qdrant running: `docker compose -f docker-compose.test.yml up -d`
   - Dependencies installed: `uv sync`
   - Environment configured: `.env` file with `VECTOR_DATABASE=qdrant`

2. **In Windows**:
   - Claude Desktop installed
   - WSL2 with Ubuntu (or similar)
   - Docker Desktop with WSL2 backend

## Alternative: Docker-based Configuration

If WSL approach fails, you can run everything in Docker:

```json
{
  "mcpServers": {
    "crawl4ai-rag-docker": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "-v", "//wsl$/Ubuntu/home/krashnicov/crawl4aimcp:/app",
        "-w", "/app",
        "--env-file", ".env",
        "python:3.11",
        "bash", "-c", "pip install uv && uv sync && uv run python src/crawl4ai_mcp.py 2>&1"
      ]
    }
  }
}
```

Note: The volume mount path `//wsl$/Ubuntu/` may need adjustment based on your WSL distribution name.