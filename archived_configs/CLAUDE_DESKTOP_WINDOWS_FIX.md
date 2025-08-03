# Claude Desktop Windows Configuration Fix

## Problem
You're running Claude Desktop on Windows, but your MCP server is in WSL. The error "spawn /home/krashnicov/.local/bin/uv ENOENT" occurs because Windows cannot directly access WSL paths.

## Solution

Edit your Claude Desktop configuration at `%APPDATA%\Claude\claude_desktop_config.json`:

### Option 1: Using WSL with Full UV Path (Recommended)

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
      ]
    }
  }
}
```

### Option 2: Using WSL with Bash -c

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
        "TRANSPORT=stdio VECTOR_DATABASE=qdrant QDRANT_URL=http://localhost:6333 /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

### Option 3: Using the Wrapper Script

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

### Option 4: Using WSL with Environment Variables

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
        "export PATH=/home/krashnicov/.local/bin:$PATH && export TRANSPORT=stdio && export VECTOR_DATABASE=qdrant && export QDRANT_URL=http://localhost:6333 && uv run python src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

## How to Apply the Fix

1. **Open the configuration file:**
   - Press `Win + R`
   - Type `%APPDATA%\Claude\claude_desktop_config.json`
   - Press Enter

2. **Replace the content** with one of the options above

3. **Save the file** and restart Claude Desktop

## Testing the Configuration

1. **Test from Windows PowerShell:**
```powershell
wsl --cd /home/krashnicov/crawl4aimcp -- /home/krashnicov/.local/bin/uv --version
```

2. **Test the full command:**
```powershell
wsl --cd /home/krashnicov/crawl4aimcp -- /home/krashnicov/.local/bin/uv run python --version
```

3. **Test with the wrapper script:**
```powershell
wsl --cd /home/krashnicov/crawl4aimcp -- ./run_mcp_server.sh
```

## Prerequisites

Before using the MCP server:

1. **In WSL, ensure Qdrant is running:**
```bash
docker compose -f docker-compose.test.yml up -d
```

2. **In WSL, verify the server can start:**
```bash
cd /home/krashnicov/crawl4aimcp
TRANSPORT=stdio /home/krashnicov/.local/bin/uv run python src/crawl4ai_mcp.py
```
Press Ctrl+C to stop.

## Troubleshooting

If you still get errors:

1. **Check WSL is installed:**
```powershell
wsl --status
```

2. **Check WSL distribution name:**
```powershell
wsl --list
```
If your distribution is not the default, you may need to specify it:
```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "wsl",
      "args": [
        "-d",
        "Ubuntu",  // or your distribution name
        "--cd",
        "/home/krashnicov/crawl4aimcp",
        "--",
        "/home/krashnicov/.local/bin/uv",
        "run",
        "python",
        "src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

3. **Enable debug logging in Claude Desktop** to see the exact error

## Important Notes

- Claude Desktop on Windows needs to use `wsl` command to access WSL environment
- The STDIO transport is required for Claude Desktop
- Environment variables can be set in the bash command or via export statements
- Ensure Docker Desktop is running with WSL2 backend for Qdrant access