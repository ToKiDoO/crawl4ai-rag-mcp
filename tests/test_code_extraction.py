"""
Unit tests for Neo4j code extraction functionality.

Tests the Neo4jCodeExtractor class that extracts structured code examples
from Neo4j knowledge graph for embedding generation and Qdrant indexing.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from knowledge_graph.code_extractor import (
    CodeExample,
    Neo4jCodeExtractor,
    extract_repository_code,
)


class TestCodeExample:
    """Test CodeExample data class functionality."""

    def test_code_example_creation(self):
        """Test creating a CodeExample instance."""
        example = CodeExample(
            repository_name="test-repo",
            file_path="src/main.py",
            module_name="main",
            code_type="class",
            name="TestClass",
            full_name="main.TestClass",
            code_text="class TestClass:\n    pass",
            parameters=["self", "param1"],
            return_type="None",
            class_name="TestClass",
            method_count=3,
        )

        assert example.repository_name == "test-repo"
        assert example.code_type == "class"
        assert example.name == "TestClass"
        assert example.method_count == 3
        assert example.language == "python"  # default
        assert example.validation_status == "extracted"  # default

    def test_code_example_to_metadata(self):
        """Test converting CodeExample to metadata dictionary."""
        example = CodeExample(
            repository_name="test-repo",
            file_path="src/utils.py",
            module_name="utils",
            code_type="function",
            name="helper_func",
            full_name="utils.helper_func",
            code_text="def helper_func(x: int) -> str:\n    return str(x)",
            parameters=["x"],
            return_type="str",
        )

        metadata = example.to_metadata()

        assert metadata["repository_name"] == "test-repo"
        assert metadata["code_type"] == "function"
        assert metadata["name"] == "helper_func"
        assert metadata["parameters"] == ["x"]
        assert metadata["return_type"] == "str"
        assert metadata["language"] == "python"

        # Optional fields should not be present if None
        assert "class_name" not in metadata
        assert "method_count" not in metadata

    def test_code_example_generate_embedding_text_class(self):
        """Test generating embedding text for a class."""
        example = CodeExample(
            repository_name="django-project",
            file_path="models.py",
            module_name="myapp.models",
            code_type="class",
            name="User",
            full_name="myapp.models.User",
            code_text="class User(models.Model):\n    username = models.CharField()",
            method_count=5,
        )

        embedding_text = example.generate_embedding_text()

        assert "Python class User" in embedding_text
        assert "myapp.models" in embedding_text
        assert "Full name: myapp.models.User" in embedding_text
        assert "Contains 5 methods" in embedding_text
        assert "class User(models.Model)" in embedding_text

    def test_code_example_generate_embedding_text_method(self):
        """Test generating embedding text for a method."""
        example = CodeExample(
            repository_name="api-service",
            file_path="handlers.py",
            module_name="api.handlers",
            code_type="method",
            name="authenticate",
            full_name="api.handlers.AuthHandler.authenticate",
            code_text="def authenticate(self, username, password):\n    return check_credentials(username, password)",
            parameters=["self", "username", "password"],
            return_type="bool",
            class_name="AuthHandler",
        )

        embedding_text = example.generate_embedding_text()

        assert "Python method authenticate" in embedding_text
        assert "in class AuthHandler" in embedding_text
        assert "from api.handlers" in embedding_text
        assert "Parameters: self, username, password" in embedding_text
        assert "Returns: bool" in embedding_text
        assert "def authenticate" in embedding_text

    def test_code_example_generate_embedding_text_function(self):
        """Test generating embedding text for a standalone function."""
        example = CodeExample(
            repository_name="utils-lib",
            file_path="helpers.py",
            module_name="utils.helpers",
            code_type="function",
            name="calculate_hash",
            full_name="utils.helpers.calculate_hash",
            code_text="def calculate_hash(data: bytes) -> str:\n    return hashlib.sha256(data).hexdigest()",
            parameters=["data"],
            return_type="str",
        )

        embedding_text = example.generate_embedding_text()

        assert "Python function calculate_hash" in embedding_text
        assert "from utils.helpers" in embedding_text
        assert "Parameters: data" in embedding_text
        assert "Returns: str" in embedding_text
        assert "def calculate_hash" in embedding_text


class TestNeo4jCodeExtractor:
    """Test Neo4jCodeExtractor functionality."""

    @pytest.fixture
    def mock_neo4j_session(self):
        """Create a mock Neo4j session."""
        session = AsyncMock()
        session.run = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def code_extractor(self, mock_neo4j_session):
        """Create a Neo4jCodeExtractor with mocked session."""
        return Neo4jCodeExtractor(mock_neo4j_session)

    @pytest.mark.asyncio
    async def test_extract_repository_code_repository_not_found(
        self, code_extractor, mock_neo4j_session
    ):
        """Test extracting code when repository doesn't exist."""
        # Mock repository not found
        mock_result = AsyncMock()
        mock_result.single.return_value = None
        mock_neo4j_session.run.return_value = mock_result

        with pytest.raises(ValueError, match="Repository 'nonexistent-repo' not found"):
            await code_extractor.extract_repository_code("nonexistent-repo")

    @pytest.mark.asyncio
    async def test_extract_repository_code_success(
        self, code_extractor, mock_neo4j_session
    ):
        """Test successful code extraction from repository."""
        # Mock repository exists
        repo_result = AsyncMock()
        repo_result.single.return_value = {"name": "test-repo"}

        # Mock class extraction result
        class_result = AsyncMock()
        class_result.__aiter__.return_value = iter(
            [
                {
                    "class_name": "TestClass",
                    "class_full_name": "module.TestClass",
                    "file_path": "src/module.py",
                    "module_name": "module",
                    "method_count": 2,
                    "methods": [
                        {
                            "name": "init_method",
                            "params_list": ["self", "param1"],
                            "params_detailed": ["self", "param1: str"],
                            "return_type": "None",
                            "args": ["self", "param1"],
                        },
                        {
                            "name": "public_method",
                            "params_list": ["self"],
                            "params_detailed": ["self"],
                            "return_type": "str",
                            "args": ["self"],
                        },
                    ],
                },
            ]
        )

        # Mock function extraction result
        function_result = AsyncMock()
        function_result.__aiter__.return_value = iter(
            [
                {
                    "function_name": "utility_function",
                    "params_list": ["data", "format"],
                    "params_detailed": ["data: dict", "format: str"],
                    "return_type": "str",
                    "args": ["data", "format"],
                    "file_path": "src/utils.py",
                    "module_name": "utils",
                },
            ]
        )

        # Set up mock session responses
        mock_neo4j_session.run.side_effect = [
            repo_result,  # Repository exists check
            class_result,  # Class extraction
            function_result,  # Function extraction
        ]

        result = await code_extractor.extract_repository_code("test-repo")

        assert len(result) == 4  # 1 class + 2 methods + 1 function

        # Verify class example
        class_examples = [ex for ex in result if ex.code_type == "class"]
        assert len(class_examples) == 1
        class_ex = class_examples[0]
        assert class_ex.name == "TestClass"
        assert class_ex.method_count == 2
        assert "class TestClass:" in class_ex.code_text

        # Verify method examples
        method_examples = [ex for ex in result if ex.code_type == "method"]
        assert len(method_examples) == 2

        public_method = next(ex for ex in method_examples if ex.name == "public_method")
        assert public_method.class_name == "TestClass"
        assert public_method.return_type == "str"

        # Verify function example
        function_examples = [ex for ex in result if ex.code_type == "function"]
        assert len(function_examples) == 1
        func_ex = function_examples[0]
        assert func_ex.name == "utility_function"
        assert func_ex.parameters == ["data", "format"]
        assert func_ex.return_type == "str"

    @pytest.mark.asyncio
    async def test_extract_classes_with_methods(
        self, code_extractor, mock_neo4j_session
    ):
        """Test extracting classes with their methods."""
        # Mock successful class query result
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter(
            [
                {
                    "class_name": "DataProcessor",
                    "class_full_name": "services.DataProcessor",
                    "file_path": "src/services.py",
                    "module_name": "services",
                    "method_count": 3,
                    "methods": [
                        {
                            "name": "__init__",
                            "params_list": ["self", "config"],
                            "params_detailed": ["self", "config: dict"],
                            "return_type": None,
                            "args": ["self", "config"],
                        },
                        {
                            "name": "process",
                            "params_list": ["self", "data"],
                            "params_detailed": ["self", "data: list"],
                            "return_type": "dict",
                            "args": ["self", "data"],
                        },
                        {
                            "name": "_private_method",
                            "params_list": ["self"],
                            "params_detailed": ["self"],
                            "return_type": "bool",
                            "args": ["self"],
                        },
                    ],
                },
            ]
        )
        mock_neo4j_session.run.return_value = mock_result

        classes = await code_extractor._extract_classes("test-repo")

        # Should have 1 class + 1 public method (private method excluded)
        assert len(classes) == 2

        class_example = next(ex for ex in classes if ex.code_type == "class")
        assert class_example.name == "DataProcessor"
        assert class_example.method_count == 3

        method_examples = [ex for ex in classes if ex.code_type == "method"]
        assert len(method_examples) == 1  # Only public method
        assert method_examples[0].name == "process"

    @pytest.mark.asyncio
    async def test_extract_functions_filtering(
        self, code_extractor, mock_neo4j_session
    ):
        """Test extracting functions with proper filtering."""
        # Mock function query result with private and public functions
        mock_result = AsyncMock()
        mock_result.__aiter__.return_value = iter(
            [
                {
                    "function_name": "public_function",
                    "params_list": ["param1", "param2"],
                    "params_detailed": ["param1: str", "param2: int"],
                    "return_type": "bool",
                    "args": ["param1", "param2"],
                    "file_path": "src/helpers.py",
                    "module_name": "helpers",
                },
                {
                    "function_name": "_private_function",
                    "params_list": ["data"],
                    "params_detailed": ["data: dict"],
                    "return_type": "None",
                    "args": ["data"],
                    "file_path": "src/helpers.py",
                    "module_name": "helpers",
                },
                {
                    "function_name": None,  # Invalid function name
                    "params_list": [],
                    "params_detailed": [],
                    "return_type": "None",
                    "args": [],
                    "file_path": "src/broken.py",
                    "module_name": "broken",
                },
            ]
        )
        mock_neo4j_session.run.return_value = mock_result

        functions = await code_extractor._extract_functions("test-repo")

        # Should only include public_function (filter out private and invalid)
        assert len(functions) == 1
        func = functions[0]
        assert func.name == "public_function"
        assert func.parameters == ["param1", "param2"]
        assert func.return_type == "bool"

    def test_generate_class_code(self, code_extractor):
        """Test generating code representation for a class."""
        methods = [
            {
                "name": "__init__",
                "params_list": ["self", "name"],
                "return_type": "None",
            },
            {
                "name": "get_name",
                "params_list": ["self"],
                "return_type": "str",
            },
            {
                "name": "_private_method",
                "params_list": ["self"],
                "return_type": "bool",
            },
        ]

        code = code_extractor._generate_class_code("TestClass", methods)

        assert "class TestClass:" in code
        assert "def get_name(self) -> str: ..." in code
        assert "_private_method" not in code  # Private methods excluded
        assert "__init__" not in code  # Constructor excluded from public methods

    def test_generate_method_code(self, code_extractor):
        """Test generating code representation for a method."""
        method = {
            "name": "calculate_total",
            "params_list": ["self", "items", "tax_rate"],
            "return_type": "float",
        }

        code = code_extractor._generate_method_code(method)

        assert "def calculate_total(self, items, tax_rate) -> float:" in code
        assert '"""Method implementation"""' in code
        assert "pass" in code

    def test_generate_function_code(self, code_extractor):
        """Test generating code representation for a function."""
        function = {
            "name": "format_currency",
            "params_list": ["amount", "currency"],
            "return_type": "str",
        }

        code = code_extractor._generate_function_code(function)

        assert "def format_currency(amount, currency) -> str:" in code
        assert '"""Function implementation"""' in code
        assert "pass" in code

    @pytest.mark.asyncio
    async def test_repository_exists_check(self, code_extractor, mock_neo4j_session):
        """Test repository existence check."""
        # Test existing repository
        existing_result = AsyncMock()
        existing_result.single.return_value = {"name": "existing-repo"}
        mock_neo4j_session.run.return_value = existing_result

        exists = await code_extractor._repository_exists("existing-repo")
        assert exists is True

        # Test non-existing repository
        missing_result = AsyncMock()
        missing_result.single.return_value = None
        mock_neo4j_session.run.return_value = missing_result

        exists = await code_extractor._repository_exists("missing-repo")
        assert exists is False

    @pytest.mark.asyncio
    async def test_extraction_error_handling(self, code_extractor, mock_neo4j_session):
        """Test error handling during code extraction."""
        # Mock repository exists
        repo_result = AsyncMock()
        repo_result.single.return_value = {"name": "test-repo"}

        # Mock error during class extraction
        mock_neo4j_session.run.side_effect = [
            repo_result,  # Repository exists
            Exception("Neo4j query failed"),  # Class extraction fails
        ]

        with pytest.raises(Exception, match="Neo4j query failed"):
            await code_extractor.extract_repository_code("test-repo")


class TestExtractRepositoryCodeFunction:
    """Test the extract_repository_code helper function."""

    @pytest.fixture
    def mock_repo_extractor(self):
        """Create a mock repository extractor."""
        mock_extractor = MagicMock()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value.__aenter__.return_value = mock_session
        mock_extractor.driver = mock_driver
        return mock_extractor, mock_session

    @pytest.mark.asyncio
    async def test_extract_repository_code_success(self, mock_repo_extractor):
        """Test successful repository code extraction."""
        mock_extractor, mock_session = mock_repo_extractor

        # Mock Neo4jCodeExtractor
        with patch(
            "knowledge_graph.code_extractor.Neo4jCodeExtractor"
        ) as mock_extractor_class:
            mock_instance = AsyncMock()
            mock_extractor_class.return_value = mock_instance

            # Mock extraction results
            mock_code_examples = [
                CodeExample(
                    repository_name="test-repo",
                    file_path="src/main.py",
                    module_name="main",
                    code_type="class",
                    name="MainClass",
                    full_name="main.MainClass",
                    code_text="class MainClass:\n    pass",
                ),
                CodeExample(
                    repository_name="test-repo",
                    file_path="src/utils.py",
                    module_name="utils",
                    code_type="function",
                    name="helper_func",
                    full_name="utils.helper_func",
                    code_text="def helper_func():\n    pass",
                ),
            ]
            mock_instance.extract_repository_code.return_value = mock_code_examples

            result = await extract_repository_code(mock_extractor, "test-repo")

            # Verify successful extraction
            assert result["success"] is True
            assert result["repository_name"] == "test-repo"
            assert result["code_examples_count"] == 2
            assert len(result["code_examples"]) == 2

            # Verify extraction summary
            summary = result["extraction_summary"]
            assert summary["classes"] == 1
            assert summary["functions"] == 1
            assert summary["methods"] == 0

            # Verify example data structure
            class_example = result["code_examples"][0]
            assert class_example["code_type"] == "class"
            assert class_example["name"] == "MainClass"
            assert "embedding_text" in class_example
            assert "metadata" in class_example

    @pytest.mark.asyncio
    async def test_extract_repository_code_error(self, mock_repo_extractor):
        """Test error handling in repository code extraction."""
        mock_extractor, mock_session = mock_repo_extractor

        # Mock Neo4jCodeExtractor with error
        with patch(
            "knowledge_graph.code_extractor.Neo4jCodeExtractor"
        ) as mock_extractor_class:
            mock_instance = AsyncMock()
            mock_extractor_class.return_value = mock_instance
            mock_instance.extract_repository_code.side_effect = Exception(
                "Extraction failed"
            )

            result = await extract_repository_code(mock_extractor, "test-repo")

            # Verify error handling
            assert result["success"] is False
            assert result["repository_name"] == "test-repo"
            assert "error" in result
            assert "Extraction failed" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_repository_code_empty_result(self, mock_repo_extractor):
        """Test extraction with no code examples found."""
        mock_extractor, mock_session = mock_repo_extractor

        with patch(
            "knowledge_graph.code_extractor.Neo4jCodeExtractor"
        ) as mock_extractor_class:
            mock_instance = AsyncMock()
            mock_extractor_class.return_value = mock_instance
            mock_instance.extract_repository_code.return_value = []  # No examples

            result = await extract_repository_code(mock_extractor, "empty-repo")

            assert result["success"] is True
            assert result["code_examples_count"] == 0
            assert result["code_examples"] == []
            assert result["extraction_summary"]["classes"] == 0
            assert result["extraction_summary"]["methods"] == 0
            assert result["extraction_summary"]["functions"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
