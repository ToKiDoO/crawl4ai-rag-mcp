#!/usr/bin/env python3
"""
Simple test to verify deprecation warnings are present and documented.
Created: 2025-01-05
Purpose: Quick verification of deprecation warnings
Context: Fix 5.2 - QA + Code reviewer verify deprecation documentation
References: docs/DEPRECATION_WARNINGS.md
"""

import subprocess
import sys
from pathlib import Path


def test_simple_deprecation_capture():
    """Run a simple test to capture deprecation warnings."""
    print("🔍 Running simple test to capture deprecation warnings...")

    # Run a single test file that's likely to show warnings
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_mcp_protocol.py::TestMCPProtocol::test_server_name",
        "-v",
        "-W",
        "default::DeprecationWarning",
        "-s",  # Show output
    ]

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )

        output = result.stdout + result.stderr

        # Check for known warnings
        found_pydantic = (
            "PydanticDeprecatedSince20" in output
            or "class-based `config` is deprecated" in output
        )
        found_fake_http = (
            "read_text is deprecated" in output or "fake_http_header" in output
        )

        print("\n📊 Results:")
        print(
            f"✅ Pydantic deprecation warning: {'Found' if found_pydantic else 'Not found'}"
        )
        print(
            f"✅ fake_http_header warning: {'Found' if found_fake_http else 'Not found'}"
        )

        # Show relevant output lines
        print("\n📋 Deprecation warning lines found:")
        for line in output.split("\n"):
            if "DeprecationWarning" in line or "deprecated" in line.lower():
                print(f"   {line.strip()[:100]}")

        return found_pydantic or found_fake_http

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def verify_documentation_exists():
    """Verify the deprecation documentation file exists and has content."""
    doc_path = Path("docs/DEPRECATION_WARNINGS.md")

    if not doc_path.exists():
        print(f"❌ Documentation file not found: {doc_path}")
        return False

    content = doc_path.read_text()

    # Check for documented warnings
    has_pydantic = (
        "PydanticDeprecatedSince20" in content or "pydantic" in content.lower()
    )
    has_fake_http = "fake_http_header" in content or "read_text" in content

    print("\n📄 Documentation check:")
    print(f"✅ File exists: {doc_path}")
    print(f"✅ Documents Pydantic warning: {'Yes' if has_pydantic else 'No'}")
    print(f"✅ Documents fake_http_header warning: {'Yes' if has_fake_http else 'No'}")

    return has_pydantic and has_fake_http


def main():
    """Run simple verification."""
    print("🚀 Starting simple deprecation verification...")
    print("=" * 60)

    # Test 1: Check if warnings appear in test output
    warnings_found = test_simple_deprecation_capture()

    # Test 2: Check if documentation exists
    docs_exist = verify_documentation_exists()

    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)

    if warnings_found and docs_exist:
        print("✅ PASS: Deprecation warnings are present and documented!")
        print("\nNote: These warnings are from external dependencies:")
        print("- Pydantic V2 (class-based config)")
        print("- fake_http_header (read_text method)")
        print(
            "\nNo action required - warnings are tracked in docs/DEPRECATION_WARNINGS.md"
        )
        return True
    print("❌ FAIL: Issue with deprecation documentation")
    if not warnings_found:
        print("- Warnings not detected in test output")
    if not docs_exist:
        print("- Documentation incomplete or missing")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
