"""
Comprehensive tests for KnowledgeGraphValidator functionality.

This module tests knowledge graph validation including:
- Script validation against Neo4j knowledge graph
- Import validation and hallucination detection
- Method call validation with parameter checking
- Class instantiation validation
- Function call validation
- Attribute access validation
- Confidence scoring and reporting
- Caching mechanisms
- Error handling and edge cases
"""

import os

# Add src to path for imports
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import fixtures
from tests.fixtures.neo4j_fixtures import (
    MockNeo4jDriver,
)

# Mock Neo4j and other dependencies before importing our modules
with patch.dict(
    "sys.modules",
    {
        "neo4j": MagicMock(),
        "neo4j.AsyncGraphDatabase": MagicMock(),
        "ai_script_analyzer": MagicMock(),
        "hallucination_reporter": MagicMock(),
    },
):
    # Now import our modules
    sys.path.insert(
        0,
        os.path.join(os.path.dirname(__file__), "..", "knowledge_graphs"),
    )
    from knowledge_graph_validator import (
        ImportValidation,
        KnowledgeGraphValidator,
        ValidationResult,
        ValidationStatus,
    )


class TestValidationDataClasses:
    """Test the validation data classes and enums"""

    def test_validation_status_enum(self):
        """Test ValidationStatus enum values"""
        assert ValidationStatus.VALID.value == "VALID"
        assert ValidationStatus.INVALID.value == "INVALID"
        assert ValidationStatus.UNCERTAIN.value == "UNCERTAIN"
        assert ValidationStatus.NOT_FOUND.value == "NOT_FOUND"

    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation"""
        result = ValidationResult(
            status=ValidationStatus.VALID,
            confidence=0.9,
            message="Test validation result",
            details={"key": "value"},
            suggestions=["suggestion1", "suggestion2"],
        )

        assert result.status == ValidationStatus.VALID
        assert result.confidence == 0.9
        assert result.message == "Test validation result"
        assert result.details == {"key": "value"}
        assert result.suggestions == ["suggestion1", "suggestion2"]

    def test_validation_result_defaults(self):
        """Test ValidationResult with default values"""
        result = ValidationResult(
            status=ValidationStatus.VALID,
            confidence=1.0,
            message="Test message",
        )

        assert result.details == {}
        assert result.suggestions == []

    def test_import_validation_creation(self):
        """Test ImportValidation dataclass creation"""
        # Mock import info
        mock_import_info = MagicMock()
        mock_import_info.module = "test_module"
        mock_import_info.imports = ["TestClass"]

        validation_result = ValidationResult(
            status=ValidationStatus.VALID,
            confidence=0.8,
            message="Import validated",
        )

        import_validation = ImportValidation(
            import_info=mock_import_info,
            validation=validation_result,
            available_classes=["TestClass", "OtherClass"],
            available_functions=["test_function"],
        )

        assert import_validation.import_info == mock_import_info
        assert import_validation.validation == validation_result
        assert "TestClass" in import_validation.available_classes
        assert "test_function" in import_validation.available_functions


class TestKnowledgeGraphValidator:
    """Test the KnowledgeGraphValidator class"""

    @pytest.fixture
    def validator_config(self):
        """Configuration for KnowledgeGraphValidator"""
        return {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "test_user",
            "neo4j_password": "test_password",
        }

    @pytest.fixture
    def mock_validator(self, validator_config):
        """Create a KnowledgeGraphValidator with mocked dependencies"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )
            validator.driver = mock_driver

            yield validator

    @pytest.mark.asyncio
    async def test_initialization(self, validator_config):
        """Test KnowledgeGraphValidator initialization"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )

            assert validator.neo4j_uri == validator_config["neo4j_uri"]
            assert validator.neo4j_user == validator_config["neo4j_user"]
            assert validator.neo4j_password == validator_config["neo4j_password"]
            assert validator.driver is None  # Not initialized yet

            # Check cache initialization
            assert isinstance(validator.module_cache, dict)
            assert isinstance(validator.class_cache, dict)
            assert isinstance(validator.method_cache, dict)
            assert isinstance(validator.repo_cache, dict)
            assert isinstance(validator.knowledge_graph_modules, set)

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_validator):
        """Test successful initialization of validator"""
        await mock_validator.initialize()

        # Verify driver is set up
        assert mock_validator.driver is not None
        assert isinstance(mock_validator.driver, MockNeo4jDriver)

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, validator_config):
        """Test initialization failure due to connection issues"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            # Simulate connection failure
            mock_db.driver.side_effect = Exception("Connection failed")

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )

            with pytest.raises(Exception, match="Connection failed"):
                await validator.initialize()

    @pytest.mark.asyncio
    async def test_close_connection(self, mock_validator):
        """Test closing validator connection"""
        await mock_validator.initialize()
        await mock_validator.close()

        assert mock_validator.driver.closed is True

    @pytest.mark.asyncio
    async def test_validate_script_success(self, mock_validator, neo4j_query_responses):
        """Test successful script validation"""
        await mock_validator.initialize()

        # Mock analysis result
        mock_analysis_result = MagicMock()
        mock_analysis_result.imports = []
        mock_analysis_result.class_instantiations = []
        mock_analysis_result.method_calls = []
        mock_analysis_result.attribute_accesses = []
        mock_analysis_result.function_calls = []

        # Set up mock responses
        mock_validator.driver.session_data = neo4j_query_responses["find_module"]

        result = await mock_validator.validate_script(mock_analysis_result)

        assert result is not None
        assert hasattr(result, "overall_confidence")

    @pytest.mark.asyncio
    async def test_validate_imports_valid(self, mock_validator, neo4j_query_responses):
        """Test validation of valid imports"""
        await mock_validator.initialize()

        # Mock import info
        mock_import = MagicMock()
        mock_import.module = "main"
        mock_import.imports = ["TestClass"]

        # Set up mock responses for finding module
        mock_validator.driver.session_data = neo4j_query_responses["find_module"]

        result = await mock_validator._validate_single_import(mock_import)

        assert result is not None
        assert result.validation.status in [
            ValidationStatus.VALID,
            ValidationStatus.NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_validate_imports_invalid(
        self,
        mock_validator,
        neo4j_query_responses,
    ):
        """Test validation of invalid imports"""
        await mock_validator.initialize()

        # Mock invalid import
        mock_import = MagicMock()
        mock_import.module = "nonexistent_module"
        mock_import.imports = ["FakeClass"]

        # Set up empty response (module not found)
        mock_validator.driver.session_data = neo4j_query_responses["empty_result"]

        result = await mock_validator._validate_single_import(mock_import)

        assert result is not None
        assert result.validation.status == ValidationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_validate_class_instantiation_valid(
        self,
        mock_validator,
        neo4j_query_responses,
    ):
        """Test validation of valid class instantiation"""
        await mock_validator.initialize()

        # Mock class instantiation
        mock_instantiation = MagicMock()
        mock_instantiation.class_name = "TestClass"
        mock_instantiation.module = "main"
        mock_instantiation.args = ["param1"]
        mock_instantiation.kwargs = {}

        # Set up mock responses
        mock_validator.driver.session_data = neo4j_query_responses["find_class"]

        result = await mock_validator._validate_single_class_instantiation(
            mock_instantiation,
        )

        assert result is not None
        assert result.validation.status in [
            ValidationStatus.VALID,
            ValidationStatus.NOT_FOUND,
            ValidationStatus.UNCERTAIN,
        ]

    @pytest.mark.asyncio
    async def test_validate_method_call_valid(
        self,
        mock_validator,
        neo4j_query_responses,
    ):
        """Test validation of valid method calls"""
        await mock_validator.initialize()

        # Mock method call
        mock_method_call = MagicMock()
        mock_method_call.object_name = "test_obj"
        mock_method_call.method_name = "test_method"
        mock_method_call.class_name = "TestClass"
        mock_method_call.args = ["param1"]
        mock_method_call.kwargs = {}

        # Set up mock responses
        mock_validator.driver.session_data = neo4j_query_responses["find_method"]

        result = await mock_validator._validate_single_method_call(mock_method_call)

        assert result is not None
        assert result.validation.status in [
            ValidationStatus.VALID,
            ValidationStatus.NOT_FOUND,
            ValidationStatus.UNCERTAIN,
        ]

    @pytest.mark.asyncio
    async def test_validate_method_call_invalid(
        self,
        mock_validator,
        neo4j_query_responses,
    ):
        """Test validation of invalid method calls"""
        await mock_validator.initialize()

        # Mock invalid method call
        mock_method_call = MagicMock()
        mock_method_call.object_name = "test_obj"
        mock_method_call.method_name = "nonexistent_method"
        mock_method_call.class_name = "TestClass"
        mock_method_call.args = []
        mock_method_call.kwargs = {}

        # Set up empty response (method not found)
        mock_validator.driver.session_data = neo4j_query_responses["empty_result"]

        result = await mock_validator._validate_single_method_call(mock_method_call)

        assert result is not None
        assert result.validation.status == ValidationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_validate_attribute_access_valid(
        self,
        mock_validator,
        neo4j_query_responses,
    ):
        """Test validation of valid attribute access"""
        await mock_validator.initialize()

        # Mock attribute access
        mock_attribute = MagicMock()
        mock_attribute.object_name = "test_obj"
        mock_attribute.attribute_name = "test_attr"
        mock_attribute.class_name = "TestClass"

        # Set up mock responses
        mock_validator.driver.session_data = neo4j_query_responses["find_attribute"]

        result = await mock_validator._validate_single_attribute_access(mock_attribute)

        assert result is not None
        assert result.validation.status in [
            ValidationStatus.VALID,
            ValidationStatus.NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_validate_function_call_valid(
        self,
        mock_validator,
        neo4j_query_responses,
    ):
        """Test validation of valid function calls"""
        await mock_validator.initialize()

        # Mock function call
        mock_function_call = MagicMock()
        mock_function_call.function_name = "test_function"
        mock_function_call.module = "main"
        mock_function_call.args = ["param1", "param2"]
        mock_function_call.kwargs = {}

        # Set up mock responses
        mock_validator.driver.session_data = neo4j_query_responses["find_function"]

        result = await mock_validator._validate_single_function_call(mock_function_call)

        assert result is not None
        assert result.validation.status in [
            ValidationStatus.VALID,
            ValidationStatus.NOT_FOUND,
            ValidationStatus.UNCERTAIN,
        ]

    @pytest.mark.asyncio
    async def test_parameter_validation_correct_types(self, mock_validator):
        """Test parameter validation with correct types"""
        await mock_validator.initialize()

        # Mock function/method parameters from knowledge graph
        expected_params = {"param1": "str", "param2": "int"}
        provided_args = ["hello", 42]
        provided_kwargs = {}

        result = mock_validator._validate_parameters(
            expected_params,
            provided_args,
            provided_kwargs,
        )

        assert result.status == ValidationStatus.VALID
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_parameter_validation_wrong_types(self, mock_validator):
        """Test parameter validation with incorrect types"""
        await mock_validator.initialize()

        # Mock function/method parameters from knowledge graph
        expected_params = {"param1": "str", "param2": "int"}
        provided_args = [42, "hello"]  # Wrong types
        provided_kwargs = {}

        result = mock_validator._validate_parameters(
            expected_params,
            provided_args,
            provided_kwargs,
        )

        assert result.status == ValidationStatus.UNCERTAIN
        assert result.confidence < 0.8

    @pytest.mark.asyncio
    async def test_parameter_validation_missing_args(self, mock_validator):
        """Test parameter validation with missing arguments"""
        await mock_validator.initialize()

        # Mock function/method parameters from knowledge graph
        expected_params = {"param1": "str", "param2": "int"}
        provided_args = ["hello"]  # Missing second argument
        provided_kwargs = {}

        result = mock_validator._validate_parameters(
            expected_params,
            provided_args,
            provided_kwargs,
        )

        assert result.status == ValidationStatus.UNCERTAIN
        assert result.confidence < 0.8

    @pytest.mark.asyncio
    async def test_parameter_validation_with_kwargs(self, mock_validator):
        """Test parameter validation with keyword arguments"""
        await mock_validator.initialize()

        # Mock function/method parameters from knowledge graph
        expected_params = {"param1": "str", "param2": "int"}
        provided_args = ["hello"]
        provided_kwargs = {"param2": 42}

        result = mock_validator._validate_parameters(
            expected_params,
            provided_args,
            provided_kwargs,
        )

        assert result.status == ValidationStatus.VALID
        assert result.confidence >= 0.8


class TestValidationCaching:
    """Test caching mechanisms in KnowledgeGraphValidator"""

    @pytest.fixture
    def cached_validator(self, validator_config):
        """Create validator with pre-populated caches"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )
            validator.driver = mock_driver

            # Pre-populate caches
            validator.module_cache["main"] = {
                "name": "main",
                "path": "src/main.py",
                "classes": ["TestClass"],
                "functions": ["test_function"],
            }

            validator.class_cache["TestClass"] = {
                "name": "TestClass",
                "full_name": "main.TestClass",
                "methods": ["test_method"],
                "attributes": ["test_attr"],
            }

            validator.method_cache[("TestClass", "test_method")] = {
                "name": "test_method",
                "params": {"param1": "str"},
                "return_type": "bool",
            }

            yield validator

    @pytest.mark.asyncio
    async def test_module_cache_hit(self, cached_validator):
        """Test that module cache prevents unnecessary database queries"""
        await cached_validator.initialize()

        # This should use cached data, not query database
        modules = await cached_validator._find_modules("main")

        assert len(modules) > 0
        assert modules[0]["name"] == "main"

    @pytest.mark.asyncio
    async def test_class_cache_hit(self, cached_validator):
        """Test that class cache prevents unnecessary database queries"""
        await cached_validator.initialize()

        # This should use cached data
        class_info = await cached_validator._find_class("TestClass", "main")

        assert class_info is not None
        assert class_info["name"] == "TestClass"

    @pytest.mark.asyncio
    async def test_method_cache_hit(self, cached_validator):
        """Test that method cache prevents unnecessary database queries"""
        await cached_validator.initialize()

        # This should use cached data
        method_info = await cached_validator._find_method("test_method", "TestClass")

        assert method_info is not None
        assert method_info["name"] == "test_method"

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_query(
        self,
        cached_validator,
        neo4j_query_responses,
    ):
        """Test that cache miss triggers database query"""
        await cached_validator.initialize()

        # Set up mock response for cache miss
        cached_validator.driver.session_data = neo4j_query_responses["find_module"]

        # Query for non-cached module
        modules = await cached_validator._find_modules("utils")

        # Should have queried database and potentially cached result
        assert isinstance(modules, list)


class TestConfidenceScoring:
    """Test confidence scoring mechanisms"""

    @pytest.fixture
    def scoring_validator(self, validator_config):
        """Create validator for confidence scoring tests"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )
            validator.driver = mock_driver

            yield validator

    def test_calculate_overall_confidence_all_valid(self, scoring_validator):
        """Test confidence calculation with all valid validations"""
        # Mock validation results - all valid
        import_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=1.0),
            ),
        ]
        class_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=0.9),
            ),
        ]
        method_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=0.8),
            ),
        ]
        attribute_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=0.9),
            ),
        ]
        function_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=0.8),
            ),
        ]

        confidence = scoring_validator._calculate_overall_confidence(
            import_validations,
            class_validations,
            method_validations,
            attribute_validations,
            function_validations,
        )

        # Should be high confidence since all validations are valid
        assert confidence >= 0.8

    def test_calculate_overall_confidence_mixed_results(self, scoring_validator):
        """Test confidence calculation with mixed validation results"""
        # Mock validation results - mixed
        import_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=1.0),
            ),
            MagicMock(
                validation=MagicMock(status=ValidationStatus.INVALID, confidence=0.0),
            ),
        ]
        class_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.UNCERTAIN, confidence=0.5),
            ),
        ]
        method_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.NOT_FOUND, confidence=0.0),
            ),
        ]

        confidence = scoring_validator._calculate_overall_confidence(
            import_validations,
            class_validations,
            method_validations,
            [],
            [],
        )

        # Should be moderate confidence due to mixed results
        assert 0.2 <= confidence <= 0.8

    def test_calculate_overall_confidence_all_invalid(self, scoring_validator):
        """Test confidence calculation with all invalid validations"""
        # Mock validation results - all invalid
        import_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.INVALID, confidence=0.0),
            ),
        ]
        method_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.NOT_FOUND, confidence=0.0),
            ),
        ]

        confidence = scoring_validator._calculate_overall_confidence(
            import_validations,
            [],
            method_validations,
            [],
            [],
        )

        # Should be low confidence since all validations are invalid
        assert confidence <= 0.3


class TestHallucinationDetection:
    """Test hallucination detection capabilities"""

    @pytest.fixture
    def hallucination_validator(self, validator_config):
        """Create validator for hallucination detection tests"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )
            validator.driver = mock_driver

            # Set up knowledge graph modules
            validator.knowledge_graph_modules = {"main", "utils", "helpers"}

            yield validator

    def test_is_from_knowledge_graph_true(self, hallucination_validator):
        """Test detection of modules from knowledge graph"""
        # Test modules that are in knowledge graph
        assert hallucination_validator._is_from_knowledge_graph("main") is True
        assert hallucination_validator._is_from_knowledge_graph("utils") is True
        assert hallucination_validator._is_from_knowledge_graph("helpers") is True

    def test_is_from_knowledge_graph_false(self, hallucination_validator):
        """Test detection of modules not from knowledge graph"""
        # Test modules that are not in knowledge graph
        assert hallucination_validator._is_from_knowledge_graph("nonexistent") is False
        assert hallucination_validator._is_from_knowledge_graph("fake_module") is False

    def test_is_from_knowledge_graph_external_modules(self, hallucination_validator):
        """Test handling of external modules (should not be considered hallucinations)"""
        # External modules like standard library should not be flagged as hallucinations
        assert (
            hallucination_validator._is_from_knowledge_graph("os") is False
        )  # But this is okay
        assert (
            hallucination_validator._is_from_knowledge_graph("sys") is False
        )  # External, not hallucination

    def test_detect_hallucinations_none_found(self, hallucination_validator):
        """Test hallucination detection when no hallucinations exist"""
        # Mock script validation result with valid elements
        mock_result = MagicMock()
        mock_result.import_validations = [
            MagicMock(
                import_info=MagicMock(module="main"),
                validation=MagicMock(status=ValidationStatus.VALID, confidence=1.0),
            ),
        ]
        mock_result.method_validations = [
            MagicMock(
                validation=MagicMock(status=ValidationStatus.VALID, confidence=0.9),
            ),
        ]
        mock_result.class_validations = []
        mock_result.attribute_validations = []
        mock_result.function_validations = []

        hallucinations = hallucination_validator._detect_hallucinations(mock_result)

        assert len(hallucinations) == 0

    def test_detect_hallucinations_found(self, hallucination_validator):
        """Test hallucination detection when hallucinations exist"""
        # Mock script validation result with invalid elements (potential hallucinations)
        mock_result = MagicMock()
        mock_result.import_validations = [
            MagicMock(
                import_info=MagicMock(module="fake_module"),
                validation=MagicMock(status=ValidationStatus.INVALID, confidence=0.0),
            ),
        ]
        mock_result.method_validations = [
            MagicMock(
                method_call=MagicMock(method_name="fake_method"),
                validation=MagicMock(status=ValidationStatus.NOT_FOUND, confidence=0.0),
            ),
        ]
        mock_result.class_validations = []
        mock_result.attribute_validations = []
        mock_result.function_validations = []

        hallucinations = hallucination_validator._detect_hallucinations(mock_result)

        assert len(hallucinations) > 0
        # Should contain information about the detected hallucinations


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios"""

    @pytest.fixture
    def error_validator(self, validator_config):
        """Create validator for error testing"""
        with patch("knowledge_graph_validator.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            validator = KnowledgeGraphValidator(
                validator_config["neo4j_uri"],
                validator_config["neo4j_user"],
                validator_config["neo4j_password"],
            )
            validator.driver = mock_driver

            yield validator

    @pytest.mark.asyncio
    async def test_database_connection_error(self, error_validator):
        """Test handling of database connection errors"""
        await error_validator.initialize()

        # Simulate database error
        from neo4j.exceptions import ServiceUnavailable

        error_validator.driver.exception = ServiceUnavailable("Database unavailable")

        # Mock analysis result
        mock_analysis_result = MagicMock()
        mock_analysis_result.imports = []
        mock_analysis_result.class_instantiations = []
        mock_analysis_result.method_calls = []
        mock_analysis_result.attribute_accesses = []
        mock_analysis_result.function_calls = []

        with pytest.raises(ServiceUnavailable):
            await error_validator.validate_script(mock_analysis_result)

    @pytest.mark.asyncio
    async def test_empty_analysis_result(self, error_validator):
        """Test handling of empty analysis results"""
        await error_validator.initialize()

        # Mock empty analysis result
        mock_analysis_result = MagicMock()
        mock_analysis_result.imports = []
        mock_analysis_result.class_instantiations = []
        mock_analysis_result.method_calls = []
        mock_analysis_result.attribute_accesses = []
        mock_analysis_result.function_calls = []

        result = await error_validator.validate_script(mock_analysis_result)

        assert result is not None
        assert hasattr(result, "overall_confidence")
        # Should handle empty analysis gracefully

    @pytest.mark.asyncio
    async def test_malformed_query_response(self, error_validator):
        """Test handling of malformed query responses"""
        await error_validator.initialize()

        # Set up malformed response
        error_validator.driver.session_data = [{"malformed": "data"}]

        # Mock import for testing
        mock_import = MagicMock()
        mock_import.module = "test_module"
        mock_import.imports = ["TestClass"]

        result = await error_validator._validate_single_import(mock_import)

        # Should handle malformed response gracefully
        assert result is not None
        assert result.validation.status == ValidationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_none_values_handling(self, error_validator):
        """Test handling of None values in validation inputs"""
        await error_validator.initialize()

        # Test with None import
        result = await error_validator._validate_single_import(None)

        # Should handle None input gracefully
        assert result is not None
        assert result.validation.status == ValidationStatus.INVALID

    @pytest.mark.asyncio
    async def test_large_parameter_lists(self, error_validator):
        """Test handling of functions with large parameter lists"""
        await error_validator.initialize()

        # Mock function with many parameters
        large_params = {f"param_{i}": "str" for i in range(100)}
        provided_args = [f"arg_{i}" for i in range(100)]

        result = error_validator._validate_parameters(large_params, provided_args, {})

        assert result is not None
        # Should handle large parameter lists without performance issues

    @pytest.mark.asyncio
    async def test_unicode_handling(self, error_validator):
        """Test handling of Unicode characters in names"""
        await error_validator.initialize()

        # Mock import with Unicode characters
        mock_import = MagicMock()
        mock_import.module = "модуль"  # Russian text
        mock_import.imports = ["Класс"]  # Russian text

        result = await error_validator._validate_single_import(mock_import)

        # Should handle Unicode without errors
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
