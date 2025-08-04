"""
Configuration module for Crawl4AI MCP Server.

Handles secure loading and validation of configuration from environment variables.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def load_config() -> Dict[str, Any]:
    """
    Load and validate configuration from environment variables.
    
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Required configuration
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API key for embeddings",
    }
    
    config = {}
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            raise ValueError(f"Required environment variable {var} ({description}) is not set")
        config[var] = value
    
    # Optional configuration with defaults
    config.update({
        # Debug settings
        "DEBUG": os.getenv("DEBUG", "false").lower() == "true",
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        
        # Security settings
        "ENCRYPTION_ENABLED": os.getenv("ENCRYPTION_ENABLED", "true").lower() == "true",
        "ENCRYPTION_ALGORITHM": os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM"),
        "REQUIRE_HTTPS": os.getenv("REQUIRE_HTTPS", "true").lower() == "true",
        
        # Security headers
        "security_headers": {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
        },
        
        # Database configuration
        "VECTOR_DATABASE": os.getenv("VECTOR_DATABASE", "qdrant"),
        "QDRANT_URL": os.getenv("QDRANT_URL", "http://localhost:6333"),
        "QDRANT_API_KEY": os.getenv("QDRANT_API_KEY", ""),
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),
        
        # Neo4j configuration
        "NEO4J_URI": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME", "neo4j"),
        "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD", "password"),
        "USE_KNOWLEDGE_GRAPH": os.getenv("USE_KNOWLEDGE_GRAPH", "false").lower() == "true",
        
        # Search configuration
        "SEARXNG_URL": os.getenv("SEARXNG_URL", "http://localhost:8080"),
        
        # Model configuration
        "MODEL_CHOICE": os.getenv("MODEL_CHOICE", "text-embedding-3-small"),
        "USE_CONTEXTUAL_EMBEDDINGS": os.getenv("USE_CONTEXTUAL_EMBEDDINGS", "false").lower() == "true",
        "USE_HYBRID_SEARCH": os.getenv("USE_HYBRID_SEARCH", "false").lower() == "true",
        "USE_AGENTIC_RAG": os.getenv("USE_AGENTIC_RAG", "false").lower() == "true",
        "USE_RERANKING": os.getenv("USE_RERANKING", "false").lower() == "true",
        
        # Rate limiting
        "RATE_LIMIT_REQUESTS": int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        "RATE_LIMIT_WINDOW": int(os.getenv("RATE_LIMIT_WINDOW", "60")),
        
        # CORS settings
        "CORS_ALLOWED_ORIGINS": os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://claude.ai"),
        
        # Transport settings
        "TRANSPORT": os.getenv("TRANSPORT", "stdio"),
        "HOST": os.getenv("HOST", "0.0.0.0"),
        "PORT": int(os.getenv("PORT", "8051")),
    })
    
    # Validate configuration
    validate_config(config)
    
    return config


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration values.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    # Validate OpenAI API key format
    api_key = config.get("OPENAI_API_KEY", "")
    if not api_key.startswith("sk-"):
        raise ValueError("Invalid OPENAI_API_KEY format: must start with 'sk-'")
    
    # Validate URLs
    if config.get("SUPABASE_URL"):
        if not config["SUPABASE_URL"].startswith(("http://", "https://")):
            raise ValueError("Invalid SUPABASE_URL: must be a valid HTTP(S) URL")
    
    # Validate Neo4j URI
    neo4j_uri = config.get("NEO4J_URI", "")
    if not any(neo4j_uri.startswith(proto) for proto in ["bolt://", "neo4j://", "neo4j+s://", "neo4j+ssc://"]):
        raise ValueError("Invalid NEO4J_URI: must use bolt or neo4j protocol")
    
    # Validate rate limits
    if config["RATE_LIMIT_REQUESTS"] < 1:
        raise ValueError("RATE_LIMIT_REQUESTS must be at least 1")
    if config["RATE_LIMIT_WINDOW"] < 1:
        raise ValueError("RATE_LIMIT_WINDOW must be at least 1 second")
    
    # Validate port
    if not 1 <= config["PORT"] <= 65535:
        raise ValueError("PORT must be between 1 and 65535")


def get_config() -> Dict[str, Any]:
    """
    Get cached configuration or load it.
    
    Returns:
        Configuration dictionary
    """
    if not hasattr(get_config, "_config"):
        get_config._config = load_config()
    return get_config._config


def reload_config() -> Dict[str, Any]:
    """
    Reload configuration from environment variables.
    
    Returns:
        Updated configuration dictionary
    """
    if hasattr(get_config, "_config"):
        delattr(get_config, "_config")
    return get_config()