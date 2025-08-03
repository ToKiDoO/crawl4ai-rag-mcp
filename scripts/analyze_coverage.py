import json
import sys
from pathlib import Path

def analyze_coverage():
    """Analyze coverage.json to identify modules with low coverage."""
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("Run: uv run pytest tests/ --cov=src --cov-report=json")
        sys.exit(1)
    
    with open(coverage_file) as f:
        data = json.load(f)
    
    files = data.get("files", {})
    low_coverage = []
    
    for file_path, file_data in files.items():
        coverage = file_data["summary"]["percent_covered"]
        if coverage < 80:
            missing_lines = file_data["missing_lines"]
            low_coverage.append({
                "file": file_path,
                "coverage": coverage,
                "missing_lines": len(missing_lines),
                "lines": missing_lines[:10]  # First 10 missing lines
            })
    
    # Sort by coverage percentage
    low_coverage.sort(key=lambda x: x["coverage"])
    
    print("Modules with coverage < 80%:")
    for module in low_coverage:
        print(f"\n{module['file']}: {module['coverage']:.1f}%")
        print(f"  Missing {module['missing_lines']} lines")
        if module['lines']:
            print(f"  First missing lines: {module['lines']}")

if __name__ == "__main__":
    analyze_coverage()