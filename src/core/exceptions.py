"""Custom exceptions for the Crawl4AI MCP server."""


class MCPToolError(Exception):
    """Custom exception for MCP tool errors that should be returned as JSON-RPC errors."""

    def __init__(self, message: str, code: int = -32000):
        self.message = message
        self.code = code
        super().__init__(message)
