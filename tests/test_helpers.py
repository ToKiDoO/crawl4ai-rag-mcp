"""Test utilities and helpers for the Crawl4AI MCP test suite."""

import asyncio
import json
import random
import string
from pathlib import Path
from typing import Any


class TestDataBuilder:
    """Builder pattern for test data creation."""

    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string for unique test data."""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def document(
        url: str | None = None,
        content: str | None = None,
        chunk_number: int = 1,
        metadata: dict | None = None,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create a test document with sensible defaults."""
        return {
            "url": url or f"https://test-{TestDataBuilder.random_string(8)}.com",
            "content": content or f"Test content {TestDataBuilder.random_string(20)}",
            "chunk_number": chunk_number,
            "metadata": metadata or {"source": "test", "timestamp": "2025-08-02"},
            "embedding": embedding or [random.random() for _ in range(1536)],
        }

    @staticmethod
    def search_result(
        score: float = 0.9,
        id: str | None = None,
        **doc_kwargs,
    ) -> dict[str, Any]:
        """Create a search result with document data."""
        doc = TestDataBuilder.document(**doc_kwargs)
        return {
            "id": id or f"test-{TestDataBuilder.random_string(8)}",
            "score": score,
            **doc,
        }

    @staticmethod
    def code_example(
        language: str = "python",
        code: str | None = None,
        description: str | None = None,
        url: str | None = None,
    ) -> dict[str, Any]:
        """Create a test code example."""
        default_code = '''def hello_world():
    """Test function."""
    return "Hello, World!"
'''
        return {
            "language": language,
            "code": code or default_code,
            "description": description or "Test code example",
            "url": url or f"https://test-{TestDataBuilder.random_string(8)}.com",
            "embedding": [random.random() for _ in range(1536)],
        }

    @staticmethod
    def batch_documents(count: int = 10, **kwargs) -> list[dict[str, Any]]:
        """Create a batch of test documents."""
        return [
            TestDataBuilder.document(
                url=f"https://test.com/page-{i}",
                content=f"Content for page {i}",
                chunk_number=i % 3 + 1,
                **kwargs,
            )
            for i in range(count)
        ]


class TestAssertions:
    """Custom assertions with detailed error messages."""

    @staticmethod
    def assert_search_result_valid(result: dict[str, Any]) -> None:
        """Validate search result structure."""
        required_fields = ["id", "score", "content", "url", "metadata"]
        for field in required_fields:
            assert field in result, (
                f"Missing required field '{field}' in result: {result}"
            )

        assert isinstance(result["score"], (int, float)), (
            f"Score must be numeric, got {type(result['score'])}"
        )
        assert 0 <= result["score"] <= 1, (
            f"Score must be between 0 and 1, got {result['score']}"
        )
        assert isinstance(result["metadata"], dict), (
            f"Metadata must be dict, got {type(result['metadata'])}"
        )

    @staticmethod
    def assert_embedding_valid(
        embedding: list[float],
        expected_dim: int = 1536,
    ) -> None:
        """Validate embedding structure."""
        assert isinstance(embedding, list), (
            f"Embedding must be list, got {type(embedding)}"
        )
        assert len(embedding) == expected_dim, (
            f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}"
        )
        assert all(isinstance(x, (int, float)) for x in embedding), (
            "All embedding values must be numeric"
        )

    @staticmethod
    def assert_api_response_valid(response: dict[str, Any]) -> None:
        """Validate API response structure."""
        assert "success" in response, f"Missing 'success' field in response: {response}"

        if response.get("success"):
            assert "data" in response, f"Successful response missing 'data': {response}"
        else:
            assert "error" in response, f"Failed response missing 'error': {response}"
            assert isinstance(response["error"], str), (
                f"Error must be string, got {type(response['error'])}"
            )

    @staticmethod
    def assert_async_callable(func) -> None:
        """Verify function is async callable."""
        assert asyncio.iscoroutinefunction(func), (
            f"{func.__name__} must be async function"
        )


class TestFixtures:
    """Reusable test fixtures."""

    @staticmethod
    async def create_test_database(adapter_class, **kwargs):
        """Create and initialize a test database adapter."""
        adapter = adapter_class(**kwargs)
        await adapter.initialize()
        return adapter

    @staticmethod
    def load_test_config(env_file: str = ".env.test") -> dict[str, str]:
        """Load test configuration from env file."""
        env_path = Path(env_file)
        config = {}

        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip().strip("\"'")

        return config

    @staticmethod
    def mock_async_response(data: Any, delay: float = 0.0):
        """Create a mock async response with optional delay."""

        async def _response():
            if delay > 0:
                await asyncio.sleep(delay)
            return data

        return _response()


class TestMetrics:
    """Track and report test metrics."""

    def __init__(self):
        self.start_times = {}
        self.durations = {}
        self.assertions = 0
        self.mocks_created = 0

    def start_timer(self, test_name: str):
        """Start timing a test."""
        import time

        self.start_times[test_name] = time.time()

    def end_timer(self, test_name: str):
        """End timing and record duration."""
        import time

        if test_name in self.start_times:
            self.durations[test_name] = time.time() - self.start_times[test_name]

    def record_assertion(self):
        """Record an assertion was made."""
        self.assertions += 1

    def record_mock(self):
        """Record a mock was created."""
        self.mocks_created += 1

    def report(self):
        """Generate metrics report."""
        avg_duration = (
            sum(self.durations.values()) / len(self.durations) if self.durations else 0
        )
        return {
            "total_tests": len(self.durations),
            "total_duration": sum(self.durations.values()),
            "average_duration": avg_duration,
            "total_assertions": self.assertions,
            "total_mocks": self.mocks_created,
            "mocks_per_test": self.mocks_created / len(self.durations)
            if self.durations
            else 0,
        }


# Example usage
if __name__ == "__main__":
    # Test data creation
    doc = TestDataBuilder.document()
    print(f"Sample document: {json.dumps(doc, indent=2)}")

    # Test assertions
    result = TestDataBuilder.search_result()
    TestAssertions.assert_search_result_valid(result)
    print("✅ Search result validation passed")

    # Test metrics
    metrics = TestMetrics()
    metrics.start_timer("test_example")
    metrics.record_assertion()
    metrics.record_mock()
    metrics.end_timer("test_example")
    print(f"Metrics: {json.dumps(metrics.report(), indent=2)}")
