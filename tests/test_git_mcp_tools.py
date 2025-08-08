#!/usr/bin/env python3
"""
Test script for Git-related MCP tools.

This script tests the new Git repository parsing tools:
- parse_repository_branch
- get_repository_info
- update_parsed_repository

Run this after the MCP server is connected and Neo4j is configured.
"""

import json
import logging
from datetime import datetime
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class GitToolsTester:
    """Test harness for Git-related MCP tools."""

    def __init__(self):
        self.results = []
        self.test_repo = "https://github.com/octocat/Hello-World"
        self.test_branch = "test"
        self.repo_name = "Hello-World"

    def log_result(self, test_name: str, status: str, details: dict[str, Any]):
        """Log test result."""
        result = {
            "test": test_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }
        self.results.append(result)

        # Print summary
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"{symbol} {test_name}: {status}")
        if status == "FAILED":
            print(f"   Error: {details.get('error', 'Unknown error')}")

    def test_parse_repository_branch(self):
        """Test parsing a specific branch."""
        test_name = "parse_repository_branch"
        print(f"\n🧪 Testing {test_name}...")

        try:
            # This would be called via MCP in real testing
            # For documentation purposes, showing expected parameters
            params = {
                "repo_url": self.test_repo,
                "branch": self.test_branch,
            }

            expected = {
                "status": "success",
                "repository": self.repo_name,
                "branch": self.test_branch,
                "statistics": {
                    "files_analyzed": ">0",
                    "branches": ">0",
                    "recent_commits": ">0",
                },
            }

            print(f"   Parameters: {json.dumps(params, indent=2)}")
            print(f"   Expected: Repository parsed from branch '{self.test_branch}'")
            print("   Expected: Git metadata extracted")

            # In actual test, check response from MCP tool
            self.log_result(
                test_name,
                "PENDING",
                {
                    "params": params,
                    "expected": expected,
                    "note": "Execute via MCP client",
                },
            )

        except Exception as e:
            self.log_result(test_name, "FAILED", {"error": str(e)})

    def test_get_repository_info(self):
        """Test retrieving repository metadata."""
        test_name = "get_repository_info"
        print(f"\n🧪 Testing {test_name}...")

        try:
            params = {
                "repo_name": self.repo_name,
            }

            expected = {
                "repository": self.repo_name,
                "metadata": {
                    "remote_url": "not null",
                    "current_branch": "not null",
                    "file_count": ">0",
                },
                "branches": "array",
                "recent_commits": "array",
                "code_statistics": {
                    "files_analyzed": ">0",
                },
            }

            print(f"   Parameters: {json.dumps(params, indent=2)}")
            print("   Expected: Complete repository metadata")
            print("   Expected: Branches and commits included")

            self.log_result(
                test_name,
                "PENDING",
                {
                    "params": params,
                    "expected": expected,
                    "note": "Requires repository to be parsed first",
                },
            )

        except Exception as e:
            self.log_result(test_name, "FAILED", {"error": str(e)})

    def test_update_parsed_repository(self):
        """Test updating an existing repository."""
        test_name = "update_parsed_repository"
        print(f"\n🧪 Testing {test_name}...")

        try:
            params = {
                "repo_url": self.test_repo,
            }

            expected = {
                "status": "success",
                "repository": self.repo_name,
                "message": "Repository updated successfully",
            }

            print(f"   Parameters: {json.dumps(params, indent=2)}")
            print("   Expected: Repository updated without errors")
            print("   Note: Currently performs full re-parse")

            self.log_result(
                test_name,
                "PENDING",
                {
                    "params": params,
                    "expected": expected,
                    "note": "Requires repository to be parsed first",
                },
            )

        except Exception as e:
            self.log_result(test_name, "FAILED", {"error": str(e)})

    def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n🧪 Testing error handling...")

        # Test 1: Invalid repository URL
        test_name = "parse_invalid_repo"
        try:
            params = {
                "repo_url": "https://github.com/nonexistent/repo",
            }

            print(f"   Test: {test_name}")
            print(f"   Parameters: {json.dumps(params, indent=2)}")
            print("   Expected: Clear error about invalid repository")

            self.log_result(
                test_name,
                "PENDING",
                {
                    "params": params,
                    "expected": "Error message about invalid repo",
                },
            )
        except Exception as e:
            self.log_result(test_name, "FAILED", {"error": str(e)})

        # Test 2: Non-existent branch
        test_name = "parse_nonexistent_branch"
        try:
            params = {
                "repo_url": self.test_repo,
                "branch": "nonexistent-branch-xyz",
            }

            print(f"   Test: {test_name}")
            print(f"   Parameters: {json.dumps(params, indent=2)}")
            print("   Expected: Error about branch not found")

            self.log_result(
                test_name,
                "PENDING",
                {
                    "params": params,
                    "expected": "Error message about branch not found",
                },
            )
        except Exception as e:
            self.log_result(test_name, "FAILED", {"error": str(e)})

        # Test 3: Get info for non-parsed repo
        test_name = "get_info_nonexistent"
        try:
            params = {
                "repo_name": "never-parsed-repo",
            }

            print(f"   Test: {test_name}")
            print(f"   Parameters: {json.dumps(params, indent=2)}")
            print("   Expected: Error that repo not found")

            self.log_result(
                test_name,
                "PENDING",
                {
                    "params": params,
                    "expected": "Error message about repo not found",
                },
            )
        except Exception as e:
            self.log_result(test_name, "FAILED", {"error": str(e)})

    def generate_report(self):
        """Generate test report."""
        print("\n" + "=" * 60)
        print("Git MCP Tools Test Report")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Total tests: {len(self.results)}")

        # Count results
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        pending = sum(1 for r in self.results if r["status"] == "PENDING")

        print(f"Results: {passed} passed, {failed} failed, {pending} pending")

        # Detailed results
        print("\nDetailed Results:")
        print("-" * 60)
        for result in self.results:
            status_symbol = {
                "PASSED": "✅",
                "FAILED": "❌",
                "PENDING": "⏳",
            }.get(result["status"], "❓")

            print(f"{status_symbol} {result['test']}: {result['status']}")
            if result["status"] == "PENDING":
                print(f"   Note: {result['details'].get('note', '')}")
            elif result["status"] == "FAILED":
                print(f"   Error: {result['details'].get('error', '')}")

        # Test instructions
        print("\n" + "=" * 60)
        print("Manual Testing Instructions")
        print("=" * 60)
        print("""
1. Connect to MCP server via Claude Code or mcp-cli
2. Ensure Neo4j is configured (USE_KNOWLEDGE_GRAPH=true)
3. Execute each test using the MCP tools with prefix:
   - mcp__crawl4ai-docker__parse_repository_branch
   - mcp__crawl4ai-docker__get_repository_info
   - mcp__crawl4ai-docker__update_parsed_repository

4. Test sequence:
   a. First parse the main repository (parse_github_repository)
   b. Test parse_repository_branch with 'test' branch
   c. Test get_repository_info to verify metadata
   d. Test update_parsed_repository
   e. Test error scenarios

5. Verify in Neo4j:
   - Check Repository nodes have Git metadata
   - Check Branch nodes exist
   - Check Commit nodes exist
   - Verify relationships are correct

6. Document results in tests/results/YYYYMMDD-GIT_TOOLS_TESTING.md
        """)

        return self.results


def main():
    """Run Git tools tests."""
    tester = GitToolsTester()

    print("Git MCP Tools Testing Suite")
    print("=" * 60)
    print(f"Test repository: {tester.test_repo}")
    print(f"Test branch: {tester.test_branch}")
    print("=" * 60)

    # Run tests
    tester.test_parse_repository_branch()
    tester.test_get_repository_info()
    tester.test_update_parsed_repository()
    tester.test_error_handling()

    # Generate report
    tester.generate_report()

    # Save results
    results_file = (
        f"tests/results/{datetime.now().strftime('%Y%m%d-%H%M')}-GIT_TOOLS_TEST.json"
    )
    print(f"\nSaving results to: {results_file}")

    # Note: In real test, save the results
    # with open(results_file, 'w') as f:
    #     json.dump(tester.results, f, indent=2)


if __name__ == "__main__":
    main()
