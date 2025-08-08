#!/usr/bin/env python3
"""Debug script to help identify where URL truncation might be occurring."""

import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def simulate_common_truncation_scenarios():
    """Simulate common scenarios where URL truncation might occur."""
    
    print("🔍 Simulating common URL truncation scenarios...")
    
    original_url = "https://www.iana.org/help/example-domains"
    
    scenarios = {
        "String slicing from middle": original_url[15:],  # ".../help/example-domains"
        "Logging with max length": original_url[:20] + "...",
        "Display truncation": "..." + original_url[-20:],
        "Path-only extraction": "/" + "/".join(original_url.split("/")[3:]),
        "Domain removal": original_url.split("//")[1].split("/", 1)[1] if "//" in original_url else original_url,
    }
    
    for scenario, truncated in scenarios.items():
        print(f"\n{scenario}:")
        print(f"  Original: {original_url}")
        print(f"  Result:   {truncated}")
        
        # Test our validation against this truncated version
        from utils.validation import validate_crawl_url
        result = validate_crawl_url(truncated)
        print(f"  Validation: {'✅ PASS' if result['valid'] else '❌ FAIL'}")
        if not result['valid']:
            print(f"    Error: {result['error'][:100]}...")

def check_for_url_processing_functions():
    """Check if there are any functions in the codebase that might truncate URLs."""
    
    print("\n🔍 Checking for potential URL processing that might cause truncation...")
    
    # Search for string operations that might truncate URLs
    import subprocess
    
    patterns = [
        r'url\[.*:\]',  # String slicing on url variables
        r'\.\.\..*url',  # Adding ellipsis to URLs
        r'url.*\.\.\.',  # URLs followed by ellipsis
        r'url.*\[:.*\]',  # URL slicing patterns
    ]
    
    for pattern in patterns:
        try:
            result = subprocess.run(
                ['grep', '-rn', pattern, 'src/', 'tests/'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__)
            )
            if result.stdout:
                print(f"\nPattern '{pattern}':")
                for line in result.stdout.strip().split('\n')[:5]:  # Limit to first 5 matches
                    print(f"  {line}")
        except Exception as e:
            print(f"Error searching for pattern {pattern}: {e}")

def provide_debugging_recommendations():
    """Provide recommendations for debugging URL truncation."""
    
    print("\n📝 Debugging Recommendations:")
    print("=" * 50)
    
    recommendations = [
        "1. Add logging before URL validation to capture original URLs",
        "2. Check if any middleware or preprocessing is modifying URLs",
        "3. Look for logging systems that might truncate long strings",
        "4. Check if any JSON serialization/deserialization is affecting URLs",
        "5. Review any string formatting or templating that processes URLs",
        "6. Check browser console or client-side JavaScript for URL modification",
        "7. Verify MCP client is sending complete URLs (not truncating in display)",
    ]
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n🛠️  Immediate Action Items:")
    print("   • The validation fix prevents crashes and provides helpful errors")
    print("   • Users will get clear messages about truncated URLs")
    print("   • Auto-fixing handles common cases (missing protocols)")
    print("   • Enhanced logging helps identify the source of truncated URLs")

if __name__ == "__main__":
    simulate_common_truncation_scenarios()
    check_for_url_processing_functions()
    provide_debugging_recommendations()
    
    print("\n✅ URL truncation analysis completed!")
    print("   The validation fix should handle this issue effectively.")