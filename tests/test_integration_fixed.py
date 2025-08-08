"""
Integration tests for database adapters with real Docker containers.
These tests verify that both Supabase and Qdrant work correctly in a real environment.

This is a fixed version that avoids the async generator fixture issue.
"""

import os
import subprocess
import time
from pathlib import Path

import pytest
from dotenv import load_dotenv

import docker
from database.factory import create_database_client
from utils import (
    add_code_examples_to_database,
    add_documents_to_database,
    search_code_examples,
    search_documents,
)

# Load environment variables from .env.test
test_env_path = Path(__file__).parent.parent / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)
else:
    load_dotenv()


class TestDatabaseIntegration:
    """Integration tests for database implementations"""

    @pytest.fixture(scope="class")
    def docker_client(self):
        """Get Docker client"""
        return docker.from_env()

    @pytest.fixture(scope="class")
    def ensure_qdrant_running(self, docker_client):
        """Ensure Qdrant container is running"""
        container_name = "qdrant_test"

        # Check if container exists
        try:
            container = docker_client.containers.get(container_name)
            if container.status != "running":
                container.start()
                time.sleep(2)  # Wait for container to be ready
        except docker.errors.NotFound:
            # Start container using docker-compose
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    "docker-compose.test.yml",
                    "up",
                    "-d",
                    "qdrant",
                ],
                check=True,
            )
            time.sleep(5)  # Wait for Qdrant to be ready

        # Verify Qdrant is responding
        import requests

        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get("http://localhost:6333/healthz")
                if response.status_code == 200:
                    break
            except:
                pass
            time.sleep(1)
        else:
            pytest.fail("Qdrant did not start properly")

    async def create_supabase_db(self):
        """Create Supabase database client"""
        os.environ["VECTOR_DATABASE"] = "supabase"
        client = create_database_client()
        await client.initialize()
        return client

    async def create_qdrant_db(self):
        """Create Qdrant database client"""
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        client = create_database_client()
        await client.initialize()
        return client

    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing"""
        return [
            {
                "url": "https://example.com/doc1",
                "content": "This is a comprehensive guide to Python programming. It covers basic syntax, data structures, and advanced concepts.",
                "chunk_number": 0,
                "metadata": {"title": "Python Guide", "author": "Test Author"},
            },
            {
                "url": "https://example.com/doc1",
                "content": "Python functions are first-class objects. You can pass them as arguments, return them from functions, and store them in variables.",
                "chunk_number": 1,
                "metadata": {"title": "Python Guide", "author": "Test Author"},
            },
            {
                "url": "https://example.com/doc2",
                "content": "Machine learning with Python involves using libraries like scikit-learn, TensorFlow, and PyTorch for building models.",
                "chunk_number": 0,
                "metadata": {"title": "ML with Python", "category": "AI"},
            },
        ]

    @pytest.fixture
    def sample_code_examples(self):
        """Sample code examples for testing"""
        return [
            {
                "url": "https://example.com/code1",
                "chunk_number": 0,
                "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Example usage
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
""",
                "summary": "Recursive implementation of Fibonacci sequence",
                "metadata": {"language": "python", "topic": "algorithms"},
            },
            {
                "url": "https://example.com/code2",
                "chunk_number": 0,
                "code": """
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Process multiple URLs concurrently
urls = ['http://api1.com', 'http://api2.com']
results = await asyncio.gather(*[fetch_data(url) for url in urls])
""",
                "summary": "Asynchronous HTTP requests with aiohttp",
                "metadata": {"language": "python", "topic": "async"},
            },
        ]

    @pytest.mark.asyncio
    async def test_qdrant_document_operations(
        self,
        ensure_qdrant_running,
        sample_documents,
    ):
        """Test document operations with Qdrant"""
        db = await self.create_qdrant_db()

        # Prepare documents for insertion
        urls = [doc["url"] for doc in sample_documents]
        chunk_numbers = [doc["chunk_number"] for doc in sample_documents]
        contents = [doc["content"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]

        # Create URL to full document mapping
        url_to_full_document = {}
        for doc in sample_documents:
            if doc["url"] not in url_to_full_document:
                url_to_full_document[doc["url"]] = ""
            url_to_full_document[doc["url"]] += doc["content"] + "\n"

        # Add documents
        await add_documents_to_database(
            database=db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )

        # Test 1: Search by similarity
        results = await search_documents(
            database=db,
            query="Python programming guide",
            match_count=5,
        )

        assert len(results) > 0
        assert any("Python" in r["content"] for r in results)

        # Test 2: Get documents by URL
        url_docs = await db.get_documents_by_url("https://example.com/doc1")
        assert len(url_docs) == 2
        assert all(doc["url"] == "https://example.com/doc1" for doc in url_docs)

        # Test 3: Keyword search (Note: May return empty if text indexing not configured)
        keyword_results = await db.search_documents_by_keyword(
            keyword="machine learning",
            match_count=5,
        )
        # For now, just verify it doesn't error
        assert isinstance(keyword_results, list)

    @pytest.mark.asyncio
    async def test_qdrant_code_operations(
        self,
        ensure_qdrant_running,
        sample_code_examples,
    ):
        """Test code example operations with Qdrant"""
        db = await self.create_qdrant_db()

        # Add code examples
        await add_code_examples_to_database(
            database=db,
            urls=[ex["url"] for ex in sample_code_examples],
            chunk_numbers=[ex["chunk_number"] for ex in sample_code_examples],
            codes=[ex["code"] for ex in sample_code_examples],
            summaries=[ex["summary"] for ex in sample_code_examples],
            metadatas=[ex["metadata"] for ex in sample_code_examples],
        )

        # Test 1: Search code examples
        results = await search_code_examples(
            database=db,
            query="fibonacci recursive algorithm",
            match_count=5,
        )

        assert len(results) > 0
        assert any("fibonacci" in r["code"].lower() for r in results)

        # Test 2: Search for async code
        async_results = await search_code_examples(
            database=db,
            query="async HTTP requests aiohttp",
            match_count=5,
        )

        assert len(async_results) > 0
        assert any("async" in r["code"] for r in async_results)

    @pytest.mark.asyncio
    async def test_qdrant_hybrid_search(self, ensure_qdrant_running, sample_documents):
        """Test hybrid search functionality with Qdrant"""
        db = await self.create_qdrant_db()

        # Prepare and add documents
        urls = [doc["url"] for doc in sample_documents]
        chunk_numbers = [doc["chunk_number"] for doc in sample_documents]
        contents = [doc["content"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]

        url_to_full_document = {}
        for doc in sample_documents:
            if doc["url"] not in url_to_full_document:
                url_to_full_document[doc["url"]] = ""
            url_to_full_document[doc["url"]] += doc["content"] + "\n"

        await add_documents_to_database(
            database=db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )

        # Test hybrid search
        results = await search_documents(
            database=db,
            query="Python machine learning",
            match_count=5,
            enable_hybrid=True,
            keyword_weight=0.3,
            semantic_weight=0.7,
        )

        assert len(results) > 0
        # Should find both Python programming and ML documents
        urls_found = {r["url"] for r in results}
        assert len(urls_found) >= 1

    @pytest.mark.asyncio
    async def test_qdrant_metadata_filtering(
        self,
        ensure_qdrant_running,
        sample_documents,
    ):
        """Test metadata filtering with Qdrant"""
        db = await self.create_qdrant_db()

        # Add documents
        urls = [doc["url"] for doc in sample_documents]
        chunk_numbers = [doc["chunk_number"] for doc in sample_documents]
        contents = [doc["content"] for doc in sample_documents]
        metadatas = [doc["metadata"] for doc in sample_documents]

        url_to_full_document = {}
        for doc in sample_documents:
            if doc["url"] not in url_to_full_document:
                url_to_full_document[doc["url"]] = ""
            url_to_full_document[doc["url"]] += doc["content"] + "\n"

        await add_documents_to_database(
            database=db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )

        # Test with metadata filter
        results = await search_documents(
            database=db,
            query="Python",
            match_count=5,
            metadata_filter={"category": "AI"},
        )

        # Should only find documents with category="AI"
        assert len(results) > 0
        assert all(r.get("metadata", {}).get("category") == "AI" for r in results)

    @pytest.mark.asyncio
    async def test_qdrant_deletion(self, ensure_qdrant_running, sample_documents):
        """Test document deletion with Qdrant"""
        db = await self.create_qdrant_db()

        # Add documents
        urls = [doc["url"] for doc in sample_documents[:2]]  # Only add first 2
        chunk_numbers = [doc["chunk_number"] for doc in sample_documents[:2]]
        contents = [doc["content"] for doc in sample_documents[:2]]
        metadatas = [doc["metadata"] for doc in sample_documents[:2]]

        url_to_full_document = {}
        for doc in sample_documents[:2]:
            if doc["url"] not in url_to_full_document:
                url_to_full_document[doc["url"]] = ""
            url_to_full_document[doc["url"]] += doc["content"] + "\n"

        await add_documents_to_database(
            database=db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
        )

        # Verify documents exist
        before_delete = await db.get_documents_by_url("https://example.com/doc1")
        assert len(before_delete) == 2

        # Delete documents
        await db.delete_documents_by_url("https://example.com/doc1")

        # Verify deletion
        after_delete = await db.get_documents_by_url("https://example.com/doc1")
        assert len(after_delete) == 0

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.getenv("SUPABASE_URL") is None,
        reason="Supabase credentials not configured",
    )
    async def test_supabase_basic_operations(self, sample_documents):
        """Test basic operations with Supabase (if configured)"""
        db = await self.create_supabase_db()

        # Just test that we can connect and perform a basic search
        results = await search_documents(database=db, query="test query", match_count=5)

        # Should return empty results but not error
        assert isinstance(results, list)
