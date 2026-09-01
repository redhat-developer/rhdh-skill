"""Tests for rhdh-smoke-tests operator_upgrade.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    PROJECT_ROOT / "skills" / "release" / "rhdh-smoke-tests" / "scripts" / "operator_upgrade.sh"
)


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
    assert "--channel" in result.stdout


def test_missing_channel_exits_two() -> None:
    result = _run()
    assert result.returncode == 2
    assert "--channel is required" in result.stderr


def test_unknown_option_exits_two() -> None:
    result = _run("--not-a-real-flag")
    assert result.returncode == 2
    assert "Unknown option" in result.stderr


def test_dry_run_prints_patch_and_skips_oc() -> None:
    result = _run(
        "--dry-run",
        "--json",
        "--channel",
        "fast-1.10",
        "--starting-csv",
        "rhdh-operator.v1.10.4",
    )
    assert result.returncode == 0
    assert "patch subscription rhdh" in result.stdout
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["dryRun"] is True
    assert payload["channel"] == "fast-1.10"
    assert payload["startingCSV"] == "rhdh-operator.v1.10.4"
