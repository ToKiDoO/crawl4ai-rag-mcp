# Claude Desktop Configuration Examples

This document provides various configuration examples for connecting Claude Desktop to the Crawl4AI MCP server.

## Basic Configuration (Linux/macOS)

Save this to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `~/.config/Claude/claude_desktop_config.json` (Linux):

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "src/crawl4ai_mcp.py"
      ],
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

## Windows Configuration

Save this to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "C:\\Users\\YourUsername\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "python",
        "src/crawl4ai_mcp.py"
      ],
      "cwd": "C:\\Users\\YourUsername\\crawl4aimcp",
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333"
      }
    }
  }
}
```

## Windows WSL Configuration

If running the server in WSL but Claude Desktop on Windows:

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

## Docker Configuration

If running the server in Docker:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network", "host",
        "-e", "TRANSPORT=stdio",
        "-e", "VECTOR_DATABASE=qdrant",
        "-e", "QDRANT_URL=http://localhost:6333",
        "-v", "/home/krashnicov/crawl4aimcp:/app",
        "-w", "/app",
        "python:3.12",
        "uv", "run", "python", "src/crawl4ai_mcp.py"
      ]
    }
  }
}
```

## Configuration with All Environment Variables

Complete configuration with all available environment variables:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "src/crawl4ai_mcp.py"
      ],
      "cwd": "/home/krashnicov/crawl4aimcp",
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "",
        "OPENAI_API_KEY": "your-openai-api-key",
        "USE_RERANKING": "true",
        "ENABLE_AGENTIC_RAG": "true",
        "ENABLE_HYBRID_SEARCH": "true",
        "USE_KNOWLEDGE_GRAPH": "false",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "your-password",
        "MCP_DEBUG": "false"
      }
    }
  }
}
```

## Multiple Server Configuration

Running multiple MCP servers including Crawl4AI:

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "command": "uv",
      "args": ["run", "python", "src/crawl4ai_mcp.py"],
      "cwd": "/home/krashnicov/crawl4aimcp",
      "env": {
        "TRANSPORT": "stdio",
        "VECTOR_DATABASE": "qdrant"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/krashnicov"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your-github-pat"
      }
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **Server not connecting**: Make sure the path in `cwd` exists and contains the project
2. **UV not found**: Ensure UV is installed and the path is correct
3. **Permission denied**: Make sure the Python script is executable
4. **Environment variables not loading**: Check that your `.env` file is in the project root

### Debug Mode

Enable debug logging by adding to the env section:

```json
"env": {
  "MCP_DEBUG": "true",
  // ... other env vars
}
```

### Verifying Configuration

1. Save the configuration file
2. Restart Claude Desktop completely
3. Open Claude Desktop and look for the MCP icon in the interface
4. Click on it to see if your server is listed

### Testing the Connection

Once configured, you can test by asking Claude:

- "What MCP tools are available?"
- "Can you scrape <https://example.com>?"
- "Search for 'test' in the scraped content"
