"""
Simplified integration tests using test doubles.
"""

import os
import sys

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tests.factories import DocumentFactory
from tests.test_doubles import FakeCrawler, FakeEmbeddingService, FakeQdrantClient


class FakeCrossEncoder:
    """Fake cross-encoder for reranking."""

    def __init__(self, model_name: str = "test-model"):
        self.model_name = model_name

    def predict(self, pairs: list[list[str]]) -> list[list[float]]:
        """Return fake reranking scores."""
        # Return descending scores for each pair
        return [[0.9 - i * 0.1 for i in range(len(pairs))]]


class TestIntegrationSimplified:
    """Simplified integration tests with test doubles."""

    @pytest.fixture
    def setup_environment(self):
        """Set up test environment."""
        # Force Qdrant as vector database
        os.environ["VECTOR_DATABASE"] = "qdrant"
        os.environ["QDRANT_URL"] = "http://localhost:6333"
        os.environ["OPENAI_API_KEY"] = "test-key"

        yield

        # Cleanup
        os.environ.pop("VECTOR_DATABASE", None)
        os.environ.pop("QDRANT_URL", None)

    @pytest.fixture
    def fake_services(self):
        """Create fake services for testing."""
        return {
            "crawler": FakeCrawler(
                responses={
                    "https://test.com": "<html><body>Test content about machine learning</body></html>",
                    "https://example.com": "<html><body>Example content about Python</body></html>",
                },
            ),
            "qdrant": FakeQdrantClient(),
            "embeddings": FakeEmbeddingService(),
            "reranker": FakeCrossEncoder(),
        }

    @pytest.mark.asyncio
    async def test_scrape_and_store_flow(self, setup_environment, fake_services):
        """Test the complete scrape and store flow."""
        # Simulate scraping
        url = "https://test.com"
        crawler = fake_services["crawler"]
        result = await crawler.arun(url)

        assert result.success is True
        assert "machine learning" in result.markdown

        # Simulate chunking and embedding
        chunks = [
            result.markdown[i : i + 100] for i in range(0, len(result.markdown), 100)
        ]
        embeddings_service = fake_services["embeddings"]
        embeddings = embeddings_service.create_embeddings(chunks)

        assert len(embeddings) == len(chunks)
        assert all(len(emb) == 1536 for emb in embeddings)

        # Simulate storing in Qdrant
        qdrant = fake_services["qdrant"]
        points = [
            {
                "id": f"{url}_chunk_{i}",
                "payload": {"url": url, "content": chunk, "chunk_number": i},
                "vector": embedding,
            }
            for i, (chunk, embedding) in enumerate(
                zip(chunks, embeddings, strict=False)
            )
        ]

        result = qdrant.upsert("crawled_pages", points)
        assert result["status"] == "ok"
        assert len(qdrant.collections.get("crawled_pages", [])) == len(points)

    @pytest.mark.asyncio
    async def test_rag_query_flow(self, setup_environment, fake_services):
        """Test the complete RAG query flow."""
        # Pre-populate Qdrant with test data
        qdrant = fake_services["qdrant"]
        test_docs = DocumentFactory.create_batch(5)

        # Set up search results
        qdrant.search_results = [
            {
                "id": f"doc_{i}",
                "score": 0.9 - i * 0.1,
                "payload": {
                    "url": doc.url,
                    "content": doc.content,
                    "chunk_number": doc.chunk_number,
                    "metadata": doc.metadata,
                },
            }
            for i, doc in enumerate(test_docs[:3])
        ]

        # Simulate query embedding
        query = "What is machine learning?"
        embeddings_service = fake_services["embeddings"]
        query_embedding = embeddings_service.create_embeddings([query])[0]

        # Simulate search
        search_results = qdrant.search("crawled_pages", query_embedding, limit=3)
        assert len(search_results) == 3
        assert search_results[0]["score"] > search_results[1]["score"]

        # Simulate reranking
        reranker = fake_services["reranker"]
        pairs = [[query, result["payload"]["content"]] for result in search_results]
        rerank_scores = reranker.predict(pairs)[0]

        assert len(rerank_scores) == len(search_results)
        assert all(isinstance(score, float) for score in rerank_scores)

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, setup_environment, fake_services):
        """Test error handling in the integration flow."""
        # Test crawler failure
        crawler = fake_services["crawler"]
        crawler.should_fail = True

        with pytest.raises(Exception) as exc_info:
            await crawler.arun("https://fail.com")
        assert "Failed to crawl" in str(exc_info.value)

        # Test Qdrant failure
        qdrant = fake_services["qdrant"]
        qdrant.should_fail = True

        with pytest.raises(Exception) as exc_info:
            qdrant.search("crawled_pages", [0.1] * 1536)
        assert "Search failed" in str(exc_info.value)

        # Test embeddings failure
        embeddings_service = fake_services["embeddings"]
        embeddings_service.should_fail = True

        with pytest.raises(Exception) as exc_info:
            embeddings_service.create_embeddings(["test text"])
        assert "Embedding creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_batch_processing_flow(self, setup_environment, fake_services):
        """Test batch processing in the integration."""
        urls = [f"https://test{i}.com" for i in range(10)]
        crawler = fake_services["crawler"]

        # Process URLs in batch
        results = []
        for url in urls:
            try:
                result = await crawler.arun(url)
                results.append(
                    {"url": url, "success": True, "content": result.markdown},
                )
            except Exception as e:
                results.append({"url": url, "success": False, "error": str(e)})

        # All should succeed with fake crawler
        assert all(r["success"] for r in results)
        assert len(results) == len(urls)

        # Simulate batch embedding
        embeddings_service = fake_services["embeddings"]
        contents = [r["content"] for r in results if r["success"]]
        embeddings = embeddings_service.create_embeddings(contents)

        assert len(embeddings) == len(contents)

        # Simulate batch storage
        qdrant = fake_services["qdrant"]
        points = [
            {
                "id": f"batch_{i}",
                "payload": {"url": results[i]["url"], "content": contents[i]},
                "vector": embeddings[i],
            }
            for i in range(len(contents))
        ]

        result = qdrant.upsert("crawled_pages", points)
        assert result["status"] == "ok"
