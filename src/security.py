"""
Security module for Crawl4AI MCP Server.

This module provides security validation, sanitization, and protection functions
to prevent common vulnerabilities including:
- SSRF (Server-Side Request Forgery)
- SQL/NoSQL Injection
- XSS (Cross-Site Scripting)
- Path Traversal
- API Key validation
- Rate limiting
- CORS configuration
"""

import os
import re
import ipaddress
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from collections import defaultdict


# Security constants
ALLOWED_URL_SCHEMES = {'http', 'https'}
PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),  # Link-local (includes AWS metadata)
    ipaddress.ip_network('::1/128'),  # IPv6 localhost
    ipaddress.ip_network('fc00::/7'),  # IPv6 private
    ipaddress.ip_network('fe80::/10'),  # IPv6 link-local
]

# Dangerous patterns for injection prevention
SQL_INJECTION_PATTERNS = [
    r"('\s*(OR|AND)\s*'?\d*\s*=\s*'?\d*)",  # ' OR '1'='1
    r"(--\s*$)",  # SQL comment
    r"(;\s*(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER)\s+)",  # SQL commands
    r"(UNION\s+(ALL\s+)?SELECT)",  # UNION attacks
    r"(\/\*.*\*\/)",  # SQL block comments
]

XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",  # Script tags
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"<iframe",  # IFrames
    r"<object",  # Object tags
    r"<embed",  # Embed tags
    r"vbscript:",  # VBScript protocol
    r"data:text/html",  # Data URLs with HTML
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",  # ../
    r"\.\.\\",  # ..\
    r"%2e%2e",  # URL encoded ..
    r"%252e%252e",  # Double encoded ..
    r"\x00",  # Null byte
    r"\.\.%",  # Partial encoding
]

# Template injection patterns
TEMPLATE_INJECTION_PATTERNS = [
    r"\{\{.*\}\}",  # Jinja2/Angular
    r"\${.*}",  # Template literals
    r"<%.*%>",  # ERB/ASP
    r"#{.*}",  # Ruby interpolation
]


class RateLimiter:
    """Rate limiter implementation for API security"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        now = time.time()
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[client_id].append(now)
        return True
    
    def get_rate_limit_headers(self, client_id: str) -> Dict[str, str]:
        """Get rate limit headers for response"""
        now = time.time()
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if now - req_time < self.window_seconds
        ]
        
        remaining = max(0, self.max_requests - len(self.requests[client_id]))
        reset_time = int(now + self.window_seconds)
        
        return {
            "X-RateLimit-Limit": str(self.max_requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }


def validate_api_key(api_key: Optional[str]) -> bool:
    """
    Validate API key format and structure.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If API key is invalid
        TypeError: If API key is not a string
    """
    if api_key is None:
        raise TypeError("API key cannot be None")
    
    if not isinstance(api_key, str):
        raise TypeError("API key must be a string")
    
    if not api_key or api_key.isspace():
        raise ValueError("API key cannot be empty or whitespace")
    
    # Check length
    if len(api_key) > 200:
        raise ValueError("API key is too long")
    
    # Check for injection attempts
    if any(pattern in api_key.lower() for pattern in ['<script>', 'drop table', 'delete from']):
        raise ValueError("Invalid API key format detected")
    
    # API key format validation - must match expected patterns
    # OpenAI keys - proper validation
    if api_key.startswith('sk-'):
        # Reject test/mock/fake/placeholder patterns first
        forbidden_patterns = ['test', 'mock', 'fake', 'placeholder', 'dummy', 'example']
        api_key_lower = api_key.lower()
        if any(pattern in api_key_lower for pattern in forbidden_patterns):
            raise ValueError("Invalid OpenAI API key format: test/mock keys not allowed")
        
        # OpenAI keys must be at least 51 characters
        if len(api_key) < 51:
            raise ValueError("Invalid OpenAI API key format: too short")
        
        return True
    
    # Other known API key patterns
    valid_prefixes = [
        'eyJ',  # JWT tokens (Supabase, etc)
        'Bearer ',  # Bearer tokens
    ]
    
    # Check if it matches any known pattern
    if not any(api_key.startswith(prefix) for prefix in valid_prefixes):
        raise ValueError("Invalid API key format")
    
    return True


def validate_credentials(credentials: Dict[str, str]) -> bool:
    """
    Validate credential formats.
    
    Args:
        credentials: Dictionary of credentials to validate
        
    Returns:
        True if all credentials are valid
        
    Raises:
        ValueError: If any credential is invalid
    """
    for key, value in credentials.items():
        if key == "OPENAI_API_KEY":
            if not value.startswith("sk-"):
                raise ValueError(f"Invalid {key} format: must start with 'sk-'")
        
        elif key == "SUPABASE_URL":
            parsed = urlparse(value)
            if parsed.scheme not in ['http', 'https']:
                raise ValueError(f"Invalid {key} format: must be HTTP(S) URL")
            if not parsed.netloc:
                raise ValueError(f"Invalid {key} format: missing domain")
        
        elif key == "NEO4J_URI":
            parsed = urlparse(value)
            if parsed.scheme not in ['bolt', 'neo4j', 'neo4j+s', 'neo4j+ssc']:
                raise ValueError(f"Invalid {key} format: must use bolt/neo4j protocol")
    
    return True


def validate_url_security(url: str) -> bool:
    """
    Validate URL for security issues (SSRF prevention).
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is safe
        
    Raises:
        ValueError: If URL has security issues
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")
    
    # Check scheme
    if parsed.scheme not in ALLOWED_URL_SCHEMES:
        raise ValueError(f"Forbidden URL scheme: {parsed.scheme}")
    
    # Check for localhost/private IPs
    hostname = parsed.hostname
    if hostname:
        # Check common localhost patterns
        if hostname.lower() in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
            raise ValueError("Access to localhost is forbidden")
        
        # Remove brackets from IPv6 addresses
        if hostname.startswith('[') and hostname.endswith(']'):
            hostname = hostname[1:-1]
            if hostname == '::1':
                raise ValueError("Access to localhost is forbidden")
        
        # Check private IP ranges
        try:
            ip = ipaddress.ip_address(hostname)
            for private_range in PRIVATE_IP_RANGES:
                if ip in private_range:
                    raise ValueError(f"Access to private IP {ip} is forbidden")
        except ValueError as e:
            # If it's our own ValueError about private IPs, re-raise it
            if "Access to private IP" in str(e):
                raise
            # Not an IP address, check for suspicious patterns
            if any(pattern in hostname.lower() for pattern in [
                'localhost', '127.', '192.168.', '10.', '172.',
                'metadata', 'localtest', 'xip.io'
            ]):
                raise ValueError("Suspicious hostname detected")
    
    # Check for dangerous patterns
    if any(danger in url.lower() for danger in [
        'javascript:', 'vbscript:', 'data:', 'file:', 'gopher:', 'dict:'
    ]):
        raise ValueError("Dangerous URL pattern detected")
    
    return True


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query to prevent injection attacks.
    
    Args:
        query: Search query to sanitize
        
    Returns:
        Sanitized query
    """
    if not query:
        return ""
    
    # Convert to string if not already
    query = str(query)
    
    # Remove path traversal patterns first
    for pattern in PATH_TRAVERSAL_PATTERNS:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)
    
    # Remove SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)
    
    # Remove XSS patterns
    for pattern in XSS_PATTERNS:
        query = re.sub(pattern, '', query, flags=re.IGNORECASE)
    
    # Remove template injection patterns
    for pattern in TEMPLATE_INJECTION_PATTERNS:
        query = re.sub(pattern, '', query)
    
    # Remove control characters
    query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)
    
    # Remove dangerous SQL keywords
    dangerous_keywords = [
        'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'UPDATE SET',
        'CREATE TABLE', 'ALTER TABLE', 'EXEC', 'EXECUTE'
    ]
    for keyword in dangerous_keywords:
        query = re.sub(rf'\b{keyword}\b', '', query, flags=re.IGNORECASE)
    
    # Limit length
    query = query[:1000]
    
    return query.strip()


def validate_file_path(path: str) -> bool:
    """
    Validate file path to prevent path traversal attacks.
    
    Args:
        path: File path to validate
        
    Returns:
        True if path is safe
        
    Raises:
        ValueError: If path contains traversal attempts
    """
    if not path or not isinstance(path, str):
        raise ValueError("Path must be a non-empty string")
    
    # Check for path traversal patterns
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, path, re.IGNORECASE):
            raise ValueError("Path traversal attempt detected")
    
    # Check for absolute paths to sensitive locations
    sensitive_paths = [
        '/etc/', '/proc/', '/sys/', '/dev/',
        'C:\\Windows\\', 'C:\\System32\\',
        '/var/log/', '/root/', '/home/'
    ]
    
    path_lower = path.lower()
    for sensitive in sensitive_paths:
        if sensitive.lower() in path_lower:
            raise ValueError(f"Access to sensitive path forbidden: {sensitive}")
    
    # Check for null bytes
    if '\x00' in path:
        raise ValueError("Null byte injection detected")
    
    return True


def get_cors_config() -> Dict[str, Any]:
    """
    Get secure CORS configuration.
    
    Returns:
        CORS configuration dictionary
    """
    allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
    
    # Default to specific origins, never use "*"
    if not allowed_origins:
        allowed_origins = ["http://localhost:3000", "https://claude.ai"]
    
    return {
        "allow_origins": allowed_origins,
        "allow_methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "allow_credentials": False,  # Default to false for security
        "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
        "max_age": 86400,  # 24 hours
    }


def handle_error(error: Exception) -> Dict[str, Any]:
    """
    Handle errors securely without leaking sensitive information.
    
    Args:
        error: Exception to handle
        
    Returns:
        Safe error response
    """
    # Log the full error internally
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error occurred: {type(error).__name__}: {str(error)}")
    
    # Sanitize error message
    error_str = str(error)
    
    # Remove sensitive patterns
    sensitive_patterns = [
        r'sk-[a-zA-Z0-9]+',  # API keys
        r'eyJ[a-zA-Z0-9._-]+',  # JWT tokens
        r'password\s*[:=]\s*[^\s]+',  # Passwords
        r'neo4j_password_[^\s"\']+',  # Neo4j passwords
        r'://[^:]+:[^@]+@[^/]+',  # URLs with credentials
        r'token\s*[:=]\s*[^\s]+',  # Tokens
        r'key\s*[:=]\s*[^\s]+',  # Keys
        r'secret\s*[:=]\s*[^\s]+',  # Secrets
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email addresses
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',  # IP addresses
    ]
    
    for pattern in sensitive_patterns:
        error_str = re.sub(pattern, '[REDACTED]', error_str, flags=re.IGNORECASE)
    
    # Return error messages based on mode
    if os.getenv("DEBUG", "false").lower() == "true":
        # In debug mode, return sanitized error
        return {
            "error": {
                "message": error_str,
                "type": type(error).__name__
            }
        }
    else:
        # In production, return generic messages
        error_messages = {
            ValueError: "Invalid input provided",
            TypeError: "Invalid data type",
            PermissionError: "Access denied",
            FileNotFoundError: "Resource not found",
        }
        
        # Get specific error message or use default
        error_type = type(error)
        message = "An error occurred processing your request"
        
        for err_class, err_msg in error_messages.items():
            if isinstance(error, err_class):
                message = err_msg
                break
        
        return {
            "error": {
                "message": message,
                "type": "error"
            }
        }


def requires_https(func):
    """Decorator to require HTTPS for certain endpoints"""
    def wrapper(*args, **kwargs):
        # This is a placeholder - actual implementation would check request
        # For MCP, this would be handled at transport layer
        request = kwargs.get('request')
        if request and hasattr(request, 'is_secure') and not request.is_secure:
            return {
                "status_code": 301,
                "headers": {
                    "Location": request.url.replace("http://", "https://")
                }
            }
        return func(*args, **kwargs)
    return wrapper


def validate_sse_connection(auth_token: Optional[str]) -> bool:
    """
    Validate SSE connection authentication.
    
    Args:
        auth_token: Authentication token for SSE
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If authentication fails
    """
    if not auth_token:
        raise ValueError("Authentication token required for SSE connection")
    
    # In production, this would validate against a token store
    # For now, just check format
    if not isinstance(auth_token, str) or len(auth_token) < 32:
        raise ValueError("Invalid authentication token")
    
    return True


def mask_sensitive_data(data: str, sensitive_keys: List[str]) -> str:
    """
    Mask sensitive data in strings.
    
    Args:
        data: String that may contain sensitive data
        sensitive_keys: List of keys to mask
        
    Returns:
        String with sensitive data masked
    """
    masked = data
    
    for key in sensitive_keys:
        # Various patterns for key-value pairs
        patterns = [
            rf'{key}\s*=\s*"([^"]+)"',  # key="value"
            rf'{key}\s*=\s*\'([^\']+)\'',  # key='value'
            rf'{key}\s*:\s*"([^"]+)"',  # key: "value"
            rf'{key}\s*:\s*\'([^\']+)\'',  # key: 'value'
            rf'{key}\s*=\s*([^\s,;]+)',  # key=value
        ]
        
        for pattern in patterns:
            masked = re.sub(pattern, f'{key}=[REDACTED]', masked, flags=re.IGNORECASE)
    
    return masked


# Configuration loading with security
def load_config() -> Dict[str, Any]:
    """
    Load configuration with security validation.
    
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If required configuration is missing
    """
    required_vars = ["OPENAI_API_KEY"]
    config = {}
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Required environment variable {var} is not set")
        config[var] = value
    
    # Load optional vars with defaults
    config["DEBUG"] = os.getenv("DEBUG", "false")
    config["ENCRYPTION_ENABLED"] = True
    config["ENCRYPTION_ALGORITHM"] = "AES-256-GCM"
    
    return config