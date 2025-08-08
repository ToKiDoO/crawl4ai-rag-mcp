#!/usr/bin/env python3
"""
Simple test script to verify Qdrant connection in CI environment.
This helps debug CI failures by testing the connection directly.
"""

import os
import sys
import time
from urllib.parse import urlparse

import requests


def test_qdrant_connection():
    """Test basic Qdrant connectivity."""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    print(f"🔍 Testing Qdrant connection at: {qdrant_url}")

    # Parse URL
    parsed = urlparse(qdrant_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Test endpoints
    endpoints = [
        "/readyz",
        "/health",
        "/",
        "/collections",
    ]

    success = False

    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"\n📡 Testing endpoint: {url}")

            response = requests.get(url, timeout=5)
            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ Success! Response: {response.text[:100]}...")
                success = True

                # If we can reach Qdrant, try to get collections
                if endpoint == "/collections":
                    try:
                        data = response.json()
                        print(f"   Collections: {data}")
                    except:
                        pass
            else:
                print(f"   ❌ Failed with status: {response.status_code}")

        except requests.exceptions.ConnectionError:
            print("   ❌ Connection refused")
        except requests.exceptions.Timeout:
            print("   ❌ Request timeout")
        except Exception as e:
            print(f"   ❌ Error: {type(e).__name__}: {e}")

    if success:
        print("\n✅ Qdrant is accessible!")
        return 0
    print("\n❌ Could not connect to Qdrant!")
    return 1


def main():
    """Main entry point."""
    # Wait a bit if requested
    wait_time = int(os.getenv("WAIT_BEFORE_TEST", "0"))
    if wait_time > 0:
        print(f"⏳ Waiting {wait_time} seconds before testing...")
        time.sleep(wait_time)

    return test_qdrant_connection()


if __name__ == "__main__":
    sys.exit(main())
