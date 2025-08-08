"""
Comprehensive tests for Neo4j cleanup functionality.

Tests the Neo4j cleanup fix that was implemented to resolve HAS_COMMIT relationship warnings.
This module focuses specifically on the `clear_repository_data` method and its transactional behavior.

Key areas tested:
1. Basic repository cleanup functionality
2. Transaction management and rollback
3. Branch and commit relationship cleanup
4. Edge cases and error handling
5. Integration with repository parsing
"""

import os
import sys
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
    from parse_repo_into_neo4j import DirectNeo4jExtractor


class MockNeo4jTransaction:
    """Mock Neo4j transaction for testing transaction behavior"""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.operations = []

    async def run(self, query, **kwargs):
        """Mock transaction run method"""
        self.operations.append({"query": query, "params": kwargs})

        # Create mock result based on query type
        if "deleted_count" in query:
            return MockResult([{"deleted_count": 1}])
        return MockResult([])

    async def commit(self):
        """Mock transaction commit"""
        self.committed = True

    async def rollback(self):
        """Mock transaction rollback"""
        self.rolled_back = True


class MockSession:
    """Mock Neo4j session for testing"""

    def __init__(self):
        self.current_transaction = None
        self.operations = []

    async def run(self, query, **kwargs):
        """Mock session run method (for non-transactional operations)"""
        self.operations.append({"query": query, "params": kwargs})

        if "repo_count" in query:
            # Mock repository existence check
            return MockResult([{"repo_count": 1}])
        return MockResult([])

    @asynccontextmanager
    async def begin_transaction(self):
        """Mock transaction context manager"""
        self.current_transaction = MockNeo4jTransaction()
        try:
            yield self.current_transaction
        except Exception:
            await self.current_transaction.rollback()
            raise


class MockResult:
    """Mock Neo4j result"""

    def __init__(self, records):
        self.records = records

    async def single(self):
        """Return single record"""
        return self.records[0] if self.records else None


class MockDriver:
    """Mock Neo4j driver"""

    def __init__(self):
        self.sessions = []

    @asynccontextmanager
    async def session(self):
        """Mock session context manager"""
        session = MockSession()
        self.sessions.append(session)
        yield session


class TestNeo4jCleanupFunctionality:
    """Test the Neo4j cleanup fix implementation"""

    @pytest.fixture
    def mock_extractor(self):
        """Create a DirectNeo4jExtractor with mocked Neo4j driver"""
        extractor = DirectNeo4jExtractor(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test_user",
            neo4j_password="test_password",
        )
        extractor.driver = MockDriver()
        return extractor

    async def test_successful_repository_cleanup(self, mock_extractor):
        """Test successful cleanup of a repository with all node types"""
        repo_name = "test-repo"

        await mock_extractor.clear_repository_data(repo_name)

        # Verify driver was used
        assert (
            len(mock_extractor.driver.sessions) == 2
        )  # One for validation, one for cleanup

        cleanup_session = mock_extractor.driver.sessions[1]
        assert cleanup_session.current_transaction is not None
        assert cleanup_session.current_transaction.committed
        assert not cleanup_session.current_transaction.rolled_back

        # Verify all cleanup operations were performed (including final repository deletion)
        operations = cleanup_session.current_transaction.operations
        assert len(operations) == 8  # 7 deletion steps + repository

        # Check deletion order (methods, attributes, functions, classes, files, branches, commits, repo)
        expected_patterns = [
            "HAS_METHOD",  # Methods deletion
            "HAS_ATTRIBUTE",  # Attributes deletion
            "DEFINES]->(func:Function)",  # Functions deletion
            "DEFINES]->(c:Class)",  # Classes deletion
            "CONTAINS]->(f:File)",  # Files deletion
            "HAS_BRANCH",  # Branches deletion (new)
            "HAS_COMMIT",  # Commits deletion (new)
            "MATCH (r:Repository",  # Repository deletion
        ]

        for i, pattern in enumerate(expected_patterns):
            operation_query = operations[i]["query"]
            assert pattern in operation_query, (
                f"Expected pattern '{pattern}' not found in query: {operation_query}"
            )

    @pytest.mark.asyncio
    async def test_repository_not_found_graceful_handling(self, mock_extractor):
        """Test graceful handling when repository doesn't exist"""
        repo_name = "nonexistent-repo"

        # Mock the repository existence check to return 0
        validation_session = MockSession()
        validation_session.run = AsyncMock(return_value=MockResult([{"repo_count": 0}]))

        with patch.object(mock_extractor.driver, "session") as mock_session_context:
            mock_session_context.return_value.__aenter__ = AsyncMock(
                return_value=validation_session
            )
            mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

            await mock_extractor.clear_repository_data(repo_name)

            # Verify validation was called but no cleanup operations occurred
            validation_session.run.assert_called_once()
            query_args = validation_session.run.call_args[0]
            assert "count(r) as repo_count" in query_args[0]

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_failure(self, mock_extractor):
        """Test transaction rollback when cleanup operations fail"""
        repo_name = "test-repo"

        # Create a session that fails during transaction
        failing_session = MockSession()

        # Mock transaction that fails on commit
        class FailingTransaction(MockNeo4jTransaction):
            async def run(self, query, **kwargs):
                if "HAS_COMMIT" in query:  # Fail on commit deletion
                    raise Exception("Simulated Neo4j failure")
                return await super().run(query, **kwargs)

        @asynccontextmanager
        async def failing_transaction_context():
            transaction = FailingTransaction()
            failing_session.current_transaction = transaction
            try:
                yield transaction
            except Exception:
                await transaction.rollback()
                raise

        failing_session.begin_transaction = failing_transaction_context

        # Mock driver to return failing session for cleanup (second session)
        sessions = [MockSession(), failing_session]  # Validation, then failing cleanup

        with patch.object(mock_extractor.driver, "session") as mock_session_context:
            mock_session_context.return_value.__aenter__ = AsyncMock(
                side_effect=[s for s in sessions]
            )
            mock_session_context.return_value.__aexit__ = AsyncMock(return_value=None)

            # Expect the cleanup to fail and raise an exception
            with pytest.raises(
                Exception, match="Repository cleanup failed and was rolled back"
            ):
                await mock_extractor.clear_repository_data(repo_name)

            # Verify transaction was rolled back
            assert failing_session.current_transaction.rolled_back
            assert not failing_session.current_transaction.committed

    @pytest.mark.asyncio
    async def test_has_branch_relationship_cleanup(self, mock_extractor):
        """Test that HAS_BRANCH relationships are properly cleaned up"""
        repo_name = "test-repo-with-branches"

        await mock_extractor.clear_repository_data(repo_name)

        cleanup_session = mock_extractor.driver.sessions[1]
        operations = cleanup_session.current_transaction.operations

        # Find the branches cleanup operation
        branch_op = None
        for op in operations:
            if "HAS_BRANCH" in op["query"]:
                branch_op = op
                break

        assert branch_op is not None, "HAS_BRANCH cleanup operation not found"
        assert "OPTIONAL MATCH (r)-[:HAS_BRANCH]->(b:Branch)" in branch_op["query"]
        assert "DETACH DELETE branch" in branch_op["query"]
        assert op["params"]["repo_name"] == repo_name

    @pytest.mark.asyncio
    async def test_has_commit_relationship_cleanup(self, mock_extractor):
        """Test that HAS_COMMIT relationships are properly cleaned up"""
        repo_name = "test-repo-with-commits"

        await mock_extractor.clear_repository_data(repo_name)

        cleanup_session = mock_extractor.driver.sessions[1]
        operations = cleanup_session.current_transaction.operations

        # Find the commits cleanup operation
        commit_op = None
        for op in operations:
            if "HAS_COMMIT" in op["query"]:
                commit_op = op
                break

        assert commit_op is not None, "HAS_COMMIT cleanup operation not found"
        assert "OPTIONAL MATCH (r)-[:HAS_COMMIT]->(c:Commit)" in commit_op["query"]
        assert "DETACH DELETE commit" in commit_op["query"]
        assert op["params"]["repo_name"] == repo_name

    @pytest.mark.asyncio
    async def test_cleanup_operation_order(self, mock_extractor):
        """Test that cleanup operations follow correct dependency order"""
        repo_name = "test-repo"

        await mock_extractor.clear_repository_data(repo_name)

        cleanup_session = mock_extractor.driver.sessions[1]
        operations = cleanup_session.current_transaction.operations

        # Extract operation types in order
        operation_types = []
        for op in operations:
            query = op["query"]
            if "HAS_METHOD" in query:
                operation_types.append("methods")
            elif "HAS_ATTRIBUTE" in query:
                operation_types.append("attributes")
            elif "DEFINES.*Function" in query or "DEFINES]->(func:Function)" in query:
                operation_types.append("functions")
            elif "DEFINES.*Class" in query or "DEFINES]->(c:Class)" in query:
                operation_types.append("classes")
            elif "CONTAINS.*File" in query or "CONTAINS]->(f:File)" in query:
                operation_types.append("files")
            elif "HAS_BRANCH" in query:
                operation_types.append("branches")
            elif "HAS_COMMIT" in query:
                operation_types.append("commits")
            elif "Repository" in query and "DETACH DELETE r" in query:
                operation_types.append("repository")

        # Verify correct order: dependencies first, then repository last
        expected_order = [
            "methods",
            "attributes",
            "functions",
            "classes",
            "files",
            "branches",
            "commits",
            "repository",
        ]
        assert operation_types == expected_order, (
            f"Expected {expected_order}, got {operation_types}"
        )

    @pytest.mark.asyncio
    async def test_optional_match_usage(self, mock_extractor):
        """Test that OPTIONAL MATCH is used to handle non-existent nodes gracefully"""
        repo_name = "empty-repo"

        await mock_extractor.clear_repository_data(repo_name)

        cleanup_session = mock_extractor.driver.sessions[1]
        operations = cleanup_session.current_transaction.operations

        # Verify all deletion operations use OPTIONAL MATCH
        for op in operations:
            if (
                "DETACH DELETE" in op["query"]
                and op["query"] != operations[-1]["query"]
            ):  # Skip final repo deletion
                assert "OPTIONAL MATCH" in op["query"], (
                    f"OPTIONAL MATCH not found in query: {op['query']}"
                )

    @pytest.mark.asyncio
    async def test_cleanup_statistics_tracking(self, mock_extractor):
        """Test that cleanup operations return deletion counts for statistics"""
        repo_name = "test-repo"

        await mock_extractor.clear_repository_data(repo_name)

        cleanup_session = mock_extractor.driver.sessions[1]
        operations = cleanup_session.current_transaction.operations

        # Verify all operations (except repository) return deleted_count
        for op in operations[:-1]:  # All except the final repository deletion
            assert "RETURN count(" in op["query"], (
                f"Missing count return in query: {op['query']}"
            )
            assert "deleted_count" in op["query"], (
                f"Missing deleted_count alias in query: {op['query']}"
            )


class TestNeo4jCleanupIntegration:
    """Integration tests for Neo4j cleanup with repository operations"""

    @pytest.fixture
    def mock_extractor_with_analyzer(self):
        """Create extractor with mocked analyzer for integration testing"""
        extractor = DirectNeo4jExtractor(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="test_user",
            neo4j_password="test_password",
        )
        extractor.driver = MockDriver()
        extractor.analyzer = MagicMock()
        return extractor

    async def test_cleanup_then_reparse_workflow(self, mock_extractor_with_analyzer):
        """Test complete workflow: parse → cleanup → re-parse"""
        repo_url = "https://github.com/test/test-integration-repo.git"
        temp_dir = "/tmp/test-repo"

        # Mock git operations and file system
        with patch.object(
            mock_extractor_with_analyzer, "clone_repo", return_value=temp_dir
        ):
            with patch.object(
                mock_extractor_with_analyzer, "get_python_files", return_value=[]
            ):
                with patch.object(
                    mock_extractor_with_analyzer,
                    "get_repository_metadata",
                    return_value={},
                ):
                    with patch.object(
                        mock_extractor_with_analyzer, "_create_graph", return_value=None
                    ):
                        with patch(
                            "os.path.exists", return_value=False
                        ):  # Skip cleanup
                            # First: Parse repository
                            await mock_extractor_with_analyzer.analyze_repository(
                                repo_url, temp_dir
                            )

                            # Then: Cleanup repository
                            await mock_extractor_with_analyzer.clear_repository_data(
                                "test-integration-repo"
                            )

                            # Finally: Re-parse repository
                            await mock_extractor_with_analyzer.analyze_repository(
                                repo_url, temp_dir
                            )

        # Verify both operations completed successfully
        # Should have sessions for: initial cleanup, cleanup validation, cleanup transaction, second cleanup
        assert len(mock_extractor_with_analyzer.driver.sessions) >= 4

        # Find the cleanup transaction (will be one of the middle sessions)
        cleanup_session = None
        for session in mock_extractor_with_analyzer.driver.sessions:
            if (
                hasattr(session, "current_transaction")
                and session.current_transaction
                and session.current_transaction.operations
            ):
                cleanup_session = session
                break

        assert cleanup_session is not None
        assert cleanup_session.current_transaction.committed
        assert not cleanup_session.current_transaction.rolled_back

    async def test_no_warnings_after_cleanup_reparse(
        self, mock_extractor_with_analyzer
    ):
        """Test that no HAS_COMMIT warnings occur after cleanup and re-parse"""
        repo_url = "https://github.com/test/warning-test-repo.git"
        temp_dir = "/tmp/warning-test"

        # Mock git operations and file system
        with patch.object(
            mock_extractor_with_analyzer, "clone_repo", return_value=temp_dir
        ):
            with patch.object(
                mock_extractor_with_analyzer, "get_python_files", return_value=[]
            ):
                with patch.object(
                    mock_extractor_with_analyzer,
                    "get_repository_metadata",
                    return_value={
                        "branches": [{"name": "main", "commit_hash": "abc123"}],
                        "commits": [{"hash": "abc123", "message": "Initial commit"}],
                    },
                ):
                    with patch.object(
                        mock_extractor_with_analyzer, "_create_graph", return_value=None
                    ):
                        with patch(
                            "os.path.exists", return_value=False
                        ):  # Skip cleanup
                            # Parse
                            await mock_extractor_with_analyzer.analyze_repository(
                                repo_url, temp_dir
                            )

                            # Cleanup
                            await mock_extractor_with_analyzer.clear_repository_data(
                                "warning-test-repo"
                            )

                            # Re-parse
                            await mock_extractor_with_analyzer.analyze_repository(
                                repo_url, temp_dir
                            )

        # Verify cleanup included branch and commit relationship handling
        cleanup_session = None
        for session in mock_extractor_with_analyzer.driver.sessions:
            if (
                hasattr(session, "current_transaction")
                and session.current_transaction
                and session.current_transaction.operations
            ):
                cleanup_session = session
                break

        assert cleanup_session is not None
        operations = cleanup_session.current_transaction.operations

        # Check that HAS_BRANCH and HAS_COMMIT cleanups were performed
        has_branch_cleanup = any("HAS_BRANCH" in op["query"] for op in operations)
        has_commit_cleanup = any("HAS_COMMIT" in op["query"] for op in operations)

        assert has_branch_cleanup, "HAS_BRANCH cleanup not found in operations"
        assert has_commit_cleanup, "HAS_COMMIT cleanup not found in operations"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
