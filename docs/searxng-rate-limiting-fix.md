# SearXNG Rate Limiting Fix Documentation

## Issue Overview

The MCP server was receiving 429 "Too Many Requests" errors when attempting to search through SearXNG, despite rate limiting being disabled in the configuration.

## Root Cause Analysis

SearXNG's bot detection mechanism was blocking requests based on HTTP headers, specifically the `Accept` header. The bot detection expected browser-like headers but was receiving API-style headers.

### Error Details

```
DEBUG   searx.botdetection            : BLOCK 172.18.0.1/32: HTTP header Accept did not contain text/html
DEBUG   searx.limiter                 : NOT OK (searx.botdetection.http_accept)
```

## Solution Implementation

### Code Change

**File**: `src/crawl4ai_mcp.py`  
**Line**: 556  
**Function**: `search_and_crawl_with_searxng()`

#### Before

```python
headers = {
    "User-Agent": user_agent,
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.5"
}
```

#### After

```python
headers = {
    "User-Agent": user_agent,
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.5"
}
```

### Explanation

The updated Accept header includes:

- `text/html` - Satisfies bot detection requirements
- `application/json;q=0.9` - Still accepts JSON with high priority
- `*/*;q=0.8` - Fallback for any content type

This makes requests appear more browser-like while maintaining JSON compatibility for the MCP server.

## Configuration Notes

### SearXNG Settings

The `searxng-test/settings.yml` configuration already had rate limiting disabled:

```yaml
server:
  limiter: false
  limiter_mapping:
    botdetection.ip_limit: false
    botdetection.link_token: false
```

However, bot detection for HTTP headers was still active by default. To fully disable bot detection, add:

```yaml
botdetection:
  http_accept: false
  http_accept_encoding: false
  http_accept_language: false
  http_user_agent: false
```

## Testing Verification

### Test Command

```bash
curl -X GET "http://localhost:8081/search?q=test&format=json&categories=general&limit=1" \
  -H "User-Agent: MCP-Crawl4AI-RAG-Server/1.0" \
  -H "Accept: text/html,application/json;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.5" \
  -H "Accept-Encoding: gzip, deflate" \
  --compressed
```

### Expected Result

Successful JSON response with search results, no 429 errors.

## Prevention Guidelines

1. **Always include browser-like headers** when interacting with SearXNG's API
2. **Test with minimal queries first** to verify configuration before bulk operations
3. **Monitor SearXNG logs** for bot detection warnings during development
4. **Consider disabling all bot detection** in test environments

## Related Files

- `/src/crawl4ai_mcp.py` - MCP server implementation
- `/searxng-test/settings.yml` - SearXNG test configuration
- `/docker-compose.test.yml` - Test environment setup

## Date: 2025-08-02

## Author: Claude Code Assistant
