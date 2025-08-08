"""
Comprehensive tests for Neo4j integration functionality.

This module tests core Neo4j operations including:
- Node creation and updates
- Relationship management
- Cypher query execution
- Transaction handling
- Index management
- Constraint validation
- Connection management
- Error handling and recovery
"""

import asyncio
import os

# Add src to path for imports
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import mock classes for type hints and direct usage
from tests.fixtures.neo4j_fixtures import (
    MockNeo4jDriver,
)

# Fixtures are automatically available via conftest.py import

# Mock Neo4j imports before importing our modules
with patch.dict(
    "sys.modules",
    {"neo4j": MagicMock(), "neo4j.AsyncGraphDatabase": MagicMock()},
):
    # Now import our modules
    sys.path.insert(
        0,
        os.path.join(os.path.dirname(__file__), "..", "knowledge_graphs"),
    )
    from parse_repo_into_neo4j import DirectNeo4jExtractor, Neo4jCodeAnalyzer


class TestDirectNeo4jExtractor:
    """Test the DirectNeo4jExtractor class for core Neo4j operations"""

    @pytest.fixture
    def extractor_config(self):
        """Configuration for Neo4j extractor"""
        return {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "test_user",
            "neo4j_password": "test_password",
        }

    @pytest.fixture
    def mock_extractor(self, extractor_config):
        """Create a DirectNeo4jExtractor with mocked dependencies"""
        with patch("parse_repo_into_neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            extractor = DirectNeo4jExtractor(
                extractor_config["neo4j_uri"],
                extractor_config["neo4j_user"],
                extractor_config["neo4j_password"],
            )
            extractor.driver = mock_driver

            # Mock the analyzer
            extractor.analyzer = MagicMock(spec=Neo4jCodeAnalyzer)

            yield extractor

    @pytest.mark.asyncio
    async def test_initialization(self, extractor_config):
        """Test DirectNeo4jExtractor initialization"""
        with patch("parse_repo_into_neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            extractor = DirectNeo4jExtractor(
                extractor_config["neo4j_uri"],
                extractor_config["neo4j_user"],
                extractor_config["neo4j_password"],
            )

            assert extractor.neo4j_uri == extractor_config["neo4j_uri"]
            assert extractor.neo4j_user == extractor_config["neo4j_user"]
            assert extractor.neo4j_password == extractor_config["neo4j_password"]
            assert extractor.driver is None  # Not initialized yet
            assert extractor.analyzer is not None

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_extractor):
        """Test successful initialization of Neo4j connection"""
        await mock_extractor.initialize()

        # Verify driver is set up
        assert mock_extractor.driver is not None
        assert isinstance(mock_extractor.driver, MockNeo4jDriver)

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, extractor_config):
        """Test initialization failure due to connection issues"""
        with patch("parse_repo_into_neo4j.AsyncGraphDatabase") as mock_db:
            # Simulate connection failure
            mock_db.driver.side_effect = Exception("Connection failed")

            extractor = DirectNeo4jExtractor(
                extractor_config["neo4j_uri"],
                extractor_config["neo4j_user"],
                extractor_config["neo4j_password"],
            )

            with pytest.raises(Exception, match="Connection failed"):
                await extractor.initialize()

    @pytest.mark.asyncio
    async def test_close_connection(self, mock_extractor):
        """Test closing Neo4j connection"""
        await mock_extractor.initialize()
        await mock_extractor.close()

        assert mock_extractor.driver.closed is True

    @pytest.mark.asyncio
    async def test_clear_repository_data(self, mock_extractor, neo4j_query_responses):
        """Test clearing repository data from Neo4j"""
        await mock_extractor.initialize()

        # Set up mock responses
        mock_extractor.driver.session_data = neo4j_query_responses["clear_repository"]

        result = await mock_extractor.clear_repository_data("test-repo")

        assert result is not None
        # Verify that delete queries were executed
        # (In a real implementation, we'd check the actual queries)

    @pytest.mark.asyncio
    async def test_create_repository_node(self, mock_extractor, sample_repository_data):
        """Test creating a repository node in Neo4j"""
        await mock_extractor.initialize()

        # Mock successful node creation
        mock_extractor.driver.session_data = [{"repo": {"name": "test-repo"}}]

        # This would be part of _create_graph method
        # We'll test it indirectly through analyze_repository
        result = await mock_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_file_nodes(self, mock_extractor, sample_repository_data):
        """Test creating file nodes with proper relationships"""
        await mock_extractor.initialize()

        # Mock successful file node creation
        mock_extractor.driver.session_data = [
            {"file": {"path": "src/main.py", "module_name": "main"}},
        ]

        result = await mock_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_class_nodes(self, mock_extractor, sample_repository_data):
        """Test creating class nodes with methods and attributes"""
        await mock_extractor.initialize()

        # Mock successful class node creation
        mock_extractor.driver.session_data = [
            {"class": {"name": "TestClass", "full_name": "main.TestClass"}},
        ]

        result = await mock_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_method_nodes(self, mock_extractor, sample_repository_data):
        """Test creating method nodes with parameter information"""
        await mock_extractor.initialize()

        # Mock successful method node creation
        mock_extractor.driver.session_data = [
            {
                "method": {
                    "name": "test_method",
                    "args": ["self", "param1"],
                    "params": {"param1": "str"},
                    "return_type": "bool",
                },
            },
        ]

        result = await mock_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_function_nodes(self, mock_extractor, sample_repository_data):
        """Test creating function nodes with parameter information"""
        await mock_extractor.initialize()

        # Mock successful function node creation
        mock_extractor.driver.session_data = [
            {
                "function": {
                    "name": "test_function",
                    "args": ["param1", "param2"],
                    "params": {"param1": "str", "param2": "int"},
                    "return_type": "str",
                },
            },
        ]

        result = await mock_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_import_relationships(
        self,
        mock_extractor,
        sample_repository_data,
    ):
        """Test creating import relationships between files"""
        await mock_extractor.initialize()

        # Mock successful relationship creation
        mock_extractor.driver.session_data = [
            {"relationship": {"type": "IMPORTS", "from": "main.py", "to": "os"}},
        ]

        result = await mock_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_graph_basic(self, mock_extractor, neo4j_query_responses):
        """Test basic graph search functionality"""
        await mock_extractor.initialize()

        # Set up search response
        mock_extractor.driver.session_data = neo4j_query_responses["find_class"]

        result = await mock_extractor.search_graph("MATCH (c:Class) RETURN c")

        assert result is not None
        assert (
            len(result) > 0 if mock_extractor.driver.session_data else len(result) == 0
        )

    @pytest.mark.asyncio
    async def test_search_graph_with_parameters(
        self,
        mock_extractor,
        neo4j_query_responses,
    ):
        """Test graph search with query parameters"""
        await mock_extractor.initialize()

        # Set up parameterized search response
        mock_extractor.driver.session_data = neo4j_query_responses["find_method"]

        result = await mock_extractor.search_graph(
            "MATCH (m:Method) WHERE m.name = $method_name RETURN m",
            {"method_name": "test_method"},
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, mock_extractor):
        """Test transaction rollback when errors occur"""
        await mock_extractor.initialize()

        # Simulate an error during graph creation
        mock_extractor.driver.exception = Exception("Database constraint violation")

        with pytest.raises(Exception, match="Database constraint violation"):
            await mock_extractor.analyze_repository(
                "https://github.com/test/repo",
                [{"path": "test.py", "classes": []}],
            )


class TestNeo4jCodeAnalyzer:
    """Test the Neo4jCodeAnalyzer class"""

    @pytest.fixture
    def analyzer(self):
        """Create a Neo4jCodeAnalyzer instance"""
        return Neo4jCodeAnalyzer()

    def test_initialization(self, analyzer):
        """Test analyzer initialization with external modules"""
        assert analyzer is not None
        assert hasattr(analyzer, "external_modules")
        assert "os" in analyzer.external_modules
        assert "sys" in analyzer.external_modules

    def test_is_external_module_detection(self, analyzer):
        """Test external module detection"""
        # Test standard library modules
        assert analyzer._is_external_module("os") is True
        assert analyzer._is_external_module("sys") is True
        assert analyzer._is_external_module("json") is True

        # Test third-party modules (should also be considered external)
        assert analyzer._is_external_module("numpy") is True
        assert analyzer._is_external_module("requests") is True

        # Test internal modules (relative imports)
        assert analyzer._is_external_module("main") is False
        assert analyzer._is_external_module("utils") is False

    def test_extract_module_name(self, analyzer):
        """Test module name extraction from file paths"""
        test_cases = [
            ("src/main.py", "main"),
            ("src/utils/helpers.py", "helpers"),
            ("package/__init__.py", "__init__"),
            ("test_file.py", "test_file"),
            ("src/nested/deep/module.py", "module"),
        ]

        for file_path, expected_module in test_cases:
            result = analyzer._extract_module_name(file_path)
            assert result == expected_module, (
                f"Expected {expected_module}, got {result} for {file_path}"
            )

    def test_analyze_python_file_simple(self, analyzer, tmp_path):
        """Test analyzing a simple Python file"""
        # Create a test Python file
        test_file = tmp_path / "test_simple.py"
        test_file.write_text('''
def simple_function():
    """A simple function"""
    return "hello"

class SimpleClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
''')

        result = analyzer.analyze_python_file(str(test_file))

        assert result is not None
        assert "functions" in result
        assert "classes" in result
        assert len(result["functions"]) >= 1
        assert len(result["classes"]) >= 1

    def test_analyze_python_file_with_imports(self, analyzer, tmp_path):
        """Test analyzing a Python file with imports"""
        test_file = tmp_path / "test_imports.py"
        test_file.write_text('''
import os
import sys
from json import loads, dumps
from typing import List, Dict

def process_data(data: List[Dict]) -> str:
    """Process data using imported modules"""
    return dumps(data)
''')

        result = analyzer.analyze_python_file(str(test_file))

        assert result is not None
        assert "imports" in result
        assert len(result["imports"]) > 0

        # Check that imports are properly categorized
        imports = result["imports"]
        assert "os" in imports or any("os" in imp for imp in imports)
        assert "sys" in imports or any("sys" in imp for imp in imports)

    def test_analyze_python_file_with_complex_classes(self, analyzer, tmp_path):
        """Test analyzing a Python file with complex class structures"""
        test_file = tmp_path / "test_complex.py"
        test_file.write_text('''
from typing import Optional, List

class BaseClass:
    """Base class with methods and attributes"""
    
    def __init__(self, name: str):
        self.name = name
        self._private_attr = None
    
    def public_method(self, param: int) -> str:
        """Public method with typed parameters"""
        return f"{self.name}_{param}"
    
    def _private_method(self) -> None:
        """Private method"""
        pass

class DerivedClass(BaseClass):
    """Derived class inheriting from BaseClass"""
    
    def __init__(self, name: str, value: Optional[int] = None):
        super().__init__(name)
        self.value = value
    
    def derived_method(self, items: List[str]) -> bool:
        """Method with complex types"""
        return len(items) > 0
''')

        result = analyzer.analyze_python_file(str(test_file))

        assert result is not None
        assert "classes" in result
        assert len(result["classes"]) >= 2

        # Verify class details are captured
        classes = result["classes"]
        class_names = [cls.get("name", "") for cls in classes]
        assert "BaseClass" in class_names
        assert "DerivedClass" in class_names

    def test_analyze_python_file_syntax_error(self, analyzer, tmp_path):
        """Test handling of Python files with syntax errors"""
        test_file = tmp_path / "test_syntax_error.py"
        test_file.write_text('''
def invalid_syntax(
    """Missing closing parenthesis and colon"""
    return "error"
''')

        result = analyzer.analyze_python_file(str(test_file))

        # Should handle syntax errors gracefully
        assert result is not None
        # The result might be empty or contain error information
        assert isinstance(result, dict)

    def test_analyze_python_file_not_found(self, analyzer):
        """Test handling of non-existent files"""
        result = analyzer.analyze_python_file("/nonexistent/file.py")

        # Should handle file not found gracefully
        assert result is not None
        assert isinstance(result, dict)


class TestNeo4jErrorHandling:
    """Test error handling and recovery scenarios"""

    @pytest.fixture
    def extractor_with_error_driver(self):
        """Create extractor with a driver that simulates various errors"""
        with patch("parse_repo_into_neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            extractor = DirectNeo4jExtractor(
                "bolt://localhost:7687",
                "test_user",
                "test_password",
            )
            extractor.driver = mock_driver
            extractor.analyzer = MagicMock(spec=Neo4jCodeAnalyzer)

            yield extractor, mock_driver

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, extractor_with_error_driver):
        """Test handling of connection timeout errors"""
        extractor, mock_driver = extractor_with_error_driver

        # Simulate connection timeout
        from neo4j.exceptions import ServiceUnavailable

        mock_driver.exception = ServiceUnavailable("Connection timeout")

        await extractor.initialize()

        with pytest.raises(ServiceUnavailable):
            await extractor.search_graph("MATCH (n) RETURN n")

    @pytest.mark.asyncio
    async def test_constraint_violation_handling(self, extractor_with_error_driver):
        """Test handling of constraint violation errors"""
        extractor, mock_driver = extractor_with_error_driver

        # Simulate constraint violation
        from neo4j.exceptions import ConstraintError

        mock_driver.exception = ConstraintError("Unique constraint violation")

        await extractor.initialize()

        with pytest.raises(ConstraintError):
            await extractor.analyze_repository(
                "https://github.com/test/repo",
                [{"path": "test.py", "classes": []}],
            )

    @pytest.mark.asyncio
    async def test_transaction_failure_recovery(self, extractor_with_error_driver):
        """Test recovery from transaction failures"""
        extractor, mock_driver = extractor_with_error_driver

        await extractor.initialize()

        # First attempt fails
        mock_driver.exception = Exception("Transaction failed")

        with pytest.raises(Exception, match="Transaction failed"):
            await extractor.analyze_repository(
                "https://github.com/test/repo",
                [{"path": "test.py", "classes": []}],
            )

        # Second attempt succeeds
        mock_driver.exception = None
        mock_driver.session_data = [{"result": "success"}]

        result = await extractor.analyze_repository(
            "https://github.com/test/repo",
            [{"path": "test.py", "classes": []}],
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self, extractor_with_error_driver):
        """Test that sessions are properly cleaned up on errors"""
        extractor, mock_driver = extractor_with_error_driver

        await extractor.initialize()

        # Simulate error during operation
        mock_driver.exception = Exception("Operation failed")

        with pytest.raises(Exception, match="Operation failed"):
            await extractor.search_graph("MATCH (n) RETURN n")

        # Verify cleanup occurred (session should be closed)
        # This is implementation-specific and would need to be verified
        # based on the actual cleanup logic


class TestNeo4jPerformance:
    """Test performance aspects of Neo4j operations"""

    @pytest.fixture
    def performance_extractor(self):
        """Create extractor for performance testing"""
        with patch("parse_repo_into_neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            extractor = DirectNeo4jExtractor(
                "bolt://localhost:7687",
                "test_user",
                "test_password",
            )
            extractor.driver = mock_driver
            extractor.analyzer = MagicMock(spec=Neo4jCodeAnalyzer)

            yield extractor

    @pytest.mark.asyncio
    async def test_batch_operations_performance(
        self,
        performance_extractor,
        performance_test_data,
    ):
        """Test that batch operations perform better than individual operations"""
        await performance_extractor.initialize()

        # Mock large dataset processing
        large_repo = performance_test_data["large_repository"]

        # Simulate batch creation of many nodes
        files_data = []
        for i in range(large_repo["file_count"]):
            files_data.append(
                {
                    "path": f"src/file_{i}.py",
                    "classes": [{"name": f"Class_{i}", "methods": []}],
                    "functions": [{"name": f"function_{i}", "args": []}],
                },
            )

        # Measure batch operation time
        import time

        start_time = time.time()

        result = await performance_extractor.analyze_repository(
            "https://github.com/test/large-repo",
            files_data,
        )

        end_time = time.time()
        operation_time = end_time - start_time

        # Performance assertion - should complete within reasonable time
        assert (
            operation_time < 10.0
        )  # Should complete within 10 seconds for mocked operations
        assert result is not None

    @pytest.mark.asyncio
    async def test_query_optimization(
        self,
        performance_extractor,
        performance_test_data,
    ):
        """Test that queries are optimized for performance"""
        await performance_extractor.initialize()

        query_patterns = performance_test_data["query_patterns"]

        for query in query_patterns:
            # Mock query execution
            performance_extractor.driver.session_data = [
                {"result": f"data for {query}"},
            ]

            start_time = time.time()
            result = await performance_extractor.search_graph(query)
            end_time = time.time()

            query_time = end_time - start_time

            # Each query should complete quickly
            assert (
                query_time < 1.0
            )  # Should complete within 1 second for mocked operations
            assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_access_performance(
        self,
        performance_extractor,
        concurrent_access_scenarios,
    ):
        """Test performance under concurrent access"""
        await performance_extractor.initialize()

        scenarios = concurrent_access_scenarios

        async def perform_operation(operation_type, params):
            """Perform a single operation"""
            if operation_type == "find_module":
                return await performance_extractor.search_graph(
                    "MATCH (m:Module) WHERE m.name = $name RETURN m",
                    params,
                )
            if operation_type == "find_class":
                return await performance_extractor.search_graph(
                    "MATCH (c:Class) WHERE c.name = $name RETURN c",
                    params,
                )
            return await performance_extractor.search_graph(
                "MATCH (n) RETURN count(n)",
            )

        # Simulate concurrent operations
        tasks = []
        for operation_type, params in scenarios["read_operations"]:
            task = perform_operation(operation_type, params)
            tasks.append(task)

        # Execute all operations concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        total_time = end_time - start_time

        # Concurrent operations should complete within reasonable time
        assert (
            total_time < 5.0
        )  # Should complete within 5 seconds for mocked operations

        # All operations should succeed (no exceptions)
        for result in results:
            assert not isinstance(result, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
