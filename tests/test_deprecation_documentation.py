#!/usr/bin/env python3
"""
Test script to verify deprecation warnings documentation.
Created: 2025-01-05
Purpose: Capture and verify all deprecation warnings against documentation
Context: Fix 5.2 - QA + Code reviewer verify deprecation documentation
References: docs/DEPRECATION_WARNINGS.md

This script captures deprecation warnings during a test run and verifies
they are documented. It does NOT suppress any warnings.
"""

import re
import subprocess
import sys
from pathlib import Path

# Known documented warnings from DEPRECATION_WARNINGS.md
DOCUMENTED_WARNINGS = {
    "PydanticDeprecatedSince20": {
        "source": "pydantic",
        "pattern": r"Support for class-based `config` is deprecated",
        "location": "pydantic/_internal/_config.py",
    },
    "read_text_deprecated": {
        "source": "fake_http_header",
        "pattern": r"read_text is deprecated.*Use files\(\) instead",
        "location": "fake_http_header/constants.py",
    },
}


def capture_deprecation_warnings() -> list[str]:
    """Run tests and capture all deprecation warnings."""
    print("🔍 Running tests to capture deprecation warnings...")

    # Run pytest with warnings captured
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "-W",
        "default::DeprecationWarning",
        "-W",
        "default::PendingDeprecationWarning",
        "--capture=no",  # Show output to see warnings
    ]

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )

        # Extract warnings from both stdout and stderr
        output = result.stdout + result.stderr

        # Find all deprecation warnings
        warning_lines = []
        lines = output.split("\n")

        for i, line in enumerate(lines):
            if "DeprecationWarning" in line or "PendingDeprecationWarning" in line:
                # Capture the warning and context
                warning_lines.append(line)
                # Also capture the next few lines for context
                for j in range(i + 1, min(i + 3, len(lines))):
                    if lines[j].strip():
                        warning_lines.append(lines[j])

        return warning_lines

    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return []


def analyze_warnings(warning_lines: list[str]) -> tuple[set[str], set[str]]:
    """Analyze captured warnings and compare with documented ones."""
    found_warnings = set()
    undocumented_warnings = set()

    print("\n📊 Analyzing captured warnings...")

    for line in warning_lines:
        # Check if this matches any documented warning
        matched = False
        for warning_id, details in DOCUMENTED_WARNINGS.items():
            if re.search(details["pattern"], line, re.IGNORECASE):
                found_warnings.add(warning_id)
                matched = True
                print(f"✅ Found documented warning: {warning_id}")
                break

        if not matched and (
            "DeprecationWarning" in line or "PendingDeprecationWarning" in line
        ):
            # This is an undocumented warning
            undocumented_warnings.add(line.strip())
            print(f"❌ Found undocumented warning: {line.strip()}")

    return found_warnings, undocumented_warnings


def verify_documentation_completeness(found_warnings: set[str]) -> list[str]:
    """Check if all documented warnings were found in test run."""
    missing_from_tests = []

    print("\n🔍 Verifying documentation completeness...")

    for warning_id in DOCUMENTED_WARNINGS:
        if warning_id not in found_warnings:
            missing_from_tests.append(warning_id)
            print(f"⚠️  Documented warning not found in tests: {warning_id}")
        else:
            print(f"✅ Documented warning verified: {warning_id}")

    return missing_from_tests


def generate_report(
    found_warnings: set[str],
    undocumented_warnings: set[str],
    missing_from_tests: list[str],
) -> bool:
    """Generate verification report."""
    print("\n" + "=" * 60)
    print("📋 DEPRECATION WARNINGS VERIFICATION REPORT")
    print("=" * 60)

    print(f"\n✅ Documented warnings found in tests: {len(found_warnings)}")
    for warning in found_warnings:
        print(f"   - {warning}")

    if undocumented_warnings:
        print(f"\n❌ Undocumented warnings found: {len(undocumented_warnings)}")
        for warning in list(undocumented_warnings)[:5]:  # Show first 5
            print(f"   - {warning[:100]}...")
        if len(undocumented_warnings) > 5:
            print(f"   ... and {len(undocumented_warnings) - 5} more")
    else:
        print("\n✅ No undocumented warnings found")

    if missing_from_tests:
        print(f"\n⚠️  Documented warnings not found in tests: {len(missing_from_tests)}")
        for warning in missing_from_tests:
            print(f"   - {warning}")
    else:
        print("\n✅ All documented warnings were found in tests")

    # Determine if documentation is up to date
    is_complete = len(undocumented_warnings) == 0

    print("\n" + "=" * 60)
    if is_complete:
        print("✅ PASS: Deprecation documentation is complete!")
    else:
        print("❌ FAIL: Deprecation documentation needs updating!")
        print("\nAction Required:")
        print("1. Review the undocumented warnings above")
        print("2. Update docs/DEPRECATION_WARNINGS.md with any new warnings")
        print("3. Run this script again to verify")
    print("=" * 60)

    return is_complete


def main():
    """Run deprecation documentation verification."""
    print("🚀 Starting deprecation documentation verification...")
    print("This will run tests and analyze deprecation warnings.")
    print("NO warnings will be suppressed.\n")

    # Capture warnings from test run
    warning_lines = capture_deprecation_warnings()

    if not warning_lines:
        print("⚠️  No deprecation warnings captured. This might mean:")
        print("   - Tests are not running properly")
        print("   - Warnings are being suppressed elsewhere")
        print("   - There genuinely are no deprecation warnings")
        return False

    # Analyze warnings
    found_warnings, undocumented_warnings = analyze_warnings(warning_lines)

    # Verify documentation completeness
    missing_from_tests = verify_documentation_completeness(found_warnings)

    # Generate report
    is_complete = generate_report(
        found_warnings, undocumented_warnings, missing_from_tests
    )

    return is_complete


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
