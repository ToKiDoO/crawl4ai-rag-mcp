#!/usr/bin/env python3
"""Integration test for batch URL processing fix."""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from utils.validation import validate_urls_for_crawling


def test_url_validation_with_parsed_urls():
    """Test that the URL validation works with properly parsed URLs."""

    # Simulate what the fixed scrape_urls tool would produce
    test_cases = [
        {
            "description": "Single URL (from string)",
            "urls": ["https://example.com"],
            "should_pass": True,
        },
        {
            "description": "Multiple URLs (from parsed JSON)",
            "urls": ["https://example.com", "https://httpbin.org/html"],
            "should_pass": True,
        },
        {
            "description": "Invalid URLs",
            "urls": ["not-a-url", "ftp://invalid.com"],
            "should_pass": False,
        },
    ]

    print("Testing URL validation with parsed URLs:")
    print("=" * 60)

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        result = validate_urls_for_crawling(test_case["urls"])
        passed = result["valid"] == test_case["should_pass"]
        all_passed = all_passed and passed

        print(f"Test {i}: {test_case['description']}")
        print(f"  URLs: {test_case['urls']}")
        print(f"  Should pass: {test_case['should_pass']}")
        print(f"  Validation result: {result['valid']}")
        if not result["valid"]:
            print(f"  Error: {result.get('error', 'Unknown error')}")
        print(f"  Status: {'✓ PASS' if passed else '✗ FAIL'}")
        print()

    return all_passed


def main():
    """Run the integration test."""
    print("Integration test for batch URL processing fix")
    print("=" * 70)
    print()

    success = test_url_validation_with_parsed_urls()

    print("=" * 70)
    print(f"Integration test result: {'✓ PASSED' if success else '✗ FAILED'}")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
