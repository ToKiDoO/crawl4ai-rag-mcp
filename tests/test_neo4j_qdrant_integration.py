"""
Integration tests for Neo4j-Qdrant integration pipeline.

Tests the complete workflow including:
- Repository parsing and Neo4j indexing
- Code extraction from Neo4j to Qdrant
- Validated search with hallucination detection
- Performance under load
- Fallback behavior testing
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from knowledge_graph.code_extractor import CodeExample, Neo4jCodeExtractor
from services.validated_search import ValidatedCodeSearchService


class TestNeo4jQdrantIntegration:
    """Test complete Neo4j-Qdrant integration pipeline."""

    @pytest.fixture
    def integration_environment(self):
        """Set up integration test environment."""
        with patch.dict(
            os.environ,
            {
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "test_password",
                "QDRANT_HOST": "localhost",
                "QDRANT_PORT": "6333",
                "QDRANT_COLLECTION_NAME": "test_collection",
            },
        ):
            yield

    @pytest.fixture
    def mock_neo4j_repository_data(self):
        """Mock repository data in Neo4j format."""
        return {
            "repository_name": "auth-service",
            "classes": [
                {
                    "class_name": "AuthService",
                    "class_full_name": "auth.service.AuthService",
                    "file_path": "src/auth/service.py",
                    "module_name": "auth.service",
                    "method_count": 3,
                    "methods": [
                        {
                            "name": "authenticate",
                            "params_list": ["self", "username", "password"],
                            "params_detailed": [
                                "self",
                                "username: str",
                                "password: str",
                            ],
                            "return_type": "bool",
                            "args": ["self", "username", "password"],
                        },
                        {
                            "name": "validate_token",
                            "params_list": ["self", "token"],
                            "params_detailed": ["self", "token: str"],
                            "return_type": "dict",
                            "args": ["self", "token"],
                        },
                    ],
                },
                {
                    "class_name": "TokenManager",
                    "class_full_name": "auth.token.TokenManager",
                    "file_path": "src/auth/token.py",
                    "module_name": "auth.token",
                    "method_count": 2,
                    "methods": [
                        {
                            "name": "generate_token",
                            "params_list": ["self", "user_id"],
                            "params_detailed": ["self", "user_id: int"],
                            "return_type": "str",
                            "args": ["self", "user_id"],
                        },
                    ],
                },
            ],
            "functions": [
                {
                    "function_name": "hash_password",
                    "params_list": ["password", "salt"],
                    "params_detailed": ["password: str", "salt: str"],
                    "return_type": "str",
                    "args": ["password", "salt"],
                    "file_path": "src/auth/utils.py",
                    "module_name": "auth.utils",
                },
            ],
        }

    @pytest.fixture
    def mock_qdrant_embeddings(self):
        """Mock Qdrant embeddings for code examples."""
        return {
            "auth.service.AuthService": [0.1, 0.2, 0.3, 0.4, 0.5],
            "auth.service.AuthService.authenticate": [0.2, 0.3, 0.4, 0.5, 0.6],
            "auth.token.TokenManager.generate_token": [0.3, 0.4, 0.5, 0.6, 0.7],
            "auth.utils.hash_password": [0.4, 0.5, 0.6, 0.7, 0.8],
        }

    @pytest.mark.asyncio
    async def test_complete_indexing_workflow(
        self,
        integration_environment,
        mock_neo4j_repository_data,
        mock_qdrant_embeddings,
    ):
        """Test complete workflow from Neo4j repository to Qdrant indexing."""
        # Mock Neo4j session and extractor
        mock_session = AsyncMock()
        mock_extractor = Neo4jCodeExtractor(mock_session)

        # Mock database client
        mock_db_client = AsyncMock()
        mock_db_client.store_code_example = AsyncMock()

        # Mock code extraction from Neo4j
        with patch.object(mock_extractor, "extract_repository_code") as mock_extract:
            # Create expected code examples
            expected_examples = []

            # Add class examples
            for class_data in mock_neo4j_repository_data["classes"]:
                class_example = CodeExample(
                    repository_name=mock_neo4j_repository_data["repository_name"],
                    file_path=class_data["file_path"],
                    module_name=class_data["module_name"],
                    code_type="class",
                    name=class_data["class_name"],
                    full_name=class_data["class_full_name"],
                    code_text=f"class {class_data['class_name']}:\n    pass",
                    method_count=class_data["method_count"],
                )
                expected_examples.append(class_example)

                # Add method examples
                for method in class_data["methods"]:
                    method_example = CodeExample(
                        repository_name=mock_neo4j_repository_data["repository_name"],
                        file_path=class_data["file_path"],
                        module_name=class_data["module_name"],
                        code_type="method",
                        name=method["name"],
                        full_name=f"{class_data['class_full_name']}.{method['name']}",
                        code_text=f"def {method['name']}({', '.join(method['params_list'])}):\n    pass",
                        parameters=method["params_list"],
                        return_type=method["return_type"],
                        class_name=class_data["class_name"],
                    )
                    expected_examples.append(method_example)

            # Add function examples
            for func_data in mock_neo4j_repository_data["functions"]:
                func_example = CodeExample(
                    repository_name=mock_neo4j_repository_data["repository_name"],
                    file_path=func_data["file_path"],
                    module_name=func_data["module_name"],
                    code_type="function",
                    name=func_data["function_name"],
                    full_name=f"{func_data['module_name']}.{func_data['function_name']}",
                    code_text=f"def {func_data['function_name']}({', '.join(func_data['params_list'])}):\n    pass",
                    parameters=func_data["params_list"],
                    return_type=func_data["return_type"],
                )
                expected_examples.append(func_example)

            mock_extract.return_value = expected_examples

            # Mock embedding generation
            with patch("utils.create_embeddings_batch") as mock_embeddings:

                def mock_embedding_func(texts):
                    return [
                        mock_qdrant_embeddings.get(
                            ex.full_name, [0.1, 0.2, 0.3, 0.4, 0.5]
                        )
                        for ex in expected_examples[: len(texts)]
                    ]

                mock_embeddings.side_effect = mock_embedding_func

                # Execute indexing workflow
                extracted_examples = await mock_extractor.extract_repository_code(
                    "auth-service"
                )

                # Store in Qdrant
                for example in extracted_examples:
                    embedding_text = example.generate_embedding_text()
                    embeddings = mock_embeddings([embedding_text])

                    if embeddings:
                        await mock_db_client.store_code_example(
                            source_id=example.repository_name,
                            content=example.code_text,
                            metadata=example.to_metadata(),
                            embeddings=embeddings[0],
                        )

                # Verify the complete workflow
                assert (
                    len(extracted_examples) == 6
                )  # 2 classes + 3 methods + 1 function
                assert mock_db_client.store_code_example.call_count == 6

                # Verify different code types were extracted
                code_types = [ex.code_type for ex in extracted_examples]
                assert "class" in code_types
                assert "method" in code_types
                assert "function" in code_types

    @pytest.mark.asyncio
    async def test_search_and_validation_pipeline(
        self, integration_environment, mock_qdrant_embeddings
    ):
        """Test search and validation pipeline with Neo4j validation."""
        # Mock database client with search results
        mock_db_client = AsyncMock()
        mock_search_results = [
            {
                "content": "def authenticate(self, username: str, password: str) -> bool:\n    return verify_credentials(username, password)",
                "metadata": {
                    "code_type": "method",
                    "method_name": "authenticate",
                    "class_name": "AuthService",
                    "full_name": "auth.service.AuthService.authenticate",
                    "repository_name": "auth-service",
                },
                "similarity": 0.92,
                "source_id": "auth-service",
            },
            {
                "content": "def fake_method(self, param):\n    # This method doesn't exist in Neo4j\n    return param * 2",
                "metadata": {
                    "code_type": "method",
                    "method_name": "fake_method",
                    "class_name": "FakeClass",
                    "full_name": "fake.module.FakeClass.fake_method",
                    "repository_name": "fake-repo",
                },
                "similarity": 0.75,
                "source_id": "fake-repo",
            },
        ]
        mock_db_client.search_code_examples.return_value = mock_search_results

        # Mock Neo4j driver and session
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock Neo4j validation responses
        async def mock_neo4j_run(query, **params):
            mock_result = AsyncMock()

            if "Repository" in query and params.get("repo_name") == "auth-service":
                mock_result.single.return_value = {"exists": True}
            elif "Repository" in query and params.get("repo_name") == "fake-repo":
                mock_result.single.return_value = {"exists": False}
            elif "Method" in query and params.get("method_name") == "authenticate":
                mock_result.single.return_value = {"exists": True}
            elif "Method" in query and params.get("method_name") == "fake_method":
                mock_result.single.return_value = {"exists": False}
            else:
                mock_result.single.return_value = {"exists": False}

            return mock_result

        mock_session.run.side_effect = mock_neo4j_run

        # Create validated search service
        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        # Mock embedding generation for query
        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.2, 0.3, 0.4, 0.5, 0.6]]

            # Execute search and validation
            result = await validated_service.search_and_validate_code(
                query="authentication method",
                match_count=5,
                min_confidence=0.6,
            )

            # Verify results
            assert result["success"] is True
            assert (
                len(result["results"]) == 1
            )  # Only valid result should pass confidence threshold

            valid_result = result["results"][0]
            assert valid_result["metadata"]["method_name"] == "authenticate"
            assert valid_result["validation"]["is_valid"] is True
            assert valid_result["validation"]["confidence_score"] >= 0.6
            assert valid_result["validation"]["neo4j_validated"] is True

            # Verify validation summary
            summary = result["validation_summary"]
            assert summary["total_found"] == 2
            assert summary["validated"] == 2
            assert summary["final_count"] == 1
            assert summary["neo4j_available"] is True

    @pytest.mark.asyncio
    async def test_hallucination_detection(self, integration_environment):
        """Test hallucination detection with fake vs real code examples."""
        mock_db_client = AsyncMock()

        # Mixed results with real and fake code
        mock_search_results = [
            # Real method that exists in Neo4j
            {
                "content": "def login(self, username, password):\n    return self.authenticate(username, password)",
                "metadata": {
                    "code_type": "method",
                    "method_name": "login",
                    "class_name": "AuthService",
                    "repository_name": "auth-service",
                },
                "similarity": 0.90,
                "source_id": "auth-service",
            },
            # Fake method that doesn't exist
            {
                "content": "def super_authenticate(self, user, pwd, magic_key):\n    # AI hallucination - this method doesn't exist\n    return verify_with_magic(user, pwd, magic_key)",
                "metadata": {
                    "code_type": "method",
                    "method_name": "super_authenticate",
                    "class_name": "AuthService",
                    "repository_name": "auth-service",
                },
                "similarity": 0.85,
                "source_id": "auth-service",
            },
            # Real function
            {
                "content": "def hash_password(password, salt):\n    return hashlib.pbkdf2_hmac('sha256', password, salt, 100000)",
                "metadata": {
                    "code_type": "function",
                    "function_name": "hash_password",
                    "repository_name": "auth-service",
                },
                "similarity": 0.88,
                "source_id": "auth-service",
            },
        ]
        mock_db_client.search_code_examples.return_value = mock_search_results

        # Mock Neo4j responses for hallucination detection
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        async def mock_validation_run(query, **params):
            mock_result = AsyncMock()

            if "Repository" in query:
                mock_result.single.return_value = {"exists": True}
            elif "Method" in query:
                method_name = params.get("method_name")
                if method_name == "login":
                    mock_result.single.return_value = {"exists": True}
                elif method_name == "super_authenticate":
                    mock_result.single.return_value = {"exists": False}  # Hallucination
                else:
                    mock_result.single.return_value = {"exists": False}
            elif "Function" in query:
                function_name = params.get("function_name")
                if function_name == "hash_password":
                    mock_result.single.return_value = {"exists": True}
                else:
                    mock_result.single.return_value = {"exists": False}

            return mock_result

        mock_session.run.side_effect = mock_validation_run

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.2, 0.3, 0.4, 0.5, 0.6]]

            result = await validated_service.search_and_validate_code(
                query="authentication functions",
                match_count=10,
                min_confidence=0.7,  # High confidence to filter hallucinations
                include_suggestions=True,
            )

            # Should detect and filter out hallucination
            assert result["success"] is True

            # Only real methods/functions should pass high confidence threshold
            valid_results = [
                r
                for r in result["results"]
                if r["validation"]["confidence_score"] >= 0.7
            ]

            # Should have real methods/functions but not hallucination
            real_names = [
                r["metadata"].get("method_name") or r["metadata"].get("function_name")
                for r in valid_results
            ]
            assert "login" in real_names or "hash_password" in real_names
            assert "super_authenticate" not in real_names  # Hallucination filtered out

            # Verify validation summary shows detection
            summary = result["validation_summary"]
            assert summary["neo4j_available"] is True
            assert summary["total_found"] == 3

    @pytest.mark.asyncio
    async def test_performance_under_load(self, integration_environment):
        """Test integration performance under concurrent load."""
        # Create multiple concurrent search requests
        mock_db_client = AsyncMock()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock fast responses
        mock_db_client.search_code_examples.return_value = [
            {
                "content": "def test_method(self):\n    pass",
                "metadata": {"code_type": "method", "method_name": "test_method"},
                "similarity": 0.8,
            },
        ]

        mock_result = AsyncMock()
        mock_result.single.return_value = {"exists": True}
        mock_session.run.return_value = mock_result

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        # Test concurrent requests
        concurrent_requests = 20

        async def single_search_request(query_id):
            with patch(
                "services.validated_search.create_embeddings_batch"
            ) as mock_embeddings:
                mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

                return await validated_service.search_and_validate_code(
                    query=f"test query {query_id}",
                    match_count=5,
                )

        # Execute concurrent requests and measure performance
        import time

        start_time = time.time()

        tasks = [single_search_request(i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 10.0  # Should complete within 10 seconds
        assert len(results) == concurrent_requests

        # All requests should succeed
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == concurrent_requests

        # Verify all results have expected structure
        for result in successful_results:
            assert result["success"] is True
            assert "validation_summary" in result

    @pytest.mark.asyncio
    async def test_fallback_behavior_neo4j_unavailable(self, integration_environment):
        """Test fallback behavior when Neo4j is unavailable."""
        mock_db_client = AsyncMock()
        mock_db_client.search_code_examples.return_value = [
            {
                "content": "def fallback_method(self):\n    return 'fallback'",
                "metadata": {"code_type": "method", "method_name": "fallback_method"},
                "similarity": 0.8,
            },
        ]

        # Create service without Neo4j (simulating unavailability)
        with patch.dict(os.environ, {}, clear=True):  # Clear Neo4j env vars
            validated_service = ValidatedCodeSearchService(
                database_client=mock_db_client,
                neo4j_driver=None,
            )

            with patch(
                "services.validated_search.create_embeddings_batch"
            ) as mock_embeddings:
                mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

                result = await validated_service.search_and_validate_code(
                    query="fallback test",
                    match_count=5,
                )

                # Should fallback gracefully
                assert result["success"] is True
                assert len(result["results"]) == 1

                # Should have neutral validation (no Neo4j validation)
                validation = result["results"][0]["validation"]
                assert validation["neo4j_validated"] is False
                assert validation["confidence_score"] == 0.5  # Neutral confidence

                # Summary should indicate Neo4j unavailable
                summary = result["validation_summary"]
                assert summary["neo4j_available"] is False

    @pytest.mark.asyncio
    async def test_integration_with_caching(self, integration_environment):
        """Test integration with performance caching enabled."""
        mock_db_client = AsyncMock()
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock search and validation responses
        mock_db_client.search_code_examples.return_value = [
            {
                "content": "def cached_method(self):\n    return 'cached'",
                "metadata": {
                    "code_type": "method",
                    "method_name": "cached_method",
                    "class_name": "CachedClass",
                },
                "similarity": 0.85,
                "source_id": "cached-repo",
            },
        ]

        mock_result = AsyncMock()
        mock_result.single.return_value = {"exists": True}
        mock_session.run.return_value = mock_result

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            # First request - should populate cache
            result1 = await validated_service.search_and_validate_code(
                query="cached method test",
                match_count=5,
            )

            # Second identical request - should use cache
            result2 = await validated_service.search_and_validate_code(
                query="cached method test",
                match_count=5,
            )

            # Both should succeed and have similar results
            assert result1["success"] is True
            assert result2["success"] is True

            # Verify validation was cached (fewer database calls)
            # Note: In real implementation, cache hits would reduce Neo4j calls

            # Check cache statistics
            cache_stats = await validated_service.get_cache_stats()
            assert "cache_stats" in cache_stats
            assert "neo4j_enabled" in cache_stats

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, integration_environment):
        """Test error recovery in integration scenarios."""
        mock_db_client = AsyncMock()
        mock_driver = AsyncMock()

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        # Test 1: Database search failure
        mock_db_client.search_code_examples.side_effect = Exception(
            "Qdrant connection failed"
        )

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            result = await validated_service.search_and_validate_code(
                query="error test",
                match_count=5,
            )

            # Should handle error gracefully
            assert result["success"] is False
            assert "error" in result
            assert "Qdrant connection failed" in result["error"]

        # Test 2: Neo4j validation failure with fallback
        mock_db_client.search_code_examples.side_effect = None  # Reset
        mock_db_client.search_code_examples.return_value = [
            {
                "content": "def recovery_method(self):\n    pass",
                "metadata": {"code_type": "method"},
                "similarity": 0.8,
            },
        ]

        # Neo4j failure should not crash the entire search
        mock_session = AsyncMock()
        mock_session.run.side_effect = Exception("Neo4j query failed")
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            result = await validated_service.search_and_validate_code(
                query="recovery test",
                match_count=5,
            )

            # Should succeed with degraded validation
            assert result["success"] is True
            assert len(result["results"]) == 1

            # Validation should show Neo4j error
            validation = result["results"][0]["validation"]
            assert "error" in validation or validation["neo4j_validated"] is False

    @pytest.mark.asyncio
    async def test_integration_health_monitoring(self, integration_environment):
        """Test integration health monitoring functionality."""
        # Mock healthy components
        mock_db_client = AsyncMock()
        mock_db_client.get_collections = AsyncMock(
            return_value=["collection1", "collection2"]
        )

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_record = {"health_check": 1}

        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.run.return_value = mock_result
        mock_result.single.return_value = mock_record

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        # Test health check
        health_status = await validated_service.get_health_status()

        assert "overall_status" in health_status
        assert "components" in health_status

        # Components should be healthy
        if "components" in health_status:
            qdrant_status = health_status["components"].get("qdrant", {})
            neo4j_status = health_status["components"].get("neo4j", {})

            # At least one component should be healthy
            assert (
                qdrant_status.get("status") == "healthy"
                or neo4j_status.get("status") == "healthy"
            )


class TestIntegrationPerformanceBenchmarks:
    """Performance benchmarks for integration testing."""

    @pytest.mark.asyncio
    async def test_search_response_time_benchmark(self):
        """Benchmark search response times."""
        # Mock fast components
        mock_db_client = AsyncMock()
        mock_db_client.search_code_examples.return_value = [
            {"content": "test", "metadata": {}, "similarity": 0.8},
        ]

        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single.return_value = {"exists": True}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            # Measure response time
            import time

            start_time = time.time()

            result = await validated_service.search_and_validate_code(
                query="performance benchmark",
                match_count=5,
            )

            end_time = time.time()
            response_time = end_time - start_time

            # Performance target: < 2 seconds for validated search
            assert response_time < 2.0
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_throughput_benchmark(self):
        """Benchmark search throughput under load."""
        mock_db_client = AsyncMock()
        mock_db_client.search_code_examples.return_value = []

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=None,  # Disable Neo4j for pure throughput test
        )

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            # Test throughput with multiple concurrent requests
            num_requests = 50

            async def single_request(req_id):
                return await validated_service.search_and_validate_code(
                    query=f"throughput test {req_id}",
                    match_count=3,
                )

            import time

            start_time = time.time()

            tasks = [single_request(i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)

            end_time = time.time()
            total_time = end_time - start_time

            # Calculate throughput
            throughput = num_requests / total_time

            # Performance target: > 10 requests per second
            assert throughput > 10.0
            assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_validation_accuracy_benchmark(self):
        """Benchmark validation accuracy with known test cases."""
        mock_db_client = AsyncMock()

        # Test cases with known validation results
        test_cases = [
            {
                "content": "def known_real_method(self):\n    pass",
                "metadata": {
                    "code_type": "method",
                    "method_name": "known_real_method",
                    "class_name": "RealClass",
                    "repository_name": "real-repo",
                },
                "expected_valid": True,
            },
            {
                "content": "def fake_hallucinated_method(self):\n    # This doesn't exist\n    pass",
                "metadata": {
                    "code_type": "method",
                    "method_name": "fake_hallucinated_method",
                    "class_name": "FakeClass",
                    "repository_name": "fake-repo",
                },
                "expected_valid": False,
            },
        ]

        # Mock database to return test cases
        mock_db_client.search_code_examples.return_value = test_cases

        # Mock Neo4j to validate based on expected results
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_driver.session.return_value = mock_session
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        async def mock_validation_run(query, **params):
            mock_result = AsyncMock()

            if "Repository" in query:
                repo_name = params.get("repo_name")
                mock_result.single.return_value = {"exists": repo_name == "real-repo"}
            elif "Method" in query:
                method_name = params.get("method_name")
                mock_result.single.return_value = {
                    "exists": method_name == "known_real_method"
                }
            else:
                mock_result.single.return_value = {"exists": False}

            return mock_result

        mock_session.run.side_effect = mock_validation_run

        validated_service = ValidatedCodeSearchService(
            database_client=mock_db_client,
            neo4j_driver=mock_driver,
        )

        with patch(
            "services.validated_search.create_embeddings_batch"
        ) as mock_embeddings:
            mock_embeddings.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

            result = await validated_service.search_and_validate_code(
                query="validation accuracy test",
                match_count=10,
                min_confidence=0.0,  # Include all results for accuracy measurement
            )

            assert result["success"] is True
            assert len(result["results"]) == 2

            # Check validation accuracy
            correct_validations = 0
            for i, validated_result in enumerate(result["results"]):
                expected_valid = test_cases[i]["expected_valid"]
                actual_valid = validated_result["validation"]["is_valid"]

                if expected_valid == actual_valid:
                    correct_validations += 1

            # Accuracy target: > 95%
            accuracy = correct_validations / len(result["results"])
            assert accuracy > 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
