# MCP Client Configuration Guide

This guide provides the configuration for connecting MCP clients to the Crawl4AI MCP server running in Docker with HTTP transport.

## Prerequisites

- Docker and Docker Compose installed
- The Crawl4AI MCP server running via Docker Compose
- MCP client (e.g., Claude Desktop, MCP CLI)

## Starting the Server

1. Clone the repository and navigate to the project directory
2. Copy `.env.example` to `.env` and configure your API keys
3. Start the services:

```bash
docker compose up -d
```

The MCP server will be available at `http://localhost:8051` with HTTP transport.

## MCP Client Configuration

### Claude Desktop Configuration

Save this configuration to your Claude Desktop config file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "crawl4ai-docker": {
      "url": "http://localhost:8051",
      "transport": "http"
    }
  }
}
```

### MCP CLI Configuration

For the MCP CLI tool, use this configuration:

```bash
# Connect to the server
mcp connect http://localhost:8051

# Or with environment variable
export MCP_SERVER_URL=http://localhost:8051
mcp list-tools
```

## Docker Compose Configuration

The server runs with these default settings in `docker-compose.yml`:

```yaml
services:
  mcp-crawl4ai:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: mcp-crawl4ai
    restart: unless-stopped
    environment:
      - TRANSPORT=http
      - HOST=0.0.0.0
      - PORT=8051
    ports:
      - "8051:8051"
    # ... other configurations
```

## Environment Variables

Configure these in your `.env` file:

```bash
# Transport (fixed to HTTP for Docker deployment)
TRANSPORT=http
HOST=0.0.0.0
PORT=8051

# Vector Database
VECTOR_DATABASE=qdrant
QDRANT_URL=http://qdrant:6333

# API Keys
OPENAI_API_KEY=your-openai-api-key

# Optional Features
USE_RERANKING=true
ENABLE_AGENTIC_RAG=true
ENABLE_HYBRID_SEARCH=true
USE_KNOWLEDGE_GRAPH=false
```

## Available Tools

Once connected, the following tools are available:

1. **scrape_urls** - Crawl and store web pages
2. **perform_rag_query** - Search through scraped content
3. **search_code_examples** - Find code snippets
4. **web_search** - Search the web via SearXNG
5. **list_mcp_tools** - List all available tools

## Testing the Connection

### Using Claude Desktop

1. Save the configuration and restart Claude Desktop
2. Look for the MCP icon in the interface
3. Test with: "What MCP tools are available?"

### Using MCP CLI

```bash
# List available tools
mcp list-tools --server http://localhost:8051

# Call a tool
mcp call scrape_urls --url "https://example.com"
```

### Using curl

```bash
# Health check
curl http://localhost:8051/health

# List tools (MCP protocol)
curl -X POST http://localhost:8051 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}'
```

## Troubleshooting

### Connection Issues

1. **Check if services are running:**
   ```bash
   docker compose ps
   ```

2. **View logs:**
   ```bash
   docker compose logs -f mcp-crawl4ai
   ```

3. **Test connectivity:**
   ```bash
   curl http://localhost:8051/health
   ```

### Common Problems

- **Port 8051 already in use**: Change the port in `.env` and docker-compose.yml
- **Connection refused**: Ensure Docker containers are running and healthy
- **Authentication errors**: Check your API keys in the `.env` file
- **Vector database errors**: Ensure Qdrant is running and accessible

## Production Deployment

For production deployments:

1. Use a reverse proxy (nginx, traefik) with SSL
2. Configure authentication/authorization
3. Set resource limits in docker-compose.yml
4. Enable monitoring and logging
5. Use external vector database and cache services

Example nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name mcp.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8051;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Support

For issues or questions:
- Check the logs: `docker compose logs -f mcp-crawl4ai`
- Review the [README.md](README.md) for more details
- Submit issues to the project repository