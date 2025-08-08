#!/usr/bin/env python3
"""Direct test of MCP server functionality without protocol overhead"""

import asyncio
import os

from crawl4ai import AsyncWebCrawler


async def test_crawl4ai_directly():
    """Test the core crawl4ai functionality"""

    print("Testing Crawl4AI functionality directly...\n")

    # Test 1: Basic crawling
    print("1. Testing basic web crawling...")
    async with AsyncWebCrawler() as crawler:
        try:
            result = await crawler.arun(
                url="https://example.com",
                word_count_threshold=10,
                verbose=False,
            )

            if result.success:
                print("✅ Crawling successful!")
                print(f"   - Title: {result.metadata.get('title', 'N/A')}")
                print(f"   - Content length: {len(result.markdown)} characters")
                print(f"   - First 200 chars: {result.markdown[:200]}...")
            else:
                print("❌ Crawling failed:", result.error_message)

        except Exception as e:
            print(f"❌ Error during crawling: {e}")

    # Test 2: Check SearXNG availability
    print("\n2. Testing SearXNG search engine...")
    import aiohttp

    searxng_url = os.getenv("SEARXNG_URL", "http://localhost:8081")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{searxng_url}/search?q=test&format=json"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ SearXNG is accessible!")
                    print(f"   - Results found: {len(data.get('results', []))}")
                else:
                    print(f"❌ SearXNG returned status: {response.status}")
    except Exception as e:
        print(f"❌ SearXNG connection error: {e}")

    # Test 3: Check Qdrant availability
    print("\n3. Testing Qdrant vector database...")
    from qdrant_client import QdrantClient

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    try:
        client = QdrantClient(url=qdrant_url)
        collections = client.get_collections()
        print("✅ Qdrant is accessible!")
        print(f"   - Collections: {[c.name for c in collections.collections]}")

        # Check if crawled_pages collection exists
        collection_names = [c.name for c in collections.collections]
        if "crawled_pages" in collection_names:
            collection_info = client.get_collection("crawled_pages")
            print(f"   - crawled_pages vectors: {collection_info.vectors_count}")
        else:
            print(
                "   - crawled_pages collection not found (will be created on first use)"
            )

    except Exception as e:
        print(f"❌ Qdrant connection error: {e}")

    print("\n4. Testing embedding generation...")
    try:
        # This would normally use OpenAI but we'll skip if no API key
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and not api_key.startswith("sk-test"):
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="Test embedding",
            )
            print("✅ OpenAI embedding generation works!")
            print(f"   - Embedding dimension: {len(response.data[0].embedding)}")
        else:
            print("⚠️  Skipping OpenAI test (no valid API key)")
    except Exception as e:
        print(f"❌ Embedding generation error: {e}")


if __name__ == "__main__":
    # Set test environment
    os.environ["VECTOR_DATABASE"] = "qdrant"
    os.environ["QDRANT_URL"] = "http://localhost:6333"
    os.environ["SEARXNG_URL"] = "http://localhost:8081"

    asyncio.run(test_crawl4ai_directly())
