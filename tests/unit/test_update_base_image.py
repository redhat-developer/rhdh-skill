"""Tests for update-base-image skill - bundled analyze-base-images.sh smoke behavior."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPDATE_BASE_IMAGE_DIR = PROJECT_ROOT / "skills" / "update-base-image"
ANALYZE_SCRIPT = UPDATE_BASE_IMAGE_DIR / "scripts" / "analyze-base-images.sh"

RHDH_ENV_VARS = ("RHDH_BUILD_SCRIPTS", "RHDH_REPO", "RHDH_OPERATOR_REPO")


def _clean_rhdh_env() -> dict[str, str]:
    """Return a copy of os.environ without update-base-image path overrides."""
    return {k: v for k, v in os.environ.items() if k not in RHDH_ENV_VARS}


def _run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = _clean_rhdh_env()
    if env:
        run_env.update(env)
    return subprocess.run(
        [str(ANALYZE_SCRIPT), *args],
        capture_output=True,
        text=True,
        env=run_env,
    )


class TestAnalyzeBaseImagesScript:
    """Smoke tests for the bundled Bash analyzer."""

    def test_script_exists(self) -> None:
        assert ANALYZE_SCRIPT.is_file()

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_prints_usage_and_exits_nonzero(self, flag: str) -> None:
        result = _run_script(flag)
        assert result.returncode != 0
        assert "Usage:" in result.stdout + result.stderr

    def test_unknown_option_exits_nonzero(self) -> None:
        result = _run_script("--not-a-real-flag")
        assert result.returncode != 0
        assert "Unknown option" in result.stderr

    def test_missing_workdirs_without_env_exits_nonzero(self) -> None:
        result = _run_script()
        assert result.returncode != 0
        assert "Set RHDH_REPO and RHDH_OPERATOR_REPO" in result.stderr

    def test_missing_build_scripts_dir_exits_nonzero(self, tmp_path: Path) -> None:
        result = _run_script(
            "-w",
            str(tmp_path),
            env={
                "RHDH_REPO": str(tmp_path / "rhdh"),
                "RHDH_OPERATOR_REPO": str(tmp_path / "operator"),
            },
        )
        assert result.returncode != 0
        assert "Set RHDH_BUILD_SCRIPTS" in result.stderr

    def test_missing_get_latest_script_exits_nonzero(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        result = _run_script(
            "-s",
            str(scripts_dir),
            "-w",
            str(repo_dir),
            env=_clean_rhdh_env(),
        )
        assert result.returncode != 0
        assert "getLatestImageTags.sh not found" in result.stderr

    @pytest.mark.skipif(shutil.which("skopeo") is None, reason="skopeo not installed")
    def test_missing_repo_dir_exits_nonzero(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "getLatestImageTags.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
        (scripts_dir / "getLatestImageTags.sh").chmod(0o755)

        result = _run_script(
            "-s",
            str(scripts_dir),
            "-w",
            str(tmp_path / "missing-repo"),
            env=_clean_rhdh_env(),
        )
        assert result.returncode != 0
        assert "Repo not found" in result.stderr

    @pytest.mark.skipif(shutil.which("skopeo") is None, reason="skopeo not installed")
    def test_no_containerfiles_found_exits_nonzero(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "getLatestImageTags.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
        (scripts_dir / "getLatestImageTags.sh").chmod(0o755)
        repo_dir = tmp_path / "empty-repo"
        repo_dir.mkdir()

        result = _run_script(
            "-s",
            str(scripts_dir),
            "-w",
            str(repo_dir),
            env=_clean_rhdh_env(),
        )
        assert result.returncode != 0
        assert "No Containerfiles or Dockerfiles found" in result.stdout + result.stderr
