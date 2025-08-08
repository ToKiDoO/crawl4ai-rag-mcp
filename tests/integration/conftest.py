"""
Integration test configuration and fixtures.

Provides Docker-based test services and shared fixtures for integration testing.
Uses real services (Qdrant, SearXNG) running in Docker containers.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from database.factory import create_and_initialize_database
from database.qdrant_adapter import QdrantAdapter
from database.supabase_adapter import SupabaseAdapter


@pytest.fixture(scope="session")
def docker_compose_services():
    """Start Docker Compose services for integration tests."""
    compose_file = Path(__file__).parent.parent.parent / "docker-compose.yml"

    if not compose_file.exists():
        pytest.skip("Docker Compose file not found, skipping integration tests")

    # Start services
    try:
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "up",
                "-d",
                "--wait",
                "qdrant",
                "searxng",
                "valkey",
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )

        # Wait for services to be ready
        time.sleep(10)

        yield

    except subprocess.TimeoutExpired:
        pytest.fail("Docker services failed to start within timeout")
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start Docker services: {e}")
    finally:
        # Cleanup: Stop services
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down", "-v"],
                check=False,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            pass


@pytest.fixture(scope="session")
def qdrant_service_url(docker_compose_services):
    """Get Qdrant service URL for integration tests."""
    return "http://localhost:6333"


@pytest.fixture(scope="session")
def searxng_service_url(docker_compose_services):
    """Get SearXNG service URL for integration tests."""
    return "http://localhost:8080"


@pytest.fixture
async def qdrant_client(qdrant_service_url):
    """Create Qdrant client connected to test service."""
    adapter = QdrantAdapter(
        url=qdrant_service_url,
        api_key=None,  # No auth for test instance
    )

    # Initialize and clean up any existing data
    await adapter.initialize()

    # Clean up any existing test data
    try:
        # Delete all test data by filtering on test metadata
        import asyncio

        loop = asyncio.get_event_loop()
        if hasattr(adapter, "client") and adapter.client:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            try:
                test_filter = Filter(
                    must=[FieldCondition(key="test", match=MatchValue(value=True))],
                )
                await loop.run_in_executor(
                    None,
                    adapter.client.delete,
                    adapter.CRAWLED_PAGES,
                    test_filter,
                )
            except:
                pass  # Ignore cleanup errors
    except:
        pass  # Collection might not exist

    yield adapter

    # Cleanup after test
    try:
        import asyncio

        loop = asyncio.get_event_loop()
        if hasattr(adapter, "client") and adapter.client:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            try:
                test_filter = Filter(
                    must=[FieldCondition(key="test", match=MatchValue(value=True))],
                )
                await loop.run_in_executor(
                    None,
                    adapter.client.delete,
                    adapter.CRAWLED_PAGES,
                    test_filter,
                )
            except:
                pass  # Ignore cleanup errors
    except:
        pass


@pytest.fixture
async def supabase_client():
    """Create Supabase client for testing (if configured)."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        pytest.skip("Supabase credentials not configured, skipping Supabase tests")

    adapter = SupabaseAdapter(
        url=supabase_url,
        key=supabase_key,
        table_name="test_crawled_pages",
    )

    await adapter.initialize()

    # Clean up test data
    await adapter.delete_all_test_data()

    yield adapter

    # Cleanup
    await adapter.delete_all_test_data()


@pytest.fixture
async def database_factory(qdrant_client):
    """Create database factory with test configuration."""

    # Mock environment for testing
    test_env = {
        "VECTOR_DATABASE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "",
        "QDRANT_COLLECTION_NAME": "test_collection",
    }

    with patch.dict(os.environ, test_env):
        adapter = await create_and_initialize_database()

        yield adapter

        # Cleanup
        if hasattr(adapter, "close"):
            await adapter.close()


@pytest.fixture
def integration_test_env():
    """Set up environment variables for integration tests."""
    test_env = {
        "ENVIRONMENT": "test",
        "DATABASE_TYPE": "qdrant",
        "QDRANT_URL": "http://localhost:6333",
        "QDRANT_API_KEY": "",
        "QDRANT_COLLECTION_NAME": "test_collection",
        "SEARXNG_URL": "http://localhost:8080",
        "CACHE_REDIS_URL": "redis://localhost:6379/1",
        "ENHANCED_CONTEXT": "false",
        "USE_RERANKING": "false",
        "USE_AGENTIC_RAG": "false",
        "USE_HYBRID_SEARCH": "false",
        "LOG_LEVEL": "INFO",
    }

    # Backup original environment
    original_env = {k: os.environ.get(k) for k in test_env}

    # Set test environment
    os.environ.update(test_env)

    yield test_env

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
async def crawl4ai_session():
    """Create a Crawl4AI session for testing."""
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(
            headless=True,
            verbose=False,
            # Use minimal config for testing
            browser_type="chromium",
            headers={"User-Agent": "test-crawler/1.0"},
        ) as crawler:
            yield crawler

    except ImportError:
        # Mock crawler if Crawl4AI not available
        mock_crawler = AsyncMock()
        mock_crawler.arun = AsyncMock()
        mock_crawler.arun_many = AsyncMock()
        yield mock_crawler


@pytest.fixture
def sample_urls():
    """Sample URLs for testing."""
    return [
        "https://example.com",
        "https://httpbin.org/json",
        "https://httpbin.org/html",
    ]


@pytest.fixture
def sample_crawl_results():
    """Sample crawl results for testing."""
    return [
        {
            "url": "https://example.com",
            "html": "<html><body><h1>Example</h1><p>This is an example page.</p></body></html>",
            "cleaned_html": "<h1>Example</h1><p>This is an example page.</p>",
            "markdown": "# Example\n\nThis is an example page.",
            "extracted_content": "Example\nThis is an example page.",
            "success": True,
            "status_code": 200,
            "response_headers": {"content-type": "text/html"},
            "links": {"internal": [], "external": []},
            "media": {"images": [], "videos": [], "audios": []},
        },
        {
            "url": "https://httpbin.org/json",
            "html": '<html><body><pre>{"slideshow": {"title": "Sample"}}</pre></body></html>',
            "cleaned_html": '<pre>{"slideshow": {"title": "Sample"}}</pre>',
            "markdown": '```\n{"slideshow": {"title": "Sample"}}\n```',
            "extracted_content": '{"slideshow": {"title": "Sample"}}',
            "success": True,
            "status_code": 200,
            "response_headers": {"content-type": "application/json"},
            "links": {"internal": [], "external": []},
            "media": {"images": [], "videos": [], "audios": []},
        },
    ]


@pytest.fixture
def performance_thresholds():
    """Performance thresholds for integration tests."""
    return {
        "crawl_single_url_ms": 5000,  # 5 seconds max
        "crawl_batch_urls_ms": 15000,  # 15 seconds max for batch
        "store_document_ms": 1000,  # 1 second max
        "search_documents_ms": 2000,  # 2 seconds max
        "e2e_workflow_ms": 20000,  # 20 seconds max for full workflow
    }


@pytest.fixture
async def cleanup_database(qdrant_client):
    """Fixture to clean up database after each test."""
    yield

    # Clean up test data
    try:
        # Delete all documents in test collection
        await qdrant_client.client.delete(
            collection_name=qdrant_client.collection_name,
            points_selector={
                "filter": {"must": [{"key": "test", "match": {"value": True}}]},
            },
        )
    except Exception:
        pass  # Ignore cleanup errors


# Pytest markers for integration tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring Docker services",
    )
    config.addinivalue_line("markers", "e2e: mark test as end-to-end workflow test")
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance benchmark",
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Add markers to integration tests automatically."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.slow)
