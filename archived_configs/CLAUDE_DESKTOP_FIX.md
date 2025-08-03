# Claude Desktop MCP Server Fix for "spawn uv ENOENT" Error

## Problem
Claude Desktop reports: "MCP crawl4ai: spawn uv ENOENT"

This error occurs because:
- `uv` is installed in the user's local directory (e.g., `/home/krashnicov/.local/bin/`)
- Claude Desktop doesn't have access to user PATH modifications
- The `uv` command cannot be found when spawning the process

## Solutions

### Solution 1: Use Full Path to UV (Recommended)

1. First, find where UV is installed:
```bash
which uv
# Expected output: /home/krashnicov/.local/bin/uv
```

2. Update your Claude Desktop configuration to use the full path:

**For Linux/Mac:**
Edit `~/.config/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "/home/krashnicov/.local/bin/uv",
      "args": ["run", "python", "src/crawl4ai_mcp.py"],
      "cwd": "/home/krashnicov/crawl4aimcp",
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333"
      }
    }
  }
}
```

**For Windows with WSL:**
Edit `%APPDATA%\Claude\claude_desktop_config.json`:
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
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333"
      }
    }
  }
}
```

### Solution 2: Create a Wrapper Script

1. Create a wrapper script that sets up the environment:

```bash
cat > /home/krashnicov/crawl4aimcp/run_mcp_server.sh << 'EOF'
#!/bin/bash
# MCP Server Wrapper Script

# Add UV to PATH
export PATH="/home/krashnicov/.local/bin:$PATH"

# Set working directory
cd /home/krashnicov/crawl4aimcp

# Run the MCP server with UV
exec uv run python src/crawl4ai_mcp.py
EOF

chmod +x /home/krashnicov/crawl4aimcp/run_mcp_server.sh
```

2. Update Claude Desktop configuration to use the wrapper:

**For Linux/Mac:**
```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "/home/krashnicov/crawl4aimcp/run_mcp_server.sh",
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333"
      }
    }
  }
}
```

**For Windows with WSL:**
```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "wsl",
      "args": [
        "--",
        "/home/krashnicov/crawl4aimcp/run_mcp_server.sh"
      ],
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333"
      }
    }
  }
}
```

### Solution 3: Use Python Directly (Alternative)

If UV continues to cause issues, run Python directly:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "python",
      "args": ["src/crawl4ai_mcp.py"],
      "cwd": "/home/krashnicov/crawl4aimcp",
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "PYTHONPATH": "/home/krashnicov/crawl4aimcp"
      }
    }
  }
}
```

Note: This requires all dependencies to be installed in the system Python.

## Testing the Fix

1. **Test UV is accessible:**
```bash
/home/krashnicov/.local/bin/uv --version
```

2. **Test the MCP server starts:**
```bash
cd /home/krashnicov/crawl4aimcp
TRANSPORT=stdio VECTOR_DATABASE=qdrant QDRANT_URL=http://localhost:6333 /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py
```

3. **Restart Claude Desktop** after updating the configuration

4. **Check Claude Desktop logs** for any errors

## Prerequisites

Before starting the MCP server:

1. **Ensure Qdrant is running:**
```bash
docker compose -f docker-compose.test.yml up -d
```

2. **Verify Qdrant is accessible:**
```bash
curl http://localhost:6333/healthz
# Should return: healthz check passed
```

3. **Install dependencies (if not already done):**
```bash
cd /home/krashnicov/crawl4aimcp
/home/krashnicov/.local/bin/uv sync
```

## Troubleshooting

If the error persists:

1. **Check UV installation:**
```bash
ls -la /home/krashnicov/.local/bin/uv
# Should show the UV executable
```

2. **Try running with debug output:**
```bash
TRANSPORT=stdio /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py 2>&1
```

3. **Check file permissions:**
```bash
chmod +x /home/krashnicov/.local/bin/uv
```

4. **Verify Python environment:**
```bash
/home/krashnicov/.local/bin/uv run python --version
# Should show Python 3.11 or 3.12
```

## Additional Notes

- The STDIO transport is required for Claude Desktop communication
- Qdrant must be running on localhost:6333
- The MCP server will output logs to stderr for debugging
- Environment variables can be set in the config or passed via the env property