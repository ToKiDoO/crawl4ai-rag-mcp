#!/usr/bin/env python3
"""Test script to validate the hallucination detection volume mounting fix."""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.validation import get_accessible_script_path, validate_script_path


def test_path_mapping():
    """Test the path mapping functionality."""
    print("\n=== Testing Path Mapping ===\n")

    test_cases = [
        (
            "analysis_scripts/test_scripts/test_hallucination.py",
            "/app/analysis_scripts/test_scripts/test_hallucination.py",
        ),
        (
            "./analysis_scripts/user_scripts/my_script.py",
            "/app/analysis_scripts/user_scripts/my_script.py",
        ),
        ("/tmp/test.py", "/app/tmp_scripts/test.py"),
        ("my_script.py", "/app/analysis_scripts/user_scripts/my_script.py"),
        (
            "test_scripts/test.py",
            "/app/analysis_scripts/user_scripts/test_scripts/test.py",
        ),
    ]

    for input_path, expected_output in test_cases:
        result = get_accessible_script_path(input_path)
        status = "✓" if result == expected_output else "✗"
        print(f"{status} Input: {input_path}")
        print(f"  Expected: {expected_output}")
        print(f"  Got: {result}")
        print()


def test_validation():
    """Test the validation functionality."""
    print("\n=== Testing Script Validation ===\n")

    # Test with our test script
    test_path = "analysis_scripts/test_scripts/test_hallucination.py"
    result = validate_script_path(test_path)

    print(f"Testing: {test_path}")
    print(f"Valid: {result.get('valid', False)}")
    if result.get("valid"):
        print(f"Container path: {result.get('container_path', 'N/A')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    print()

    # Test with non-existent file
    test_path = "non_existent.py"
    result = validate_script_path(test_path)

    print(f"Testing: {test_path}")
    print(f"Valid: {result.get('valid', False)}")
    if not result.get("valid"):
        print(f"Error (truncated): {result.get('error', 'Unknown error')[:100]}...")


async def test_hallucination_tools():
    """Test the actual hallucination detection tools."""
    print("\n=== Testing Hallucination Detection Tools ===\n")

    # Note: This would need the full MCP server running
    # For now, we'll just test that our validation works

    test_script = "analysis_scripts/test_scripts/test_hallucination.py"
    validation = validate_script_path(test_script)

    if validation.get("valid"):
        print(f"✓ Script {test_script} is ready for hallucination detection")
        print(f"  Container path: {validation.get('container_path')}")
        print("\nTo test the actual tools, use the MCP client with:")
        print(f'  check_ai_script_hallucinations(script_path="{test_script}")')
        print(f'  check_ai_script_hallucinations_enhanced(script_path="{test_script}")')
    else:
        print(f"✗ Script validation failed: {validation.get('error')}")


if __name__ == "__main__":
    print("=" * 60)
    print("Hallucination Detection Volume Mount Testing")
    print("=" * 60)

    test_path_mapping()
    test_validation()
    asyncio.run(test_hallucination_tools())

    print("\n" + "=" * 60)
    print("Testing Complete")
    print("=" * 60)
