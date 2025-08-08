"""Validation utilities for the Crawl4AI MCP server."""

import os
import re
from typing import Any

from config import get_settings

# Get settings instance
settings = get_settings()


def validate_neo4j_connection() -> bool:
    """Check if Neo4j environment variables are configured."""
    return all(
        [
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password,
        ],
    )


def get_accessible_script_path(script_path: str) -> str:
    """Convert host path to container-accessible path.

    This function maps common host paths to their container equivalents,
    allowing users to reference scripts using convenient paths.
    """
    # Map common host paths to container paths
    path_mappings = {
        "/tmp/": "/app/tmp_scripts/",
        "./analysis_scripts/": "/app/analysis_scripts/",
        "analysis_scripts/": "/app/analysis_scripts/",
    }

    for host_prefix, container_prefix in path_mappings.items():
        if script_path.startswith(host_prefix):
            return script_path.replace(host_prefix, container_prefix, 1)

    # If path doesn't start with /, assume it's relative to analysis_scripts
    if not script_path.startswith("/"):
        # Check if the path already includes analysis_scripts
        if not script_path.startswith("analysis_scripts"):
            return f"/app/analysis_scripts/user_scripts/{script_path}"
        return f"/app/{script_path}"

    # Return as-is if no mapping found (might be a direct container path)
    return script_path


def validate_script_path(script_path: str) -> dict[str, Any]:
    """Validate script path and return error info if invalid.

    Automatically translates host paths to container-accessible paths.
    """
    if not script_path or not isinstance(script_path, str):
        return {"valid": False, "error": "Script path is required"}

    # Convert to container-accessible path
    container_path = get_accessible_script_path(script_path)

    if not os.path.exists(container_path):
        # Provide helpful error message
        error_msg = f"Script not found: {script_path}"
        if not script_path.startswith("/app/"):
            error_msg += "\n\nPlease place your scripts in one of these locations:"
            error_msg += "\n  - ./analysis_scripts/user_scripts/ (recommended)"
            error_msg += "\n  - ./analysis_scripts/test_scripts/ (for testing)"
            error_msg += "\n  - /tmp/ (temporary scripts)"
            error_msg += "\n\nExample: analysis_scripts/user_scripts/my_script.py"
        return {"valid": False, "error": error_msg}

    if not container_path.endswith(".py"):
        return {"valid": False, "error": "Only Python (.py) files are supported"}

    try:
        # Check if file is readable
        with open(container_path, encoding="utf-8") as f:
            f.read(1)  # Read first character to test
        # Always return the container path for downstream use
        return {"valid": True, "container_path": container_path}
    except Exception as e:
        return {"valid": False, "error": f"Cannot read script file: {e!s}"}


def detect_and_fix_truncated_url(url: str) -> dict[str, Any]:
    """Detect and attempt to fix truncated URLs.

    Common truncation patterns:
    - "...domain/path" -> likely truncated from "https://www.domain/path"
    - "domain/path" without protocol -> add https://

    Args:
        url: Potentially truncated URL

    Returns:
        Dictionary with fix result and suggested URL
    """
    if not url or not isinstance(url, str):
        return {"fixed": False, "error": "Invalid URL input"}

    url = url.strip()

    # Pattern 1: URLs starting with "..."
    if url.startswith("..."):
        # Extract the domain and path part
        truncated_part = url[3:]  # Remove the "..."

        # Try to reconstruct common patterns
        suggestions = []

        # If it looks like it might be a domain/path, try adding https://www.
        if "/" in truncated_part and not truncated_part.startswith("/"):
            suggestions.append(f"https://www.{truncated_part}")
            suggestions.append(f"https://{truncated_part}")
            suggestions.append(f"http://www.{truncated_part}")
            suggestions.append(f"http://{truncated_part}")

        return {
            "fixed": False,
            "truncated": True,
            "original_url": url,
            "suggestions": suggestions,
            "error": f"URL '{url}' appears truncated. Suggested complete URLs: {suggestions[:2]}",
        }

    # Pattern 2: Missing protocol but looks like a valid domain/path
    if "/" in url and not url.startswith(("http://", "https://", "file://", "raw:")):
        # Check if it looks like a domain (contains dots and common TLD patterns)
        domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$"
        if re.match(domain_pattern, url):
            suggested_url = f"https://{url}"
            return {
                "fixed": True,
                "original_url": url,
                "fixed_url": suggested_url,
                "message": f"Added https:// protocol to '{url}'",
            }

    return {"fixed": False, "no_issues": True}


def validate_crawl_url(url: str) -> dict[str, Any]:
    """Validate URL for crawl4ai compatibility.

    Crawl4ai only accepts URLs starting with 'http://', 'https://', 'file://', or 'raw:'.
    This function validates and normalizes URLs before passing to crawl4ai.

    Args:
        url: URL to validate

    Returns:
        Dictionary with validation result and normalized URL
    """
    if not url or not isinstance(url, str):
        return {"valid": False, "error": "URL is required and must be a string"}

    original_url = url
    url = url.strip()

    if not url:
        return {"valid": False, "error": "URL cannot be empty"}

    # First, try to detect and fix truncated URLs
    fix_result = detect_and_fix_truncated_url(url)
    if fix_result.get("fixed"):
        # Use the fixed URL for validation
        url = fix_result["fixed_url"]
    elif fix_result.get("truncated"):
        # URL is truncated and can't be auto-fixed, return helpful error
        return {"valid": False, "error": fix_result["error"]}

    # Check if URL starts with allowed protocols for crawl4ai
    allowed_protocols = ["http://", "https://", "file://", "raw:"]
    if not any(url.startswith(protocol) for protocol in allowed_protocols):
        error_msg = (
            f"URL must start with one of: {', '.join(allowed_protocols)}. Got: '{url}'"
        )

        # Try to provide fix suggestions
        fix_result = detect_and_fix_truncated_url(original_url)
        if fix_result.get("suggestions"):
            error_msg += f" Suggested fixes: {fix_result['suggestions'][:2]}"
        elif "/" in url and not url.startswith(("http://", "https://")):
            error_msg += ". Hint: If this should be a web URL, try adding 'https://' at the beginning."

        return {"valid": False, "error": error_msg}

    # Basic URL format validation for http/https URLs
    if url.startswith(("http://", "https://")):
        # Check for common URL format issues
        if url.count("://") > 1:
            return {
                "valid": False,
                "error": f"Invalid URL format - multiple protocols found: {url}",
            }

        # Check if there's a domain after the protocol
        domain_part = url.split("://", 1)[1] if "://" in url else ""
        if not domain_part or domain_part.startswith("/"):
            return {
                "valid": False,
                "error": f"Invalid URL format - missing domain: {url}",
            }

    # Normalize URL by removing fragment
    from urllib.parse import urldefrag

    normalized_url = urldefrag(url)[0]

    result = {"valid": True, "normalized_url": normalized_url}

    # Add info about any fixes that were applied
    if fix_result.get("fixed"):
        result["auto_fixed"] = True
        result["original_url"] = original_url
        result["fix_message"] = fix_result["message"]

    return result


def validate_urls_for_crawling(urls: list[str]) -> dict[str, Any]:
    """Validate a list of URLs for crawl4ai compatibility.

    Args:
        urls: List of URLs to validate

    Returns:
        Dictionary with validation results
    """
    if not urls or not isinstance(urls, list):
        return {"valid": False, "error": "URLs must be provided as a non-empty list"}

    valid_urls = []
    invalid_urls = []
    errors = []

    for i, url in enumerate(urls):
        result = validate_crawl_url(url)
        if result["valid"]:
            valid_urls.append(result["normalized_url"])
        else:
            invalid_urls.append(url)
            errors.append(f"URL {i + 1} ({url}): {result['error']}")

    if invalid_urls:
        return {
            "valid": False,
            "error": f"Found {len(invalid_urls)} invalid URLs: " + "; ".join(errors),
            "invalid_urls": invalid_urls,
            "valid_urls": valid_urls,
        }

    return {"valid": True, "urls": valid_urls}


def validate_github_url(repo_url: str) -> dict[str, Any]:
    """Validate GitHub repository URL."""
    if not repo_url or not isinstance(repo_url, str):
        return {"valid": False, "error": "Repository URL is required"}

    repo_url = repo_url.strip()

    # Basic GitHub URL validation
    if not ("github.com" in repo_url.lower() or repo_url.endswith(".git")):
        return {"valid": False, "error": "Please provide a valid GitHub repository URL"}

    # Check URL format
    if not (repo_url.startswith("https://") or repo_url.startswith("git@")):
        return {
            "valid": False,
            "error": "Repository URL must start with https:// or git@",
        }

    return {"valid": True, "repo_name": repo_url.split("/")[-1].replace(".git", "")}
