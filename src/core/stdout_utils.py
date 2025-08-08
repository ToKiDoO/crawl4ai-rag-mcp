"""Utilities for managing stdout/stderr output."""

import sys


class SuppressStdout:
    """Context manager to suppress stdout during crawl operations."""

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = sys.stderr
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._stdout
        return False
