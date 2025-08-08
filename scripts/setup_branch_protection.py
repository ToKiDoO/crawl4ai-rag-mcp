#!/usr/bin/env python3
"""
GitHub Branch Protection Setup Script

This script provides a programmatic way to configure branch protection rules
for the Crawl4AI MCP repository. It can be used to verify current settings
or apply recommended protection rules.

Requirements:
    - GitHub Personal Access Token with repo permissions
    - PyGithub library: pip install PyGithub

Usage:
    # Check current protection status
    python scripts/setup_branch_protection.py --check

    # Apply protection rules (dry run)
    python scripts/setup_branch_protection.py --apply --dry-run

    # Apply protection rules
    python scripts/setup_branch_protection.py --apply

Environment Variables:
    GITHUB_TOKEN: GitHub Personal Access Token
"""

import os
import sys
import argparse
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

try:
    from github import Github, GithubException
except ImportError:
    print("Error: PyGithub is required. Install with: pip install PyGithub")
    sys.exit(1)


@dataclass
class BranchProtectionConfig:
    """Configuration for branch protection rules"""
    
    # Required status checks
    require_status_checks: bool = True
    strict_status_checks: bool = True  # Require branches to be up to date
    required_status_check_contexts: List[str] = None
    
    # Pull request reviews
    require_pull_request_reviews: bool = True
    required_approving_review_count: int = 1
    dismiss_stale_reviews: bool = True
    require_code_owner_review: bool = True
    require_last_push_approval: bool = True
    
    # Additional settings
    require_conversation_resolution: bool = True
    require_signed_commits: bool = False
    require_linear_history: bool = False
    allow_force_pushes: bool = False
    allow_deletions: bool = False
    
    # Enforcement
    enforce_admins: bool = True
    
    # Restrictions (optional)
    restrict_push_access: bool = False
    push_restrictions_users: List[str] = None
    push_restrictions_teams: List[str] = None
    
    def __post_init__(self):
        if self.required_status_check_contexts is None:
            self.required_status_check_contexts = []
        if self.push_restrictions_users is None:
            self.push_restrictions_users = []
        if self.push_restrictions_teams is None:
            self.push_restrictions_teams = []


# Define protection rules for each branch
BRANCH_PROTECTION_RULES = {
    "main": BranchProtectionConfig(
        required_status_check_contexts=[
            "Code Quality & Linting",
            "Unit Tests (3.12, core)",
            "Unit Tests (3.12, adapters)",
            "Unit Tests (3.12, interfaces)",
            "Unit Tests (3.13, core)",
            "Unit Tests (3.13, adapters)",
            "Unit Tests (3.13, interfaces)",
            "Integration Tests",
            "Coverage Report & Status",
            "Security Scan",
            "Build & Docker Test",
            "PR Validation"
        ],
        require_signed_commits=True,
        require_linear_history=True,
        dismiss_stale_reviews=True,
        require_last_push_approval=True,
        enforce_admins=True
    ),
    "develop": BranchProtectionConfig(
        required_status_check_contexts=[
            "Code Quality & Linting",
            "Unit Tests (3.12, core)",
            "Unit Tests (3.12, adapters)",
            "Unit Tests (3.12, interfaces)",
            "Unit Tests (3.13, core)",
            "Unit Tests (3.13, adapters)",
            "Unit Tests (3.13, interfaces)",
            "Integration Tests",
            "Coverage Report & Status",
            "PR Validation"
        ],
        require_signed_commits=False,
        require_linear_history=False,
        dismiss_stale_reviews=False,
        require_last_push_approval=True,
        enforce_admins=True
    )
}


class BranchProtectionManager:
    """Manages GitHub branch protection rules"""
    
    def __init__(self, token: str, repo_name: str):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        
    def check_protection(self, branch_name: str) -> Dict:
        """Check current protection status for a branch"""
        try:
            branch = self.repo.get_branch(branch_name)
            protection = branch.get_protection()
            
            return {
                "protected": True,
                "enforce_admins": protection.enforce_admins,
                "require_status_checks": protection.required_status_checks is not None,
                "status_check_contexts": protection.required_status_checks.contexts if protection.required_status_checks else [],
                "strict_status_checks": protection.required_status_checks.strict if protection.required_status_checks else False,
                "require_pull_request_reviews": protection.required_pull_request_reviews is not None,
                "required_approving_reviews": protection.required_pull_request_reviews.required_approving_review_count if protection.required_pull_request_reviews else 0,
                "dismiss_stale_reviews": protection.required_pull_request_reviews.dismiss_stale_reviews if protection.required_pull_request_reviews else False,
                "require_code_owner_reviews": protection.required_pull_request_reviews.require_code_owner_reviews if protection.required_pull_request_reviews else False,
                "require_conversation_resolution": protection.required_conversation_resolution,
                "require_signed_commits": protection.required_signatures,
                "require_linear_history": protection.required_linear_history,
                "allow_force_pushes": protection.allow_force_pushes,
                "allow_deletions": protection.allow_deletions
            }
        except GithubException as e:
            if e.status == 404:
                return {"protected": False, "error": "Branch not found or not protected"}
            else:
                return {"protected": False, "error": str(e)}
    
    def apply_protection(self, branch_name: str, config: BranchProtectionConfig, dry_run: bool = False) -> bool:
        """Apply protection rules to a branch"""
        if dry_run:
            print(f"\n[DRY RUN] Would apply these settings to '{branch_name}':")
            print(json.dumps(asdict(config), indent=2))
            return True
        
        try:
            branch = self.repo.get_branch(branch_name)
            
            # Build protection parameters
            kwargs = {
                "enforce_admins": config.enforce_admins,
                "required_status_checks": {
                    "strict": config.strict_status_checks,
                    "contexts": config.required_status_check_contexts
                } if config.require_status_checks else None,
                "required_pull_request_reviews": {
                    "required_approving_review_count": config.required_approving_review_count,
                    "dismiss_stale_reviews": config.dismiss_stale_reviews,
                    "require_code_owner_reviews": config.require_code_owner_review,
                    "require_last_push_approval": config.require_last_push_approval
                } if config.require_pull_request_reviews else None,
                "restrictions": {
                    "users": config.push_restrictions_users,
                    "teams": config.push_restrictions_teams
                } if config.restrict_push_access else None,
                "allow_force_pushes": config.allow_force_pushes,
                "allow_deletions": config.allow_deletions,
                "required_conversation_resolution": config.require_conversation_resolution,
                "required_signatures": config.require_signed_commits,
                "required_linear_history": config.require_linear_history
            }
            
            # Apply protection
            branch.edit_protection(**kwargs)
            print(f"✅ Successfully applied protection to '{branch_name}'")
            return True
            
        except GithubException as e:
            print(f"❌ Error applying protection to '{branch_name}': {e}")
            return False
    
    def generate_report(self) -> str:
        """Generate a report of current protection status"""
        report = ["# Branch Protection Status Report\n"]
        report.append(f"Repository: {self.repo.full_name}\n")
        
        for branch_name in BRANCH_PROTECTION_RULES.keys():
            report.append(f"\n## Branch: {branch_name}")
            
            status = self.check_protection(branch_name)
            if status["protected"]:
                report.append("✅ **Protected**\n")
                report.append("### Current Settings:")
                report.append(f"- Enforce admins: {status.get('enforce_admins', False)}")
                report.append(f"- Require status checks: {status.get('require_status_checks', False)}")
                if status.get('require_status_checks'):
                    report.append(f"  - Strict: {status.get('strict_status_checks', False)}")
                    report.append(f"  - Required contexts: {len(status.get('status_check_contexts', []))}")
                report.append(f"- Require PR reviews: {status.get('require_pull_request_reviews', False)}")
                if status.get('require_pull_request_reviews'):
                    report.append(f"  - Required approvals: {status.get('required_approving_reviews', 0)}")
                    report.append(f"  - Dismiss stale reviews: {status.get('dismiss_stale_reviews', False)}")
                report.append(f"- Require conversation resolution: {status.get('require_conversation_resolution', False)}")
                report.append(f"- Require signed commits: {status.get('require_signed_commits', False)}")
                report.append(f"- Allow force pushes: {status.get('allow_force_pushes', False)}")
                report.append(f"- Allow deletions: {status.get('allow_deletions', False)}")
            else:
                report.append("❌ **Not Protected**")
                if "error" in status:
                    report.append(f"Error: {status['error']}")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Setup GitHub branch protection rules")
    parser.add_argument("--check", action="store_true", help="Check current protection status")
    parser.add_argument("--apply", action="store_true", help="Apply protection rules")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied without making changes")
    parser.add_argument("--report", action="store_true", help="Generate a detailed status report")
    parser.add_argument("--token", help="GitHub token (or use GITHUB_TOKEN env var)")
    parser.add_argument("--repo", default="crawl4ai/crawl4ai-mcp", help="Repository name (owner/repo)")
    
    args = parser.parse_args()
    
    # Get GitHub token
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token required. Set GITHUB_TOKEN environment variable or use --token")
        sys.exit(1)
    
    # Initialize manager
    try:
        manager = BranchProtectionManager(token, args.repo)
    except Exception as e:
        print(f"Error: Failed to connect to GitHub: {e}")
        sys.exit(1)
    
    # Execute requested actions
    if args.report:
        print(manager.generate_report())
    
    elif args.check:
        for branch_name in BRANCH_PROTECTION_RULES.keys():
            print(f"\n🔍 Checking branch: {branch_name}")
            status = manager.check_protection(branch_name)
            print(json.dumps(status, indent=2))
    
    elif args.apply:
        success_count = 0
        for branch_name, config in BRANCH_PROTECTION_RULES.items():
            print(f"\n🔧 Configuring branch: {branch_name}")
            if manager.apply_protection(branch_name, config, args.dry_run):
                success_count += 1
        
        if not args.dry_run:
            print(f"\n✅ Successfully configured {success_count}/{len(BRANCH_PROTECTION_RULES)} branches")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()