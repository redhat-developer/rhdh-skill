"""Deterministic RHDH context and work-state CLI.

This package provides stable local interfaces for:
- Environment status checking
- Configuration management
- Workspace operations for the overlay repo
- Activity tracking (worklog, todo)
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rhdh-skills")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
