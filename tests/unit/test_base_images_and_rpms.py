"""Tests for the rhdh-base-images shell interfaces."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / "skills" / "ci" / "rhdh-base-images"
ANALYZE_SCRIPT = SKILL_DIR / "scripts" / "analyze-base-images.sh"
MAIN_SCRIPT = SKILL_DIR / "scripts" / "base-images-and-rpms.sh"

RHDH_ENV_VARS = ("RHDH_BUILD_SCRIPTS", "RHDH_REPO", "RHDH_OPERATOR_REPO")


def _clean_rhdh_env() -> dict[str, str]:
    """Return a copy of os.environ without base-images path overrides."""
    return {k: v for k, v in os.environ.items() if k not in RHDH_ENV_VARS}


def _shell_script_cmd(script: Path, *args: str) -> list[str]:
    """Build argv to run a .sh script (via bash on Windows)."""
    if os.name == "nt":
        wsl = shutil.which("wsl")
        if wsl is None:
            pytest.skip("WSL bash required to run .sh scripts on Windows")
        converted_script = subprocess.run(
            [wsl, "wslpath", "-u", script.as_posix()],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        converted_args = []
        for arg in args:
            if len(arg) >= 3 and arg[1:3] == ":\\":
                arg = subprocess.run(
                    [wsl, "wslpath", "-u", arg.replace("\\", "/")],
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
            converted_args.append(arg)
        return [wsl, "bash", converted_script, *converted_args]
    return [str(script), *args]


def _run_analyze(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = _clean_rhdh_env()
    if env:
        run_env.update(env)
    return subprocess.run(
        _shell_script_cmd(ANALYZE_SCRIPT, *args),
        capture_output=True,
        text=True,
        env=run_env,
    )


class TestAnalyzeBaseImagesScript:
    """Smoke tests for the bundled Bash analyzer."""

    def test_script_exists(self) -> None:
        assert ANALYZE_SCRIPT.is_file()

    @pytest.mark.parametrize("flag", ["--help", "-h"])
    def test_help_prints_usage_and_exits_zero(self, flag: str) -> None:
        result = _run_analyze(flag)
        assert result.returncode == 0
        assert "Usage:" in result.stdout + result.stderr

    def test_unknown_option_exits_nonzero(self) -> None:
        result = _run_analyze("--not-a-real-flag")
        assert result.returncode != 0
        assert "Unknown option" in result.stderr

    def test_missing_workdirs_without_env_exits_nonzero(self) -> None:
        result = _run_analyze()
        assert result.returncode != 0
        assert "Set RHDH_REPO and RHDH_OPERATOR_REPO" in result.stderr

    def test_missing_build_scripts_dir_exits_nonzero(self, tmp_path: Path) -> None:
        result = _run_analyze(
            "-w",
            str(tmp_path),
            env={
                "RHDH_REPO": str(tmp_path / "rhdh"),
                "RHDH_OPERATOR_REPO": str(tmp_path / "operator"),
            },
        )
        assert result.returncode != 0
        assert "Set RHDH_BUILD_SCRIPTS" in result.stderr

    @pytest.mark.skipif(shutil.which("skopeo") is None, reason="skopeo not installed")
    def test_missing_get_latest_script_exits_nonzero(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        result = _run_analyze(
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

        result = _run_analyze(
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

        result = _run_analyze(
            "-s",
            str(scripts_dir),
            "-w",
            str(repo_dir),
            env=_clean_rhdh_env(),
        )
        assert result.returncode != 0
        assert "No Containerfiles or Dockerfiles found" in result.stdout + result.stderr

    @staticmethod
    def _setup_mock_glit(scripts_dir: Path, output: str) -> None:
        glit = scripts_dir / "getLatestImageTags.sh"
        glit.write_text(
            f"#!/usr/bin/env bash\ncat <<'EOF'\n{output.rstrip()}\nEOF\n",
        )
        glit.chmod(0o755)

    @staticmethod
    def _write_containerfile(repo_dir: Path, tag: str) -> Path:
        cf = repo_dir / "Containerfile"
        cf.write_text(
            "# https://registry.access.redhat.com/ubi9/nodejs-24\n"
            f"FROM registry.access.redhat.com/ubi9/nodejs-24:{tag}@sha256:abc AS skeleton\n"
        )
        return cf

    @pytest.mark.skipif(shutil.which("skopeo") is None, reason="skopeo not installed")
    def test_well_formed_latest_tag_selected(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        self._setup_mock_glit(
            scripts_dir,
            "registry.access.redhat.com/ubi9/nodejs-24:1780432632\n"
            "registry.access.redhat.com/ubi9/nodejs-24:9.8-1780434037",
        )
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        self._write_containerfile(repo_dir, "9.8-1780430000")

        result = _run_analyze(
            "-s",
            str(scripts_dir),
            "-w",
            str(repo_dir),
            str(repo_dir / "Containerfile"),
            env=_clean_rhdh_env(),
        )
        assert result.returncode == 0
        assert "latest:  9.8-1780434037" in result.stdout
        assert "UPDATE AVAILABLE" in result.stdout

    @pytest.mark.skipif(shutil.which("skopeo") is None, reason="skopeo not installed")
    def test_bare_numeric_current_tag_warns_and_skips(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        self._setup_mock_glit(
            scripts_dir,
            "registry.access.redhat.com/ubi9/nodejs-24:9.8-1780434037",
        )
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        self._write_containerfile(repo_dir, "1780432632")

        result = _run_analyze(
            "-s",
            str(scripts_dir),
            "-w",
            str(repo_dir),
            str(repo_dir / "Containerfile"),
            env=_clean_rhdh_env(),
        )
        assert result.returncode == 0
        assert "warning: current tag is not well-formed" in result.stdout
        assert "SKIPPED (malformed current tag" in result.stdout

    @pytest.mark.skipif(shutil.which("skopeo") is None, reason="skopeo not installed")
    def test_no_well_formed_latest_skips_update(self, tmp_path: Path) -> None:
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        self._setup_mock_glit(
            scripts_dir,
            "registry.access.redhat.com/ubi9/nodejs-24:1780432632\n"
            "registry.access.redhat.com/ubi9/nodejs-24:1780439999",
        )
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        self._write_containerfile(repo_dir, "9.8-1780430000")

        result = _run_analyze(
            "-s",
            str(scripts_dir),
            "-w",
            str(repo_dir),
            str(repo_dir / "Containerfile"),
            env=_clean_rhdh_env(),
        )
        assert result.returncode == 0
        assert "no well-formed x.y-z or x.y.z-z tag" in result.stdout
        assert "SKIPPED (no well-formed tag" in result.stdout


class TestBaseImagesAndRpmsScript:
    """Smoke tests for the orchestrator --analyze flag."""

    def test_main_script_help_lists_analyze(self) -> None:
        result = subprocess.run(
            _shell_script_cmd(MAIN_SCRIPT, "--help"),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "--analyze" in result.stdout
