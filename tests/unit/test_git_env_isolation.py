"""A test that creates a git repository must not be able to reach the checkout
pytest is running in.

A git hook exports GIT_DIR and friends. A `git init` that inherits them retargets
the hook's repository: it rewrites that repository's config (marking a normal
checkout core.bare=true) and points `git add` at the real index.
"""

from __future__ import annotations

import subprocess

from conftest import GIT_LOCAL_ENV_VARS, git_env


def test_location_vars_are_removed(monkeypatch):
    assert {"GIT_CONFIG", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"} <= set(GIT_LOCAL_ENV_VARS)
    for name in GIT_LOCAL_ENV_VARS:
        monkeypatch.setenv(name, "/somewhere/else")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "redirect.setting")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "inherited")

    env = git_env()

    assert not [name for name in GIT_LOCAL_ENV_VARS if name in env]
    assert "GIT_CONFIG_KEY_0" not in env
    assert "GIT_CONFIG_VALUE_0" not in env


def test_identity_vars_survive_because_they_do_not_redirect(monkeypatch):
    monkeypatch.setenv("GIT_DIR", "/somewhere/else")

    env = git_env(GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@test.com")

    assert env["GIT_AUTHOR_NAME"] == "test"
    assert env["GIT_AUTHOR_EMAIL"] == "test@test.com"
    assert "GIT_DIR" not in env


def test_overrides_are_applied(monkeypatch):
    monkeypatch.setenv("HOME", "/original")

    assert git_env(HOME="/replacement")["HOME"] == "/replacement"


def test_git_init_under_a_hook_environment_leaves_the_outer_repo_alone(tmp_path, monkeypatch):
    """The regression. Without git_env, this git init rewrites `outer`'s config."""
    outer = tmp_path / "outer"
    outer.mkdir()
    subprocess.run(["git", "init"], cwd=outer, check=True, capture_output=True, env=git_env())
    assert (
        subprocess.run(
            ["git", "config", "--get", "core.bare"],
            cwd=outer,
            capture_output=True,
            text=True,
            env=git_env(),
        ).stdout.strip()
        == "false"
    )

    # Stand where a git hook stands: GIT_DIR already points at another repository.
    monkeypatch.setenv("GIT_DIR", str(outer / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(outer))

    inner = tmp_path / "inner"
    inner.mkdir()
    subprocess.run(["git", "init"], cwd=inner, check=True, capture_output=True, env=git_env())

    assert (inner / ".git").is_dir(), "git init did not create a repository where it was asked to"
    still_bare = subprocess.run(
        ["git", "config", "--get", "core.bare"],
        cwd=outer,
        capture_output=True,
        text=True,
        env=git_env(),
    ).stdout.strip()
    assert still_bare == "false", "git init reached out of its cwd and rewrote the outer repository"


def test_dynamic_config_environment_does_not_reach_a_temporary_repo(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, env=git_env())

    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "redirect.setting")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "inherited")
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "'other.setting'='also-inherited'")

    result = subprocess.run(
        ["git", "config", "--get-regexp", r"^(redirect|other)\.setting$"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=git_env(),
    )

    assert result.returncode == 1
    assert result.stdout == ""
