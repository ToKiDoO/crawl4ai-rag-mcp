"""Test environment configuration with proper isolation."""

import os
from pathlib import Path

from dotenv import load_dotenv


def load_test_env(override: bool = True):
    """Load test environment with proper isolation."""
    # Clear problematic env vars first
    problematic_vars = [
        "OPENAI_API_KEY",
        "DATABASE_URL",
        "QDRANT_URL",
        "VECTOR_DATABASE",
    ]
    for var in problematic_vars:
        if var in os.environ:
            del os.environ[var]

    # Load .env.test with override
    env_file = Path(__file__).parent.parent / ".env.test"
    if env_file.exists():
        load_dotenv(env_file, override=override)
        print(f"✅ Loaded test environment from {env_file}")
    # In CI, environment variables are set directly, so missing .env.test is OK

    # Only warn about missing OPENAI_API_KEY if we're not in CI
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("CI"):
        print("⚠️ OPENAI_API_KEY not set after loading .env.test")

    # Force test database
    os.environ["VECTOR_DATABASE"] = "qdrant"
    os.environ["QDRANT_URL"] = "http://localhost:6333"

    # Verify settings
    print(f"VECTOR_DATABASE: {os.getenv('VECTOR_DATABASE')}")
    print(f"QDRANT_URL: {os.getenv('QDRANT_URL')}")


# Auto-load when imported
load_test_env()
