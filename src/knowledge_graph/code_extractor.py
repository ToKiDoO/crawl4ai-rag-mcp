"""
Code extraction from Neo4j knowledge graph for Qdrant indexing.

This module extracts structured code examples from Neo4j and prepares them
for embedding generation and storage in Qdrant vector database.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeExample:
    """Structured code example for embedding and indexing."""

    repository_name: str
    file_path: str
    module_name: str
    code_type: str  # 'class', 'method', 'function'
    name: str
    full_name: str
    code_text: str  # Generated code representation
    parameters: list[str] | None = None
    return_type: str | None = None
    class_name: str | None = None  # For methods
    method_count: int | None = None  # For classes
    language: str = "python"
    validation_status: str = "extracted"  # extracted, validated, verified

    def to_metadata(self) -> dict[str, Any]:
        """Convert to metadata dictionary for Qdrant storage."""
        metadata = {
            "repository_name": self.repository_name,
            "file_path": self.file_path,
            "module_name": self.module_name,
            "code_type": self.code_type,
            "name": self.name,
            "full_name": self.full_name,
            "language": self.language,
            "validation_status": self.validation_status,
        }

        if self.parameters:
            metadata["parameters"] = self.parameters
        if self.return_type:
            metadata["return_type"] = self.return_type
        if self.class_name:
            metadata["class_name"] = self.class_name
        if self.method_count is not None:
            metadata["method_count"] = self.method_count

        return metadata

    def generate_embedding_text(self) -> str:
        """Generate text representation for embedding generation."""
        if self.code_type == "class":
            text = f"Python class {self.name} in {self.module_name}\n"
            text += f"Full name: {self.full_name}\n"
            if self.method_count:
                text += f"Contains {self.method_count} methods\n"
            text += f"Code: {self.code_text}"

        elif self.code_type == "method":
            text = f"Python method {self.name}"
            if self.class_name:
                text += f" in class {self.class_name}"
            text += f" from {self.module_name}\n"
            if self.parameters:
                text += f"Parameters: {', '.join(self.parameters)}\n"
            if self.return_type:
                text += f"Returns: {self.return_type}\n"
            text += f"Code: {self.code_text}"

        elif self.code_type == "function":
            text = f"Python function {self.name} from {self.module_name}\n"
            if self.parameters:
                text += f"Parameters: {', '.join(self.parameters)}\n"
            if self.return_type:
                text += f"Returns: {self.return_type}\n"
            text += f"Code: {self.code_text}"

        else:
            text = f"Python {self.code_type} {self.name}: {self.code_text}"

        return text


class Neo4jCodeExtractor:
    """Extracts code examples from Neo4j knowledge graph."""

    def __init__(self, neo4j_session: Any):
        """Initialize with Neo4j session."""
        self.session = neo4j_session

    async def extract_repository_code(self, repo_name: str) -> list[CodeExample]:
        """
        Extract all code examples from a repository in Neo4j.

        Args:
            repo_name: Name of the repository to extract from

        Returns:
            List of CodeExample objects ready for embedding
        """
        logger.info(f"Extracting code from repository: {repo_name}")

        # Check if repository exists
        if not await self._repository_exists(repo_name):
            raise ValueError(f"Repository '{repo_name}' not found in knowledge graph")

        code_examples = []

        # Extract classes with their methods
        classes = await self._extract_classes(repo_name)
        code_examples.extend(classes)

        # Extract standalone functions
        functions = await self._extract_functions(repo_name)
        code_examples.extend(functions)

        logger.info(f"Extracted {len(code_examples)} code examples from {repo_name}")
        return code_examples

    async def _repository_exists(self, repo_name: str) -> bool:
        """Check if repository exists in Neo4j."""
        query = """
        MATCH (r:Repository {name: $repo_name})
        RETURN r.name as name
        LIMIT 1
        """
        result = await self.session.run(query, repo_name=repo_name)
        record = await result.single()
        return record is not None

    async def _extract_classes(self, repo_name: str) -> list[CodeExample]:
        """Extract class definitions with their methods."""
        query = """
        MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
        OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
        RETURN 
            c.name as class_name,
            c.full_name as class_full_name,
            f.path as file_path,
            f.module_name as module_name,
            count(m) as method_count,
            collect({
                name: m.name,
                params_list: m.params_list,
                params_detailed: m.params_detailed,
                return_type: m.return_type,
                args: m.args
            }) as methods
        ORDER BY c.name
        """

        result = await self.session.run(query, repo_name=repo_name)
        classes = []

        async for record in result:
            class_name = record["class_name"]
            class_full_name = record["class_full_name"]
            file_path = record["file_path"]
            module_name = record["module_name"] or ""
            method_count = record["method_count"]
            methods = record["methods"]

            # Generate class code representation
            class_code = self._generate_class_code(class_name, methods)

            # Create class example
            class_example = CodeExample(
                repository_name=repo_name,
                file_path=file_path,
                module_name=module_name,
                code_type="class",
                name=class_name,
                full_name=class_full_name,
                code_text=class_code,
                method_count=method_count,
            )
            classes.append(class_example)

            # Create individual method examples for important methods
            for method in methods:
                if method["name"] and not method["name"].startswith(
                    "_"
                ):  # Public methods
                    method_code = self._generate_method_code(method)
                    method_example = CodeExample(
                        repository_name=repo_name,
                        file_path=file_path,
                        module_name=module_name,
                        code_type="method",
                        name=method["name"],
                        full_name=f"{class_full_name}.{method['name']}",
                        code_text=method_code,
                        parameters=method["params_list"],
                        return_type=method["return_type"],
                        class_name=class_name,
                    )
                    classes.append(method_example)

        return classes

    async def _extract_functions(self, repo_name: str) -> list[CodeExample]:
        """Extract standalone function definitions."""
        query = """
        MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(func:Function)
        RETURN 
            func.name as function_name,
            func.params_list as params_list,
            func.params_detailed as params_detailed,
            func.return_type as return_type,
            func.args as args,
            f.path as file_path,
            f.module_name as module_name
        ORDER BY func.name
        """

        result = await self.session.run(query, repo_name=repo_name)
        functions = []

        async for record in result:
            function_name = record["function_name"]
            if not function_name or function_name.startswith(
                "_"
            ):  # Skip private functions
                continue

            file_path = record["file_path"]
            module_name = record["module_name"] or ""
            params_list = record["params_list"]
            return_type = record["return_type"]

            # Generate function code representation
            function_code = self._generate_function_code(
                {
                    "name": function_name,
                    "params_list": params_list,
                    "params_detailed": record["params_detailed"],
                    "return_type": return_type,
                    "args": record["args"],
                }
            )

            full_name = (
                f"{module_name}.{function_name}" if module_name else function_name
            )

            function_example = CodeExample(
                repository_name=repo_name,
                file_path=file_path,
                module_name=module_name,
                code_type="function",
                name=function_name,
                full_name=full_name,
                code_text=function_code,
                parameters=params_list,
                return_type=return_type,
            )
            functions.append(function_example)

        return functions

    def _generate_class_code(self, class_name: str, methods: list[dict]) -> str:
        """Generate a code representation for a class."""
        code = f"class {class_name}:\n"
        code += '    """Class with the following public methods:"""\n'

        public_methods = [
            m for m in methods if m["name"] and not m["name"].startswith("_")
        ]
        if public_methods:
            for method in public_methods[:5]:  # Limit to first 5 methods
                params = ", ".join(method["params_list"] or [])
                return_type = method["return_type"] or "Any"
                code += f"    def {method['name']}({params}) -> {return_type}: ...\n"
        else:
            code += "    pass\n"

        return code

    def _generate_method_code(self, method: dict) -> str:
        """Generate a code representation for a method."""
        name = method["name"]
        params = ", ".join(method["params_list"] or [])
        return_type = method["return_type"] or "Any"

        code = f"def {name}({params}) -> {return_type}:\n"
        code += '    """Method implementation"""\n'
        code += "    pass"

        return code

    def _generate_function_code(self, function: dict) -> str:
        """Generate a code representation for a function."""
        name = function["name"]
        params = ", ".join(function["params_list"] or [])
        return_type = function["return_type"] or "Any"

        code = f"def {name}({params}) -> {return_type}:\n"
        code += '    """Function implementation"""\n'
        code += "    pass"

        return code


async def extract_repository_code(
    repo_extractor: Any, repo_name: str
) -> dict[str, Any]:
    """
    Main function to extract code from a repository using the repository extractor.

    Args:
        repo_extractor: Repository extractor instance with Neo4j connection
        repo_name: Name of the repository to extract from

    Returns:
        Dictionary with extraction results
    """
    try:
        # Get Neo4j session from the repository extractor
        async with repo_extractor.driver.session() as session:
            extractor = Neo4jCodeExtractor(session)
            code_examples = await extractor.extract_repository_code(repo_name)

            # Convert to serializable format
            examples_data = []
            for example in code_examples:
                examples_data.append(
                    {
                        "repository_name": example.repository_name,
                        "file_path": example.file_path,
                        "module_name": example.module_name,
                        "code_type": example.code_type,
                        "name": example.name,
                        "full_name": example.full_name,
                        "code_text": example.code_text,
                        "embedding_text": example.generate_embedding_text(),
                        "metadata": example.to_metadata(),
                    }
                )

            return {
                "success": True,
                "repository_name": repo_name,
                "code_examples_count": len(code_examples),
                "code_examples": examples_data,
                "extraction_summary": {
                    "classes": len(
                        [e for e in code_examples if e.code_type == "class"]
                    ),
                    "methods": len(
                        [e for e in code_examples if e.code_type == "method"]
                    ),
                    "functions": len(
                        [e for e in code_examples if e.code_type == "function"]
                    ),
                },
            }

    except Exception as e:
        logger.error(f"Error extracting code from repository {repo_name}: {e}")
        return {
            "success": False,
            "repository_name": repo_name,
            "error": str(e),
        }
