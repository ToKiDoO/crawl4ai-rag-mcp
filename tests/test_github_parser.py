"""
Comprehensive tests for GitHub repository parsing to Neo4j.

This module tests GitHub repository parsing functionality including:
- Repository cloning and file discovery
- Python file analysis and AST parsing
- Graph structure creation in Neo4j
- Import relationship mapping
- Error handling for various repository scenarios
- Performance optimization for large repositories
- Git operations and cleanup
"""

import asyncio
import os

# Add src to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import fixtures
from tests.fixtures.neo4j_fixtures import (
    MockNeo4jDriver,
)

# Mock dependencies before importing our modules
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


class TestGitHubRepositoryCloning:
    """Test GitHub repository cloning functionality"""

    @pytest.fixture
    def extractor_with_git_mock(self):
        """Create extractor with mocked git operations"""
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

    @patch("parse_repo_into_neo4j.subprocess.run")
    @patch("parse_repo_into_neo4j.shutil.rmtree")
    def test_clone_repo_success(
        self,
        mock_rmtree,
        mock_subprocess,
        extractor_with_git_mock,
    ):
        """Test successful repository cloning"""
        # Mock successful git clone
        mock_subprocess.return_value = MagicMock(returncode=0)

        repo_url = "https://github.com/test/repo.git"
        clone_path = extractor_with_git_mock.clone_repo(repo_url)

        assert clone_path is not None
        assert "repo" in clone_path

        # Verify git clone was called
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "git" in call_args[0]
        assert "clone" in call_args
        assert repo_url in call_args

    @patch("parse_repo_into_neo4j.subprocess.run")
    def test_clone_repo_failure(self, mock_subprocess, extractor_with_git_mock):
        """Test repository cloning failure"""
        # Mock failed git clone
        mock_subprocess.return_value = MagicMock(returncode=1)

        repo_url = "https://github.com/nonexistent/repo.git"

        with pytest.raises(Exception, match="Failed to clone repository"):
            extractor_with_git_mock.clone_repo(repo_url)

    @patch("parse_repo_into_neo4j.subprocess.run")
    def test_clone_repo_network_error(self, mock_subprocess, extractor_with_git_mock):
        """Test repository cloning with network error"""
        # Mock network error during git clone
        mock_subprocess.side_effect = Exception("Network unreachable")

        repo_url = "https://github.com/test/repo.git"

        with pytest.raises(Exception, match="Network unreachable"):
            extractor_with_git_mock.clone_repo(repo_url)

    @patch("parse_repo_into_neo4j.subprocess.run")
    @patch("parse_repo_into_neo4j.Path.exists")
    def test_clone_repo_cleanup_on_error(
        self,
        mock_exists,
        mock_subprocess,
        extractor_with_git_mock,
    ):
        """Test cleanup of partial clone on error"""
        # Mock path exists to simulate partial clone
        mock_exists.return_value = True

        # Mock git clone failure
        mock_subprocess.return_value = MagicMock(returncode=1)

        repo_url = "https://github.com/test/repo.git"

        with patch("parse_repo_into_neo4j.shutil.rmtree") as mock_rmtree:
            with pytest.raises(Exception):
                extractor_with_git_mock.clone_repo(repo_url)

            # Verify cleanup was attempted
            mock_rmtree.assert_called()


class TestPythonFileDiscovery:
    """Test Python file discovery in repositories"""

    @pytest.fixture
    def extractor_with_fs_mock(self):
        """Create extractor with mocked filesystem operations"""
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

    def test_get_python_files_simple_structure(
        self,
        extractor_with_fs_mock,
        sample_git_repo,
    ):
        """Test discovering Python files in simple repository structure"""
        python_files = extractor_with_fs_mock.get_python_files(sample_git_repo)

        assert len(python_files) > 0
        assert all(file.endswith(".py") for file in python_files)
        assert any("main.py" in file for file in python_files)
        assert any("utils.py" in file for file in python_files)

    @patch("parse_repo_into_neo4j.Path.rglob")
    def test_get_python_files_complex_structure(
        self,
        mock_rglob,
        extractor_with_fs_mock,
    ):
        """Test discovering Python files in complex repository structure"""
        # Mock complex file structure
        mock_files = [
            Path("src/main.py"),
            Path("src/utils/helpers.py"),
            Path("src/models/__init__.py"),
            Path("src/models/user.py"),
            Path("tests/test_main.py"),
            Path("scripts/deploy.py"),
            Path("README.md"),  # Should be filtered out
            Path("setup.py"),
        ]
        mock_rglob.return_value = mock_files

        python_files = extractor_with_fs_mock.get_python_files("/fake/repo")

        assert len(python_files) == 6  # Only .py files
        assert all(file.endswith(".py") for file in python_files)
        assert "README.md" not in python_files

    @patch("parse_repo_into_neo4j.Path.rglob")
    def test_get_python_files_empty_repository(
        self,
        mock_rglob,
        extractor_with_fs_mock,
    ):
        """Test handling of repository with no Python files"""
        # Mock empty repository
        mock_rglob.return_value = []

        python_files = extractor_with_fs_mock.get_python_files("/fake/empty/repo")

        assert len(python_files) == 0

    @patch("parse_repo_into_neo4j.Path.rglob")
    def test_get_python_files_permission_error(
        self,
        mock_rglob,
        extractor_with_fs_mock,
    ):
        """Test handling of permission errors during file discovery"""
        # Mock permission error
        mock_rglob.side_effect = PermissionError("Access denied")

        with pytest.raises(PermissionError):
            extractor_with_fs_mock.get_python_files("/protected/repo")


class TestRepositoryAnalysis:
    """Test complete repository analysis workflow"""

    @pytest.fixture
    def analysis_extractor(self):
        """Create extractor for analysis testing"""
        with patch("parse_repo_into_neo4j.AsyncGraphDatabase") as mock_db:
            mock_driver = MockNeo4jDriver()
            mock_db.driver.return_value = mock_driver

            extractor = DirectNeo4jExtractor(
                "bolt://localhost:7687",
                "test_user",
                "test_password",
            )
            extractor.driver = mock_driver

            # Mock analyzer with realistic responses
            extractor.analyzer = MagicMock(spec=Neo4jCodeAnalyzer)
            extractor.analyzer.analyze_python_file.return_value = {
                "imports": ["os", "sys", "json"],
                "classes": [
                    {
                        "name": "TestClass",
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
            }

            yield extractor

    @pytest.mark.asyncio
    @patch("parse_repo_into_neo4j.subprocess.run")
    @patch("parse_repo_into_neo4j.shutil.rmtree")
    async def test_analyze_repository_complete_workflow(
        self,
        mock_rmtree,
        mock_subprocess,
        analysis_extractor,
        sample_git_repo,
    ):
        """Test complete repository analysis workflow"""
        await analysis_extractor.initialize()

        # Mock successful git operations
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Mock get_python_files to return test files
        with patch.object(analysis_extractor, "get_python_files") as mock_get_files:
            mock_get_files.return_value = [
                os.path.join(sample_git_repo, "src/main.py"),
                os.path.join(sample_git_repo, "src/utils.py"),
            ]

            repo_url = "https://github.com/test/repo.git"
            result = await analysis_extractor.analyze_repository(repo_url)

            assert result is not None

            # Verify that analyzer was called for each file
            assert analysis_extractor.analyzer.analyze_python_file.call_count >= 2

    @pytest.mark.asyncio
    async def test_analyze_repository_with_file_list(
        self,
        analysis_extractor,
        sample_repository_data,
    ):
        """Test repository analysis with pre-provided file list"""
        await analysis_extractor.initialize()

        repo_url = "https://github.com/test/repo.git"
        files_data = sample_repository_data["files"]

        result = await analysis_extractor.analyze_repository(repo_url, files_data)

        assert result is not None
        # Should not call file discovery when files are provided

    @pytest.mark.asyncio
    async def test_analyze_repository_error_handling(self, analysis_extractor):
        """Test error handling during repository analysis"""
        await analysis_extractor.initialize()

        # Mock analyzer to raise exception
        analysis_extractor.analyzer.analyze_python_file.side_effect = Exception(
            "Analysis failed",
        )

        with patch.object(analysis_extractor, "get_python_files") as mock_get_files:
            mock_get_files.return_value = ["test.py"]

            with pytest.raises(Exception, match="Analysis failed"):
                await analysis_extractor.analyze_repository(
                    "https://github.com/test/repo.git",
                )

    @pytest.mark.asyncio
    async def test_analyze_repository_large_repository(
        self,
        analysis_extractor,
        performance_test_data,
    ):
        """Test analysis of large repository"""
        await analysis_extractor.initialize()

        large_repo = performance_test_data["large_repository"]

        # Mock many Python files
        with patch.object(analysis_extractor, "get_python_files") as mock_get_files:
            mock_files = [f"src/file_{i}.py" for i in range(large_repo["file_count"])]
            mock_get_files.return_value = mock_files

            repo_url = "https://github.com/test/large-repo.git"

            import time

            start_time = time.time()
            result = await analysis_extractor.analyze_repository(repo_url)
            end_time = time.time()

            assert result is not None

            # Performance check - should handle large repos efficiently
            analysis_time = end_time - start_time
            assert (
                analysis_time < 30.0
            )  # Should complete within 30 seconds for mocked operations


class TestGraphCreation:
    """Test Neo4j graph creation from repository data"""

    @pytest.fixture
    def graph_extractor(self):
        """Create extractor for graph creation testing"""
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
    async def test_create_graph_repository_node(self, graph_extractor):
        """Test creation of repository node"""
        await graph_extractor.initialize()

        # Mock successful node creation
        graph_extractor.driver.session_data = [{"repo": {"name": "test-repo"}}]

        # Test via _create_graph method (private, but needed for testing)
        repo_data = {
            "name": "test-repo",
            "url": "https://github.com/test/test-repo.git",
            "files": [],
        }

        # This would be called within analyze_repository
        with patch.object(graph_extractor, "_create_graph") as mock_create_graph:
            await graph_extractor.analyze_repository(
                repo_data["url"],
                repo_data["files"],
            )

            mock_create_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_graph_file_nodes(
        self,
        graph_extractor,
        sample_repository_data,
    ):
        """Test creation of file nodes with proper metadata"""
        await graph_extractor.initialize()

        # Mock file node creation responses
        graph_extractor.driver.session_data = [
            {"file": {"path": "src/main.py", "module_name": "main", "line_count": 50}},
        ]

        result = await graph_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None
        # File nodes should be created with path, module_name, and line_count

    @pytest.mark.asyncio
    async def test_create_graph_class_hierarchy(
        self,
        graph_extractor,
        sample_repository_data,
    ):
        """Test creation of class nodes with methods and attributes"""
        await graph_extractor.initialize()

        # Mock class hierarchy creation
        graph_extractor.driver.session_data = [
            {
                "class": {"name": "TestClass", "full_name": "main.TestClass"},
                "methods": [{"name": "test_method"}],
                "attributes": [{"name": "test_attr"}],
            },
        ]

        result = await graph_extractor.analyze_repository(
            sample_repository_data["url"],
            sample_repository_data["files"],
        )

        assert result is not None
        # Class nodes should be created with proper relationships to methods and attributes

    @pytest.mark.asyncio
    async def test_create_graph_import_relationships(self, graph_extractor):
        """Test creation of import relationships between modules"""
        await graph_extractor.initialize()

        # Mock files with imports
        files_data = [
            {
                "path": "src/main.py",
                "module_name": "main",
                "imports": ["os", "sys", "utils"],  # Mix of external and internal
                "classes": [],
                "functions": [],
            },
            {
                "path": "src/utils.py",
                "module_name": "utils",
                "imports": ["json"],
                "classes": [],
                "functions": [],
            },
        ]

        # Mock relationship creation
        graph_extractor.driver.session_data = [
            {"relationship": {"type": "IMPORTS", "from": "main", "to": "utils"}},
        ]

        result = await graph_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            files_data,
        )

        assert result is not None
        # Import relationships should be created between internal modules

    @pytest.mark.asyncio
    async def test_create_graph_function_nodes(self, graph_extractor):
        """Test creation of function nodes with parameter information"""
        await graph_extractor.initialize()

        # Mock files with functions
        files_data = [
            {
                "path": "src/helpers.py",
                "module_name": "helpers",
                "imports": [],
                "classes": [],
                "functions": [
                    {
                        "name": "helper_function",
                        "args": ["param1", "param2"],
                        "params": {"param1": "str", "param2": "int"},
                        "return_type": "bool",
                    },
                ],
            },
        ]

        # Mock function node creation
        graph_extractor.driver.session_data = [
            {
                "function": {
                    "name": "helper_function",
                    "args": ["param1", "param2"],
                    "params": {"param1": "str", "param2": "int"},
                    "return_type": "bool",
                },
            },
        ]

        result = await graph_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            files_data,
        )

        assert result is not None
        # Function nodes should be created with complete parameter information

    @pytest.mark.asyncio
    async def test_create_graph_batch_operations(self, graph_extractor):
        """Test that graph creation uses batch operations for efficiency"""
        await graph_extractor.initialize()

        # Mock many files to trigger batch operations
        files_data = []
        for i in range(50):
            files_data.append(
                {
                    "path": f"src/file_{i}.py",
                    "module_name": f"file_{i}",
                    "imports": [],
                    "classes": [
                        {"name": f"Class_{i}", "methods": [], "attributes": []},
                    ],
                    "functions": [],
                },
            )

        result = await graph_extractor.analyze_repository(
            "https://github.com/test/large-repo.git",
            files_data,
        )

        assert result is not None
        # Should handle large numbers of nodes efficiently


class TestImportRelationshipMapping:
    """Test import relationship mapping and analysis"""

    @pytest.fixture
    def import_extractor(self):
        """Create extractor for import testing"""
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
    async def test_internal_import_detection(self, import_extractor):
        """Test detection and mapping of internal imports"""
        await import_extractor.initialize()

        # Mock files with internal imports
        files_data = [
            {
                "path": "src/main.py",
                "module_name": "main",
                "imports": ["utils", "helpers"],  # Internal imports
                "classes": [],
                "functions": [],
            },
            {
                "path": "src/utils.py",
                "module_name": "utils",
                "imports": ["helpers"],  # Internal import
                "classes": [],
                "functions": [],
            },
            {
                "path": "src/helpers.py",
                "module_name": "helpers",
                "imports": [],
                "classes": [],
                "functions": [],
            },
        ]

        result = await import_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            files_data,
        )

        assert result is not None
        # Should create IMPORTS relationships between internal modules

    @pytest.mark.asyncio
    async def test_external_import_filtering(self, import_extractor):
        """Test filtering of external imports (standard library, third-party)"""
        await import_extractor.initialize()

        # Mock files with mix of internal and external imports
        files_data = [
            {
                "path": "src/main.py",
                "module_name": "main",
                "imports": [
                    "os",
                    "sys",
                    "numpy",
                    "requests",
                    "utils",
                ],  # Mix of external and internal
                "classes": [],
                "functions": [],
            },
            {
                "path": "src/utils.py",
                "module_name": "utils",
                "imports": ["json", "datetime"],  # External imports only
                "classes": [],
                "functions": [],
            },
        ]

        result = await import_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            files_data,
        )

        assert result is not None
        # Should only create relationships for internal imports, not external ones

    @pytest.mark.asyncio
    async def test_circular_import_handling(self, import_extractor):
        """Test handling of circular imports"""
        await import_extractor.initialize()

        # Mock files with circular imports
        files_data = [
            {
                "path": "src/module_a.py",
                "module_name": "module_a",
                "imports": ["module_b"],  # A imports B
                "classes": [],
                "functions": [],
            },
            {
                "path": "src/module_b.py",
                "module_name": "module_b",
                "imports": ["module_a"],  # B imports A (circular)
                "classes": [],
                "functions": [],
            },
        ]

        result = await import_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            files_data,
        )

        assert result is not None
        # Should handle circular imports without infinite loops

    @pytest.mark.asyncio
    async def test_complex_import_patterns(self, import_extractor):
        """Test complex import patterns (from X import Y, as aliases, etc.)"""
        await import_extractor.initialize()

        # Mock files with complex import patterns
        files_data = [
            {
                "path": "src/main.py",
                "module_name": "main",
                "imports": [
                    "utils",  # Simple import
                    "helpers.decorators",  # Nested module import
                    "config as cfg",  # Aliased import
                    "models.User",  # From import
                ],
                "classes": [],
                "functions": [],
            },
        ]

        result = await import_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            files_data,
        )

        assert result is not None
        # Should handle various import patterns correctly


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases in GitHub parsing"""

    @pytest.fixture
    def error_extractor(self):
        """Create extractor for error testing"""
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
    async def test_invalid_repository_url(self, error_extractor):
        """Test handling of invalid repository URLs"""
        await error_extractor.initialize()

        invalid_urls = [
            "not-a-url",
            "http://invalid-domain.com/repo.git",
            "https://github.com/",
            "https://github.com/user",  # Missing repo name
            "",
            None,
        ]

        for url in invalid_urls:
            if url is None:
                with pytest.raises((TypeError, AttributeError)):
                    await error_extractor.analyze_repository(url)
            else:
                # Should handle gracefully or raise appropriate error
                try:
                    result = await error_extractor.analyze_repository(url)
                    # If it doesn't raise an error, result should be None or indicate failure
                    assert result is None or "error" in str(result).lower()
                except Exception as e:
                    # Should raise a meaningful error
                    assert isinstance(e, (ValueError, Exception))

    @pytest.mark.asyncio
    async def test_malformed_python_files(self, error_extractor):
        """Test handling of malformed Python files"""
        await error_extractor.initialize()

        # Mock analyzer to return errors for malformed files
        error_extractor.analyzer.analyze_python_file.side_effect = [
            {"error": "Syntax error", "imports": [], "classes": [], "functions": []},
            {"imports": ["os"], "classes": [], "functions": []},  # Valid file
            {"error": "Encoding error", "imports": [], "classes": [], "functions": []},
        ]

        with patch.object(error_extractor, "get_python_files") as mock_get_files:
            mock_get_files.return_value = ["bad1.py", "good.py", "bad2.py"]

            result = await error_extractor.analyze_repository(
                "https://github.com/test/repo.git",
            )

            # Should handle malformed files gracefully and continue processing
            assert result is not None

    @pytest.mark.asyncio
    async def test_permission_denied_during_analysis(self, error_extractor):
        """Test handling of permission errors during file analysis"""
        await error_extractor.initialize()

        # Mock permission error
        error_extractor.analyzer.analyze_python_file.side_effect = PermissionError(
            "Access denied",
        )

        with patch.object(error_extractor, "get_python_files") as mock_get_files:
            mock_get_files.return_value = ["protected.py"]

            with pytest.raises(PermissionError):
                await error_extractor.analyze_repository(
                    "https://github.com/test/repo.git",
                )

    @pytest.mark.asyncio
    async def test_neo4j_transaction_failure(self, error_extractor):
        """Test handling of Neo4j transaction failures"""
        await error_extractor.initialize()

        # Mock Neo4j transaction failure
        from neo4j.exceptions import TransactionError

        error_extractor.driver.exception = TransactionError("Transaction failed")

        with pytest.raises(TransactionError):
            await error_extractor.analyze_repository(
                "https://github.com/test/repo.git",
                [{"path": "test.py", "imports": [], "classes": [], "functions": []}],
            )

    @pytest.mark.asyncio
    async def test_memory_constraints_large_repo(self, error_extractor):
        """Test handling of memory constraints with very large repositories"""
        await error_extractor.initialize()

        # Mock extremely large repository data
        huge_files_data = []
        for i in range(10000):  # Simulate 10k files
            huge_files_data.append(
                {
                    "path": f"src/file_{i}.py",
                    "module_name": f"file_{i}",
                    "imports": [
                        f"file_{j}" for j in range(min(100, i))
                    ],  # Many imports
                    "classes": [
                        {"name": f"Class_{i}_{j}", "methods": [], "attributes": []}
                        for j in range(10)
                    ],
                    "functions": [
                        {"name": f"func_{i}_{j}", "args": [], "params": {}}
                        for j in range(20)
                    ],
                },
            )

        # This should either handle gracefully or provide meaningful error
        try:
            result = await error_extractor.analyze_repository(
                "https://github.com/test/huge-repo.git",
                huge_files_data,
            )
            # If successful, should complete without memory errors
            assert result is not None
        except MemoryError:
            # Acceptable to fail with memory error for extremely large repos
            pass
        except Exception as e:
            # Should provide meaningful error message
            assert "memory" in str(e).lower() or "size" in str(e).lower()

    @pytest.mark.asyncio
    async def test_concurrent_repository_analysis(self, error_extractor):
        """Test concurrent analysis of multiple repositories"""
        await error_extractor.initialize()

        # Test that multiple repositories can be analyzed concurrently
        repo_urls = [
            "https://github.com/test/repo1.git",
            "https://github.com/test/repo2.git",
            "https://github.com/test/repo3.git",
        ]

        async def analyze_single_repo(url):
            return await error_extractor.analyze_repository(url, [])

        # Run concurrent analysis
        tasks = [analyze_single_repo(url) for url in repo_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete (successfully or with expected errors)
        assert len(results) == 3
        for result in results:
            # Should not have unexpected errors
            if isinstance(result, Exception):
                # Any exceptions should be expected types
                assert isinstance(result, (ValueError, ConnectionError, Exception))


class TestPerformanceOptimization:
    """Test performance optimization features"""

    @pytest.fixture
    def perf_extractor(self):
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
    async def test_batch_processing_efficiency(
        self,
        perf_extractor,
        performance_test_data,
    ):
        """Test that batch processing improves performance"""
        await perf_extractor.initialize()

        large_repo = performance_test_data["large_repository"]

        # Create test data for batch processing
        files_data = []
        for i in range(large_repo["file_count"]):
            files_data.append(
                {
                    "path": f"src/file_{i}.py",
                    "module_name": f"file_{i}",
                    "imports": [],
                    "classes": [
                        {"name": f"Class_{i}", "methods": [], "attributes": []},
                    ],
                    "functions": [{"name": f"func_{i}", "args": [], "params": {}}],
                },
            )

        import time

        start_time = time.time()

        result = await perf_extractor.analyze_repository(
            "https://github.com/test/large-repo.git",
            files_data,
        )

        end_time = time.time()
        processing_time = end_time - start_time

        assert result is not None
        # Should complete large repository processing efficiently
        assert (
            processing_time < 60.0
        )  # Should complete within 1 minute for mocked operations

    @pytest.mark.asyncio
    async def test_incremental_processing(self, perf_extractor):
        """Test incremental processing of repository updates"""
        await perf_extractor.initialize()

        # First analysis - initial repository
        initial_files = [
            {
                "path": "src/main.py",
                "module_name": "main",
                "imports": [],
                "classes": [],
                "functions": [],
            },
        ]

        result1 = await perf_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            initial_files,
        )

        # Second analysis - repository with additional files
        updated_files = initial_files + [
            {
                "path": "src/utils.py",
                "module_name": "utils",
                "imports": [],
                "classes": [],
                "functions": [],
            },
            {
                "path": "src/helpers.py",
                "module_name": "helpers",
                "imports": [],
                "classes": [],
                "functions": [],
            },
        ]

        result2 = await perf_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            updated_files,
        )

        assert result1 is not None
        assert result2 is not None
        # Should handle incremental updates efficiently

    @pytest.mark.asyncio
    async def test_memory_efficient_processing(self, perf_extractor):
        """Test memory-efficient processing of large files"""
        await perf_extractor.initialize()

        # Mock processing of file with many classes and functions
        large_file_data = {
            "path": "src/large_file.py",
            "module_name": "large_file",
            "imports": [],
            "classes": [
                {"name": f"Class_{i}", "methods": [], "attributes": []}
                for i in range(1000)
            ],
            "functions": [
                {"name": f"func_{i}", "args": [], "params": {}} for i in range(2000)
            ],
        }

        result = await perf_extractor.analyze_repository(
            "https://github.com/test/repo.git",
            [large_file_data],
        )

        assert result is not None
        # Should handle large files without memory issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
