"""Unit tests for skills/backport/scripts/backport.py."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKPORT_SCRIPTS = PROJECT_ROOT / "skills" / "plugins" / "rhdh-backport" / "scripts"
if str(_BACKPORT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BACKPORT_SCRIPTS))

import backport  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> backport.BackportState:
    defaults = dict(
        release="1.10",
        pr_num=3456,
        plugin="orchestrator",
        release_branch="release-1.10/orchestrator",
        backport_branch="backport/3456-to-release-1.10",
        overlays_branch="release-1.10",
        repo="redhat-developer/rhdh-plugins",
        overlays_repo="redhat-developer/rhdh-plugin-export-overlays",
    )
    defaults.update(kwargs)
    return backport.BackportState(**defaults)


def _completed_process(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


# ---------------------------------------------------------------------------
# Yarn.lock-only detection in step2
# ---------------------------------------------------------------------------


class TestYarnLockOnlyDetection:
    def test_yarn_lock_only_sets_flag(self):
        state = _make_state(
            files=[
                "workspaces/orchestrator/yarn.lock",
                "workspaces/orchestrator/plugins/orchestrator/yarn.lock",
            ],
        )
        with patch.object(backport, "run_git") as mock_git:
            mock_git.return_value = _completed_process(stdout="abc123 refs/heads/release-1.10/orchestrator")
            backport.step2_detect_plugin(state)

        assert state.yarn_lock_only is True

    def test_mixed_files_no_flag(self):
        state = _make_state(
            files=[
                "workspaces/orchestrator/yarn.lock",
                "workspaces/orchestrator/plugins/orchestrator/src/index.ts",
            ],
        )
        with patch.object(backport, "run_git") as mock_git:
            mock_git.return_value = _completed_process(stdout="abc123 refs/heads/release-1.10/orchestrator")
            backport.step2_detect_plugin(state)

        assert state.yarn_lock_only is False

    def test_no_yarn_lock_no_flag(self):
        state = _make_state(
            files=[
                "workspaces/orchestrator/plugins/orchestrator/src/index.ts",
            ],
        )
        with patch.object(backport, "run_git") as mock_git:
            mock_git.return_value = _completed_process(stdout="abc123 refs/heads/release-1.10/orchestrator")
            backport.step2_detect_plugin(state)

        assert state.yarn_lock_only is False


# ---------------------------------------------------------------------------
# Step 7 — VP skip for yarn.lock-only
# ---------------------------------------------------------------------------


class TestStep7YarnLockOnlySkip:
    def test_skips_vp_when_yarn_lock_only(self):
        state = _make_state(yarn_lock_only=True)

        with patch.object(backport, "run_git") as mock_git:
            mock_git.return_value = _completed_process(stdout="abc123def456")
            backport.step7_detect_version_packages(state)

        assert state.vp_commit == "abc123def456"
        assert state.vp_version == "n/a (yarn.lock-only)"
        assert state.vp_pr_num == 0

    def test_calls_cleanup_when_not_yarn_lock_only(self):
        state = _make_state(yarn_lock_only=False)

        with (
            patch.object(backport, "cleanup_stale_vp_branch") as mock_cleanup,
            patch.object(backport, "run_gh_json") as mock_gh_json,
            patch.object(backport, "poll_for_vp_creation", return_value=100),
            patch.object(backport, "poll_ci"),
            patch.object(backport, "merge_pr"),
            patch.object(backport, "wait_for_merged"),
            patch("time.sleep"),
        ):
            mock_gh_json.side_effect = [
                None,
                {"title": "Version Packages (orchestrator)", "baseRefName": "release-1.10/orchestrator"},
                {"mergeCommit": {"oid": "deadbeef"}, "body": "@redhat-developer/orchestrator@5.7.15"},
            ]
            backport.step7_detect_version_packages(state)

        mock_cleanup.assert_called_once_with(state)


# ---------------------------------------------------------------------------
# Step 9 — Changelog skip for yarn.lock-only
# ---------------------------------------------------------------------------


class TestStep9YarnLockOnlySkip:
    def test_skips_changelog_when_yarn_lock_only(self):
        state = _make_state(yarn_lock_only=True)

        with patch.object(backport, "run_git") as mock_git:
            backport.step9_changelog_pr(state)

        mock_git.assert_not_called()
        assert state.changelog_pr_num == 0


# ---------------------------------------------------------------------------
# Stale maintenance-changesets-release branch cleanup
# ---------------------------------------------------------------------------


class TestCleanupStaleVpBranch:
    def test_deletes_stale_branch(self):
        state = _make_state()

        with (
            patch.object(backport, "run_git") as mock_git,
            patch.object(backport, "run_gh") as mock_gh,
        ):
            mock_git.return_value = _completed_process(
                stdout="abc123 refs/heads/maintenance-changesets-release/release-1.10/orchestrator"
            )
            backport.cleanup_stale_vp_branch(state)

        mock_gh.assert_called_once()
        api_call = mock_gh.call_args
        assert "DELETE" in api_call[0][0]
        assert "maintenance-changesets-release/release-1.10/orchestrator" in api_call[0][0][-1]

    def test_no_delete_when_branch_missing(self):
        state = _make_state()

        with (
            patch.object(backport, "run_git") as mock_git,
            patch.object(backport, "run_gh") as mock_gh,
        ):
            mock_git.return_value = _completed_process(stdout="")
            backport.cleanup_stale_vp_branch(state)

        mock_gh.assert_not_called()


# ---------------------------------------------------------------------------
# State serialization — yarn_lock_only roundtrip
# ---------------------------------------------------------------------------


class TestStateSerialization:
    def test_yarn_lock_only_persists(self, tmp_path):
        state = _make_state(yarn_lock_only=True)
        path = tmp_path / "state.json"
        state.save(path)

        loaded = backport.BackportState.load(path)
        assert loaded.yarn_lock_only is True

    def test_yarn_lock_only_defaults_false(self, tmp_path):
        state = _make_state()
        path = tmp_path / "state.json"
        state.save(path)

        loaded = backport.BackportState.load(path)
        assert loaded.yarn_lock_only is False


# ---------------------------------------------------------------------------
# PR source parsing (existing logic, basic coverage)
# ---------------------------------------------------------------------------


class TestParsePrSource:
    def test_number(self):
        assert backport.parse_pr_source("3456") == (3456, None)

    def test_hash_number(self):
        assert backport.parse_pr_source("#3456") == (3456, None)

    def test_url(self):
        pr_num, sha = backport.parse_pr_source(
            "https://github.com/redhat-developer/rhdh-plugins/pull/3456"
        )
        assert pr_num == 3456
        assert sha is None

    def test_commit_sha(self):
        pr_num, sha = backport.parse_pr_source("abc123f")
        assert pr_num is None
        assert sha == "abc123f"

    def test_invalid_exits(self):
        with pytest.raises(SystemExit):
            backport.parse_pr_source("not-valid!")
