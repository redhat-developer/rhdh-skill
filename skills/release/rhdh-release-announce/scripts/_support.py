"""Output formatting and Atlassian CLI discovery for the release CLI.

Bundled with this skill so it runs installed alone. A sibling skill
carrying something similar is expected, not a defect.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from collections.abc import Callable


def find_acli() -> Optional[str]:
    """Return the path to the Atlassian CLI, or None.

    PATH wins; the extra candidates cover Windows installers that do not
    amend PATH.
    """
    on_path = shutil.which("acli")
    if on_path:
        return on_path
    home = Path.home()
    for candidate in (
        home / ".path" / "acli.exe",
        home / "AppData" / "Local" / "acli" / "acli.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


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


@dataclass
class OutputFormatter:
    """Formats CLI output as JSON or human-readable.

    In human mode, commands use log_ok/log_warn/log_fail for inline output,
    then call success() just for next_steps. In JSON mode, success() outputs
    the full structured response.

    Attributes:
        mode: "human" for colored text, "json" for machine-parseable output
        verbose: Include debug information
    """

    mode: str = "auto"  # "auto", "human", or "json"
    verbose: bool = False
    _debug_info: dict[str, Any] = field(default_factory=dict)
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

    def add_debug(self, key: str, value: Any) -> None:
        """Add debug information (included if verbose=True)."""
        self._debug_info[key] = value

    # =========================================================================
    # Success Output
    # =========================================================================

    def success(
        self,
        data: dict[str, Any],
        next_steps: list[str] | None = None,
    ) -> None:
        """Output a success response."""
        if self.is_human:
            self._render_human_success(data, next_steps)
        else:
            self._render_json_success(data, next_steps)

    def _render_json_success(
        self,
        data: dict[str, Any],
        next_steps: list[str] | None,
    ) -> None:
        """Render success as JSON."""
        response = {
            "success": True,
            "data": data,
        }
        if next_steps:
            response["next_steps"] = next_steps
        if self.verbose and self._debug_info:
            response["debug"] = self._debug_info
        print(json.dumps(response, indent=2, default=str))

    def _render_human_success(
        self,
        data: dict[str, Any],
        next_steps: list[str] | None,
    ) -> None:
        """Render success as human-readable text.

        If log_* methods were used, skip data rendering (already shown inline).
        Only render next_steps.
        """
        if not self._has_human_output:
            # No inline output was done, render the data
            self._render_data(data)

        if next_steps:
            print(f"\n{self._paint(BOLD, 'Next steps:')}")
            for step in next_steps:
                print(f"  {self._paint(BLUE, step)}")

    def _render_data(self, data: dict[str, Any], indent: int = 0) -> None:
        """Recursively render data in human-readable format."""
        prefix = "  " * indent

        for key, value in data.items():
            if key == "checks" and isinstance(value, list):
                self._render_checks(value, prefix)
            elif key == "items" and isinstance(value, list):
                self._render_items(value, prefix)
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
                icon = self._paint(GREEN, "✓") if value else self._paint(RED, "✗")
                print(f"{prefix}{icon} {key}")
            else:
                print(f"{prefix}{key}: {value}")

    def _render_checks(self, checks: list[dict], prefix: str) -> None:
        """Render a list of check results."""
        for check in checks:
            status = check.get("status", "unknown")
            name = check.get("name", "unknown")
            message = check.get("message", "")

            if status == "pass":
                icon = self._paint(GREEN, "✓")
            elif status == "warn":
                icon = self._paint(YELLOW, "⚠")
            else:
                icon = self._paint(RED, "✗")

            if message:
                print(f"{prefix}{icon} {name}: {message}")
            else:
                print(f"{prefix}{icon} {name}")

    def _render_items(self, items: list[dict], prefix: str) -> None:
        """Render a list of items (workspaces, etc.)."""
        for item in items:
            name = item.get("name", "unknown")
            detail = item.get("detail", "")
            print(f"{prefix}  {self._paint(BLUE, f'{name:<30}')} {detail}")

    # =========================================================================
    # Error Output
    # =========================================================================

    def error(
        self,
        code: str,
        message: str,
        next_steps: list[str] | None = None,
    ) -> None:
        """Output an error response."""
        if self.is_human:
            self._render_human_error(code, message, next_steps)
        else:
            self._render_json_error(code, message, next_steps)

    def _render_json_error(
        self,
        code: str,
        message: str,
        next_steps: list[str] | None,
    ) -> None:
        """Render error as JSON."""
        response = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if next_steps:
            response["next_steps"] = next_steps
        if self.verbose and self._debug_info:
            response["debug"] = self._debug_info
        print(json.dumps(response, indent=2))

    def _render_human_error(
        self,
        code: str,
        message: str,
        next_steps: list[str] | None,
    ) -> None:
        """Render error as human-readable text, entirely on stderr."""
        print(f"{self._paint(RED, f'Error [{code}]:')} {message}", file=sys.stderr)

        if next_steps:
            print(f"\n{self._paint(BOLD, 'To fix:')}", file=sys.stderr)
            for step in next_steps:
                print(f"  - {step}", file=sys.stderr)

    # =========================================================================
    # Convenience Methods (human-style logging)
    # =========================================================================

    def header(self, text: str) -> None:
        """Print a section header (human mode only, ignored in JSON)."""
        if self.is_human:
            print(f"\n{self._paint(BOLD, text)}")
            self._has_human_output = True

    def log_ok(self, message: str) -> None:
        """Log success message (human mode only)."""
        if self.is_human:
            print(f"  {self._paint(GREEN, '✓')} {message}")
            self._has_human_output = True

    def log_warn(self, message: str) -> None:
        """Log warning message (human mode only)."""
        if self.is_human:
            print(f"  {self._paint(YELLOW, '⚠')} {message}")
            self._has_human_output = True

    def log_fail(self, message: str) -> None:
        """Log failure message (human mode only)."""
        if self.is_human:
            print(f"  {self._paint(RED, '✗')} {message}")
            self._has_human_output = True

    def log_info(self, message: str) -> None:
        """Log info message (human mode only)."""
        if self.is_human:
            print(f"  {self._paint(BLUE, '→')} {message}")
            self._has_human_output = True

    # =========================================================================
    # Rendering Methods (human mode only, ignored in JSON)
    # =========================================================================

    def render_list(
        self,
        items: list[dict],
        format_fn: Callable[[dict], str],
        *,
        summary: str | None = None,
    ) -> None:
        """Render a list of items (human mode only, ignored in JSON).

        Args:
            items: List of item dicts to render
            format_fn: Function that takes an item dict and returns formatted string
            summary: Optional summary line (e.g., "Total: 5 items")
        """
        if not self.is_human:
            return

        print()
        for item in items:
            print(f"  {format_fn(item)}")
        if summary:
            print()
            print(f"  {summary}")
        self._has_human_output = True

    def render_banner(
        self,
        message: str,
        call_to_action: str | None = None,
        style: str = "warn",
    ) -> None:
        """Render a call-to-action banner (human mode only, ignored in JSON).

        Args:
            message: Main message text
            call_to_action: Optional command to show
            style: "warn" (yellow) or "info" (blue)
        """
        if not self.is_human:
            return

        color = YELLOW if style == "warn" else BLUE
        print()
        print(self._paint(color, message))
        if call_to_action:
            print(f"  {call_to_action}")
        self._has_human_output = True

    def render_raw(self, content: str) -> None:
        """Render raw content (human mode only, ignored in JSON)."""
        if not self.is_human:
            return

        print(content)
        self._has_human_output = True
