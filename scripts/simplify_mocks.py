"""Simplify complex mocks in test files."""
from pathlib import Path
import ast
import re

def analyze_mock_complexity(test_file: Path):
    """Analyze mock complexity in a test file."""
    content = test_file.read_text()
    
    # Find mock chains (e.g., mock.method.return_value.attribute)
    mock_chains = re.findall(r'mock\w*(?:\.\w+){3,}', content)
    
    # Find nested Mock/MagicMock/AsyncMock creation
    nested_mocks = re.findall(r'(?:Magic|Async)?Mock\([^)]*(?:Magic|Async)?Mock', content)
    
    if mock_chains or nested_mocks:
        print(f"\n{test_file}:")
        if mock_chains:
            print(f"  Complex mock chains ({len(mock_chains)}):")
            for chain in set(mock_chains[:5]):  # Show first 5 unique
                print(f"    - {chain}")
        if nested_mocks:
            print(f"  Nested mock creation: {len(nested_mocks)} instances")
    
    return len(mock_chains) + len(nested_mocks)

# Analyze all test files
total_complexity = 0
for test_file in Path("tests").glob("test_*.py"):
    total_complexity += analyze_mock_complexity(test_file)

print(f"\nTotal mock complexity score: {total_complexity}")
print("\nRecommendation: Replace complex mocks with test doubles")