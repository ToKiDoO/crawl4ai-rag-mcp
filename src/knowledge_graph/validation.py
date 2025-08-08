"""
AI script validation and hallucination detection functionality.

Validates AI-generated Python scripts against the knowledge graph.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def check_ai_script_hallucinations(
    knowledge_validator: Any,
    script_analyzer: Any,
    hallucination_reporter: Any,
    script_path: str,
) -> str:
    """
    Check an AI-generated Python script for hallucinations using the knowledge graph.

    This analyzes a Python script for potential AI hallucinations by validating
    imports, method calls, class instantiations, and function calls against a Neo4j
    knowledge graph containing real repository data.

    The tool performs comprehensive analysis including:
    - Import validation against known repositories
    - Method call validation on classes from the knowledge graph
    - Class instantiation parameter validation
    - Function call parameter validation
    - Attribute access validation

    Args:
        knowledge_validator: Knowledge validator instance from context
        script_analyzer: AI script analyzer instance from context
        hallucination_reporter: Hallucination reporter instance from context
        script_path: Absolute path to the Python script to analyze

    Returns:
        JSON string with hallucination detection results, confidence scores, and recommendations
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

        if not knowledge_validator:
            return json.dumps(
                {
                    "success": False,
                    "error": "Knowledge validator not available. Check Neo4j configuration and ensure repositories have been parsed.",
                },
                indent=2,
            )

        # Validate script path
        script_file = Path(script_path)
        if not script_file.exists():
            return json.dumps(
                {
                    "success": False,
                    "script_path": script_path,
                    "error": f"Script file not found: {script_path}",
                },
                indent=2,
            )

        if not script_file.suffix == ".py":
            return json.dumps(
                {
                    "success": False,
                    "script_path": script_path,
                    "error": "Only Python (.py) files are supported",
                },
                indent=2,
            )

        # Read the script content
        try:
            script_content = script_file.read_text(encoding="utf-8")
        except Exception as e:
            return json.dumps(
                {
                    "success": False,
                    "script_path": script_path,
                    "error": f"Failed to read script: {e!s}",
                },
                indent=2,
            )

        logger.info(f"Analyzing script for hallucinations: {script_path}")

        # Step 1: Analyze the script structure
        # The script_analyzer extracts:
        # - Imports and their usage
        # - Class instantiations with parameters
        # - Method calls with arguments
        # - Function calls with arguments
        # - Attribute accesses
        analysis_result = await script_analyzer.analyze_script(
            script_content, str(script_file)
        )

        # Step 2: Validate against the knowledge graph
        # The knowledge_validator checks:
        # - Whether imported modules exist in parsed repositories
        # - Whether classes exist with the used methods
        # - Whether methods accept the provided parameters
        # - Whether functions exist with the correct signatures
        validation_result = await knowledge_validator.validate_analysis(analysis_result)

        # Step 3: Generate comprehensive report
        # The hallucination_reporter creates:
        # - Overall confidence score
        # - List of detected hallucinations
        # - Recommendations for fixes
        # - Detailed validation results
        report = await hallucination_reporter.generate_report(
            analysis_result,
            validation_result,
            script_path,
        )

        # Format the final response
        return json.dumps(
            {
                "success": True,
                "script_path": script_path,
                "confidence_score": report.get("confidence_score", 0),
                "summary": report.get("summary", {}),
                "hallucinations": report.get("hallucinations", []),
                "recommendations": report.get("recommendations", []),
                "metadata": {
                    "total_imports": len(analysis_result.get("imports", [])),
                    "total_classes": len(analysis_result.get("classes", [])),
                    "total_methods": len(analysis_result.get("methods", [])),
                    "total_functions": len(analysis_result.get("functions", [])),
                    "analysis_timestamp": report.get("timestamp"),
                },
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error checking script hallucinations: {e}")
        return json.dumps(
            {
                "success": False,
                "script_path": script_path,
                "error": f"Hallucination check failed: {e!s}",
            },
            indent=2,
        )
