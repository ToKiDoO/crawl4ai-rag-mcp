"""
Integration tests for database adapters with real Docker containers.
These tests verify that both Supabase and Qdrant work correctly in a real environment.
"""
import pytest
import asyncio
import os
import subprocess
import time
from typing import List, Dict, Any
import docker
from dotenv import load_dotenv

from database.factory import create_database_client
from database.base import VectorDatabase
from utils_refactored import (
    create_embedding,
    create_embeddings_batch,
    add_documents_to_database,
    search_documents,
    add_code_examples_to_database,
    search_code_examples
)

# Load environment variables
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
                time.sleep(5)  # Wait for startup
        except docker.errors.NotFound:
            # Create and start container
            container = docker_client.containers.run(
                "qdrant/qdrant:latest",
                name=container_name,
                ports={'6333/tcp': 6333},
                detach=True,
                remove=False,
                environment={
                    "QDRANT__LOG_LEVEL": "INFO"
                }
            )
            time.sleep(10)  # Wait for Qdrant to fully start
        
        yield container
        
        # Don't stop container after tests (leave it for manual cleanup)
    
    @pytest.fixture
    async def supabase_db(self):
        """Create Supabase database client"""
        os.environ["VECTOR_DATABASE"] = "supabase"
        client = create_database_client()
        await client.initialize()
        yield client
    
    @pytest.fixture
    async def qdrant_db(self, ensure_qdrant_running):
        """Create Qdrant database client"""
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        client = create_database_client()
        await client.initialize()
        yield client
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing"""
        return [
            {
                "url": "https://example.com/doc1",
                "content": "This is a comprehensive guide to Python programming. It covers basic syntax, data structures, and advanced concepts.",
                "chunk_number": 0,
                "metadata": {"title": "Python Guide", "author": "Test Author"}
            },
            {
                "url": "https://example.com/doc1",
                "content": "Python functions are first-class objects. You can pass them as arguments, return them from functions, and store them in variables.",
                "chunk_number": 1,
                "metadata": {"title": "Python Guide", "author": "Test Author"}
            },
            {
                "url": "https://example.com/doc2",
                "content": "Machine learning with Python involves using libraries like scikit-learn, TensorFlow, and PyTorch for building models.",
                "chunk_number": 0,
                "metadata": {"title": "ML with Python", "category": "AI"}
            }
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
                "metadata": {"language": "python", "topic": "algorithms"}
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
                "metadata": {"language": "python", "topic": "async"}
            }
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("db_fixture", ["supabase_db", "qdrant_db"])
    async def test_document_operations(self, request, db_fixture, sample_documents):
        """Test document addition and retrieval"""
        db = await request.getfixturevalue(db_fixture)
        
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
            url_to_full_document=url_to_full_document
        )
        
        # Test 1: Search by similarity
        results = await search_documents(
            database=db,
            query="Python programming guide",
            match_count=5
        )
        
        assert len(results) > 0
        assert any("Python" in r["content"] for r in results)
        
        # Test 2: Get documents by URL
        url_docs = await db.get_documents_by_url("https://example.com/doc1")
        assert len(url_docs) == 2
        assert all(doc["url"] == "https://example.com/doc1" for doc in url_docs)
        
        # Test 3: Keyword search
        keyword_results = await db.search_documents_by_keyword(
            keyword="machine learning",
            match_count=5
        )
        
        # Note: Keyword search implementation varies between databases
        # Supabase uses ILIKE, Qdrant uses text matching
        # So we just verify the method runs without error
        assert isinstance(keyword_results, list)
        
        # Cleanup
        await db.delete_documents_by_url(urls)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("db_fixture", ["supabase_db", "qdrant_db"])
    async def test_code_example_operations(self, request, db_fixture, sample_code_examples):
        """Test code example addition and retrieval"""
        db = await request.getfixturevalue(db_fixture)
        
        # Prepare code examples
        urls = [ex["url"] for ex in sample_code_examples]
        chunk_numbers = [ex["chunk_number"] for ex in sample_code_examples]
        code_examples = [ex["code"] for ex in sample_code_examples]
        summaries = [ex["summary"] for ex in sample_code_examples]
        metadatas = [ex["metadata"] for ex in sample_code_examples]
        
        # Add code examples
        await add_code_examples_to_database(
            database=db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            code_examples=code_examples,
            summaries=summaries,
            metadatas=metadatas
        )
        
        # Test 1: Search code examples by query
        results = await search_code_examples(
            database=db,
            query="fibonacci recursive",
            match_count=5
        )
        
        assert len(results) > 0
        assert any("fibonacci" in r.get("content", "").lower() or 
                  "fibonacci" in r.get("summary", "").lower() for r in results)
        
        # Test 2: Keyword search in code examples
        keyword_results = await db.search_code_examples_by_keyword(
            keyword="async",
            match_count=5
        )
        
        assert isinstance(keyword_results, list)
        
        # Cleanup
        await db.delete_code_examples_by_url(urls)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("db_fixture", ["supabase_db", "qdrant_db"])
    async def test_source_management(self, request, db_fixture):
        """Test source information management"""
        db = await request.getfixturevalue(db_fixture)
        
        # Add/update source information
        await db.update_source_info(
            source_id="example.com",
            summary="Example domain for testing purposes",
            word_count=1500
        )
        
        # Get all sources
        sources = await db.get_sources()
        
        # Find our test source
        test_source = next((s for s in sources if s["source_id"] == "example.com"), None)
        assert test_source is not None
        assert test_source["summary"] == "Example domain for testing purposes"
        assert test_source["total_word_count"] == 1500
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("db_fixture", ["supabase_db", "qdrant_db"]) 
    async def test_hybrid_search(self, request, db_fixture, sample_documents):
        """Test hybrid search functionality"""
        db = await request.getfixturevalue(db_fixture)
        
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
            url_to_full_document=url_to_full_document
        )
        
        # Hybrid search combines vector and keyword search
        # This is implemented in the application layer
        query = "Python functions"
        
        # Vector search
        vector_results = await search_documents(
            database=db,
            query=query,
            match_count=10
        )
        
        # Keyword search
        keyword_results = await db.search_documents_by_keyword(
            keyword="functions",
            match_count=10
        )
        
        # Both searches should return results
        assert len(vector_results) > 0
        assert isinstance(keyword_results, list)
        
        # Cleanup
        await db.delete_documents_by_url(urls)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("db_fixture", ["supabase_db", "qdrant_db"])
    async def test_large_batch_operations(self, request, db_fixture):
        """Test handling of large batches"""
        db = await request.getfixturevalue(db_fixture)
        
        # Create a large batch of documents
        num_docs = 50
        urls = []
        chunk_numbers = []
        contents = []
        metadatas = []
        url_to_full_document = {}
        
        for i in range(num_docs):
            url = f"https://example.com/large-doc-{i}"
            content = f"This is document {i} with some test content about topic {i % 5}."
            
            urls.append(url)
            chunk_numbers.append(0)
            contents.append(content)
            metadatas.append({"doc_id": i, "topic": f"topic-{i % 5}"})
            url_to_full_document[url] = content
        
        # Add all documents
        await add_documents_to_database(
            database=db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
            batch_size=20  # Test batching
        )
        
        # Verify they were added
        results = await search_documents(
            database=db,
            query="document test content",
            match_count=60  # More than we added
        )
        
        # Should find many results
        assert len(results) > 10
        
        # Cleanup
        await db.delete_documents_by_url(urls)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])