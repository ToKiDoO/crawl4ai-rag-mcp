"""
Knowledge graph package for Neo4j operations.

Provides tools for repository parsing, code analysis, and hallucination detection.
"""

from .handlers import (
    handle_repos_command,
    handle_explore_command,
    handle_classes_command,
    handle_class_command,
    handle_method_command,
    handle_query_command,
)
from .queries import query_knowledge_graph
from .repository import parse_github_repository
from .validation import check_ai_script_hallucinations
from .enhanced_validation import (
    check_ai_script_hallucinations_enhanced,
    EnhancedHallucinationDetector,
    EnhancedScriptAnalyzer
)

__all__ = [
    "query_knowledge_graph",
    "parse_github_repository",
    "check_ai_script_hallucinations",
    "check_ai_script_hallucinations_enhanced",
    "EnhancedHallucinationDetector",
    "EnhancedScriptAnalyzer",
    "handle_repos_command",
    "handle_explore_command",
    "handle_classes_command",
    "handle_class_command",
    "handle_method_command",
    "handle_query_command",
]