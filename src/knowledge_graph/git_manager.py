"""
Git Repository Manager for enhanced Git operations.

This module provides comprehensive Git repository management including
cloning, updating, branch/tag management, and history analysis.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GitRepositoryManager:
    """Manages Git repository operations with async support."""

    def __init__(self):
        """Initialize the Git repository manager."""
        self.logger = logger

    async def clone_repository(
        self,
        url: str,
        target_dir: str,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
        single_branch: bool = False,
    ) -> str:
        """
        Clone a Git repository with advanced options.

        Args:
            url: Repository URL (GitHub, GitLab, local path, etc.)
            target_dir: Target directory for cloning
            branch: Specific branch to clone (default: main/master)
            depth: Clone depth for shallow cloning (default: full history)
            single_branch: Whether to clone only specified branch

        Returns:
            Path to the cloned repository

        Raises:
            RuntimeError: If cloning fails
        """
        self.logger.info(f"Cloning repository from {url} to {target_dir}")

        # Clean up existing directory if it exists
        if os.path.exists(target_dir):
            self.logger.info(f"Removing existing directory: {target_dir}")
            await self._remove_directory(target_dir)

        # Build git clone command
        cmd = ["git", "clone"]

        if depth:
            cmd.extend(["--depth", str(depth)])

        if single_branch:
            cmd.append("--single-branch")

        if branch:
            cmd.extend(["--branch", branch])

        cmd.extend([url, target_dir])

        # Execute clone command
        try:
            result = await self._run_git_command(cmd)
            self.logger.info(f"Repository cloned successfully to {target_dir}")
            return target_dir
        except Exception as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

    async def update_repository(self, repo_dir: str, branch: Optional[str] = None) -> Dict:
        """
        Update an existing repository (pull latest changes).

        Args:
            repo_dir: Path to the repository
            branch: Branch to update (default: current branch)

        Returns:
            Update information including changed files
        """
        self.logger.info(f"Updating repository at {repo_dir}")

        # Store current commit
        old_commit = await self.get_current_commit(repo_dir)

        # Checkout branch if specified
        if branch:
            await self.checkout_branch(repo_dir, branch)

        # Pull latest changes
        cmd = ["git", "pull", "--ff-only"]
        await self._run_git_command(cmd, cwd=repo_dir)

        # Get new commit
        new_commit = await self.get_current_commit(repo_dir)

        # Get changed files
        changed_files = []
        if old_commit != new_commit:
            cmd = ["git", "diff", "--name-only", old_commit, new_commit]
            result = await self._run_git_command(cmd, cwd=repo_dir)
            changed_files = result.strip().split("\n") if result else []

        return {
            "old_commit": old_commit,
            "new_commit": new_commit,
            "changed_files": changed_files,
            "updated": old_commit != new_commit,
        }

    async def get_branches(self, repo_dir: str) -> List[Dict[str, str]]:
        """
        Get all branches in the repository.

        Args:
            repo_dir: Path to the repository

        Returns:
            List of branch information
        """
        cmd = ["git", "branch", "-a", "--format=%(refname:short)|%(committerdate:iso)|%(subject)"]
        result = await self._run_git_command(cmd, cwd=repo_dir)

        branches = []
        for line in result.strip().split("\n"):
            if line:
                parts = line.split("|", 2)
                if len(parts) >= 3:
                    branches.append({
                        "name": parts[0].replace("origin/", ""),
                        "last_commit_date": parts[1],
                        "last_commit_message": parts[2],
                    })

        return branches

    async def get_tags(self, repo_dir: str) -> List[Dict[str, str]]:
        """
        Get all tags in the repository.

        Args:
            repo_dir: Path to the repository

        Returns:
            List of tag information
        """
        cmd = ["git", "tag", "-l", "--format=%(refname:short)|%(creatordate:iso)|%(subject)"]
        result = await self._run_git_command(cmd, cwd=repo_dir)

        tags = []
        for line in result.strip().split("\n"):
            if line:
                parts = line.split("|", 2)
                if len(parts) >= 2:
                    tags.append({
                        "name": parts[0],
                        "date": parts[1] if len(parts) > 1 else "",
                        "message": parts[2] if len(parts) > 2 else "",
                    })

        return tags

    async def get_commits(
        self, repo_dir: str, limit: int = 100, branch: Optional[str] = None
    ) -> List[Dict]:
        """
        Get commit history.

        Args:
            repo_dir: Path to the repository
            limit: Maximum number of commits to retrieve
            branch: Specific branch (default: current branch)

        Returns:
            List of commit information
        """
        cmd = [
            "git",
            "log",
            f"--max-count={limit}",
            "--pretty=format:%H|%an|%ae|%at|%s",
            "--no-merges",
        ]

        if branch:
            cmd.append(branch)

        result = await self._run_git_command(cmd, cwd=repo_dir)

        commits = []
        for line in result.strip().split("\n"):
            if line:
                parts = line.split("|", 4)
                if len(parts) >= 5:
                    commits.append({
                        "hash": parts[0],
                        "author_name": parts[1],
                        "author_email": parts[2],
                        "timestamp": int(parts[3]),
                        "date": datetime.fromtimestamp(int(parts[3])).isoformat(),
                        "message": parts[4],
                    })

        return commits

    async def get_file_history(
        self, repo_dir: str, file_path: str, limit: int = 50
    ) -> List[Dict]:
        """
        Get commit history for a specific file.

        Args:
            repo_dir: Path to the repository
            file_path: Path to the file relative to repo root
            limit: Maximum number of commits

        Returns:
            List of commits that modified the file
        """
        cmd = [
            "git",
            "log",
            f"--max-count={limit}",
            "--pretty=format:%H|%an|%at|%s",
            "--follow",
            "--",
            file_path,
        ]

        result = await self._run_git_command(cmd, cwd=repo_dir)

        history = []
        for line in result.strip().split("\n"):
            if line:
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    history.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "timestamp": int(parts[2]),
                        "date": datetime.fromtimestamp(int(parts[2])).isoformat(),
                        "message": parts[3],
                    })

        return history

    async def checkout_branch(self, repo_dir: str, branch: str) -> None:
        """
        Checkout a specific branch.

        Args:
            repo_dir: Path to the repository
            branch: Branch name to checkout
        """
        cmd = ["git", "checkout", branch]
        await self._run_git_command(cmd, cwd=repo_dir)
        self.logger.info(f"Checked out branch: {branch}")

    async def get_current_commit(self, repo_dir: str) -> str:
        """
        Get the current commit hash.

        Args:
            repo_dir: Path to the repository

        Returns:
            Current commit hash
        """
        cmd = ["git", "rev-parse", "HEAD"]
        result = await self._run_git_command(cmd, cwd=repo_dir)
        return result.strip()

    async def get_repository_info(self, repo_dir: str) -> Dict:
        """
        Get comprehensive repository information.

        Args:
            repo_dir: Path to the repository

        Returns:
            Repository metadata including size, file count, etc.
        """
        info = {}

        # Get remote URL
        try:
            cmd = ["git", "config", "--get", "remote.origin.url"]
            info["remote_url"] = (await self._run_git_command(cmd, cwd=repo_dir)).strip()
        except:
            info["remote_url"] = None

        # Get current branch
        try:
            cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            info["current_branch"] = (await self._run_git_command(cmd, cwd=repo_dir)).strip()
        except:
            info["current_branch"] = None

        # Get file statistics
        try:
            cmd = ["git", "ls-files"]
            files = (await self._run_git_command(cmd, cwd=repo_dir)).strip().split("\n")
            info["file_count"] = len([f for f in files if f])

            # Count by extension
            extensions = {}
            for file in files:
                if file and "." in file:
                    ext = file.split(".")[-1].lower()
                    extensions[ext] = extensions.get(ext, 0) + 1
            info["file_extensions"] = extensions
        except:
            info["file_count"] = 0
            info["file_extensions"] = {}

        # Get repository size
        try:
            cmd = ["git", "count-objects", "-v", "-H"]
            result = await self._run_git_command(cmd, cwd=repo_dir)
            for line in result.strip().split("\n"):
                if "size-pack:" in line:
                    info["size"] = line.split(":")[1].strip()
        except:
            info["size"] = "unknown"

        # Get contributor count
        try:
            cmd = ["git", "log", "--format=%an"]
            authors = (await self._run_git_command(cmd, cwd=repo_dir)).strip().split("\n")
            info["contributor_count"] = len(set([a for a in authors if a]))
        except:
            info["contributor_count"] = 0

        return info

    async def is_git_repository(self, path: str) -> bool:
        """
        Check if a directory is a Git repository.

        Args:
            path: Directory path to check

        Returns:
            True if it's a Git repository
        """
        try:
            cmd = ["git", "rev-parse", "--git-dir"]
            await self._run_git_command(cmd, cwd=path)
            return True
        except:
            return False

    async def get_changed_files(
        self, repo_dir: str, from_commit: str, to_commit: str = "HEAD"
    ) -> List[Dict]:
        """
        Get files changed between two commits.

        Args:
            repo_dir: Path to the repository
            from_commit: Starting commit hash
            to_commit: Ending commit hash (default: HEAD)

        Returns:
            List of changed files with change type
        """
        cmd = ["git", "diff", "--name-status", from_commit, to_commit]
        result = await self._run_git_command(cmd, cwd=repo_dir)

        changed_files = []
        for line in result.strip().split("\n"):
            if line:
                parts = line.split("\t", 1)
                if len(parts) >= 2:
                    status_map = {
                        "A": "added",
                        "M": "modified",
                        "D": "deleted",
                        "R": "renamed",
                        "C": "copied",
                    }
                    changed_files.append({
                        "status": status_map.get(parts[0][0], "unknown"),
                        "file": parts[1],
                    })

        return changed_files

    async def _run_git_command(
        self, cmd: List[str], cwd: Optional[str] = None
    ) -> str:
        """
        Run a git command asynchronously.

        Args:
            cmd: Command arguments
            cwd: Working directory

        Returns:
            Command output

        Raises:
            RuntimeError: If command fails
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                raise RuntimeError(f"Git command failed: {error_msg}")

            return stdout.decode("utf-8")
        except Exception as e:
            self.logger.error(f"Error running git command {' '.join(cmd)}: {e}")
            raise

    async def _remove_directory(self, path: str) -> None:
        """
        Remove a directory with proper error handling.

        Args:
            path: Directory path to remove
        """
        def handle_remove_readonly(func, path, exc):
            try:
                if os.path.exists(path):
                    os.chmod(path, 0o777)
                    func(path)
            except PermissionError:
                self.logger.warning(f"Could not remove {path} - file in use")

        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: shutil.rmtree(path, onerror=handle_remove_readonly)
            )
        except Exception as e:
            self.logger.warning(f"Could not fully remove {path}: {e}")