# Migration Guide: Database Abstraction Update

This guide helps existing users migrate to the new database abstraction layer that supports both Supabase and Qdrant.

## Overview

The latest update introduces a database abstraction layer that allows you to choose between:
- **Supabase** (default, no changes needed)
- **Qdrant** (new option, self-hosted)

## For Existing Supabase Users

**No action required!** The update is fully backward compatible. Your existing setup will continue to work exactly as before.

## Switching to Qdrant

If you want to switch from Supabase to Qdrant:

### 1. Update Your Environment

Edit your `.env` file:

```env
# Change from supabase to qdrant
VECTOR_DATABASE=qdrant

# Remove or comment out Supabase credentials (optional)
# SUPABASE_URL=...
# SUPABASE_SERVICE_KEY=...
```

### 2. Enable Qdrant in Docker Compose

Edit `docker-compose.yml` and uncomment the Qdrant service:

```yaml
  # Qdrant Vector Database (Optional - uncomment if using VECTOR_DATABASE=qdrant)
  qdrant:
    container_name: qdrant
    image: qdrant/qdrant:latest
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"  # gRPC port
    volumes:
      - qdrant-data:/qdrant/storage
    environment:
      - QDRANT__LOG_LEVEL=INFO
    networks:
      - searxng
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "1"
```

### 3. Restart Services

```bash
# Stop current services
docker compose down

# Start with Qdrant
docker compose up -d
```

### 4. Migrate Existing Data (Optional)

Currently, there's no automated migration tool. If you need to preserve existing data:

1. Export from Supabase using their dashboard or API
2. Re-crawl your important URLs using the MCP tools
3. Or manually migrate using custom scripts

## Technical Details

### What Changed

1. **Database Interface**: New `VectorDatabase` protocol defines common operations
2. **Adapters**: Separate adapters for Supabase and Qdrant
3. **Factory Pattern**: Database selection based on `VECTOR_DATABASE` environment variable
4. **Utility Functions**: All utilities now accept database instances instead of Supabase clients

### New Project Structure

```
src/
├── database/
│   ├── __init__.py
│   ├── base.py           # VectorDatabase protocol
│   ├── factory.py        # Database factory
│   ├── supabase_adapter.py
│   └── qdrant_adapter.py
├── utils_refactored.py   # Database-agnostic utilities
└── crawl4ai_mcp.py      # Updated to use abstraction
```

### API Compatibility

All MCP tools maintain the same interface. No changes needed in:
- Claude Desktop configuration
- MCP client integration
- Tool parameters

## Troubleshooting

### Qdrant Connection Issues

If Qdrant fails to connect:

1. Check if the container is running:
   ```bash
   docker ps | grep qdrant
   ```

2. Verify the URL in `.env`:
   ```env
   QDRANT_URL=http://qdrant:6333  # For Docker internal network
   ```

3. Check logs:
   ```bash
   docker compose logs qdrant
   ```

### Performance Differences

- **Supabase**: Better for distributed teams, automatic scaling
- **Qdrant**: Better for local development, lower latency

### Memory Usage

Qdrant requires additional memory (recommended 2GB+). Adjust Docker settings if needed.

## Getting Help

If you encounter issues:

1. Check the [integration tests](../tests/test_integration.py)
2. Review the [GitHub issues](https://github.com/coleam00/mcp-crawl4ai-rag/issues)
3. Ensure your `.env` file has all required variables

## Future Enhancements

Planned improvements:
- Automated data migration tools
- Support for additional databases (Weaviate, Pinecone)
- Performance benchmarking tools
- Database-specific optimizations