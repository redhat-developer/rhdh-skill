"""Shared pytest fixtures for rhdh-skills tests."""

import json
import os
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Path to the project root
PROJECT_ROOT = Path(__file__).parent.parent

# Path to the context skill directory (where the preserved rhdh package lives)
RHDH_SKILL_DIR = PROJECT_ROOT / "skills" / "reference" / "rhdh-context"

# Add the context skill directory to path for testing
if str(RHDH_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(RHDH_SKILL_DIR))

# Path to the rhdh-local skill directory (where rhdh_local package lives)
RHDH_LOCAL_SKILL_DIR = PROJECT_ROOT / "skills" / "plugins" / "rhdh-local"

# Add rhdh-local skill directory to path for testing
if str(RHDH_LOCAL_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(RHDH_LOCAL_SKILL_DIR))

SCRIPTS_DIR = RHDH_SKILL_DIR / "scripts"
SKILLS_DIR = RHDH_SKILL_DIR  # Legacy alias
SKILL_DIR = RHDH_SKILL_DIR  # Legacy alias


@pytest.fixture
def skill_root():
    """Return the project root path."""
    return PROJECT_ROOT


@pytest.fixture
def skill_dir():
    """Return the context skill directory path."""
    return RHDH_SKILL_DIR


@pytest.fixture
def scripts_dir():
    """Return the scripts directory path."""
    return SCRIPTS_DIR


@pytest.fixture
def skills_dir():
    """Return the preserved CLI package directory."""
    return SKILLS_DIR


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Create an isolated environment with temp directories.

    Sets up:
    - Temporary data directory via RHDH_SKILLS_DATA_DIR env var
    - Temporary config directory (~/.config/rhdh-skills/)
    - Temporary project config directory (.rhdh/)
    - Isolated working directory
    - Mock HOME environment
    """
    # Create temp user config/data dir (matches config.py: .config/rhdh-skills)
    config_dir = tmp_path / ".config" / "rhdh-skills"
    config_dir.mkdir(parents=True)

    # Create temp project config dir
    project_config_dir = tmp_path / ".rhdh"
    project_config_dir.mkdir(parents=True)

    # Create a mock repo structure
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Create mock overlay repo
    overlay_dir = repo_dir / "rhdh-plugin-export-overlays"
    overlay_dir.mkdir()
    (overlay_dir / "versions.json").write_text('{"backstage": "1.45.0"}')
    (overlay_dir / "workspaces").mkdir()

    # Create a sample workspace
    sample_workspace = overlay_dir / "workspaces" / "test-plugin"
    sample_workspace.mkdir()
    (sample_workspace / "source.json").write_text(
        json.dumps(
            {
                "repo": "https://github.com/example/test-plugin",
                "repo-ref": "abc123",
                "repo-flat": False,
                "repo-backstage-version": "1.43.0",
            }
        )
    )
    (sample_workspace / "plugins-list.yaml").write_text("- plugins/test/frontend:\n")

    # Initialize as git repo
    subprocess.run(["git", "init"], cwd=overlay_dir, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=overlay_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=overlay_dir,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
        },
    )

    # Create mock rhdh-local
    local_dir = repo_dir / "rhdh-local"
    local_dir.mkdir()
    (local_dir / "compose.yaml").write_text("services:\n  rhdh:\n    image: rhdh\n")

    # Set HOME to temp dir so config goes there
    monkeypatch.setenv("HOME", str(tmp_path))

    # Set RHDH_SKILLS_DATA_DIR to isolate worklog/todo from user's real data
    monkeypatch.setenv("RHDH_SKILLS_DATA_DIR", str(config_dir))

    # Clear any existing env overrides
    monkeypatch.delenv("RHDH_OVERLAY_REPO", raising=False)
    monkeypatch.delenv("RHDH_LOCAL_REPO", raising=False)
    monkeypatch.delenv("RHDH_FACTORY_REPO", raising=False)
    monkeypatch.delenv("SKILL_ROOT", raising=False)

    yield {
        "root": tmp_path,
        "config_dir": config_dir,
        "project_config_dir": project_config_dir,
        "repo_dir": repo_dir,
        "overlay_dir": overlay_dir,
        "local_dir": local_dir,
    }


class CLIResult:
    """Result of running the CLI."""

    def __init__(self, returncode: int, stdout: str, stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def run_cli_python(*args, env=None, isolated_env=None):
    """Run the CLI directly in Python (no subprocess).

    Args:
        *args: CLI arguments
        env: Environment variables to set
        isolated_env: isolated_env fixture dict (for HOME path)

    Returns:
        CLIResult with returncode, stdout, stderr
    """
    # Import here to avoid circular imports and ensure fresh module state
    from rhdh import config as config_module
    from rhdh.cli import main

    # Capture stdout
    stdout_capture = StringIO()

    # Set up environment
    env_patches = {}
    if env:
        env_patches.update(env)

    # Patch config paths to isolated environment
    if isolated_env:
        new_home = Path(isolated_env["root"])
        # Patch user config paths
        config_module.USER_CONFIG_DIR = new_home / ".config" / "rhdh-skills"
        config_module.USER_CONFIG_FILE = config_module.USER_CONFIG_DIR / "config.json"

    # Mock find_git_root to return isolated dir (prevents writes to real project)
    mock_git_root = Path(isolated_env["root"]) if isolated_env else None

    with patch.dict(os.environ, env_patches, clear=False):
        with patch("sys.stdout", stdout_capture):
            # Patch find_git_root if we have an isolated env
            if mock_git_root:
                with patch.object(config_module, "find_git_root", return_value=mock_git_root):
                    try:
                        returncode = main(list(args))
                    except SystemExit as e:
                        returncode = e.code if isinstance(e.code, int) else 0
            else:
                try:
                    returncode = main(list(args))
                except SystemExit as e:
                    returncode = e.code if isinstance(e.code, int) else 0

    return CLIResult(returncode, stdout_capture.getvalue())


@pytest.fixture
def cli(isolated_env):
    """Fixture providing the run_cli function configured for the isolated env."""

    def _run_cli(*args, env=None):
        # Merge env with any existing overrides
        full_env = {}
        if env:
            full_env.update(env)
        return run_cli_python(*args, env=full_env, isolated_env=isolated_env)

    return _run_cli


@pytest.fixture
def unconfigured_cli(isolated_env, monkeypatch):
    """Fixture providing CLI with no repos configured.

    Use this to test the "needs setup" state without manual monkeypatching.
    Mocks get_repo to return None for all repos.
    """
    from rhdh import cli as cli_module

    monkeypatch.setattr(cli_module, "get_repo", lambda key: None)

    def _run_cli(*args, env=None):
        full_env = {}
        if env:
            full_env.update(env)
        return run_cli_python(*args, env=full_env, isolated_env=isolated_env)

    return _run_cli


# Legacy fixture for subprocess-based testing (kept for backward compatibility)
def run_cli_subprocess(*args, cwd=None, env=None):
    """Run the rhdh CLI via subprocess and return result.

    Args:
        *args: CLI arguments
        cwd: Working directory
        env: Environment variables (merged with current env)

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    script_path = SCRIPTS_DIR / "rhdh"

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    result = subprocess.run(
        [str(script_path), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=run_env,
    )

    return CLIResult(result.returncode, result.stdout, result.stderr)
