#!/usr/bin/env python3
"""Final test to verify URL validation fix is working correctly."""

import sys

sys.path.insert(0, "/home/krashnicov/crawl4aimcp/src")

from utils.validation import validate_urls_for_crawling


def test_original_error_scenario():
    """Test the exact scenario from the original error."""
    print("Testing Original Error Scenario")
    print("=" * 60)

    # The exact URLs from the error log
    problematic_urls = [
        "https://example.com",
        ".../help/example-domains",  # This was truncated in the logs
    ]

    print(f"Input URLs: {problematic_urls}")
    print("\nValidation Result:")

    result = validate_urls_for_crawling(problematic_urls)

    if result["valid"]:
        print("✗ UNEXPECTED: Validation passed (should have failed)")
        print(f"  Output URLs: {result['urls']}")
    else:
        print("✓ EXPECTED: Validation correctly rejected invalid URLs")
        print(f"  Error: {result['error']}")
        if result.get("invalid_urls"):
            print(f"  Invalid URLs: {result['invalid_urls']}")
        if result.get("valid_urls"):
            print(f"  Valid URLs that could be processed: {result['valid_urls']}")

    print("\n" + "=" * 60)

    # Test if we're preventing the crawl4ai error
    print("\nVerifying crawl4ai protection:")

    if not result["valid"]:
        print("✓ crawl4ai will NOT receive invalid URLs")
        print("  The ValueError from crawl4ai is prevented!")
    else:
        print("✗ crawl4ai would receive URLs and might fail")

    print("\n" + "=" * 60)
    return not result["valid"]  # Should return True (validation should fail)


def test_comprehensive_scenarios():
    """Test various URL scenarios to ensure robustness."""
    print("\nComprehensive URL Validation Tests")
    print("=" * 60)

    test_cases = [
        {
            "name": "Valid HTTPS URLs",
            "urls": [
                "https://example.com",
                "https://www.iana.org/help/example-domains",
            ],
            "should_pass": True,
        },
        {
            "name": "Truncated URLs (ellipsis)",
            "urls": [".../path/to/page", "...example.com"],
            "should_pass": False,
        },
        {
            "name": "Mixed valid and truncated",
            "urls": ["https://valid.com", ".../truncated/path"],
            "should_pass": False,
        },
        {
            "name": "URLs without protocol",
            "urls": ["example.com", "www.example.org"],
            "should_pass": False,
        },
        {
            "name": "Invalid protocols",
            "urls": ["ftp://example.com", "ssh://server.com"],
            "should_pass": False,
        },
        {
            "name": "File and raw protocols (valid for crawl4ai)",
            "urls": ["file:///path/to/file.html", "raw:Some raw content"],
            "should_pass": True,
        },
    ]

    all_passed = True

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"URLs: {test['urls']}")

        result = validate_urls_for_crawling(test["urls"])

        if test["should_pass"]:
            if result["valid"]:
                print("✓ PASS: Validation correctly accepted valid URLs")
            else:
                print(f"✗ FAIL: Should have passed but got error: {result['error']}")
                all_passed = False
        elif not result["valid"]:
            print("✓ PASS: Validation correctly rejected invalid URLs")
            print(f"  Reason: {result['error'][:100]}...")
        else:
            print(f"✗ FAIL: Should have failed but passed with URLs: {result['urls']}")
            all_passed = False

    print("\n" + "=" * 60)
    return all_passed


def main():
    """Run all tests."""
    print("\n🔍 URL VALIDATION FIX VERIFICATION")
    print("=" * 60)

    # Test the original error scenario
    original_fixed = test_original_error_scenario()

    # Test comprehensive scenarios
    comprehensive_passed = test_comprehensive_scenarios()

    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)

    if original_fixed:
        print("✅ Original error scenario: FIXED")
        print("   - Truncated URLs are properly detected")
        print("   - Helpful error messages are provided")
        print("   - crawl4ai won't receive invalid URLs")
    else:
        print("❌ Original error scenario: NOT FIXED")

    if comprehensive_passed:
        print("✅ Comprehensive tests: ALL PASSED")
    else:
        print("❌ Comprehensive tests: SOME FAILED")

    if original_fixed and comprehensive_passed:
        print("\n🎉 SUCCESS: URL validation is working correctly!")
        print(
            "The crawl4ai error 'URL must start with http://, https://, file://, or raw:' is prevented."
        )
    else:
        print("\n⚠️  ATTENTION: Some tests failed. Review the results above.")

    print("=" * 60)


if __name__ == "__main__":
    main()
