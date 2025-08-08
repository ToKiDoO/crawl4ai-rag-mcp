#!/usr/bin/env python3
"""
Test live scraping with the MCP service running.
"""

import requests


def test_mcp_service():
    """Test the MCP service directly via HTTP."""

    print("🔥 Testing live MCP service...")

    # Test single URL
    print("\n1. Testing single URL string...")
    try:
        response = requests.post(
            "http://localhost:8051/scrape_urls",
            json={
                "url": "https://httpbin.org/html",
                "return_raw_markdown": True,
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS: {result.get('success', False)}")
            if result.get("success"):
                print(f"   URL: {result.get('url', 'N/A')}")
                content_length = len(
                    result.get("results", {}).get(result.get("url", ""), "")
                )
                print(f"   Content length: {content_length} chars")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Exception: {e!s}")

    # Test JSON array
    print("\n2. Testing JSON array string...")
    try:
        response = requests.post(
            "http://localhost:8051/scrape_urls",
            json={
                "url": '["https://httpbin.org/html", "https://example.com"]',
                "return_raw_markdown": True,
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ SUCCESS: {result.get('success', False)}")
            if result.get("success"):
                urls_processed = result.get("summary", {}).get("urls_processed", 0)
                print(f"   URLs processed: {urls_processed}")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")

    except Exception as e:
        print(f"   ❌ Exception: {e!s}")

    # Test invalid input
    print("\n3. Testing invalid input...")
    try:
        response = requests.post(
            "http://localhost:8051/scrape_urls",
            json={
                "url": "",
                "return_raw_markdown": True,
            },
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            success = result.get("success", False)
            print(f"   Expected failure: {not success}")
            if not success:
                print(f"   Error message: {result.get('error', 'N/A')}")
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Exception: {e!s}")


if __name__ == "__main__":
    test_mcp_service()
