"""Text processing utilities for the Crawl4AI MCP server."""

import re
from typing import Any

# Import from utils if available
try:
    from utils import generate_code_example_summary
except ImportError:
    # Provide a simple fallback implementation
    def generate_code_example_summary(
        code: str, context_before: str = "", context_after: str = ""
    ) -> str:
        """Simple fallback for code example summary generation."""
        lines = code.strip().split("\n")
        first_line = lines[0] if lines else ""
        return f"Code example: {first_line[:100]}..."


def smart_chunk_markdown(text: str, chunk_size: int = 5000) -> list[str]:
    """Split text into chunks, respecting code blocks and paragraphs."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're at the end of the text, just take what's left
        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find a code block boundary first (```)
        chunk = text[start:end]
        code_block = chunk.rfind("```")
        if code_block != -1 and code_block > chunk_size * 0.3:
            end = start + code_block

        # If no code block, try to break at a paragraph
        elif "\n\n" in chunk:
            # Find the last paragraph break
            last_break = chunk.rfind("\n\n")
            if (
                last_break > chunk_size * 0.3
            ):  # Only break if we're past 30% of chunk_size
                end = start + last_break

        # If no paragraph break, try to break at a sentence
        elif ". " in chunk:
            # Find the last sentence break
            last_period = chunk.rfind(". ")
            if (
                last_period > chunk_size * 0.3
            ):  # Only break if we're past 30% of chunk_size
                end = start + last_period + 1

        # Extract chunk and clean it up
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position for next chunk
        start = end

    return chunks


def extract_section_info(chunk: str) -> dict[str, Any]:
    """
    Extracts headers and stats from a chunk.

    Args:
        chunk: Markdown chunk

    Returns:
        Dictionary with headers and stats
    """
    headers = re.findall(r"^(#+)\s+(.+)$", chunk, re.MULTILINE)
    header_str = "; ".join([f"{h[0]} {h[1]}" for h in headers]) if headers else ""

    return {
        "headers": header_str,
        "char_count": len(chunk),
        "word_count": len(chunk.split()),
    }


def process_code_example(args):
    """
    Process a single code example to generate its summary.
    This function is designed to be used with concurrent.futures.

    Args:
        args: Tuple containing (code, context_before, context_after)

    Returns:
        The generated summary
    """
    code, context_before, context_after = args
    return generate_code_example_summary(code, context_before, context_after)
