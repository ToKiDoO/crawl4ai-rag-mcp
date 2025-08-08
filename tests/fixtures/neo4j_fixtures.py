"""
Neo4j test fixtures for testing knowledge graph functionality.

This module provides reusable fixtures, mock data, and utilities for testing
Neo4j integration including graph operations, knowledge graph validation,
and GitHub repository parsing.
"""

import os
from unittest.mock import MagicMock

import pytest


# Mock Neo4j driver and session classes for testing
class MockNeo4jSession:
    """Mock Neo4j session for testing"""

    def __init__(self):
        self.results = []
        self.exception = None
        self.closed = False

    def run(self, query: str, parameters: dict | None = None):
        """Mock run method that returns predefined results"""
        if self.exception:
            raise self.exception

        # Return mock result based on query type
        result = MockNeo4jResult(self.results)
        return result

    async def run_async(self, query: str, parameters: dict | None = None):
        """Async version of run method"""
        return self.run(query, parameters)

    def close(self):
        """Mock close method"""
        self.closed = True

    async def close_async(self):
        """Async version of close method"""
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class MockNeo4jResult:
    """Mock Neo4j result for testing"""

    def __init__(self, records: list[dict] = None):
        self.records = records or []
        self._consumed = False

    def data(self):
        """Return result data"""
        return self.records

    def single(self):
        """Return single record"""
        if not self.records:
            return None
        return MockNeo4jRecord(self.records[0])

    def consume(self):
        """Mock consume method"""
        self._consumed = True
        return MagicMock(
            counters=MagicMock(
                nodes_created=0,
                relationships_created=0,
                properties_set=0,
            ),
        )


class MockNeo4jRecord:
    """Mock Neo4j record for testing"""

    def __init__(self, data: dict):
        self._data = data

    def __getitem__(self, key):
        return self._data.get(key)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def data(self):
        return self._data


class MockNeo4jDriver:
    """Mock Neo4j driver for testing"""

    def __init__(self):
        self.session_data = []
        self.exception = None
        self.closed = False

    def session(self, **kwargs):
        """Create mock session"""
        session = MockNeo4jSession()
        session.results = self.session_data
        session.exception = self.exception
        return session

    async def session_async(self, **kwargs):
        """Async version of session method"""
        return self.session(**kwargs)

    def close(self):
        """Mock close method"""
        self.closed = True

    async def close_async(self):
        """Async version of close method"""
        self.close()

    def verify_connectivity(self):
        """Mock connectivity verification"""
        if self.exception:
            raise self.exception
        return True


@pytest.fixture
def mock_neo4j_driver():
    """Fixture providing a mock Neo4j driver"""
    return MockNeo4jDriver()


@pytest.fixture
def sample_repository_data():
    """Sample repository data for testing"""
    return {
        "name": "test-repo",
        "url": "https://github.com/test/test-repo",
        "files": [
            {
                "path": "src/main.py",
                "module_name": "main",
                "line_count": 50,
                "classes": [
                    {
                        "name": "TestClass",
                        "full_name": "main.TestClass",
                        "methods": [
                            {
                                "name": "test_method",
                                "args": ["self", "param1"],
                                "params": {"param1": "str"},
                                "return_type": "bool",
                            },
                        ],
                        "attributes": [{"name": "test_attr", "type": "str"}],
                    },
                ],
                "functions": [
                    {
                        "name": "test_function",
                        "args": ["param1", "param2"],
                        "params": {"param1": "str", "param2": "int"},
                        "return_type": "str",
                    },
                ],
                "imports": ["os", "sys", "json"],
            },
        ],
    }


@pytest.fixture
def sample_python_script():
    """Sample Python script content for testing validation"""
    return '''
import os
import sys
from main import TestClass

def example_function():
    """Example function for testing"""
    test_obj = TestClass()
    result = test_obj.test_method("hello")
    value = test_obj.test_attr
    return result

if __name__ == "__main__":
    print(example_function())
'''


@pytest.fixture
def sample_script_file(tmp_path):
    """Create a temporary Python script file for testing"""
    script_content = '''
import os
import sys
from main import TestClass

def example_function():
    """Example function for testing"""
    test_obj = TestClass()
    result = test_obj.test_method("hello")
    value = test_obj.test_attr
    return result

if __name__ == "__main__":
    print(example_function())
'''

    script_file = tmp_path / "test_script.py"
    script_file.write_text(script_content)
    return str(script_file)


@pytest.fixture
def sample_git_repo(tmp_path):
    """Create a temporary git repository for testing"""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create some Python files
    src_dir = repo_dir / "src"
    src_dir.mkdir()

    main_py = src_dir / "main.py"
    main_py.write_text('''
class TestClass:
    def __init__(self):
        self.test_attr = "test_value"
    
    def test_method(self, param1: str) -> bool:
        """Test method"""
        return len(param1) > 0

def test_function(param1: str, param2: int) -> str:
    """Test function"""
    return f"{param1}_{param2}"
''')

    utils_py = src_dir / "utils.py"
    utils_py.write_text('''
import os
import sys

def helper_function():
    """Helper function"""
    pass
''')

    return str(repo_dir)


@pytest.fixture
def validation_test_cases():
    """Test cases for validation scenarios"""
    return {
        "valid_cases": [
            {
                "description": "Valid import from known module",
                "import_statement": "from main import TestClass",
                "expected_status": "VALID",
                "expected_confidence": 1.0,
            },
            {
                "description": "Valid method call on known class",
                "code": "test_obj.test_method('hello')",
                "expected_status": "VALID",
                "expected_confidence": 0.9,
            },
        ],
        "invalid_cases": [
            {
                "description": "Import from non-existent module",
                "import_statement": "from nonexistent import FakeClass",
                "expected_status": "INVALID",
                "expected_confidence": 0.0,
            },
            {
                "description": "Method call on non-existent method",
                "code": "test_obj.fake_method()",
                "expected_status": "INVALID",
                "expected_confidence": 0.0,
            },
        ],
        "uncertain_cases": [
            {
                "description": "Method with uncertain parameters",
                "code": "test_obj.test_method(123)",  # Wrong parameter type
                "expected_status": "UNCERTAIN",
                "expected_confidence": 0.5,
            },
        ],
    }


@pytest.fixture
def neo4j_query_responses():
    """Mock Neo4j query responses for different query types"""
    return {
        "find_module": [{"m": {"name": "main", "path": "src/main.py"}}],
        "find_class": [{"c": {"name": "TestClass", "full_name": "main.TestClass"}}],
        "find_method": [
            {
                "m": {
                    "name": "test_method",
                    "args": ["self", "param1"],
                    "params": {"param1": "str"},
                    "return_type": "bool",
                },
            },
        ],
        "find_function": [
            {
                "f": {
                    "name": "test_function",
                    "args": ["param1", "param2"],
                    "params": {"param1": "str", "param2": "int"},
                    "return_type": "str",
                },
            },
        ],
        "find_attribute": [{"a": {"name": "test_attr", "type": "str"}}],
        "empty_result": [],
        "repository_count": [{"count": 1}],
        "clear_repository": [{"nodes_deleted": 10, "relationships_deleted": 5}],
    }


@pytest.fixture
def knowledge_graph_environment():
    """Set up environment variables for knowledge graph testing"""
    original_env = {}
    test_env = {
        "USE_KNOWLEDGE_GRAPH": "true",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "test_user",
        "NEO4J_PASSWORD": "test_password",
    }

    # Store original values
    for key in test_env:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env[key]

    yield test_env

    # Restore original values
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing"""
    return {
        "large_repository": {
            "name": "large-test-repo",
            "file_count": 100,
            "class_count": 50,
            "method_count": 200,
            "function_count": 150,
        },
        "query_patterns": [
            "MATCH (n) RETURN count(n)",
            "MATCH (c:Class) RETURN c.name LIMIT 10",
            "MATCH (m:Method)-[:BELONGS_TO]->(c:Class) RETURN m.name, c.name LIMIT 20",
            "MATCH (f:File)-[:IMPORTS]->(m:Module) RETURN f.path, m.name LIMIT 15",
        ],
    }


@pytest.fixture
def concurrent_access_scenarios():
    """Scenarios for testing concurrent access to Neo4j"""
    return {
        "read_operations": [
            ("find_module", {"module_name": "main"}),
            ("find_class", {"class_name": "TestClass"}),
            ("find_method", {"method_name": "test_method"}),
        ],
        "write_operations": [
            ("create_node", {"label": "TestNode", "properties": {"name": "test"}}),
            (
                "create_relationship",
                {"from_node": "node1", "to_node": "node2", "type": "TEST"},
            ),
        ],
        "concurrent_sessions": 5,
        "operations_per_session": 10,
    }


class Neo4jTestHelper:
    """Helper class for Neo4j testing utilities"""

    @staticmethod
    def create_mock_driver_with_responses(responses: dict[str, list[dict]]):
        """Create a mock driver that returns specific responses for different query patterns"""
        driver = MockNeo4jDriver()

        def get_response_for_query(query: str):
            """Map query patterns to responses"""
            if "MATCH (m:Module)" in query:
                return responses.get("find_module", [])
            if "MATCH (c:Class)" in query:
                return responses.get("find_class", [])
            if "MATCH (method:Method)" in query:
                return responses.get("find_method", [])
            if "MATCH (f:Function)" in query:
                return responses.get("find_function", [])
            if "MATCH (a:Attribute)" in query:
                return responses.get("find_attribute", [])
            if "DELETE" in query:
                return responses.get("clear_repository", [])
            if "count(" in query.lower():
                return responses.get("repository_count", [])
            return responses.get("empty_result", [])

        # Override session creation to return query-specific responses
        original_session = driver.session

        def mock_session(**kwargs):
            session = original_session(**kwargs)
            original_run = session.run

            def mock_run(query: str, parameters: dict | None = None):
                session.results = get_response_for_query(query)
                return original_run(query, parameters)

            session.run = mock_run
            return session

        driver.session = mock_session
        return driver

    @staticmethod
    def assert_query_contains(query: str, expected_patterns: list[str]):
        """Assert that a query contains expected patterns"""
        for pattern in expected_patterns:
            assert pattern in query, f"Query should contain '{pattern}': {query}"

    @staticmethod
    def create_test_ast_nodes():
        """Create test AST nodes for script analysis"""
        import ast

        # Create a simple AST for testing
        code = """
from main import TestClass
test_obj = TestClass()
result = test_obj.test_method("hello")
"""
        return ast.parse(code)


@pytest.fixture
def neo4j_test_helper():
    """Fixture providing Neo4j test helper utilities"""
    return Neo4jTestHelper()
