"""
Unit tests for validated code search service.

Tests the ValidatedCodeSearchService that combines Qdrant semantic search
with Neo4j structural validation for high-confidence code search results.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from services.validated_search import ValidatedCodeSearchService, ValidationResult


class TestValidationResult:
    """Test ValidationResult data container."""

    def test_validation_result_initialization(self):
        """Test ValidationResult initialization with defaults."""
        result = ValidationResult()

        assert result.is_valid is False
        assert result.confidence_score == 0.0
        assert result.validation_details == {}
        assert result.suggestions == []
        assert result.metadata == {}

    def test_validation_result_with_data(self):
        """Test ValidationResult with actual validation data."""
        result = ValidationResult()
        result.is_valid = True
        result.confidence_score = 0.85
        result.validation_details = {"method_exists": True, "signature_valid": True}
        result.suggestions = ["Consider adding type hints"]
        result.metadata = {"source": "neo4j", "timestamp": "2025-01-01"}

        assert result.is_valid is True
        assert result.confidence_score == 0.85
        assert len(result.validation_details) == 2
        assert len(result.suggestions) == 1


class TestValidatedCodeSearchService:
    """Test ValidatedCodeSearchService functionality."""

    @pytest.fixture
    def mock_database_client(self):
        """Mock Qdrant database client."""
        client = AsyncMock()
        client.search_code_examples = AsyncMock()
        return client

    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver."""
        driver = AsyncMock()
        session = AsyncMock()
        driver.session.return_value = session
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        return driver

    @pytest.fixture
    def validated_search_service(self, mock_database_client):
        """Create ValidatedCodeSearchService with mocked dependencies."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_PASSWORD": "test_password",
            },
        ):
            service = ValidatedCodeSearchService(
                database_client=mock_database_client,
                neo4j_driver=None,  # Will be mocked in tests
            )
            return service

    @pytest.fixture
    def sample_semantic_results(self):
        """Sample semantic search results from Qdrant."""
        return [
            {
                "content": "def authenticate(username: str, password: str) -> bool:\n    return verify_credentials(username, password)",
                "metadata": {
                    "code_type": "function",
                    "name": "authenticate",
                    "full_name": "auth.authenticate",
                    "repository_name": "auth-service",
                },
                "similarity": 0.92,
                "source_id": "auth-service",
            },
            {
                "content": "class AuthService:\n    def login(self, user, pwd):\n        return self.authenticate(user, pwd)",
                "metadata": {
                    "code_type": "method",
                    "method_name": "login",
                    "class_name": "AuthService",
                    "full_name": "auth.AuthService.login",
                    "repository_name": "auth-service",
                },
                "similarity": 0.88,
                "source_id": "auth-service",
            },
        ]

    @pytest.mark.asyncio
    async def test_initialization_with_neo4j_enabled(self, mock_database_client):
        """Test service initialization with Neo4j enabled."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_PASSWORD": "test_password",
            },
        ):
            service = ValidatedCodeSearchService(mock_database_client)

            assert service.database_client == mock_database_client
            assert service.neo4j_enabled is True
            assert service.neo4j_uri == "bolt://localhost:7687"
            assert service.neo4j_password == "test_password"
            assert service.MIN_CONFIDENCE_THRESHOLD == 0.6
            assert service.HIGH_CONFIDENCE_THRESHOLD == 0.8

    @pytest.mark.asyncio
    async def test_initialization_without_neo4j(self, mock_database_client):
        """Test service initialization without Neo4j configuration."""
        with patch.dict(os.environ, {}, clear=True):
            service = ValidatedCodeSearchService(mock_database_client)

            assert service.neo4j_enabled is False
            assert service.neo4j_uri is None
            assert service.neo4j_password is None

    @pytest.mark.asyncio
    async def test_search_and_validate_code_basic(
        self, validated_search_service, sample_semantic_results
    ):
        """Test basic search and validation workflow."""
        # Mock semantic search
        with patch.object(
            validated_search_service, "_perform_semantic_search"
        ) as mock_semantic:
            mock_semantic.return_value = sample_semantic_results

            # Mock validation
            with patch.object(
                validated_search_service, "_validate_results_parallel"
            ) as mock_validate:
                validated_results = []
                for result in sample_semantic_results:
                    validated_result = result.copy()
                    validated_result["validation"] = {
                        "is_valid": True,
                        "confidence_score": 0.85,
                        "validation_checks": [
                            {"check": "function_exists", "passed": True, "weight": 0.7},
                        ],
                        "neo4j_validated": True,
                    }
                    validated_results.append(validated_result)
                mock_validate.return_value = validated_results

                result = await validated_search_service.search_and_validate_code(
                    query="authentication function",
                    match_count=5,
                )

                assert result["success"] is True
                assert result["query"] == "authentication function"
                assert len(result["results"]) == 2
                assert "validation_summary" in result
                assert result["validation_summary"]["validated"] == 2

    @pytest.mark.asyncio
    async def test_search_no_results(self, validated_search_service):
        """Test search with no semantic results."""
        with patch.object(
            validated_search_service, "_perform_semantic_search"
        ) as mock_semantic:
            mock_semantic.return_value = []

            result = await validated_search_service.search_and_validate_code(
                query="nonexistent function",
                match_count=5,
            )

            assert result["success"] is True
            assert result["results"] == []
            assert result["validation_summary"]["total_found"] == 0

    @pytest.mark.asyncio
    async def test_search_with_confidence_filtering(
        self, validated_search_service, sample_semantic_results
    ):
        """Test search results filtering by confidence threshold."""
        with patch.object(
            validated_search_service, "_perform_semantic_search"
        ) as mock_semantic:
            mock_semantic.return_value = sample_semantic_results

            # Mock validation with different confidence scores
            with patch.object(
                validated_search_service, "_validate_results_parallel"
            ) as mock_validate:
                validated_results = []
                confidences = [0.9, 0.4]  # One high, one low confidence

                for i, result in enumerate(sample_semantic_results):
                    validated_result = result.copy()
                    validated_result["validation"] = {
                        "is_valid": confidences[i] >= 0.6,
                        "confidence_score": confidences[i],
                        "validation_checks": [],
                        "neo4j_validated": True,
                    }
                    validated_results.append(validated_result)
                mock_validate.return_value = validated_results

                result = await validated_search_service.search_and_validate_code(
                    query="test function",
                    match_count=5,
                    min_confidence=0.7,  # Filter out low confidence
                )

                # Should only return high confidence result
                assert len(result["results"]) == 1
                assert result["results"][0]["validation"]["confidence_score"] == 0.9

    @pytest.mark.asyncio
    async def test_perform_semantic_search(
        self, validated_search_service, mock_database_client
    ):
        """Test semantic search functionality."""
        # Mock embedding generation
        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3]]  # Mock embedding

            # Mock database search
            mock_database_client.search_code_examples.return_value = [
                {
                    "content": "test content",
                    "metadata": {"code_type": "function"},
                    "similarity": 0.8,
                },
            ]

            results = await validated_search_service._perform_semantic_search(
                query="test query",
                match_count=5,
                source_filter="test-repo",
            )

            # Verify embedding generation
            mock_embeddings.assert_called_once_with(["test query"])

            # Verify database search
            mock_database_client.search_code_examples.assert_called_once()
            call_args = mock_database_client.search_code_examples.call_args
            assert call_args[1]["match_count"] == 5
            assert call_args[1]["filter_metadata"] == {"source_id": "test-repo"}

            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_validate_results_parallel(
        self, validated_search_service, sample_semantic_results
    ):
        """Test parallel validation of search results."""
        # Mock Neo4j enabled
        validated_search_service.neo4j_enabled = True

        with patch.object(
            validated_search_service, "_validate_single_result"
        ) as mock_validate_single:
            # Mock individual validation results
            mock_validate_single.side_effect = [
                {
                    **sample_semantic_results[0],
                    "validation": {"is_valid": True, "confidence_score": 0.8},
                },
                {
                    **sample_semantic_results[1],
                    "validation": {"is_valid": True, "confidence_score": 0.7},
                },
            ]

            results = await validated_search_service._validate_results_parallel(
                sample_semantic_results,
                include_suggestions=True,
            )

            assert len(results) == 2
            assert all("validation" in result for result in results)
            # Should have called validation for each result
            assert mock_validate_single.call_count == 2

    @pytest.mark.asyncio
    async def test_validate_results_neo4j_disabled(
        self, validated_search_service, sample_semantic_results
    ):
        """Test validation fallback when Neo4j is disabled."""
        validated_search_service.neo4j_enabled = False

        results = await validated_search_service._validate_results_parallel(
            sample_semantic_results,
            include_suggestions=False,
        )

        # Should add empty validation for all results
        assert len(results) == 2
        for result in results:
            assert "validation" in result
            assert result["validation"]["neo4j_validated"] is False
            assert result["validation"]["confidence_score"] == 0.5  # Neutral

    @pytest.mark.asyncio
    async def test_validate_single_result_with_caching(
        self, validated_search_service, sample_semantic_results
    ):
        """Test single result validation with caching."""
        result = sample_semantic_results[0]

        # Mock performance optimizer cache
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None  # Cache miss
        mock_cache.set = AsyncMock()
        validated_search_service.performance_optimizer.cache = mock_cache

        # Mock Neo4j validation
        with patch.object(
            validated_search_service, "_perform_neo4j_validation"
        ) as mock_neo4j:
            mock_neo4j.return_value = {
                "is_valid": True,
                "confidence_score": 0.85,
                "neo4j_validated": True,
            }

            validated_result = await validated_search_service._validate_single_result(
                result,
                include_suggestions=True,
            )

            # Verify validation was performed
            mock_neo4j.assert_called_once()

            # Verify caching
            mock_cache.set.assert_called_once()

            # Verify result structure
            assert "validation" in validated_result
            assert validated_result["validation"]["confidence_score"] == 0.85

    @pytest.mark.asyncio
    async def test_perform_neo4j_validation_function(self, validated_search_service):
        """Test Neo4j validation for function code type."""
        result = {
            "source_id": "test-repo",
            "metadata": {
                "code_type": "function",
                "method_name": "test_function",
                "full_name": "module.test_function",
            },
        }

        mock_session = AsyncMock()

        # Mock all validation checks to pass
        with (
            patch.object(
                validated_search_service, "_get_neo4j_session"
            ) as mock_get_session,
            patch.object(
                validated_search_service, "_check_repository_exists"
            ) as mock_repo,
            patch.object(
                validated_search_service, "_check_function_exists"
            ) as mock_func,
        ):
            mock_get_session.return_value = mock_session
            mock_repo.return_value = True
            mock_func.return_value = True

            validation = await validated_search_service._perform_neo4j_validation(
                result,
                include_suggestions=True,
            )

            assert validation["is_valid"] is True
            assert validation["confidence_score"] > 0.5
            assert validation["neo4j_validated"] is True
            assert len(validation["validation_checks"]) == 2  # repo + function checks

    @pytest.mark.asyncio
    async def test_perform_neo4j_validation_method(self, validated_search_service):
        """Test Neo4j validation for method code type."""
        result = {
            "source_id": "test-repo",
            "metadata": {
                "code_type": "method",
                "method_name": "authenticate",
                "class_name": "AuthService",
                "full_name": "auth.AuthService.authenticate",
            },
        }

        mock_session = AsyncMock()

        with (
            patch.object(
                validated_search_service, "_get_neo4j_session"
            ) as mock_get_session,
            patch.object(
                validated_search_service, "_check_repository_exists"
            ) as mock_repo,
            patch.object(
                validated_search_service, "_check_method_exists"
            ) as mock_method,
            patch.object(
                validated_search_service, "_validate_method_signature"
            ) as mock_signature,
        ):
            mock_get_session.return_value = mock_session
            mock_repo.return_value = True
            mock_method.return_value = True
            mock_signature.return_value = True

            validation = await validated_search_service._perform_neo4j_validation(
                result,
                include_suggestions=True,
            )

            assert validation["is_valid"] is True
            assert (
                len(validation["validation_checks"]) == 3
            )  # repo + method + signature

    @pytest.mark.asyncio
    async def test_check_repository_exists(self, validated_search_service):
        """Test repository existence check."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"exists": True}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        exists = await validated_search_service._check_repository_exists(
            mock_session,
            "test-repo",
        )

        assert exists is True
        mock_session.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_method_exists(self, validated_search_service):
        """Test method existence check."""
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"exists": True}
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result

        exists = await validated_search_service._check_method_exists(
            mock_session,
            "authenticate",
            "AuthService",
            "test-repo",
        )

        assert exists is True
        mock_session.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_suggestions_for_failed_checks(
        self, validated_search_service
    ):
        """Test suggestion generation for failed validation checks."""
        result = {
            "source_id": "missing-repo",
            "metadata": {
                "code_type": "class",
                "class_name": "MissingClass",
            },
        }

        validation_checks = [
            {"check": "repository_exists", "passed": False, "weight": 0.3},
            {"check": "class_exists", "passed": False, "weight": 0.4},
        ]

        suggestions = await validated_search_service._generate_suggestions(
            None,
            result,
            validation_checks,
        )

        assert len(suggestions) == 2
        assert "Repository 'missing-repo' not found" in suggestions[0]
        assert "Class 'MissingClass' not found" in suggestions[1]

    def test_calculate_confidence_score(self, validated_search_service):
        """Test confidence score calculation from validation checks."""
        validation_checks = [
            {"check": "repository_exists", "passed": True, "weight": 0.3},
            {"check": "method_exists", "passed": True, "weight": 0.4},
            {"check": "signature_valid", "passed": False, "weight": 0.3},
        ]

        score = validated_search_service._calculate_confidence_score(validation_checks)

        # Should be (0.3 + 0.4 + 0) / 1.0 = 0.7
        assert score == 0.7

    def test_calculate_combined_score(self, validated_search_service):
        """Test combined score calculation from semantic and validation scores."""
        result = {
            "similarity": 0.8,
            "validation": {
                "confidence_score": 0.9,
            },
        }

        combined_score = validated_search_service._calculate_combined_score(result)

        # Should be (0.8 * 0.4) + (0.9 * 0.6) = 0.32 + 0.54 = 0.86
        assert combined_score == 0.86

    def test_generate_validation_summary(self, validated_search_service):
        """Test validation summary generation."""
        semantic_results = [{"id": 1}, {"id": 2}, {"id": 3}]
        validated_results = [{"id": 1}, {"id": 2}]
        final_results = [
            {
                "id": 1,
                "validation": {"confidence_score": 0.9},  # High confidence
            },
        ]

        summary = validated_search_service._generate_validation_summary(
            semantic_results,
            validated_results,
            final_results,
        )

        assert summary["total_found"] == 3
        assert summary["validated"] == 2
        assert summary["final_count"] == 1
        assert summary["high_confidence"] == 1
        assert summary["validation_rate"] == 2 / 3
        assert summary["high_confidence_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_clear_validation_cache(self, validated_search_service):
        """Test clearing validation cache."""
        mock_cache = AsyncMock()
        validated_search_service.performance_optimizer.cache = mock_cache

        await validated_search_service.clear_validation_cache()

        mock_cache.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, validated_search_service):
        """Test getting cache statistics."""
        mock_cache = MagicMock()
        mock_cache.get_stats.return_value = {
            "hits": 10,
            "misses": 5,
            "hit_rate": 0.67,
        }
        validated_search_service.performance_optimizer.cache = mock_cache

        stats = await validated_search_service.get_cache_stats()

        assert "cache_stats" in stats
        assert stats["cache_stats"]["hits"] == 10
        assert "neo4j_enabled" in stats
        assert "thresholds" in stats

    @pytest.mark.asyncio
    async def test_get_health_status(self, validated_search_service):
        """Test getting service health status."""
        with patch(
            "services.validated_search.validate_integration_health"
        ) as mock_health:
            mock_health.return_value = {
                "overall_status": "fully_operational",
                "components": {
                    "qdrant": {"status": "healthy"},
                    "neo4j": {"status": "healthy"},
                },
            }

            health = await validated_search_service.get_health_status()

            assert health["overall_status"] == "fully_operational"
            mock_health.assert_called_once_with(
                database_client=validated_search_service.database_client,
                neo4j_driver=validated_search_service.neo4j_driver,
            )

    @pytest.mark.asyncio
    async def test_error_handling_in_search(self, validated_search_service):
        """Test error handling in search and validate workflow."""
        with patch.object(
            validated_search_service, "_perform_semantic_search"
        ) as mock_semantic:
            mock_semantic.side_effect = Exception("Database connection failed")

            result = await validated_search_service.search_and_validate_code(
                query="test query",
                match_count=5,
            )

            assert result["success"] is False
            assert "error" in result
            assert "Database connection failed" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
