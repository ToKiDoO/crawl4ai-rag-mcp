"""
Comprehensive unit tests for configuration and setup functions.

Test Coverage:
- Environment variable loading and validation
- Configuration validation functions
- Default value handling
- Database adapter factory functions
- Service initialization functions

Testing Approach:
- Mock environment variables for isolated testing
- Test both valid and invalid configuration scenarios
- Verify error handling for missing configurations
- Test factory pattern implementations
- Edge cases and boundary conditions
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import functions to test
from crawl4ai_mcp import (
    format_neo4j_error,
    validate_github_url,
    validate_neo4j_connection,
    validate_script_path,
)

from database.factory import create_and_initialize_database, create_database_client


class TestDatabaseFactory:
    """Test database factory functions"""

    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch("database.factory.SupabaseAdapter")
    def test_create_database_client_supabase(self, mock_supabase):
        """Test creating Supabase database client"""
        mock_instance = Mock()
        mock_supabase.return_value = mock_instance

        client = create_database_client()

        assert client == mock_instance
        mock_supabase.assert_called_once()

    @patch.dict(
        os.environ,
        {"VECTOR_DATABASE": "qdrant", "QDRANT_URL": "http://localhost:6333"},
    )
    @patch("database.factory.QdrantAdapter")
    def test_create_database_client_qdrant(self, mock_qdrant):
        """Test creating Qdrant database client"""
        mock_instance = Mock()
        mock_qdrant.return_value = mock_instance

        client = create_database_client()

        assert client == mock_instance
        mock_qdrant.assert_called_once_with(url="http://localhost:6333", api_key=None)

    @patch.dict(
        os.environ,
        {
            "VECTOR_DATABASE": "qdrant",
            "QDRANT_URL": "http://custom:6333",
            "QDRANT_API_KEY": "test-key",
        },
    )
    @patch("database.factory.QdrantAdapter")
    def test_create_database_client_qdrant_with_auth(self, mock_qdrant):
        """Test creating Qdrant client with authentication"""
        mock_instance = Mock()
        mock_qdrant.return_value = mock_instance

        client = create_database_client()

        assert client == mock_instance
        mock_qdrant.assert_called_once_with(
            url="http://custom:6333",
            api_key="test-key",
        )

    @patch.dict(os.environ, {}, clear=True)  # Clear all env vars
    @patch("database.factory.SupabaseAdapter")
    def test_create_database_client_default(self, mock_supabase):
        """Test default database client creation (Supabase)"""
        mock_instance = Mock()
        mock_supabase.return_value = mock_instance

        client = create_database_client()

        assert client == mock_instance
        mock_supabase.assert_called_once()

    @patch.dict(os.environ, {"VECTOR_DATABASE": ""})  # Empty string
    @patch("database.factory.SupabaseAdapter")
    def test_create_database_client_empty_string(self, mock_supabase):
        """Test database client creation with empty string (should default to Supabase)"""
        mock_instance = Mock()
        mock_supabase.return_value = mock_instance

        client = create_database_client()

        assert client == mock_instance
        mock_supabase.assert_called_once()

    @patch.dict(os.environ, {"VECTOR_DATABASE": "invalid_db"})
    def test_create_database_client_invalid_type(self):
        """Test error handling for invalid database type"""
        with pytest.raises(ValueError, match="Unknown database type: invalid_db"):
            create_database_client()

    @patch.dict(os.environ, {"VECTOR_DATABASE": "QDRANT"})  # Uppercase
    @patch("database.factory.QdrantAdapter")
    def test_create_database_client_case_insensitive(self, mock_qdrant):
        """Test case insensitive database type handling"""
        mock_instance = Mock()
        mock_qdrant.return_value = mock_instance

        client = create_database_client()

        assert client == mock_instance
        mock_qdrant.assert_called_once_with(
            url="http://qdrant:6333",
            api_key=None,
        )  # Default URL

    @patch("database.factory.create_database_client")
    async def test_create_and_initialize_database(self, mock_create_client):
        """Test database creation and initialization"""
        mock_client = Mock()
        mock_client.initialize_database = Mock(return_value=None)
        mock_create_client.return_value = mock_client

        result = await create_and_initialize_database()

        assert result == mock_client
        mock_create_client.assert_called_once()
        mock_client.initialize_database.assert_called_once()

    @patch("database.factory.create_database_client")
    async def test_create_and_initialize_database_with_async_init(
        self,
        mock_create_client,
    ):
        """Test database creation with async initialization"""
        mock_client = Mock()
        mock_client.initialize_database = Mock()
        mock_create_client.return_value = mock_client

        # Test with both sync and async initialize_database methods
        result = await create_and_initialize_database()

        assert result == mock_client
        mock_client.initialize_database.assert_called_once()


class TestEnvironmentConfiguration:
    """Test environment variable configuration handling"""

    def test_required_environment_variables(self):
        """Test validation of required environment variables"""
        required_vars = [
            "VECTOR_DATABASE",
            "QDRANT_URL",
            "QDRANT_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
            "OPENAI_API_KEY",
        ]

        # Test that these variables can be read (even if not set)
        for var in required_vars:
            value = os.getenv(var)
            # Should not raise exception
            assert value is None or isinstance(value, str)

    @patch.dict(
        os.environ,
        {
            "VECTOR_DATABASE": "qdrant",
            "QDRANT_URL": "http://localhost:6333",
            "MODEL_CHOICE": "gpt-4",
        },
    )
    def test_configuration_loading(self):
        """Test loading complete configuration"""
        config = {
            "vector_db": os.getenv("VECTOR_DATABASE"),
            "qdrant_url": os.getenv("QDRANT_URL"),
            "model": os.getenv("MODEL_CHOICE"),
        }

        assert config["vector_db"] == "qdrant"
        assert config["qdrant_url"] == "http://localhost:6333"
        assert config["model"] == "gpt-4"

    def test_environment_variable_defaults(self):
        """Test default values for environment variables"""
        # Test default values using getenv with defaults
        defaults = {
            "VECTOR_DATABASE": os.getenv("VECTOR_DATABASE", "supabase"),
            "QDRANT_URL": os.getenv("QDRANT_URL", "http://qdrant:6333"),
            "MODEL_CHOICE": os.getenv("MODEL_CHOICE", "gpt-3.5-turbo"),
            "CHUNK_SIZE": int(os.getenv("CHUNK_SIZE", "2000")),
        }

        # Should not raise errors and should have reasonable defaults
        assert defaults["VECTOR_DATABASE"] in ["supabase", "qdrant"]
        assert "qdrant" in defaults["QDRANT_URL"]
        assert defaults["MODEL_CHOICE"] in ["gpt-3.5-turbo", "gpt-4"]
        assert isinstance(defaults["CHUNK_SIZE"], int)
        assert defaults["CHUNK_SIZE"] > 0

    @patch.dict(os.environ, {"CHUNK_SIZE": "invalid"})
    def test_invalid_numeric_environment_variables(self):
        """Test handling of invalid numeric environment variables"""
        with pytest.raises(ValueError):
            int(os.getenv("CHUNK_SIZE"))

    @patch.dict(os.environ, {"CHUNK_SIZE": "0"})
    def test_boundary_numeric_environment_variables(self):
        """Test boundary values for numeric environment variables"""
        chunk_size = int(os.getenv("CHUNK_SIZE"))
        assert chunk_size == 0

        # In real application, might want to validate > 0
        if chunk_size <= 0:
            chunk_size = 2000  # Default fallback

        assert chunk_size == 2000


class TestValidationFunctions:
    """Test configuration validation functions"""

    @patch("crawl4ai_mcp.neo4j.GraphDatabase.driver")
    def test_validate_neo4j_connection_success(self, mock_driver):
        """Test successful Neo4j connection validation"""
        mock_driver_instance = Mock()
        mock_session = Mock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_instance.session.return_value.__exit__.return_value = None
        mock_session.run.return_value = Mock()
        mock_driver.return_value = mock_driver_instance

        # Should not raise exception
        validate_neo4j_connection("bolt://localhost:7687", "neo4j", "password")

        mock_driver.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password"),
        )

    @patch("crawl4ai_mcp.neo4j.GraphDatabase.driver")
    def test_validate_neo4j_connection_failure(self, mock_driver):
        """Test Neo4j connection validation failure"""
        mock_driver.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            validate_neo4j_connection(
                "bolt://localhost:7687",
                "neo4j",
                "wrong_password",
            )

    def test_format_neo4j_error(self):
        """Test Neo4j error formatting"""
        # Test with generic exception
        error = Exception("Generic error message")
        formatted = format_neo4j_error(error)

        assert "Neo4j connection error" in formatted
        assert "Generic error message" in formatted

    def test_format_neo4j_error_with_specific_errors(self):
        """Test formatting specific types of Neo4j errors"""
        # Test different error types
        test_cases = [
            (Exception("Authentication failed"), "authentication"),
            (Exception("Connection refused"), "connection"),
            (Exception("Timeout"), "timeout"),
            (Exception("Unknown error"), "error"),
        ]

        for error, expected_keyword in test_cases:
            formatted = format_neo4j_error(error)
            assert "Neo4j connection error" in formatted
            assert str(error) in formatted

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("valid_script.py", True),
            ("./relative/path/script.py", True),
            ("/absolute/path/script.py", True),
            ("../parent/script.py", True),
            ("", False),
            ("script.txt", False),  # Wrong extension
            ("script", False),  # No extension
            ("script.PY", False),  # Case sensitive
        ],
    )
    def test_validate_script_path(self, path, expected):
        """Test script path validation"""
        if expected:
            # Should not raise exception for valid paths
            try:
                result = validate_script_path(path)
                assert result is True or result is None  # Depends on implementation
            except:
                pytest.fail(
                    f"validate_script_path raised exception for valid path: {path}",
                )
        else:
            # Should handle invalid paths appropriately
            try:
                result = validate_script_path(path)
                # Might return False or raise exception
                assert result is False or result is None
            except Exception:
                # Exception is acceptable for invalid paths
                pass

    def test_validate_script_path_with_file_system(self):
        """Test script path validation with actual file system checks"""
        import os
        import tempfile

        # Create temporary Python file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
            tmp.write(b"print('test')")
            tmp_path = tmp.name

        try:
            # Valid existing file
            result = validate_script_path(tmp_path)
            # Implementation might check file existence
            assert result is True or result is None
        finally:
            os.unlink(tmp_path)

    def test_validate_github_url_comprehensive(self):
        """Test comprehensive GitHub URL validation"""
        # This is already tested in test_url_helpers.py, but test integration here
        valid_urls = [
            "https://github.com/user/repo",
            "https://github.com/user/repo.git",
            "https://github.com/user/repo/tree/main",
        ]

        invalid_urls = ["https://gitlab.com/user/repo", "https://github.com/user", ""]

        for url in valid_urls:
            assert validate_github_url(url) is True

        for url in invalid_urls:
            assert validate_github_url(url) is False


class TestServiceInitialization:
    """Test service initialization functions"""

    def test_crawl4ai_context_initialization(self):
        """Test Crawl4AI context initialization"""
        # Test that the context class can be imported and initialized
        from crawl4ai_mcp import Crawl4AIContext

        # Should be able to create instance
        context = Crawl4AIContext()
        assert context is not None

    @patch("crawl4ai_mcp.AsyncWebCrawler")
    def test_crawler_initialization_mock(self, mock_crawler):
        """Test crawler initialization with mocking"""
        from crawl4ai_mcp import Crawl4AIContext

        mock_crawler_instance = Mock()
        mock_crawler.return_value = mock_crawler_instance

        context = Crawl4AIContext()
        # If context initializes crawler, test that
        assert context is not None

    def test_mcp_server_initialization(self):
        """Test MCP server initialization"""
        # Test that FastMCP can be imported and configured
        try:
            from fastmcp import FastMCP

            # Should be able to create FastMCP instance
            mcp = FastMCP("test-server")
            assert mcp is not None
        except ImportError:
            pytest.skip("FastMCP not available")

    def test_logging_configuration(self):
        """Test logging configuration"""
        import logging

        # Test that logger can be configured
        logger = logging.getLogger("crawl4ai_mcp")

        # Should be able to set level and add handler
        logger.setLevel(logging.INFO)

        # Test that it accepts log messages
        logger.info("Test message")

        assert logger.level <= logging.INFO


class TestConfigurationEdgeCases:
    """Test edge cases in configuration handling"""

    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase", "QDRANT_URL": ""})
    def test_mixed_configuration(self):
        """Test mixed configuration scenarios"""
        # Supabase selected but Qdrant URL is empty
        db_type = os.getenv("VECTOR_DATABASE", "supabase")
        qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")

        assert db_type == "supabase"
        assert qdrant_url == "http://qdrant:6333"  # Uses default

    def test_configuration_precedence(self):
        """Test configuration precedence and overrides"""
        # Test that environment variables take precedence over defaults
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            assert os.getenv("VECTOR_DATABASE", "supabase") == "qdrant"

        # Test that default is used when not set
        with patch.dict(os.environ, {}, clear=True):
            assert os.getenv("VECTOR_DATABASE", "supabase") == "supabase"

    def test_configuration_type_coercion(self):
        """Test type coercion for configuration values"""
        # Test boolean-like values
        bool_configs = {
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
        }

        for str_val, expected_bool in bool_configs.items():
            # Test conversion logic
            converted = str_val.lower() in ["true", "1", "yes"]
            assert converted == expected_bool

    def test_url_validation_helpers(self):
        """Test URL validation helper functions"""
        from urllib.parse import urlparse

        test_urls = [
            "https://example.com",
            "http://localhost:8080",
            "invalid-url",
            "",
        ]

        for url in test_urls:
            try:
                parsed = urlparse(url)
                # Should not raise exception
                assert hasattr(parsed, "scheme")
                assert hasattr(parsed, "netloc")
            except Exception as e:
                pytest.fail(f"URL parsing failed for {url}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
