"""Comprehensive unit tests for refactored module structure."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestCoreModule:
    """Test core module components."""

    def test_exceptions(self):
        """Test custom exceptions."""
        from core.exceptions import MCPToolError

        error = MCPToolError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_logging_configuration(self):
        """Test logging configuration."""
        from core.logging import configure_logging, logger

        configure_logging()
        assert logger is not None
        assert logger.name == "crawl4ai-mcp"

    @pytest.mark.asyncio
    async def test_context_lifespan(self):
        """Test context lifespan management."""
        from core.context import crawl4ai_lifespan

        mock_ctx = Mock()

        # Test lifespan execution
        async for _ in crawl4ai_lifespan(mock_ctx):
            # Verify context has required attributes
            assert hasattr(mock_ctx, "crawl4ai")


class TestUtilsModule:
    """Test utils module components."""

    def test_url_validation(self):
        """Test URL validation functions."""
        from utils.validation import validate_github_url, validate_script_path

        # Test GitHub URL validation
        assert validate_github_url("https://github.com/user/repo") is None
        assert validate_github_url("https://github.com/user/repo.git") is None
        assert validate_github_url("invalid-url") is not None

        # Test script path validation
        assert validate_script_path("/valid/path/script.py") is None
        assert validate_script_path("../../../etc/passwd") is not None

    def test_url_helpers(self):
        """Test URL helper functions."""
        from utils.url_helpers import is_sitemap, is_txt, normalize_url

        # Test URL normalization
        assert normalize_url("example.com") == "https://example.com"
        assert normalize_url("http://example.com") == "http://example.com"

        # Test sitemap detection
        assert is_sitemap("https://example.com/sitemap.xml")
        assert not is_sitemap("https://example.com/page.html")

        # Test text file detection
        assert is_txt("https://example.com/robots.txt")
        assert not is_txt("https://example.com/page.html")

    def test_text_processing(self):
        """Test text processing functions."""
        from utils.text_processing import smart_chunk_markdown

        # Test markdown chunking
        text = "# Header\n\n" + "Content " * 100
        chunks = smart_chunk_markdown(text, chunk_size=100)
        assert len(chunks) > 1
        assert all(len(chunk) <= 150 for chunk in chunks)  # Allow some overlap


class TestConfigModule:
    """Test configuration module."""

    def test_settings_loading(self):
        """Test settings are loaded correctly."""
        from config import get_settings

        settings = get_settings()

        # Test basic properties exist
        assert hasattr(settings, "host")
        assert hasattr(settings, "port")
        assert hasattr(settings, "vector_database")
        assert hasattr(settings, "openai_api_key")

    def test_settings_defaults(self):
        """Test default values."""
        from config import get_settings

        settings = get_settings()

        # Test defaults
        assert settings.host == "0.0.0.0"
        assert settings.port == "8051"
        assert settings.vector_database in ["qdrant", "supabase"]


class TestDatabaseModule:
    """Test database module components."""

    @pytest.mark.asyncio
    async def test_factory_creation(self):
        """Test database factory."""
        from database.factory import create_database_client

        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            # Mock the database creation
            with patch("database.factory.QdrantAdapter") as mock_qdrant:
                mock_instance = AsyncMock()
                mock_qdrant.return_value = mock_instance

                db = await create_database_client()
                assert db is not None

    def test_database_interface(self):
        """Test database base interface."""
        from database.base import VectorDatabase

        # Verify abstract methods exist
        assert hasattr(VectorDatabase, "store_documents")
        assert hasattr(VectorDatabase, "search_documents")
        assert hasattr(VectorDatabase, "close")


class TestServicesModule:
    """Test services module components."""

    @pytest.mark.asyncio
    async def test_search_service_import(self):
        """Test search service can be imported."""
        from services.search import search_and_process

        assert search_and_process is not None
        assert callable(search_and_process)

    @pytest.mark.asyncio
    async def test_smart_crawl_import(self):
        """Test smart crawl service can be imported."""
        from services.smart_crawl import smart_crawl_url

        assert smart_crawl_url is not None
        assert callable(smart_crawl_url)

    @pytest.mark.asyncio
    async def test_crawling_service_import(self):
        """Test crawling service functions."""
        from services.crawling import (
            crawl_batch,
            crawl_markdown_file,
            crawl_recursive_internal_links,
        )

        assert crawl_batch is not None
        assert crawl_markdown_file is not None
        assert crawl_recursive_internal_links is not None


class TestKnowledgeGraphModule:
    """Test knowledge graph module components."""

    def test_module_imports(self):
        """Test knowledge graph imports."""
        from knowledge_graph import (
            check_ai_script_hallucinations,
            parse_github_repository,
            query_knowledge_graph,
        )

        assert query_knowledge_graph is not None
        assert parse_github_repository is not None
        assert check_ai_script_hallucinations is not None


class TestToolsModule:
    """Test tools module and registration."""

    def test_register_tools_function(self):
        """Test register_tools function exists."""
        from tools import register_tools

        assert register_tools is not None
        assert callable(register_tools)

    def test_tool_registration(self):
        """Test tool registration pattern."""
        from tools import register_tools

        # Create mock MCP instance
        mock_mcp = Mock()
        mock_mcp.tool = Mock(return_value=lambda f: f)

        # Register tools
        register_tools(mock_mcp)

        # Verify tool decorator was called
        assert mock_mcp.tool.called
        # We expect 9 tools to be registered
        assert mock_mcp.tool.call_count == 9


class TestModuleIntegration:
    """Test module integration and imports."""

    def test_all_modules_importable(self):
        """Test all modules can be imported without errors."""
        modules = [
            "core",
            "config",
            "utils",
            "database",
            "services",
            "knowledge_graph",
            "tools",
        ]

        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"Failed to import {module}: {e}")

    def test_main_imports(self):
        """Test main.py can be imported."""
        try:
            import main

            assert hasattr(main, "mcp")
            assert hasattr(main, "main")
        except ImportError as e:
            pytest.fail(f"Failed to import main: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
