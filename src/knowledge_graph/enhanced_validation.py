"""
Enhanced AI script validation that combines Neo4j knowledge graph validation
with Qdrant code example validation for comprehensive hallucination detection.

This module provides improved hallucination detection by:
1. Validating script structure against Neo4j knowledge graph
2. Finding similar code examples in Qdrant for validation
3. Providing suggested corrections from real code examples
4. Generating detailed confidence scores and recommendations
"""

import ast
import json
import logging
import os
from pathlib import Path
from typing import Any

from services.validated_search import ValidatedCodeSearchService

logger = logging.getLogger(__name__)


class EnhancedScriptAnalyzer:
    """Analyzes Python scripts to extract structural information for validation."""

    def __init__(self):
        self.imports = []
        self.classes = []
        self.methods = []
        self.functions = []
        self.variables = []
        self.method_calls = []
        self.attribute_accesses = []

    def analyze_script(self, script_content: str, script_path: str) -> dict[str, Any]:
        """
        Analyze a Python script and extract structural information.

        Args:
            script_content: The Python script content
            script_path: Path to the script file

        Returns:
            Dictionary containing extracted structural information
        """
        try:
            # Parse the script into an AST
            tree = ast.parse(script_content, filename=script_path)

            # Reset analysis state
            self._reset_analysis()

            # Walk the AST and extract information
            for node in ast.walk(tree):
                self._analyze_node(node)

            return {
                "imports": self.imports,
                "classes": self.classes,
                "methods": self.methods,
                "functions": self.functions,
                "variables": self.variables,
                "method_calls": self.method_calls,
                "attribute_accesses": self.attribute_accesses,
                "analysis_metadata": {
                    "script_path": script_path,
                    "total_lines": len(script_content.splitlines()),
                    "ast_nodes": sum(1 for _ in ast.walk(tree)),
                },
            }

        except SyntaxError as e:
            logger.error(f"Syntax error in script {script_path}: {e}")
            return {
                "error": f"Syntax error: {e}",
                "imports": [],
                "classes": [],
                "methods": [],
                "functions": [],
                "variables": [],
                "method_calls": [],
                "attribute_accesses": [],
            }
        except Exception as e:
            logger.error(f"Error analyzing script {script_path}: {e}")
            return {
                "error": f"Analysis error: {e}",
                "imports": [],
                "classes": [],
                "methods": [],
                "functions": [],
                "variables": [],
                "method_calls": [],
                "attribute_accesses": [],
            }

    def _reset_analysis(self):
        """Reset analysis state for a new script."""
        self.imports = []
        self.classes = []
        self.methods = []
        self.functions = []
        self.variables = []
        self.method_calls = []
        self.attribute_accesses = []

    def _analyze_node(self, node: ast.AST):
        """Analyze a single AST node."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.imports.append(
                    {
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                )

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                self.imports.append(
                    {
                        "type": "from_import",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                )

        elif isinstance(node, ast.ClassDef):
            self.classes.append(
                {
                    "name": node.name,
                    "bases": [self._get_node_name(base) for base in node.bases],
                    "methods": [
                        item.name
                        for item in node.body
                        if isinstance(item, ast.FunctionDef)
                    ],
                    "line": node.lineno,
                }
            )

        elif isinstance(node, ast.FunctionDef):
            # Determine if this is a method (inside a class) or a function
            parent_classes = self._find_parent_classes(node)
            if parent_classes:
                self.methods.append(
                    {
                        "name": node.name,
                        "class": parent_classes[-1],  # Immediate parent class
                        "args": [arg.arg for arg in node.args.args],
                        "line": node.lineno,
                    }
                )
            else:
                self.functions.append(
                    {
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "line": node.lineno,
                    }
                )

        elif isinstance(node, ast.Call):
            call_info = self._analyze_call(node)
            if call_info:
                self.method_calls.append(call_info)

        elif isinstance(node, ast.Attribute):
            attr_info = self._analyze_attribute(node)
            if attr_info:
                self.attribute_accesses.append(attr_info)

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.variables.append(
                        {
                            "name": target.id,
                            "line": node.lineno,
                        }
                    )

    def _get_node_name(self, node: ast.AST) -> str:
        """Get the name representation of an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        return str(node)

    def _find_parent_classes(self, node: ast.AST) -> list[str]:
        """Find parent classes for a given node (simplified)."""
        # This is a simplified implementation
        # In a real implementation, you'd walk up the AST tree
        return []

    def _analyze_call(self, node: ast.Call) -> dict[str, Any] | None:
        """Analyze a function/method call."""
        try:
            if isinstance(node.func, ast.Name):
                return {
                    "type": "function_call",
                    "name": node.func.id,
                    "args": len(node.args),
                    "keywords": len(node.keywords),
                    "line": node.lineno,
                }
            if isinstance(node.func, ast.Attribute):
                return {
                    "type": "method_call",
                    "object": self._get_node_name(node.func.value),
                    "method": node.func.attr,
                    "args": len(node.args),
                    "keywords": len(node.keywords),
                    "line": node.lineno,
                }
        except Exception:
            pass
        return None

    def _analyze_attribute(self, node: ast.Attribute) -> dict[str, Any] | None:
        """Analyze an attribute access."""
        try:
            return {
                "object": self._get_node_name(node.value),
                "attribute": node.attr,
                "line": node.lineno,
            }
        except Exception:
            pass
        return None


class EnhancedHallucinationDetector:
    """
    Enhanced hallucination detector that combines Neo4j and Qdrant validation.
    """

    def __init__(self, database_client: Any, neo4j_driver: Any = None):
        """
        Initialize the enhanced hallucination detector.

        Args:
            database_client: Qdrant database client
            neo4j_driver: Neo4j driver (optional)
        """
        self.database_client = database_client
        self.neo4j_driver = neo4j_driver
        self.script_analyzer = EnhancedScriptAnalyzer()

        # Initialize validated search service
        self.validated_search = ValidatedCodeSearchService(
            database_client, neo4j_driver
        )

        # Confidence thresholds
        self.CRITICAL_CONFIDENCE_THRESHOLD = 0.9
        self.HIGH_CONFIDENCE_THRESHOLD = 0.7
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.5

    async def check_script_hallucinations(
        self,
        script_path: str,
        include_code_suggestions: bool = True,
        detailed_analysis: bool = True,
    ) -> dict[str, Any]:
        """
        Perform comprehensive hallucination detection on a Python script.

        Args:
            script_path: Path to the Python script to analyze
            include_code_suggestions: Whether to include code suggestions from Qdrant
            detailed_analysis: Whether to perform detailed analysis

        Returns:
            Comprehensive hallucination detection report
        """
        logger.info(f"Starting enhanced hallucination detection for: {script_path}")

        try:
            # Validate script path and read content
            script_file = Path(script_path)
            if not script_file.exists():
                return self._create_error_response(
                    script_path, f"Script file not found: {script_path}"
                )

            if not script_file.suffix == ".py":
                return self._create_error_response(
                    script_path, "Only Python (.py) files are supported"
                )

            script_content = script_file.read_text(encoding="utf-8")

            # Step 1: Analyze script structure
            analysis_result = self.script_analyzer.analyze_script(
                script_content, script_path
            )

            if "error" in analysis_result:
                return self._create_error_response(
                    script_path, analysis_result["error"]
                )

            # Step 2: Perform Neo4j validation (traditional approach)
            neo4j_validation = await self._perform_neo4j_validation(analysis_result)

            # Step 3: Perform Qdrant code example validation (new approach)
            qdrant_validation = await self._perform_qdrant_validation(
                analysis_result,
                include_code_suggestions,
            )

            # Step 4: Combine validation results
            combined_validation = self._combine_validation_results(
                neo4j_validation,
                qdrant_validation,
            )

            # Step 5: Generate comprehensive report
            report = await self._generate_comprehensive_report(
                script_path,
                analysis_result,
                combined_validation,
                detailed_analysis,
            )

            return report

        except Exception as e:
            logger.error(f"Error in enhanced hallucination detection: {e}")
            return self._create_error_response(script_path, f"Detection failed: {e!s}")

    async def _perform_neo4j_validation(
        self, analysis_result: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform traditional Neo4j knowledge graph validation."""
        try:
            # Check if Neo4j is available
            if not self.validated_search.neo4j_enabled:
                return {
                    "available": False,
                    "reason": "Neo4j not configured",
                    "import_validations": [],
                    "class_validations": [],
                    "method_validations": [],
                    "function_validations": [],
                }

            session = await self.validated_search._get_neo4j_session()
            if not session:
                return {
                    "available": False,
                    "reason": "Could not establish Neo4j session",
                    "import_validations": [],
                    "class_validations": [],
                    "method_validations": [],
                    "function_validations": [],
                }

            try:
                import_validations = await self._validate_imports(
                    session, analysis_result.get("imports", [])
                )
                class_validations = await self._validate_classes(
                    session, analysis_result.get("classes", [])
                )
                method_validations = await self._validate_method_calls(
                    session, analysis_result.get("method_calls", [])
                )
                function_validations = await self._validate_function_calls(
                    session, analysis_result.get("functions", [])
                )

                return {
                    "available": True,
                    "import_validations": import_validations,
                    "class_validations": class_validations,
                    "method_validations": method_validations,
                    "function_validations": function_validations,
                }
            finally:
                await session.close()

        except Exception as e:
            logger.error(f"Neo4j validation error: {e}")
            return {
                "available": False,
                "reason": f"Validation error: {e!s}",
                "import_validations": [],
                "class_validations": [],
                "method_validations": [],
                "function_validations": [],
            }

    async def _perform_qdrant_validation(
        self,
        analysis_result: dict[str, Any],
        include_suggestions: bool,
    ) -> dict[str, Any]:
        """Perform Qdrant code example validation."""
        try:
            if not self.database_client:
                return {
                    "available": False,
                    "reason": "Qdrant client not available",
                    "code_examples": [],
                    "suggestions": [],
                }

            # Extract key code elements for search
            code_elements = self._extract_code_elements_for_search(analysis_result)

            # Search for similar code examples
            validation_results = []
            suggestions = []

            for element in code_elements:
                search_query = self._create_search_query(element)

                # Use validated search service
                search_result = await self.validated_search.search_and_validate_code(
                    query=search_query,
                    match_count=3,  # Get top 3 examples for each element
                    min_confidence=0.3,  # Lower threshold for discovery
                    include_suggestions=include_suggestions,
                    parallel_validation=True,
                )

                if search_result.get("success") and search_result.get("results"):
                    validation_results.append(
                        {
                            "element": element,
                            "query": search_query,
                            "examples": search_result["results"],
                            "validation_summary": search_result.get(
                                "validation_summary", {}
                            ),
                        }
                    )

                    # Collect suggestions
                    for result in search_result["results"]:
                        if result.get("validation", {}).get("suggestions"):
                            suggestions.extend(result["validation"]["suggestions"])

            return {
                "available": True,
                "code_examples": validation_results,
                "suggestions": list(set(suggestions)),  # Remove duplicates
            }

        except Exception as e:
            logger.error(f"Qdrant validation error: {e}")
            return {
                "available": False,
                "reason": f"Validation error: {e!s}",
                "code_examples": [],
                "suggestions": [],
            }

    def _extract_code_elements_for_search(
        self, analysis_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract key code elements that should be validated against examples."""
        elements = []

        # Extract class usage patterns
        for class_info in analysis_result.get("classes", []):
            elements.append(
                {
                    "type": "class_definition",
                    "name": class_info["name"],
                    "context": f"class {class_info['name']}",
                    "details": class_info,
                }
            )

        # Extract method call patterns
        for method_call in analysis_result.get("method_calls", []):
            if method_call.get("type") == "method_call":
                elements.append(
                    {
                        "type": "method_call",
                        "name": f"{method_call.get('object', '')}.{method_call.get('method', '')}",
                        "context": f"{method_call.get('object', '')}.{method_call.get('method', '')}()",
                        "details": method_call,
                    }
                )

        # Extract function call patterns
        for function_call in analysis_result.get("method_calls", []):
            if function_call.get("type") == "function_call":
                elements.append(
                    {
                        "type": "function_call",
                        "name": function_call.get("name", ""),
                        "context": f"{function_call.get('name', '')}()",
                        "details": function_call,
                    }
                )

        # Extract import patterns
        for import_info in analysis_result.get("imports", []):
            if import_info.get("type") == "from_import":
                elements.append(
                    {
                        "type": "import",
                        "name": f"{import_info.get('module', '')}.{import_info.get('name', '')}",
                        "context": f"from {import_info.get('module', '')} import {import_info.get('name', '')}",
                        "details": import_info,
                    }
                )

        return elements

    def _create_search_query(self, element: dict[str, Any]) -> str:
        """Create a search query for a code element."""
        element_type = element.get("type", "")
        name = element.get("name", "")
        context = element.get("context", "")

        # Create a descriptive query based on element type
        if element_type == "class_definition":
            return f"class {name} definition example"
        if element_type == "method_call":
            return f"{name} method call example"
        if element_type == "function_call":
            return f"{name} function usage example"
        if element_type == "import":
            return f"{name} import usage example"
        return context or name

    async def _validate_imports(
        self, session, imports: list[dict]
    ) -> list[dict[str, Any]]:
        """Validate imports against Neo4j knowledge graph."""
        validations = []

        for import_info in imports:
            module = import_info.get("module", "")
            name = import_info.get("name", "")

            # Check if the import exists in any parsed repository
            try:
                if import_info.get("type") == "from_import" and module and name:
                    query = """
                    MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
                    WHERE f.module_name = $module AND c.name = $name
                    RETURN count(c) > 0 as exists, r.name as repo_name
                    LIMIT 1
                    """
                    result = await session.run(query, module=module, name=name)
                    record = await result.single()

                    validations.append(
                        {
                            "import": import_info,
                            "exists": record["exists"] if record else False,
                            "found_in_repo": record.get("repo_name")
                            if record
                            else None,
                            "confidence": 0.8 if (record and record["exists"]) else 0.2,
                        }
                    )

            except Exception as e:
                logger.warning(f"Error validating import {module}.{name}: {e}")
                validations.append(
                    {
                        "import": import_info,
                        "exists": False,
                        "error": str(e),
                        "confidence": 0.0,
                    }
                )

        return validations

    async def _validate_classes(
        self, session, classes: list[dict]
    ) -> list[dict[str, Any]]:
        """Validate class definitions against Neo4j knowledge graph."""
        validations = []

        for class_info in classes:
            class_name = class_info.get("name", "")

            try:
                query = """
                MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
                WHERE c.name = $class_name
                RETURN count(c) > 0 as exists, collect(r.name) as repos
                """
                result = await session.run(query, class_name=class_name)
                record = await result.single()

                validations.append(
                    {
                        "class": class_info,
                        "exists": record["exists"] if record else False,
                        "found_in_repos": record.get("repos", []) if record else [],
                        "confidence": 0.8 if (record and record["exists"]) else 0.2,
                    }
                )

            except Exception as e:
                logger.warning(f"Error validating class {class_name}: {e}")
                validations.append(
                    {
                        "class": class_info,
                        "exists": False,
                        "error": str(e),
                        "confidence": 0.0,
                    }
                )

        return validations

    async def _validate_method_calls(
        self, session, method_calls: list[dict]
    ) -> list[dict[str, Any]]:
        """Validate method calls against Neo4j knowledge graph."""
        validations = []

        for call_info in method_calls:
            if call_info.get("type") != "method_call":
                continue

            method_name = call_info.get("method", "")

            try:
                query = """
                MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)-[:HAS_METHOD]->(m:Method)
                WHERE m.name = $method_name
                RETURN count(m) > 0 as exists, collect(DISTINCT c.name) as classes
                """
                result = await session.run(query, method_name=method_name)
                record = await result.single()

                validations.append(
                    {
                        "method_call": call_info,
                        "exists": record["exists"] if record else False,
                        "found_in_classes": record.get("classes", []) if record else [],
                        "confidence": 0.7 if (record and record["exists"]) else 0.3,
                    }
                )

            except Exception as e:
                logger.warning(f"Error validating method call {method_name}: {e}")
                validations.append(
                    {
                        "method_call": call_info,
                        "exists": False,
                        "error": str(e),
                        "confidence": 0.0,
                    }
                )

        return validations

    async def _validate_function_calls(
        self, session, functions: list[dict]
    ) -> list[dict[str, Any]]:
        """Validate function calls against Neo4j knowledge graph."""
        validations = []

        for func_info in functions:
            function_name = func_info.get("name", "")

            try:
                query = """
                MATCH (r:Repository)-[:CONTAINS]->(f:File)-[:DEFINES]->(func:Function)
                WHERE func.name = $function_name
                RETURN count(func) > 0 as exists, collect(r.name) as repos
                """
                result = await session.run(query, function_name=function_name)
                record = await result.single()

                validations.append(
                    {
                        "function": func_info,
                        "exists": record["exists"] if record else False,
                        "found_in_repos": record.get("repos", []) if record else [],
                        "confidence": 0.7 if (record and record["exists"]) else 0.3,
                    }
                )

            except Exception as e:
                logger.warning(f"Error validating function {function_name}: {e}")
                validations.append(
                    {
                        "function": func_info,
                        "exists": False,
                        "error": str(e),
                        "confidence": 0.0,
                    }
                )

        return validations

    def _combine_validation_results(
        self,
        neo4j_validation: dict[str, Any],
        qdrant_validation: dict[str, Any],
    ) -> dict[str, Any]:
        """Combine Neo4j and Qdrant validation results."""
        # Calculate overall confidence scores
        neo4j_confidence = self._calculate_neo4j_confidence(neo4j_validation)
        qdrant_confidence = self._calculate_qdrant_confidence(qdrant_validation)

        # Weight the two approaches (Neo4j for structure, Qdrant for examples)
        combined_confidence = (neo4j_confidence * 0.6) + (qdrant_confidence * 0.4)

        # Collect all hallucinations
        hallucinations = []
        hallucinations.extend(self._extract_neo4j_hallucinations(neo4j_validation))
        hallucinations.extend(self._extract_qdrant_hallucinations(qdrant_validation))

        # Collect all suggestions
        suggestions = []
        if neo4j_validation.get("available"):
            suggestions.extend(self._generate_neo4j_suggestions(neo4j_validation))
        if qdrant_validation.get("available"):
            suggestions.extend(qdrant_validation.get("suggestions", []))

        return {
            "neo4j_validation": neo4j_validation,
            "qdrant_validation": qdrant_validation,
            "combined_confidence": combined_confidence,
            "hallucinations": hallucinations,
            "suggestions": list(set(suggestions)),  # Remove duplicates
            "validation_methods": {
                "neo4j_available": neo4j_validation.get("available", False),
                "qdrant_available": qdrant_validation.get("available", False),
                "combined_approach": True,
            },
        }

    def _calculate_neo4j_confidence(self, neo4j_validation: dict[str, Any]) -> float:
        """Calculate confidence score from Neo4j validation results."""
        if not neo4j_validation.get("available"):
            return 0.5  # Neutral when not available

        all_validations = []
        all_validations.extend(neo4j_validation.get("import_validations", []))
        all_validations.extend(neo4j_validation.get("class_validations", []))
        all_validations.extend(neo4j_validation.get("method_validations", []))
        all_validations.extend(neo4j_validation.get("function_validations", []))

        if not all_validations:
            return 0.5

        total_confidence = sum(v.get("confidence", 0.0) for v in all_validations)
        return total_confidence / len(all_validations)

    def _calculate_qdrant_confidence(self, qdrant_validation: dict[str, Any]) -> float:
        """Calculate confidence score from Qdrant validation results."""
        if not qdrant_validation.get("available"):
            return 0.5  # Neutral when not available

        code_examples = qdrant_validation.get("code_examples", [])
        if not code_examples:
            return 0.5

        total_confidence = 0.0
        total_examples = 0

        for example_group in code_examples:
            for example in example_group.get("examples", []):
                validation = example.get("validation", {})
                confidence = validation.get("confidence_score", 0.5)
                total_confidence += confidence
                total_examples += 1

        return total_confidence / total_examples if total_examples > 0 else 0.5

    def _extract_neo4j_hallucinations(
        self, neo4j_validation: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract hallucinations from Neo4j validation results."""
        hallucinations = []

        # Check low confidence validations
        for validation_type in [
            "import_validations",
            "class_validations",
            "method_validations",
            "function_validations",
        ]:
            for validation in neo4j_validation.get(validation_type, []):
                if validation.get("confidence", 0) < self.MEDIUM_CONFIDENCE_THRESHOLD:
                    hallucinations.append(
                        {
                            "type": "neo4j_structural",
                            "category": validation_type,
                            "confidence": validation.get("confidence", 0),
                            "details": validation,
                            "severity": "high"
                            if validation.get("confidence", 0) < 0.3
                            else "medium",
                        }
                    )

        return hallucinations

    def _extract_qdrant_hallucinations(
        self, qdrant_validation: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract hallucinations from Qdrant validation results."""
        hallucinations = []

        for example_group in qdrant_validation.get("code_examples", []):
            element = example_group.get("element", {})
            examples = example_group.get("examples", [])

            # If no high-confidence examples found, it might be a hallucination
            high_confidence_examples = [
                ex
                for ex in examples
                if ex.get("validation", {}).get("confidence_score", 0)
                >= self.HIGH_CONFIDENCE_THRESHOLD
            ]

            if not high_confidence_examples and examples:
                # Low confidence examples suggest possible hallucination
                avg_confidence = sum(
                    ex.get("validation", {}).get("confidence_score", 0)
                    for ex in examples
                ) / len(examples)

                hallucinations.append(
                    {
                        "type": "qdrant_semantic",
                        "category": element.get("type", "unknown"),
                        "element_name": element.get("name", ""),
                        "confidence": avg_confidence,
                        "examples_found": len(examples),
                        "high_confidence_examples": 0,
                        "severity": "high" if avg_confidence < 0.3 else "medium",
                    }
                )

        return hallucinations

    def _generate_neo4j_suggestions(
        self, neo4j_validation: dict[str, Any]
    ) -> list[str]:
        """Generate suggestions from Neo4j validation results."""
        suggestions = []

        # Add suggestions for failed validations
        for validation_type in [
            "import_validations",
            "class_validations",
            "method_validations",
            "function_validations",
        ]:
            for validation in neo4j_validation.get(validation_type, []):
                if not validation.get("exists", False):
                    if validation_type == "import_validations":
                        import_info = validation.get("import", {})
                        suggestions.append(
                            f"Import '{import_info.get('module', '')}.{import_info.get('name', '')}' not found in knowledge graph. Consider checking the module name or parsing the relevant repository."
                        )
                    elif validation_type == "class_validations":
                        class_info = validation.get("class", {})
                        suggestions.append(
                            f"Class '{class_info.get('name', '')}' not found. Check class name spelling or ensure the relevant repository is parsed."
                        )

        return suggestions

    async def _generate_comprehensive_report(
        self,
        script_path: str,
        analysis_result: dict[str, Any],
        combined_validation: dict[str, Any],
        detailed_analysis: bool,
    ) -> dict[str, Any]:
        """Generate a comprehensive hallucination detection report."""
        # Determine overall assessment
        confidence = combined_validation.get("combined_confidence", 0.0)
        hallucinations = combined_validation.get("hallucinations", [])

        if confidence >= self.CRITICAL_CONFIDENCE_THRESHOLD:
            assessment = "very_high_confidence"
            risk_level = "low"
        elif confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            assessment = "high_confidence"
            risk_level = "low"
        elif confidence >= self.MEDIUM_CONFIDENCE_THRESHOLD:
            assessment = "medium_confidence"
            risk_level = "medium"
        else:
            assessment = "low_confidence"
            risk_level = "high"

        # Categorize hallucinations by severity
        critical_hallucinations = [
            h for h in hallucinations if h.get("severity") == "high"
        ]
        moderate_hallucinations = [
            h for h in hallucinations if h.get("severity") == "medium"
        ]

        report = {
            "success": True,
            "script_path": script_path,
            "overall_assessment": {
                "confidence_score": confidence,
                "assessment": assessment,
                "risk_level": risk_level,
                "hallucination_count": len(hallucinations),
                "critical_issues": len(critical_hallucinations),
                "moderate_issues": len(moderate_hallucinations),
            },
            "validation_methods": combined_validation.get("validation_methods", {}),
            "hallucinations": {
                "critical": critical_hallucinations,
                "moderate": moderate_hallucinations,
                "all": hallucinations,
            },
            "suggestions": combined_validation.get("suggestions", []),
            "analysis_metadata": {
                "script_analysis": analysis_result.get("analysis_metadata", {}),
                "neo4j_confidence": self._calculate_neo4j_confidence(
                    combined_validation.get("neo4j_validation", {})
                ),
                "qdrant_confidence": self._calculate_qdrant_confidence(
                    combined_validation.get("qdrant_validation", {})
                ),
                "combined_approach": True,
            },
        }

        # Add detailed validation results if requested
        if detailed_analysis:
            report["detailed_validation"] = {
                "neo4j_results": combined_validation.get("neo4j_validation", {}),
                "qdrant_results": combined_validation.get("qdrant_validation", {}),
                "script_structure": analysis_result,
            }

        return report

    def _create_error_response(
        self, script_path: str, error_message: str
    ) -> dict[str, Any]:
        """Create a standardized error response."""
        return {
            "success": False,
            "script_path": script_path,
            "error": error_message,
            "overall_assessment": {
                "confidence_score": 0.0,
                "assessment": "error",
                "risk_level": "unknown",
            },
        }


async def check_ai_script_hallucinations_enhanced(
    database_client: Any,
    neo4j_driver: Any,
    script_path: str,
) -> str:
    """
    Enhanced entry point for AI script hallucination detection.

    This function provides the enhanced hallucination detection that combines
    Neo4j knowledge graph validation with Qdrant code example validation.

    Args:
        database_client: Qdrant database client
        neo4j_driver: Neo4j driver (can be None if not available)
        script_path: Path to the Python script to analyze

    Returns:
        JSON string with comprehensive hallucination detection results
    """
    try:
        # Check if knowledge graph functionality is enabled
        knowledge_graph_enabled = os.getenv("USE_KNOWLEDGE_GRAPH", "false") == "true"
        if not knowledge_graph_enabled:
            return json.dumps(
                {
                    "success": False,
                    "error": "Knowledge graph functionality is disabled. Set USE_KNOWLEDGE_GRAPH=true in environment.",
                },
                indent=2,
            )

        # Initialize enhanced detector
        detector = EnhancedHallucinationDetector(database_client, neo4j_driver)

        # Perform enhanced detection
        result = await detector.check_script_hallucinations(
            script_path=script_path,
            include_code_suggestions=True,
            detailed_analysis=True,
        )

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error in enhanced hallucination detection: {e}")
        return json.dumps(
            {
                "success": False,
                "script_path": script_path,
                "error": f"Enhanced detection failed: {e!s}",
            },
            indent=2,
        )
