"""Workspace discovery, output formatting, and subprocess execution.

All bundled with this skill so the CLI runs installed alone. A
sibling skill carrying something similar is expected, not a defect.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# =============================================================================
# Workspace discovery
# =============================================================================


def _is_setup_dir(path: Path) -> bool:
    return (path / "rhdh-customizations").is_dir() and (path / "rhdh-local").is_dir()


def get_local_setup_dir(start: Optional[Path] = None) -> Optional[Path]:
    """Discover an rhdh-local-setup workspace without external configuration."""
    configured = os.environ.get("RHDH_LOCAL_SETUP_DIR")
    if configured:
        path = Path(configured).expanduser()
        if _is_setup_dir(path):
            return path.resolve()

    current = (start or Path.cwd()).resolve()
    for parent in (current, *current.parents):
        if _is_setup_dir(parent):
            return parent
        candidate = parent / "rhdh-local-setup"
        if _is_setup_dir(candidate):
            return candidate.resolve()
    return None


# =============================================================================
# Subprocess execution
# =============================================================================


def run_command(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Decoding is pinned to UTF-8 with replacement so that non-ASCII subprocess
    output does not raise on a Windows console codepage.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


# =============================================================================
# Output formatting
# =============================================================================


def detect_output_mode() -> str:
    """Detect whether to use human or JSON output.

    Returns:
        "human" if stdout is a TTY, "json" otherwise
    """
    return "human" if sys.stdout.isatty() else "json"


# ANSI color codes
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
BOLD = "\033[1m"
NC = "\033[0m"  # No Color

_OK = "✓"
_WARN = "⚠"
_FAIL = "✗"
_INFO = "→"


@dataclass
class OutputFormatter:
    """Formats rhdh-local output as JSON or human-readable text.

    Commands log inline with log_ok/log_warn/log_fail/log_info in human mode and
    then call success() for next_steps; in JSON mode success() emits the whole
    structured response. Only the surface rhdh-local actually calls is
    implemented here -- there is no debug channel, list renderer,
    banner, or raw passthrough.

    Attributes:
        mode: "human" for colored text, "json" for machine-parseable output
    """

    mode: str = "auto"  # "auto", "human", or "json"
    _has_human_output: bool = field(default=False, repr=False)
    _color: bool = field(default=True, repr=False)

    def __post_init__(self):
        if self.mode == "auto":
            self.mode = detect_output_mode()
        self._color = os.environ.get("NO_COLOR") is None

    @property
    def is_human(self) -> bool:
        return self.mode == "human"

    def _paint(self, code: str, text: str) -> str:
        """Wrap text in an ANSI code unless NO_COLOR is set."""
        return f"{code}{text}{NC}" if self._color else text

    def success(self, data: dict[str, Any], next_steps: Optional[list[str]] = None) -> None:
        """Output a success response."""
        if not self.is_human:
            response: dict[str, Any] = {"success": True, "data": data}
            if next_steps:
                response["next_steps"] = next_steps
            print(json.dumps(response, indent=2, default=str))
            return

        # Inline log_* output already covered the data; only next steps remain.
        if not self._has_human_output:
            self._render_data(data)
        if next_steps:
            print("\n" + self._paint(BOLD, "Next steps:"))
            for step in next_steps:
                print(f"  {self._paint(BLUE, step)}")

    def error(self, code: str, message: str, next_steps: Optional[list[str]] = None) -> None:
        """Output an error response. Human-mode errors go entirely to stderr."""
        if not self.is_human:
            error = {"code": code, "message": message}
            response: dict[str, Any] = {"success": False, "error": error}
            if next_steps:
                response["next_steps"] = next_steps
            print(json.dumps(response, indent=2))
            return

        print(f"{self._paint(RED, f'Error [{code}]:')} {message}", file=sys.stderr)
        if next_steps:
            print("\n" + self._paint(BOLD, "To fix:"), file=sys.stderr)
            for step in next_steps:
                print(f"  - {step}", file=sys.stderr)

    def _render_data(self, data: dict[str, Any], indent: int = 0) -> None:
        """Recursively render a data payload in human-readable form."""
        prefix = "  " * indent
        for key, value in data.items():
            if key == "checks" and isinstance(value, list):
                self._render_checks(value, prefix)
            elif isinstance(value, dict):
                print(f"{prefix}{self._paint(BOLD, f'{key}:')}")
                self._render_data(value, indent + 1)
            elif isinstance(value, list):
                if value:
                    print(f"{prefix}{self._paint(BOLD, f'{key}:')}")
                    for item in value:
                        if isinstance(item, dict):
                            self._render_data(item, indent + 1)
                            print()
                        else:
                            print(f"{prefix}  - {item}")
            elif isinstance(value, bool):
                mark = self._paint(GREEN, _OK) if value else self._paint(RED, _FAIL)
                print(f"{prefix}{mark} {key}")
            else:
                print(f"{prefix}{key}: {value}")

    def _render_checks(self, checks: list[dict], prefix: str) -> None:
        """Render the health/status check list rhdh-local emits."""
        icons = {"pass": (GREEN, _OK), "warn": (YELLOW, _WARN)}
        for check in checks:
            color, glyph = icons.get(check.get("status", ""), (RED, _FAIL))
            label = check.get("name", "unknown")
            message = check.get("message", "")
            suffix = f": {message}" if message else ""
            print(f"{prefix}{self._paint(color, glyph)} {label}{suffix}")

    def header(self, text: str) -> None:
        """Print a section header (human mode only, ignored in JSON)."""
        self._log("\n" + self._paint(BOLD, text))

    def log_ok(self, message: str) -> None:
        """Log a success message (human mode only)."""
        self._log(f"  {self._paint(GREEN, _OK)} {message}")

    def log_warn(self, message: str) -> None:
        """Log a warning message (human mode only)."""
        self._log(f"  {self._paint(YELLOW, _WARN)} {message}")

    def log_fail(self, message: str) -> None:
        """Log a failure message (human mode only)."""
        self._log(f"  {self._paint(RED, _FAIL)} {message}")

    def log_info(self, message: str) -> None:
        """Log an info message (human mode only)."""
        self._log(f"  {self._paint(BLUE, _INFO)} {message}")

    def _log(self, line: str) -> None:
        if self.is_human:
            print(line)
            self._has_human_output = True
