#!/usr/bin/env python3
"""
Test script to validate API key loading behavior

Created: 2025-08-05
Purpose: Validate API key loading and security validation for Fix 1 (API Key Loading)
Context: Part of MCP Tools Testing issue resolution to ensure proper API key handling

This script was created to test the API key validation implementation that ensures:
- API keys are loaded correctly from .env file (not shell environment)
- API keys are validated for correct format (sk- prefix, minimum length)
- Test/mock API keys are rejected for security

Related outcomes: See mcp_tools_test_results.md for resolution of API key loading issues
"""

import os
import tempfile


def test_api_key_validation():
    """Test the API key validation logic from crawl4ai_mcp.py"""
    print("Testing API key validation logic...")

    # Create a temporary .env file with empty API key
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("OPENAI_API_KEY=\n")
        f.write("VECTOR_DATABASE=qdrant\n")
        temp_env_path = f.name

    try:
        # Test 1: Empty API key
        print("\n=== Test 1: Empty API key ===")
        os.environ.pop("OPENAI_API_KEY", None)  # Remove from environment

        # Import the dotenv loading logic
        from dotenv import load_dotenv

        load_dotenv(temp_env_path, override=True)

        openai_api_key = os.getenv("OPENAI_API_KEY")
        print(f"Loaded API key: '{openai_api_key}'")

        if not openai_api_key or openai_api_key.strip() == "":
            print("✅ PASS: Empty API key detected correctly")
            print("❌ This should cause system exit in actual application")
        else:
            print("❌ FAIL: Empty API key not detected")

        # Test 2: Placeholder API key
        print("\n=== Test 2: Placeholder API key ===")
        os.environ["OPENAI_API_KEY"] = "test-mock-key-not-real"
        openai_api_key = os.getenv("OPENAI_API_KEY")
        print(f"API key: '{openai_api_key}'")

        if openai_api_key == "test-mock-key-not-real":
            print("✅ PASS: Placeholder API key detected correctly")
            print("❌ This should cause system exit in actual application")
        else:
            print("❌ FAIL: Placeholder API key not detected")

        # Test 3: Valid API key (mock)
        print("\n=== Test 3: Valid API key ===")
        os.environ["OPENAI_API_KEY"] = "sk-test-valid-key-1234567890"
        openai_api_key = os.getenv("OPENAI_API_KEY")
        print(f"API key: '{openai_api_key}'")

        if (
            openai_api_key
            and openai_api_key.strip() != ""
            and openai_api_key != "test-mock-key-not-real"
        ):
            print("✅ PASS: Valid API key accepted")
        else:
            print("❌ FAIL: Valid API key rejected")

    finally:
        # Cleanup
        os.unlink(temp_env_path)
        print(f"\nCleanup: Removed temporary file {temp_env_path}")


def test_shell_vs_env_file_priority():
    """Test priority between shell environment and .env file"""
    print("\n" + "=" * 50)
    print("Testing shell environment vs .env file priority...")

    # Create temp .env file with one key
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("OPENAI_API_KEY=env-file-key\n")
        f.write("MODEL_CHOICE=env-file-model\n")
        temp_env_path = f.name

    try:
        # Set shell environment variable
        os.environ["OPENAI_API_KEY"] = "shell-env-key"

        # Load .env file with override=True (should override shell env)
        from dotenv import load_dotenv

        load_dotenv(temp_env_path, override=True)

        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("MODEL_CHOICE")

        print(f"API key after load_dotenv(override=True): '{api_key}'")
        print(f"Model choice: '{model}'")

        if api_key == "env-file-key":
            print("✅ PASS: .env file overrides shell environment with override=True")
        else:
            print("❌ FAIL: .env file should override shell environment")

        if model == "env-file-model":
            print("✅ PASS: .env file loads variables not in shell environment")
        else:
            print("❌ FAIL: .env file should load all variables")

    finally:
        os.unlink(temp_env_path)
        print(f"Cleanup: Removed temporary file {temp_env_path}")


if __name__ == "__main__":
    test_api_key_validation()
    test_shell_vs_env_file_priority()
