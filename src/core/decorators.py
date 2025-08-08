"""Decorators for the Crawl4AI MCP server."""

import functools
import traceback
import uuid
from datetime import datetime

from fastmcp import Context

from .logging import logger


def track_request(tool_name: str):
    """Decorator to track MCP tool requests with timing and error handling."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx: Context, *args, **kwargs):
            request_id = str(uuid.uuid4())[:8]
            start_time = datetime.now().timestamp()

            logger.info(f"[{request_id}] Starting {tool_name} request")
            logger.debug(f"[{request_id}] Arguments: {kwargs}")

            try:
                result = await func(ctx, *args, **kwargs)
                duration = datetime.now().timestamp() - start_time
                logger.info(f"[{request_id}] Completed {tool_name} in {duration:.2f}s")
                return result
            except Exception as e:
                duration = datetime.now().timestamp() - start_time
                logger.error(
                    f"[{request_id}] Failed {tool_name} after {duration:.2f}s: {e!s}",
                )
                logger.debug(f"[{request_id}] Traceback: {traceback.format_exc()}")
                raise

        return wrapper

    return decorator
