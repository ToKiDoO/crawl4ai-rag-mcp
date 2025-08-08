"""
Validated code search service that combines Qdrant semantic search with Neo4j structural validation.

This service provides high-confidence code search results by:
1. Performing semantic search in Qdrant for relevant code examples
2. Validating each result against Neo4j knowledge graph structure
3. Adding confidence scores and validation metadata
4. Filtering results based on validation thresholds
"""

import asyncio
import logging
import os
from typing import Any

from neo4j import AsyncGraphDatabase

from utils import create_embeddings_batch
from utils.integration_helpers import (
    create_cache_key,
    get_performance_optimizer,
    performance_monitor,
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Container for validation results with confidence scoring."""

    def __init__(self):
        self.is_valid = False
        self.confidence_score = 0.0
        self.validation_details = {}
        self.suggestions = []
        self.metadata = {}


class ValidatedCodeSearchService:
    """
    Service that combines Qdrant semantic search with Neo4j structural validation
    to provide high-confidence code search results.
    """

    def __init__(self, database_client: Any, neo4j_driver: Any = None):
        """
        Initialize the validated search service.

        Args:
            database_client: Qdrant database client for semantic search
            neo4j_driver: Neo4j driver for structural validation (optional)
        """
        self.database_client = database_client
        self.neo4j_driver = neo4j_driver

        # Performance optimization
        self.performance_optimizer = get_performance_optimizer()
        self._validation_cache = {}  # Deprecated in favor of performance cache

        # Confidence thresholds
        self.MIN_CONFIDENCE_THRESHOLD = 0.6
        self.HIGH_CONFIDENCE_THRESHOLD = 0.8

        # Neo4j connection details
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")
        self.neo4j_enabled = bool(self.neo4j_uri and self.neo4j_password)

    async def _get_neo4j_session(self):
        """Get or create Neo4j session."""
        if not self.neo4j_enabled:
            return None

        if not self.neo4j_driver:
            # Import notification suppression (available in neo4j>=5.21.0)
            try:
                from neo4j import NotificationMinimumSeverity

                # Create Neo4j driver with notification suppression
                self.neo4j_driver = AsyncGraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_user, self.neo4j_password),
                    warn_notification_severity=NotificationMinimumSeverity.OFF,
                )
            except (ImportError, AttributeError):
                # Fallback for older versions - use logging suppression
                import logging

                logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)
                self.neo4j_driver = AsyncGraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_user, self.neo4j_password),
                )

        return self.neo4j_driver.session()

    @performance_monitor
    async def search_and_validate_code(
        self,
        query: str,
        match_count: int = 10,
        source_filter: str | None = None,
        min_confidence: float = None,
        include_suggestions: bool = True,
        parallel_validation: bool = True,
    ) -> dict[str, Any]:
        """
        Search for code examples and validate them against the knowledge graph.

        Args:
            query: Search query for semantic matching
            match_count: Maximum number of results to return
            source_filter: Optional source repository filter
            min_confidence: Minimum confidence threshold (defaults to service threshold)
            include_suggestions: Whether to include correction suggestions
            parallel_validation: Whether to validate results in parallel

        Returns:
            Dictionary with validated search results and metadata
        """
        if min_confidence is None:
            min_confidence = self.MIN_CONFIDENCE_THRESHOLD

        logger.info(f"Starting validated code search for query: {query}")

        try:
            # Step 1: Perform semantic search in Qdrant
            semantic_results = await self._perform_semantic_search(
                query,
                match_count * 2,
                source_filter,  # Get more results to filter
            )

            if not semantic_results:
                return {
                    "success": True,
                    "query": query,
                    "results": [],
                    "validation_summary": {
                        "total_found": 0,
                        "validated": 0,
                        "high_confidence": 0,
                        "neo4j_available": self.neo4j_enabled,
                    },
                }

            # Step 2: Validate results against Neo4j knowledge graph
            if parallel_validation and self.neo4j_enabled:
                validated_results = await self._validate_results_parallel(
                    semantic_results,
                    include_suggestions,
                )
            else:
                validated_results = await self._validate_results_sequential(
                    semantic_results,
                    include_suggestions,
                )

            # Step 3: Filter and rank by confidence
            filtered_results = [
                result
                for result in validated_results
                if result.get("validation", {}).get("confidence_score", 0)
                >= min_confidence
            ]

            # Sort by combined score (semantic similarity + validation confidence)
            filtered_results.sort(
                key=lambda x: self._calculate_combined_score(x),
                reverse=True,
            )

            # Limit to requested count
            final_results = filtered_results[:match_count]

            # Step 4: Generate summary statistics
            validation_summary = self._generate_validation_summary(
                semantic_results,
                validated_results,
                final_results,
            )

            return {
                "success": True,
                "query": query,
                "results": final_results,
                "validation_summary": validation_summary,
                "search_metadata": {
                    "semantic_search_count": len(semantic_results),
                    "post_validation_count": len(validated_results),
                    "final_result_count": len(final_results),
                    "min_confidence_threshold": min_confidence,
                    "parallel_validation": parallel_validation and self.neo4j_enabled,
                },
            }

        except Exception as e:
            logger.error(f"Error in validated code search: {e}")
            return {
                "success": False,
                "query": query,
                "error": str(e),
                "fallback_available": not self.neo4j_enabled,
            }

    async def _perform_semantic_search(
        self,
        query: str,
        match_count: int,
        source_filter: str | None,
    ) -> list[dict[str, Any]]:
        """Perform semantic search in Qdrant."""
        try:
            # Generate query embedding
            query_embeddings = create_embeddings_batch([query])
            if not query_embeddings:
                return []

            query_embedding = query_embeddings[0]

            # Prepare metadata filter
            filter_metadata = None
            if source_filter:
                filter_metadata = {"source_id": source_filter}

            # Search code examples
            # Note: Using query parameter instead of query_embedding for newer interface
            results = await self.database_client.search_code_examples(
                query=query,  # Pass the query string, the adapter will create embeddings
                match_count=match_count,
                filter_metadata=filter_metadata,
            )

            return results

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []

    async def _validate_results_parallel(
        self,
        results: list[dict[str, Any]],
        include_suggestions: bool,
    ) -> list[dict[str, Any]]:
        """Validate search results in parallel for better performance."""
        if not results or not self.neo4j_enabled:
            # Add empty validation for non-Neo4j mode
            return [self._add_empty_validation(result) for result in results]

        # Create validation tasks
        validation_tasks = [
            self._validate_single_result(result, include_suggestions)
            for result in results
        ]

        # Execute validations in parallel
        try:
            validated_results = await asyncio.gather(
                *validation_tasks, return_exceptions=True
            )

            # Handle any exceptions in individual validations
            final_results = []
            for i, result in enumerate(validated_results):
                if isinstance(result, Exception):
                    logger.warning(f"Validation failed for result {i}: {result}")
                    # Add the original result with empty validation
                    final_results.append(self._add_empty_validation(results[i]))
                else:
                    final_results.append(result)

            return final_results

        except Exception as e:
            logger.error(f"Error in parallel validation: {e}")
            return [self._add_empty_validation(result) for result in results]

    async def _validate_results_sequential(
        self,
        results: list[dict[str, Any]],
        include_suggestions: bool,
    ) -> list[dict[str, Any]]:
        """Validate search results sequentially."""
        validated_results = []

        for result in results:
            try:
                if self.neo4j_enabled:
                    validated_result = await self._validate_single_result(
                        result, include_suggestions
                    )
                else:
                    validated_result = self._add_empty_validation(result)
                validated_results.append(validated_result)
            except Exception as e:
                logger.warning(f"Validation failed for single result: {e}")
                validated_results.append(self._add_empty_validation(result))

        return validated_results

    async def _validate_single_result(
        self,
        result: dict[str, Any],
        include_suggestions: bool,
    ) -> dict[str, Any]:
        """Validate a single search result against Neo4j knowledge graph."""
        # Create cache key for this result
        cache_key = create_cache_key(
            "validation", result.get("source_id", ""), result.get("metadata", {})
        )

        # Check performance cache first
        cached_validation = await self.performance_optimizer.cache.get(cache_key)
        if cached_validation:
            validation = cached_validation
        else:
            # Perform validation
            validation = await self._perform_neo4j_validation(
                result, include_suggestions
            )
            # Cache the result for 1 hour
            await self.performance_optimizer.cache.set(cache_key, validation, ttl=3600)

        # Add validation to result
        enhanced_result = result.copy()
        enhanced_result["validation"] = validation

        return enhanced_result

    async def _perform_neo4j_validation(
        self,
        result: dict[str, Any],
        include_suggestions: bool,
    ) -> dict[str, Any]:
        """Perform the actual Neo4j validation logic."""
        session = await self._get_neo4j_session()
        if not session:
            return self._create_empty_validation()

        try:
            # Extract code metadata from result
            metadata = result.get("metadata", {})
            code_type = metadata.get("code_type", "unknown")
            class_name = metadata.get("class_name")
            method_name = metadata.get("method_name") or metadata.get("name")
            full_name = metadata.get("full_name", "")

            validation_result = ValidationResult()
            validation_checks = []

            # Validation 1: Check if the repository exists
            repo_exists = await self._check_repository_exists(
                session, result.get("source_id")
            )
            validation_checks.append(
                {
                    "check": "repository_exists",
                    "passed": repo_exists,
                    "weight": 0.3,
                }
            )

            if code_type == "class" and class_name:
                # Validation 2: Check if class exists
                class_exists = await self._check_class_exists(
                    session, class_name, result.get("source_id")
                )
                validation_checks.append(
                    {
                        "check": "class_exists",
                        "passed": class_exists,
                        "weight": 0.4,
                    }
                )

                # Validation 3: Check class attributes/methods if available
                if class_exists:
                    structure_valid = await self._validate_class_structure(
                        session,
                        class_name,
                        metadata,
                        result.get("source_id"),
                    )
                    validation_checks.append(
                        {
                            "check": "structure_valid",
                            "passed": structure_valid,
                            "weight": 0.3,
                        }
                    )

            elif code_type == "method" and method_name:
                # Validation 2: Check if method exists
                method_exists = await self._check_method_exists(
                    session,
                    method_name,
                    class_name,
                    result.get("source_id"),
                )
                validation_checks.append(
                    {
                        "check": "method_exists",
                        "passed": method_exists,
                        "weight": 0.4,
                    }
                )

                # Validation 3: Check method signature if available
                if method_exists:
                    signature_valid = await self._validate_method_signature(
                        session,
                        method_name,
                        class_name,
                        metadata,
                        result.get("source_id"),
                    )
                    validation_checks.append(
                        {
                            "check": "signature_valid",
                            "passed": signature_valid,
                            "weight": 0.3,
                        }
                    )

            elif code_type == "function" and method_name:
                # Validation for standalone functions
                function_exists = await self._check_function_exists(
                    session,
                    method_name,
                    result.get("source_id"),
                )
                validation_checks.append(
                    {
                        "check": "function_exists",
                        "passed": function_exists,
                        "weight": 0.7,
                    }
                )

            # Calculate overall confidence score
            confidence_score = self._calculate_confidence_score(validation_checks)

            # Generate suggestions if requested and confidence is low
            suggestions = []
            if (
                include_suggestions
                and confidence_score < self.HIGH_CONFIDENCE_THRESHOLD
            ):
                suggestions = await self._generate_suggestions(
                    session,
                    result,
                    validation_checks,
                )

            return {
                "is_valid": confidence_score >= self.MIN_CONFIDENCE_THRESHOLD,
                "confidence_score": confidence_score,
                "validation_checks": validation_checks,
                "suggestions": suggestions,
                "neo4j_validated": True,
            }

        except Exception as e:
            logger.error(f"Neo4j validation error: {e}")
            return {
                "is_valid": False,
                "confidence_score": 0.0,
                "validation_checks": [],
                "suggestions": [],
                "neo4j_validated": False,
                "error": str(e),
            }
        finally:
            await session.close()

    def _create_empty_validation(self) -> dict[str, Any]:
        """Create an empty validation result when Neo4j is not available."""
        return {
            "is_valid": True,  # Assume valid when we can't validate
            "confidence_score": 0.5,  # Neutral confidence
            "validation_checks": [],
            "suggestions": [],
            "neo4j_validated": False,
        }

    def _add_empty_validation(self, result: dict[str, Any]) -> dict[str, Any]:
        """Add empty validation to a result."""
        enhanced_result = result.copy()
        enhanced_result["validation"] = self._create_empty_validation()
        return enhanced_result

    def _create_cache_key(self, result: dict[str, Any]) -> str:
        """Create a cache key for validation results."""
        metadata = result.get("metadata", {})
        return f"{result.get('source_id', '')}__{metadata.get('code_type', '')}__{metadata.get('full_name', '')}"

    async def _check_repository_exists(self, session, source_id: str) -> bool:
        """Check if repository exists in Neo4j."""
        if not source_id:
            return False

        try:
            query = """
            MATCH (r:Repository {name: $repo_name})
            RETURN count(r) > 0 as exists
            """
            result = await session.run(query, repo_name=source_id)
            record = await result.single()
            return record["exists"] if record else False
        except Exception as e:
            logger.warning(f"Error checking repository existence: {e}")
            return False

    async def _check_class_exists(
        self, session, class_name: str, source_id: str
    ) -> bool:
        """Check if class exists in the repository."""
        if not class_name:
            return False

        try:
            query = """
            MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
            WHERE c.name = $class_name OR c.full_name = $class_name
            RETURN count(c) > 0 as exists
            """
            result = await session.run(
                query, repo_name=source_id, class_name=class_name
            )
            record = await result.single()
            return record["exists"] if record else False
        except Exception as e:
            logger.warning(f"Error checking class existence: {e}")
            return False

    async def _check_method_exists(
        self,
        session,
        method_name: str,
        class_name: str,
        source_id: str,
    ) -> bool:
        """Check if method exists in the specified class."""
        if not method_name:
            return False

        try:
            if class_name:
                query = """
                MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)-[:HAS_METHOD]->(m:Method)
                WHERE (c.name = $class_name OR c.full_name = $class_name) AND m.name = $method_name
                RETURN count(m) > 0 as exists
                """
                result = await session.run(
                    query,
                    repo_name=source_id,
                    class_name=class_name,
                    method_name=method_name,
                )
            else:
                # Search for method across all classes
                query = """
                MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)-[:HAS_METHOD]->(m:Method)
                WHERE m.name = $method_name
                RETURN count(m) > 0 as exists
                """
                result = await session.run(
                    query, repo_name=source_id, method_name=method_name
                )

            record = await result.single()
            return record["exists"] if record else False
        except Exception as e:
            logger.warning(f"Error checking method existence: {e}")
            return False

    async def _check_function_exists(
        self, session, function_name: str, source_id: str
    ) -> bool:
        """Check if standalone function exists in the repository."""
        if not function_name:
            return False

        try:
            query = """
            MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(func:Function)
            WHERE func.name = $function_name
            RETURN count(func) > 0 as exists
            """
            result = await session.run(
                query, repo_name=source_id, function_name=function_name
            )
            record = await result.single()
            return record["exists"] if record else False
        except Exception as e:
            logger.warning(f"Error checking function existence: {e}")
            return False

    async def _validate_class_structure(
        self,
        session,
        class_name: str,
        metadata: dict,
        source_id: str,
    ) -> bool:
        """Validate class structure against metadata."""
        try:
            # This is a placeholder for more sophisticated structure validation
            # Could check method counts, attribute presence, etc.
            return True
        except Exception as e:
            logger.warning(f"Error validating class structure: {e}")
            return False

    async def _validate_method_signature(
        self,
        session,
        method_name: str,
        class_name: str,
        metadata: dict,
        source_id: str,
    ) -> bool:
        """Validate method signature against metadata."""
        try:
            # This is a placeholder for method signature validation
            # Could check parameter counts, types, return types, etc.
            return True
        except Exception as e:
            logger.warning(f"Error validating method signature: {e}")
            return False

    async def _generate_suggestions(
        self,
        session,
        result: dict[str, Any],
        validation_checks: list[dict],
    ) -> list[str]:
        """Generate suggestions for improving low-confidence results."""
        suggestions = []

        for check in validation_checks:
            if not check["passed"]:
                if check["check"] == "repository_exists":
                    suggestions.append(
                        f"Repository '{result.get('source_id')}' not found in knowledge graph. Consider parsing this repository first."
                    )
                elif check["check"] == "class_exists":
                    metadata = result.get("metadata", {})
                    class_name = metadata.get("class_name")
                    suggestions.append(
                        f"Class '{class_name}' not found. Check class name spelling or repository parsing completeness."
                    )
                elif check["check"] == "method_exists":
                    metadata = result.get("metadata", {})
                    method_name = metadata.get("method_name") or metadata.get("name")
                    suggestions.append(
                        f"Method '{method_name}' not found. Verify method name or check if it's inherited."
                    )
                elif check["check"] == "function_exists":
                    metadata = result.get("metadata", {})
                    function_name = metadata.get("method_name") or metadata.get("name")
                    suggestions.append(
                        f"Function '{function_name}' not found. Check function name or module location."
                    )

        return suggestions

    def _calculate_confidence_score(self, validation_checks: list[dict]) -> float:
        """Calculate weighted confidence score from validation checks."""
        if not validation_checks:
            return 0.5  # Neutral when no checks available

        weighted_sum = 0.0
        total_weight = 0.0

        for check in validation_checks:
            weight = check.get("weight", 1.0)
            passed = check.get("passed", False)
            weighted_sum += weight * (1.0 if passed else 0.0)
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _calculate_combined_score(self, result: dict[str, Any]) -> float:
        """Calculate combined score from semantic similarity and validation confidence."""
        semantic_score = result.get("similarity", 0.0)
        validation = result.get("validation", {})
        confidence_score = validation.get("confidence_score", 0.0)

        # Weight semantic similarity and validation confidence
        # Higher weight on validation for more reliable results
        combined_score = (semantic_score * 0.4) + (confidence_score * 0.6)

        return combined_score

    def _generate_validation_summary(
        self,
        semantic_results: list[dict],
        validated_results: list[dict],
        final_results: list[dict],
    ) -> dict[str, Any]:
        """Generate summary statistics for the validation process."""
        high_confidence_count = sum(
            1
            for result in final_results
            if result.get("validation", {}).get("confidence_score", 0)
            >= self.HIGH_CONFIDENCE_THRESHOLD
        )

        return {
            "total_found": len(semantic_results),
            "validated": len(validated_results),
            "final_count": len(final_results),
            "high_confidence": high_confidence_count,
            "validation_rate": len(validated_results) / len(semantic_results)
            if semantic_results
            else 0,
            "high_confidence_rate": high_confidence_count / len(final_results)
            if final_results
            else 0,
            "neo4j_available": self.neo4j_enabled,
            "cache_hits": len(self._validation_cache),
            "confidence_thresholds": {
                "minimum": self.MIN_CONFIDENCE_THRESHOLD,
                "high": self.HIGH_CONFIDENCE_THRESHOLD,
            },
        }

    async def clear_validation_cache(self):
        """Clear the validation cache."""
        await self.performance_optimizer.cache.clear()
        logger.info("Validation cache cleared")

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get validation cache statistics."""
        cache_stats = self.performance_optimizer.cache.get_stats()
        return {
            "cache_stats": cache_stats,
            "neo4j_enabled": self.neo4j_enabled,
            "thresholds": {
                "min_confidence": self.MIN_CONFIDENCE_THRESHOLD,
                "high_confidence": self.HIGH_CONFIDENCE_THRESHOLD,
            },
        }

    async def get_health_status(self) -> dict[str, Any]:
        """Get health status of the validated search service."""
        from utils.integration_helpers import validate_integration_health

        return await validate_integration_health(
            database_client=self.database_client,
            neo4j_driver=self.neo4j_driver,
        )
