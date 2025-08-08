"""
Comprehensive unit tests for database factory pattern.

This test file provides thorough coverage of the database factory functions,
including edge cases, error scenarios, and environment variable handling.
"""

# Import test setup FIRST to configure environment

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from database.base import VectorDatabase
from database.factory import create_and_initialize_database, create_database_client
from database.qdrant_adapter import QdrantAdapter
from database.supabase_adapter import SupabaseAdapter


class TestDatabaseFactoryCreation:
    """Test database factory client creation functionality"""

    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch("database.supabase_adapter.create_client")
    def test_create_supabase_database(self, mock_create_client):
        """Test creating Supabase adapter with default environment"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, SupabaseAdapter)
        assert isinstance(db, VectorDatabase)
        assert db.__class__.__name__ == "SupabaseAdapter"

    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}, clear=True)
    def test_create_qdrant_database(self):
        """Test creating Qdrant adapter with default environment"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert isinstance(db, VectorDatabase)
        assert db.__class__.__name__ == "QdrantAdapter"
        assert db.url == "http://qdrant:6333"  # Default URL from factory
        assert db.api_key is None  # Default API key

    @patch.dict(
        os.environ,
        {
            "VECTOR_DATABASE": "qdrant",
            "QDRANT_URL": "http://localhost:6333",
            "QDRANT_API_KEY": "test-secret-key",
        },
    )
    def test_create_qdrant_database_with_custom_config(self):
        """Test creating Qdrant adapter with custom configuration"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert db.url == "http://localhost:6333"
        assert db.api_key == "test-secret-key"

    @patch.dict(
        os.environ,
        {
            "VECTOR_DATABASE": "qdrant",
            "QDRANT_URL": "https://my-cluster.qdrant.io:6333",
        },
    )
    def test_create_qdrant_database_with_custom_url_only(self):
        """Test creating Qdrant adapter with custom URL but no API key"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert db.url == "https://my-cluster.qdrant.io:6333"
        assert db.api_key is None or db.api_key == ""

    @patch.dict(
        os.environ,
        {"VECTOR_DATABASE": "qdrant", "QDRANT_API_KEY": "api-key-without-url"},
    )
    def test_create_qdrant_database_with_api_key_only(self):
        """Test creating Qdrant adapter with API key but default URL"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert db.url == "http://localhost:6333"  # Default URL (from QdrantAdapter)
        assert db.api_key == "api-key-without-url"


class TestDatabaseFactoryDefaults:
    """Test database factory default behavior and fallbacks"""

    @patch.dict(os.environ, {}, clear=True)
    @patch("database.supabase_adapter.create_client")
    def test_default_to_supabase_when_no_env_var(self, mock_create_client):
        """Test defaults to Supabase when VECTOR_DATABASE is not set"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, SupabaseAdapter)

    @patch.dict(os.environ, {"VECTOR_DATABASE": ""})
    @patch("database.supabase_adapter.create_client")
    def test_default_to_supabase_when_empty_string(self, mock_create_client):
        """Test defaults to Supabase when VECTOR_DATABASE is empty string"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, SupabaseAdapter)

    @patch.dict(os.environ, {"VECTOR_DATABASE": "   "})
    def test_whitespace_database_type_raises_error(self):
        """Test whitespace VECTOR_DATABASE raises ValueError (not treated as empty)"""
        # Act & Assert - whitespace is not stripped, so it's treated as invalid
        with pytest.raises(ValueError) as exc_info:
            create_database_client()

        assert "Unknown database type:    " in str(exc_info.value)


class TestDatabaseFactoryCaseInsensitivity:
    """Test database factory handles case variations correctly"""

    @pytest.mark.parametrize(
        "db_type",
        ["SUPABASE", "Supabase", "sUpAbAsE", "SUPABASE"],
    )
    @patch("database.supabase_adapter.create_client")
    def test_supabase_case_insensitive(self, mock_create_client, db_type):
        """Test Supabase creation is case insensitive"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act
        with patch.dict(os.environ, {"VECTOR_DATABASE": db_type}):
            db = create_database_client()

        # Assert
        assert isinstance(db, SupabaseAdapter)

    @pytest.mark.parametrize("db_type", ["QDRANT", "Qdrant", "qDrAnT", "QDRANT"])
    def test_qdrant_case_insensitive(self, db_type):
        """Test Qdrant creation is case insensitive"""
        # Act
        with patch.dict(os.environ, {"VECTOR_DATABASE": db_type}):
            db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)


class TestDatabaseFactoryErrorHandling:
    """Test database factory error scenarios"""

    def test_invalid_database_type_raises_value_error(self):
        """Test invalid database type raises ValueError"""
        # Act & Assert
        with patch.dict(os.environ, {"VECTOR_DATABASE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                create_database_client()

        # Verify error message
        error_msg = str(exc_info.value)
        assert "Unknown database type: invalid" in error_msg
        assert "Supported types are: 'supabase', 'qdrant'" in error_msg

    @pytest.mark.parametrize(
        "invalid_type",
        [
            "postgresql",
            "mysql",
            "redis",
            "elasticsearch",
            "mongodb",
            "unknown",
            "test",
            "123",
            "qdrant_invalid",
            "supabase_old",
        ],
    )
    def test_various_invalid_database_types(self, invalid_type):
        """Test various invalid database types all raise ValueError"""
        # Act & Assert
        with patch.dict(os.environ, {"VECTOR_DATABASE": invalid_type}):
            with pytest.raises(ValueError) as exc_info:
                create_database_client()

        # Verify error message contains the invalid type
        assert f"Unknown database type: {invalid_type}" in str(exc_info.value)

    def test_error_message_contains_supported_types(self):
        """Test error message lists all supported types"""
        # Act & Assert
        with patch.dict(os.environ, {"VECTOR_DATABASE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                create_database_client()

        error_msg = str(exc_info.value)
        assert "'supabase'" in error_msg
        assert "'qdrant'" in error_msg


class TestDatabaseFactoryInitialization:
    """Test database factory initialization functionality"""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch("database.supabase_adapter.create_client")
    async def test_create_and_initialize_supabase(self, mock_create_client):
        """Test create and initialize for Supabase adapter"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act
        with patch.object(
            SupabaseAdapter,
            "initialize",
            new_callable=AsyncMock,
        ) as mock_init:
            db = await create_and_initialize_database()

        # Assert
        assert isinstance(db, SupabaseAdapter)
        mock_init.assert_called_once()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"})
    async def test_create_and_initialize_qdrant(self):
        """Test create and initialize for Qdrant adapter"""
        # Act
        with patch.object(
            QdrantAdapter,
            "initialize",
            new_callable=AsyncMock,
        ) as mock_init:
            db = await create_and_initialize_database()

        # Assert
        assert isinstance(db, QdrantAdapter)
        mock_init.assert_called_once()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch("database.supabase_adapter.create_client")
    async def test_create_and_initialize_calls_initialize_exactly_once(
        self,
        mock_create_client,
    ):
        """Test that initialize is called exactly once"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act
        with patch.object(
            SupabaseAdapter,
            "initialize",
            new_callable=AsyncMock,
        ) as mock_init:
            db = await create_and_initialize_database()

        # Assert
        assert mock_init.call_count == 1
        mock_init.assert_called_once_with()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "invalid"})
    async def test_create_and_initialize_invalid_type_raises_error(self):
        """Test create and initialize with invalid type raises error"""
        # Act & Assert
        with pytest.raises(ValueError):
            await create_and_initialize_database()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"})
    @patch("database.supabase_adapter.create_client")
    async def test_create_and_initialize_propagates_initialization_errors(
        self,
        mock_create_client,
    ):
        """Test that initialization errors are propagated"""
        # Arrange
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Act & Assert
        with patch.object(
            SupabaseAdapter,
            "initialize",
            new_callable=AsyncMock,
        ) as mock_init:
            mock_init.side_effect = RuntimeError("Initialization failed")

            with pytest.raises(RuntimeError, match="Initialization failed"):
                await create_and_initialize_database()


class TestDatabaseFactoryEnvironmentHandling:
    """Test database factory environment variable handling"""

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence and can change"""
        # Test Qdrant first
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            db1 = create_database_client()
            assert isinstance(db1, QdrantAdapter)

        # Test Supabase second - should create different instance
        with patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"}):
            with patch(
                "database.supabase_adapter.create_client",
                return_value=MagicMock(),
            ):
                db2 = create_database_client()
                assert isinstance(db2, SupabaseAdapter)

        # Verify they are different types
        assert type(db1) != type(db2)

    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant", "QDRANT_URL": ""})
    def test_empty_qdrant_url_uses_empty_string(self):
        """Test empty QDRANT_URL is passed as empty string (QdrantAdapter handles fallback)"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert (
            db.url == ""
        )  # Empty URL from environment (QdrantAdapter uses "or" logic)

    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant", "QDRANT_API_KEY": ""})
    def test_empty_qdrant_api_key_is_none(self):
        """Test empty QDRANT_API_KEY is treated as None"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert db.api_key is None or db.api_key == ""

    def test_multiple_calls_create_separate_instances(self):
        """Test that multiple calls create separate instances"""
        # Act
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            db1 = create_database_client()
            db2 = create_database_client()

        # Assert
        assert isinstance(db1, QdrantAdapter)
        assert isinstance(db2, QdrantAdapter)
        assert db1 is not db2  # Different instances


class TestDatabaseFactoryIntegration:
    """Test database factory integration scenarios"""

    @pytest.mark.asyncio
    async def test_factory_creates_protocol_compliant_instances(self):
        """Test that factory creates instances that comply with VectorDatabase protocol"""
        # Test both database types
        db_configs = [{"VECTOR_DATABASE": "supabase"}, {"VECTOR_DATABASE": "qdrant"}]

        for config in db_configs:
            with patch.dict(os.environ, config):
                if config["VECTOR_DATABASE"] == "supabase":
                    with patch(
                        "database.supabase_adapter.create_client",
                        return_value=MagicMock(),
                    ):
                        db = create_database_client()
                else:
                    db = create_database_client()

                # Verify protocol compliance
                assert isinstance(db, VectorDatabase)
                assert hasattr(db, "initialize")
                assert hasattr(db, "add_documents")
                assert hasattr(db, "search_documents")
                assert hasattr(db, "delete_documents_by_url")
                assert hasattr(db, "add_code_examples")
                assert hasattr(db, "search_code_examples")
                assert hasattr(db, "delete_code_examples_by_url")
                assert hasattr(db, "update_source_info")
                assert hasattr(db, "get_documents_by_url")
                assert hasattr(db, "search_documents_by_keyword")
                assert hasattr(db, "search_code_examples_by_keyword")
                assert hasattr(db, "get_sources")

    def test_factory_preserves_adapter_specific_attributes(self):
        """Test that factory preserves adapter-specific attributes"""
        # Test Qdrant adapter attributes
        with patch.dict(
            os.environ,
            {
                "VECTOR_DATABASE": "qdrant",
                "QDRANT_URL": "http://test:6333",
                "QDRANT_API_KEY": "test-key",
            },
        ):
            qdrant_db = create_database_client()
            assert hasattr(qdrant_db, "url")
            assert hasattr(qdrant_db, "api_key")
            assert qdrant_db.url == "http://test:6333"
            assert qdrant_db.api_key == "test-key"

        # Test Supabase adapter (would have different attributes)
        with patch.dict(os.environ, {"VECTOR_DATABASE": "supabase"}):
            with patch(
                "database.supabase_adapter.create_client",
                return_value=MagicMock(),
            ):
                supabase_db = create_database_client()
                # Supabase adapter would have its own specific attributes
                assert hasattr(supabase_db, "__class__")
                assert supabase_db.__class__.__name__ == "SupabaseAdapter"


class TestDatabaseFactoryEdgeCases:
    """Test database factory edge cases and boundary conditions"""

    def test_null_byte_in_database_type(self):
        """Test that null bytes in database type raise error during environment setup"""
        # This test verifies that null bytes can't be set in environment variables
        # The error occurs when trying to set the environment variable, not in our code
        with pytest.raises(ValueError, match="embedded null byte"):
            with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant\x00"}):
                pass

    @patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant", "QDRANT_URL": "qdrant"})
    def test_qdrant_url_without_protocol(self):
        """Test Qdrant URL without protocol is accepted"""
        # Act
        db = create_database_client()

        # Assert
        assert isinstance(db, QdrantAdapter)
        assert db.url == "qdrant"  # Should accept as-is

    def test_factory_function_is_deterministic(self):
        """Test that factory function is deterministic for same environment"""
        # Act - create multiple instances with same environment
        with patch.dict(os.environ, {"VECTOR_DATABASE": "qdrant"}):
            db1 = create_database_client()
            db2 = create_database_client()

        # Assert - should be same type and configuration
        assert type(db1) == type(db2)
        assert isinstance(db1, QdrantAdapter)
        assert isinstance(db2, QdrantAdapter)
        assert db1.url == db2.url
        assert db1.api_key == db2.api_key


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
