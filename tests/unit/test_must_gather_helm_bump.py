"""Tests for rhdh-must-gather-helm-bump skill script."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / "skills" / "rhdh-must-gather-helm-bump"
MAIN_SCRIPT = SKILL_DIR / "scripts" / "bump-must-gather-helm.sh"


class TestBumpMustGatherHelmScript:
    """Smoke tests for bump-must-gather-helm.sh."""

    def test_script_exists(self) -> None:
        assert MAIN_SCRIPT.is_file()

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_exits_zero(self, flag: str) -> None:
        result = subprocess.run(
            [str(MAIN_SCRIPT), flag],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout + result.stderr

    def test_missing_to_version_exits_nonzero(self) -> None:
        result = subprocess.run(
            [str(MAIN_SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "--to VERSION is required" in result.stderr

    def test_invalid_version_exits_nonzero(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        upstream.mkdir()
        (upstream / "Makefile").write_text("HELM_VERSION := 4.2.3\n", encoding="utf-8")
        (upstream / "collection-scripts").mkdir()
        (upstream / "hack").mkdir()
        (upstream / "hack" / "update-helm-lockfile.sh").write_text("#!/bin/bash\n", encoding="utf-8")

        result = subprocess.run(
            [
                str(MAIN_SCRIPT),
                "--to",
                "not-a-version",
                "--upstream",
                str(upstream),
                "--downstream",
                str(tmp_path / "downstream"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
        assert "Invalid Helm version" in result.stderr

    def test_check_mode_prints_mode(self, tmp_path: Path) -> None:
        parent = tmp_path / "RHDH"
        upstream = parent / "1-must-gather"
        downstream = parent / "4-rhdh"
        distgit = downstream / "distgit" / "containers" / "rhdh-must-gather"
        upstream.mkdir(parents=True)
        downstream.mkdir(parents=True)
        distgit.mkdir(parents=True)
        (upstream / "Makefile").write_text("HELM_VERSION := 4.2.3\n", encoding="utf-8")
        (upstream / "collection-scripts").mkdir()
        hack = upstream / "hack"
        hack.mkdir()
        check_script = hack / "check-helm-binary-available.sh"
        check_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        check_script.chmod(0o755)
        (hack / "update-helm-lockfile.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        (downstream / ".tekton").mkdir()
        (downstream / ".tekton" / "rhdh-must-gather-2-pull.yaml").write_text(
            "prefetch-input\n  value: '[]'\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                str(MAIN_SCRIPT),
                "--to",
                "4.2.3",
                "--check",
                "--parent-dir",
                str(parent),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "mode=cgw" in result.stdout
        assert "helm_version=4.2.3" in result.stdout
