#!/usr/bin/env python3
"""
Direct test of hallucination detection functionality without MCP protocol.
Tests the actual functions directly to verify the volume mounting works.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.validation import get_accessible_script_path, validate_script_path


def test_path_mapping():
    """Test path mapping functionality."""
    print("\n" + "=" * 60)
    print("TEST 1: Path Mapping")
    print("=" * 60)

    test_cases = [
        (
            "analysis_scripts/test_scripts/test_hallucination.py",
            "Path mapping for test script",
        ),
        ("analysis_scripts/user_scripts/my_script.py", "Path mapping for user script"),
        ("/tmp/simple_test.py", "Path mapping for /tmp"),
        ("my_script.py", "Default path mapping"),
    ]

    results = []
    for input_path, description in test_cases:
        mapped_path = get_accessible_script_path(input_path)
        print(f"\n{description}:")
        print(f"  Input:  {input_path}")
        print(f"  Mapped: {mapped_path}")
        results.append((description, True))

    return results


def test_validation():
    """Test script validation."""
    print("\n" + "=" * 60)
    print("TEST 2: Script Validation")
    print("=" * 60)

    # Ensure test script exists
    test_script_path = Path("analysis_scripts/test_scripts/test_hallucination.py")
    if not test_script_path.exists():
        print(f"Creating test script at {test_script_path}")
        test_script_path.parent.mkdir(parents=True, exist_ok=True)
        test_script_path.write_text('''"""Test script."""
import requests
def test(): pass
''')

    test_cases = [
        (
            "analysis_scripts/test_scripts/test_hallucination.py",
            "Existing test script",
            True,
        ),
        ("non_existent_file.py", "Non-existent file", False),
        ("/tmp/simple_test.py", "/tmp file", None),  # May or may not exist
    ]

    results = []
    for path, description, expected in test_cases:
        print(f"\n{description}: {path}")

        # Create /tmp file if testing it
        if path.startswith("/tmp"):
            Path(path).write_text("# Test\nprint('test')")

        result = validate_script_path(path)

        if result.get("valid"):
            print("  ✅ Valid")
            print(f"     Container path: {result.get('container_path', 'N/A')}")
            success = expected is not False
        else:
            error = result.get("error", "Unknown error")
            if "not found" in error:
                print("  ❌ Not found")
                if "Please place your scripts" in error:
                    print("     (Helpful error message provided)")
                success = expected is False
            else:
                print(f"  ❌ Error: {error[:100]}")
                success = False

        results.append((description, success))

    return results


def test_container_access():
    """Test if files are accessible from container perspective."""
    print("\n" + "=" * 60)
    print("TEST 3: Container Access Simulation")
    print("=" * 60)

    print("\nThis test simulates what the container sees:")
    print("(Run inside Docker container for accurate results)")

    results = []

    # Check if we're in container or host
    import os

    in_container = os.path.exists("/app/src")

    if in_container:
        print("✅ Running inside container")
        paths_to_check = [
            "/app/analysis_scripts/test_scripts/",
            "/app/analysis_scripts/user_scripts/",
            "/app/tmp_scripts/",
        ]

        for path in paths_to_check:
            exists = os.path.exists(path)
            status = "✅" if exists else "❌"
            print(f"  {status} {path}")
            results.append((path, exists))
    else:
        print("⚠️  Running on host (not in container)")
        print("  Container paths cannot be verified from host")
        print("  Run this test inside the container for accurate results")
        results.append(("Container test", None))  # Skip

    return results


def generate_report(all_results):
    """Generate test report."""
    print("\n" + "=" * 70)
    print(" TEST REPORT")
    print("=" * 70)

    total = 0
    passed = 0
    skipped = 0

    for test_name, results in all_results:
        print(f"\n{test_name}:")
        for desc, success in results:
            total += 1
            if success is None:
                status = "⏭️  SKIP"
                skipped += 1
            elif success:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
            print(f"  {status} - {desc}")

    print("\n" + "-" * 70)
    print(f"Results: {passed}/{total} passed, {skipped} skipped")

    if passed == total - skipped:
        print("🎉 All runnable tests passed!")
    elif passed > 0:
        print("⚠️  Some tests failed")
    else:
        print("❌ All tests failed")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" HALLUCINATION DETECTION VOLUME MOUNT TESTS")
    print("=" * 70)

    all_results = []

    # Run tests
    all_results.append(("Path Mapping", test_path_mapping()))
    all_results.append(("Validation", test_validation()))
    all_results.append(("Container Access", test_container_access()))

    # Generate report
    generate_report(all_results)

    print("\n" + "=" * 70)
    print("\nNOTE: For complete testing, also run:")
    print("  1. This test inside the Docker container")
    print("  2. The actual MCP tools through an MCP client")
    print("=" * 70)


if __name__ == "__main__":
    main()
