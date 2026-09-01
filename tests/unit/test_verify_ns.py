"""Tests for rhdh-smoke-tests verify_ns.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "skills" / "release" / "rhdh-smoke-tests" / "scripts" / "verify_ns.sh"


def _cmd(*args: str) -> list[str]:
    if os.name == "nt":
        pytest.skip("bash required")
    return [str(SCRIPT), *args]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _cmd(*args),
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_exists() -> None:
    assert SCRIPT.is_file()


def test_script_uses_jq_not_python() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "python3" not in text
    assert "jq " in text


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage_and_exits_zero(flag: str) -> None:
    result = _run(flag)
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "--namespace" in result.stdout


def test_missing_namespace_exits_two() -> None:
    result = _run()
    assert result.returncode == 2
    assert "--namespace is required" in result.stderr


def test_unknown_option_exits_two() -> None:
    result = _run("--not-a-real-flag")
    assert result.returncode == 2
    assert "Unknown option" in result.stderr
