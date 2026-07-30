#!/usr/bin/env python3
"""RHDH plugin backport automation.

Cherry-picks changes to release branches, creates sequential PRs,
handles Version Packages, updates overlays, and creates changelog PRs.

Usage:
    python scripts/backport.py 1.10 3456
    python scripts/backport.py 1.10 3456 --mode create
    python scripts/backport.py 1.10 3456 --mode finish
    python scripts/backport.py 1.10 3456 --continue-from /tmp/backport-state-3456.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

DEFAULT_REPO = "redhat-developer/rhdh-plugins"
DEFAULT_OVERLAYS_REPO = "redhat-developer/rhdh-plugin-export-overlays"

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_CONFLICT = 2


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def log_step(n: int, title: str) -> None:
    log(f"\n{'=' * 16} Step {n} — {title} {'=' * 16}")


def die(msg: str, code: int = EXIT_FAILURE) -> None:
    log(f"Error: {msg}")
    sys.exit(code)


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def run_gh(
    args: list[str],
    *,
    check: bool = True,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        die("gh CLI not found. Install from https://cli.github.com/")
    except subprocess.TimeoutExpired:
        die(f"gh command timed out ({timeout}s): {' '.join(cmd)}")
    if check and result.returncode != 0:
        die(f"gh failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result


def run_gh_json(args: list[str], **kwargs) -> dict | list | None:
    result = run_gh(args, **kwargs)
    stdout = result.stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        die(f"Failed to parse JSON from: {' '.join(['gh'] + args)}\n{stdout[:200]}")
        return None


def run_git(
    args: list[str],
    *,
    check: bool = True,
    cwd: str | Path | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
    except FileNotFoundError:
        die("git not found.")
    except subprocess.TimeoutExpired:
        die(f"git command timed out ({timeout}s): {' '.join(cmd)}")
    if check and result.returncode != 0:
        die(f"git failed: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class BackportState:
    release: str = ""
    pr_num: int = 0
    repo: str = DEFAULT_REPO
    overlays_repo: str = DEFAULT_OVERLAYS_REPO
    mode: str = "auto"

    commit_sha: str = ""
    pr_title: str = ""
    pr_url: str = ""
    files: list[str] = field(default_factory=list)

    plugin: str = ""
    release_branch: str = ""
    workspace_branch: str = ""
    backport_branch: str = ""
    overlays_branch: str = ""

    reset_commit: str = ""
    overlays_dir: str = ""

    conflict_files: list[str] = field(default_factory=list)

    fork_owner: str = ""
    pr1_num: int = 0
    pr2_num: int = 0

    vp_pr_num: int = 0
    vp_commit: str = ""
    vp_version: str = ""

    overlays_pr_num: int = 0
    changelog_pr_num: int = 0

    completed_steps: list[int] = field(default_factory=list)

    def save(self, path: str | Path) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        log(f"STATE_FILE={path}")

    @classmethod
    def load(cls, path: str | Path) -> BackportState:
        with open(path) as f:
            data = json.load(f)
        state = cls()
        for k, v in data.items():
            if hasattr(state, k):
                setattr(state, k, v)
        return state


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RHDH plugin backport automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
    %(prog)s 1.10 3456
    %(prog)s 1.10 3456 --mode create
    %(prog)s 1.10 3456 --mode finish
    %(prog)s 1.10 3456 --continue-from /tmp/backport-state-3456.json
""",
    )
    parser.add_argument("release", help="Target release version (e.g. 1.10)")
    parser.add_argument("pr_source", help="PR number, URL, #N, or commit SHA")
    parser.add_argument(
        "--mode",
        choices=["auto", "create", "finish"],
        default="auto",
        help="auto: full workflow, create: steps 1-8, finish: steps 9-13",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--overlays-repo", default=DEFAULT_OVERLAYS_REPO)
    parser.add_argument(
        "--auto-approve", action="store_true", help="Skip confirmation prompts",
    )
    parser.add_argument(
        "--continue-from",
        dest="continue_from",
        metavar="STATE_JSON",
        help="Resume after conflict resolution",
    )
    parser.add_argument(
        "--force", action="store_true", help="Skip already-backported check",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="JSON output",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# PR source parsing
# ---------------------------------------------------------------------------

def parse_pr_source(pr_source: str) -> tuple[int | None, str | None]:
    if re.fullmatch(r"\d+", pr_source):
        return int(pr_source), None
    m = re.fullmatch(r"#(\d+)", pr_source)
    if m:
        return int(m.group(1)), None
    m = re.search(r"github\.com/[^/]+/[^/]+/pull/(\d+)", pr_source)
    if m:
        return int(m.group(1)), None
    if re.fullmatch(r"[a-f0-9]{7,40}", pr_source):
        return None, pr_source
    die(
        f"Invalid PR source: {pr_source}\n"
        "Expected: PR number, URL, #N, or commit SHA"
    )
    return None, None


# ---------------------------------------------------------------------------
# Step 1 — Fetch PR details
# ---------------------------------------------------------------------------

def step1_fetch_pr(state: BackportState) -> None:
    log_step(1, "Parse arguments and fetch PR details")

    if not state.pr_num and not state.commit_sha:
        die("No PR number or commit SHA available")

    if state.commit_sha and not state.pr_num:
        log(f"Looking up PR for commit {state.commit_sha}...")
        result = run_gh_json(
            [
                "pr", "list", "--repo", state.repo,
                "--search", state.commit_sha,
                "--state", "merged",
                "--json", "number",
                "--jq", ".[0].number",
            ],
            check=False,
        )
        if result:
            state.pr_num = int(result) if isinstance(result, (int, float)) else 0

        if not state.pr_num:
            die(f"Could not find merged PR for commit {state.commit_sha}")

    log(f"Fetching PR #{state.pr_num}...")
    pr_data = run_gh_json([
        "pr", "view", str(state.pr_num),
        "--repo", state.repo,
        "--json", "files,mergeCommit,title,url,state,baseRefName",
    ])
    if not pr_data:
        die(f"PR #{state.pr_num} not found")

    if pr_data["state"] != "MERGED":
        die(f"PR #{state.pr_num} is not merged (state: {pr_data['state']})")

    if pr_data["baseRefName"] != "main":
        log(f"Warning: PR #{state.pr_num} targets '{pr_data['baseRefName']}', not main")

    state.commit_sha = pr_data["mergeCommit"]["oid"]
    state.pr_title = pr_data["title"]
    state.pr_url = pr_data["url"]
    state.files = [f["path"] for f in pr_data.get("files", [])]

    log(f"  PR: #{state.pr_num} — {state.pr_title}")
    log(f"  Commit: {state.commit_sha[:10]}")
    log(f"  Files: {len(state.files)}")


# ---------------------------------------------------------------------------
# Step 2 — Detect plugin
# ---------------------------------------------------------------------------

def step2_detect_plugin(state: BackportState) -> None:
    log_step(2, "Auto-detect plugin from PR files")

    plugins: set[str] = set()
    for f in state.files:
        parts = f.split("/")
        if len(parts) >= 2 and parts[0] == "workspaces":
            plugins.add(parts[1])

    if not plugins:
        die(
            f"No workspace files found in PR #{state.pr_num}.\n"
            f"Files: {', '.join(state.files[:10])}"
        )

    if len(plugins) > 1:
        die(
            f"Multiple plugins detected: {', '.join(sorted(plugins))}\n"
            "Backport each plugin separately."
        )

    state.plugin = plugins.pop()
    state.release_branch = f"{state.plugin}/release-{state.release}"
    state.workspace_branch = f"workspace/{state.plugin}"
    state.backport_branch = f"backport/{state.pr_num}-to-release-{state.release}"
    state.overlays_branch = f"release-{state.release}"

    log(f"  Plugin: {state.plugin}")
    log(f"  Release branch: {state.release_branch}")
    log(f"  Workspace branch: {state.workspace_branch}")

    result = run_git(
        ["ls-remote", "--heads", "upstream", f"refs/heads/{state.release_branch}"],
        check=False,
    )
    if not result.stdout.strip():
        die(
            f"Release branch '{state.release_branch}' does not exist.\n"
            f"Create it first or check the release version."
        )


# ---------------------------------------------------------------------------
# Step 3 — Check if already backported
# ---------------------------------------------------------------------------

def step3_check_backported(state: BackportState, *, force: bool = False) -> None:
    log_step(3, "Check if already backported")

    run_git(["fetch", "upstream"])

    result = run_git(
        ["branch", "-r", "--contains", state.commit_sha],
        check=False,
    )
    branches = result.stdout.strip()

    for branch in (state.release_branch, state.workspace_branch):
        if f"upstream/{branch}" in branches:
            if force:
                log(f"  Warning: {state.commit_sha[:10]} already in {branch} (--force, continuing)")
            else:
                log(f"  Commit {state.commit_sha[:10]} already exists in {branch}")
                log("  Nothing to backport. Use --force to override.")
                sys.exit(EXIT_SUCCESS)
            return

    log(f"  Commit {state.commit_sha[:10]} not yet backported — proceeding")


# ---------------------------------------------------------------------------
# Step 4 — Reset workspace branch to overlays baseline
# ---------------------------------------------------------------------------

def step4_reset_workspace(state: BackportState) -> None:
    log_step(4, "Reset workspace branch to overlays baseline")

    state.overlays_dir = tempfile.mkdtemp(prefix=f"overlays-{state.release}-")
    log(f"  Cloning overlays repo to {state.overlays_dir}...")

    run_gh(
        ["repo", "clone", state.overlays_repo, state.overlays_dir, "--", "-b", state.overlays_branch],
        timeout=120,
    )

    source_path = Path(state.overlays_dir) / "workspaces" / state.plugin / "source.json"
    if not source_path.exists():
        die(f"source.json not found: {source_path}")

    with open(source_path) as f:
        source_data = json.load(f)

    state.reset_commit = source_data.get("repo-ref", "")
    if not state.reset_commit:
        die(f"repo-ref is empty in {source_path}")

    log(f"  Baseline commit from overlays: {state.reset_commit[:10]}")

    result = run_git(["cat-file", "-t", state.reset_commit], check=False)
    if result.returncode != 0:
        log("  Baseline commit not found locally, fetching...")
        run_git(["fetch", "upstream"])
        result = run_git(["cat-file", "-t", state.reset_commit], check=False)
        if result.returncode != 0:
            die(f"Baseline commit {state.reset_commit} not found in local repo")

    run_git(["checkout", state.workspace_branch])
    run_git(["reset", "--hard", state.reset_commit])
    run_git(["push", "upstream", state.workspace_branch, "--force"])

    log(f"  Reset {state.workspace_branch} to {state.reset_commit[:10]}")


# ---------------------------------------------------------------------------
# Step 5 — Cherry-pick
# ---------------------------------------------------------------------------

def step5_cherry_pick(state: BackportState) -> None:
    log_step(5, "Create local branch and cherry-pick")

    run_git(["fetch", "upstream"])
    run_git(["checkout", "-b", state.backport_branch, f"upstream/{state.release_branch}"])

    result = run_git(
        ["cherry-pick", state.commit_sha],
        check=False,
    )

    if result.returncode != 0:
        conflict_result = run_git(
            ["diff", "--name-only", "--diff-filter=U"],
            check=False,
        )
        state.conflict_files = [
            f for f in conflict_result.stdout.strip().split("\n") if f
        ]

        state_path = os.path.join(
            tempfile.gettempdir(), f"backport-state-{state.pr_num}.json",
        )
        state.save(state_path)

        log("\nCherry-pick conflict detected!")
        log(f"  Conflicting files:")
        for f in state.conflict_files:
            log(f"    - {f}")
        log("")
        log("Resolve conflicts, then re-run with:")
        log(f"  git add . && git cherry-pick --continue")
        log(f"  python scripts/backport.py {state.release} {state.pr_num} "
            f"--continue-from {state_path}")

        sys.exit(EXIT_CONFLICT)

    log(f"  Cherry-pick successful: {state.commit_sha[:10]}")


def step5_continue(state: BackportState) -> None:
    log_step(5, "Resuming after conflict resolution")

    result = run_git(["branch", "--show-current"], check=False)
    current = result.stdout.strip()
    if current != state.backport_branch:
        log(f"  Switching to {state.backport_branch}...")
        run_git(["checkout", state.backport_branch])

    result = run_git(
        ["grep", "-rlE", r"^<{7}|^={7}|^>{7}", "--", "."],
        check=False,
    )
    if result.stdout.strip():
        die(
            "Conflict markers still present in:\n"
            + result.stdout.strip()
        )

    log("  No conflict markers found — resuming")


# ---------------------------------------------------------------------------
# Step 6 — Push to fork
# ---------------------------------------------------------------------------

def step6_push_to_fork(state: BackportState) -> None:
    log_step(6, "Push backport branch to fork")

    result = run_gh_json(["api", "user", "--jq", ".login"])
    state.fork_owner = result.strip() if isinstance(result, str) else str(result)

    run_git(["push", "origin", state.backport_branch])
    log(f"  Pushed {state.backport_branch} to fork ({state.fork_owner})")


# ---------------------------------------------------------------------------
# Step 7 — Create PR #1 (fork → release branch)
# ---------------------------------------------------------------------------

def step7_create_pr1(state: BackportState, *, merge: bool = True) -> None:
    log_step(7, "Create PR #1 (backport → release)")

    body = (
        f"Backport of #{state.pr_num} to release-{state.release}\n\n"
        f"**Original PR:** {state.pr_url}\n"
        f"**Plugin:** {state.plugin}\n"
        f"**Release:** {state.release}\n\n"
        f"Cherry-picked commit: `{state.commit_sha[:10]}`\n\n"
        "---\nAuto-generated by backport skill."
    )

    run_gh([
        "pr", "create",
        "--repo", state.repo,
        "--base", state.release_branch,
        "--head", f"{state.fork_owner}:{state.backport_branch}",
        "--title", f"backport: #{state.pr_num} to release-{state.release}",
        "--body", body,
    ])

    pr_data = run_gh_json([
        "pr", "list",
        "--repo", state.repo,
        "--head", f"{state.fork_owner}:{state.backport_branch}",
        "--json", "number",
        "--jq", ".[0].number",
    ])
    state.pr1_num = int(pr_data) if pr_data else 0
    if not state.pr1_num:
        die("Failed to get PR #1 number after creation")

    log(f"  PR #1 created: #{state.pr1_num}")

    if merge:
        log("  Monitoring CI...")
        poll_ci(state.pr1_num, state.repo)
        merge_pr(state.pr1_num, state.repo)
        wait_for_merged(state.pr1_num, state.repo)
        log(f"  PR #1 merged: #{state.pr1_num}")


# ---------------------------------------------------------------------------
# Step 8 — Create PR #2 (release → workspace, from upstream)
# ---------------------------------------------------------------------------

def step8_create_pr2(state: BackportState, *, merge: bool = True) -> None:
    log_step(8, "Create PR #2 (release → workspace)")

    run_git(["fetch", "upstream"])

    body = (
        f"Backport of #{state.pr_num} to release {state.release}\n\n"
        f"Original PR: {state.pr_url}\n"
        f"Backport PR #1: #{state.pr1_num}\n\n"
        "This PR triggers the Version Packages workflow.\n\n"
        "**Do not edit manually** — auto-generated by backport skill."
    )

    run_gh([
        "pr", "create",
        "--repo", state.repo,
        "--base", state.workspace_branch,
        "--head", state.release_branch,
        "--title", f"chore: sync {state.plugin} release-{state.release} to workspace",
        "--body", body,
    ])

    pr_data = run_gh_json([
        "pr", "list",
        "--repo", state.repo,
        "--head", state.release_branch,
        "--base", state.workspace_branch,
        "--json", "number",
        "--jq", ".[0].number",
    ])
    state.pr2_num = int(pr_data) if pr_data else 0
    if not state.pr2_num:
        die("Failed to get PR #2 number after creation")

    log(f"  PR #2 created: #{state.pr2_num}")
    log(f"    {state.release_branch} → {state.workspace_branch}")

    pr_owner = run_gh_json([
        "pr", "view", str(state.pr2_num),
        "--repo", state.repo,
        "--json", "headRepositoryOwner",
        "--jq", ".headRepositoryOwner.login",
    ])
    if isinstance(pr_owner, str) and pr_owner != "redhat-developer":
        die(
            f"PR #2 head is from '{pr_owner}', not 'redhat-developer'.\n"
            "Version Packages workflow will NOT trigger from fork PRs."
        )

    if merge:
        log("  Monitoring CI...")
        poll_ci(state.pr2_num, state.repo)
        merge_pr(state.pr2_num, state.repo)
        wait_for_merged(state.pr2_num, state.repo)
        log(f"  PR #2 merged: #{state.pr2_num}")


# ---------------------------------------------------------------------------
# CI helpers
# ---------------------------------------------------------------------------

def poll_ci(
    pr_num: int,
    repo: str,
    *,
    timeout: int = 3600,
    interval: int = 30,
) -> None:
    elapsed = 0
    while elapsed < timeout:
        result = run_gh_json([
            "pr", "view", str(pr_num),
            "--repo", repo,
            "--json", "statusCheckRollup",
        ])
        checks = result.get("statusCheckRollup", []) if result else []

        if not checks:
            log(f"  No checks yet ({elapsed}s)")
            time.sleep(interval)
            elapsed += interval
            continue

        total = len(checks)
        success = sum(1 for c in checks if c.get("conclusion") == "SUCCESS")
        failure = sum(1 for c in checks if c.get("conclusion") == "FAILURE")
        pending = total - success - failure

        log(f"  Checks: {success}/{total} passed, {pending} pending, {failure} failed")

        if failure > 0:
            failed = [c["name"] for c in checks if c.get("conclusion") == "FAILURE"]
            die(f"CI failed on PR #{pr_num}: {', '.join(failed)}")

        if pending == 0 and success == total:
            log(f"  All {total} checks passed")
            return

        if pending > 0:
            pending_names = [
                c.get("name", "?")
                for c in checks
                if c.get("conclusion") not in ("SUCCESS", "FAILURE")
            ]
            log(f"    Pending: {', '.join(pending_names[:5])}")

        time.sleep(interval)
        elapsed += interval

    die(f"Timeout ({timeout}s) waiting for CI on PR #{pr_num}")


def merge_pr(pr_num: int, repo: str) -> None:
    log(f"  Merging PR #{pr_num}...")
    run_gh([
        "pr", "merge", str(pr_num),
        "--repo", repo,
        "--squash",
        "--auto",
    ])


def wait_for_merged(pr_num: int, repo: str, *, timeout: int = 300) -> None:
    elapsed = 0
    while elapsed < timeout:
        result = run_gh_json([
            "pr", "view", str(pr_num),
            "--repo", repo,
            "--json", "state",
            "--jq", ".state",
        ])
        if isinstance(result, str) and result.strip() == "MERGED":
            return
        time.sleep(10)
        elapsed += 10
    die(f"Timeout waiting for PR #{pr_num} to merge")


# ---------------------------------------------------------------------------
# Step 9 — Detect and merge Version Packages PR
# ---------------------------------------------------------------------------

def poll_for_vp_creation(
    plugin: str,
    workspace_branch: str,
    repo: str,
    *,
    timeout: int = 300,
    interval: int = 10,
) -> int:
    elapsed = 0
    while elapsed < timeout:
        result = run_gh_json(
            [
                "pr", "list", "--repo", repo,
                "--base", workspace_branch,
                "--search", f"Version Packages ({plugin}) in:title",
                "--state", "open",
                "--json", "number",
                "--jq", ".[0].number",
            ],
            check=False,
        )
        if result and int(result):
            return int(result)
        log(f"  Waiting for Version Packages PR... ({elapsed}s)")
        time.sleep(interval)
        elapsed += interval
    die(f"Version Packages PR not created after {timeout}s")
    return 0


def poll_for_vp_update(
    vp_pr_num: int,
    before_sha: str,
    repo: str,
    *,
    timeout: int = 300,
    interval: int = 10,
) -> None:
    elapsed = 0
    while elapsed < timeout:
        current = run_gh_json([
            "pr", "view", str(vp_pr_num),
            "--repo", repo,
            "--json", "headRefOid",
            "--jq", ".headRefOid",
        ])
        if isinstance(current, str) and current.strip() != before_sha:
            log(f"  VP PR #{vp_pr_num} updated (new commit)")
            return
        log(f"  Waiting for VP PR update... ({elapsed}s)")
        time.sleep(interval)
        elapsed += interval
    log(f"  Warning: VP PR #{vp_pr_num} not updated within {timeout}s, proceeding anyway")


def extract_version_from_body(body: str) -> str:
    m = re.search(r"@redhat-developer/\S+@([\d.]+)", body)
    return m.group(1) if m else "unknown"


def step9_detect_version_packages(state: BackportState) -> None:
    log_step(9, "Detect and merge Version Packages PR")

    vp_data = run_gh_json(
        [
            "pr", "list", "--repo", state.repo,
            "--base", state.workspace_branch,
            "--search", f"Version Packages ({state.plugin}) in:title",
            "--state", "open",
            "--json", "number,headRefOid",
            "--jq", ".[0]",
        ],
        check=False,
    )

    if vp_data and isinstance(vp_data, dict) and vp_data.get("number"):
        state.vp_pr_num = vp_data["number"]
        before_sha = vp_data.get("headRefOid", "")
        log(f"  Existing VP PR found: #{state.vp_pr_num}")
        if before_sha:
            poll_for_vp_update(state.vp_pr_num, before_sha, state.repo)
    else:
        log("  Waiting for Version Packages PR to be created...")
        time.sleep(10)
        state.vp_pr_num = poll_for_vp_creation(
            state.plugin, state.workspace_branch, state.repo,
        )

    log(f"  Version Packages PR: #{state.vp_pr_num}")

    vp_title = run_gh_json([
        "pr", "view", str(state.vp_pr_num),
        "--repo", state.repo,
        "--json", "title,baseRefName",
    ])
    if vp_title:
        title = vp_title.get("title", "")
        base = vp_title.get("baseRefName", "")
        if f"Version Packages ({state.plugin})" not in title:
            log(f"  Warning: VP PR title mismatch: {title}")
        if base != state.workspace_branch:
            die(f"VP PR base is '{base}', expected '{state.workspace_branch}'")

    log("  Monitoring CI on VP PR...")
    poll_ci(state.vp_pr_num, state.repo)
    merge_pr(state.vp_pr_num, state.repo)
    wait_for_merged(state.vp_pr_num, state.repo)

    vp_merged = run_gh_json([
        "pr", "view", str(state.vp_pr_num),
        "--repo", state.repo,
        "--json", "mergeCommit,body",
    ])
    if vp_merged:
        state.vp_commit = vp_merged.get("mergeCommit", {}).get("oid", "")
        state.vp_version = extract_version_from_body(vp_merged.get("body", ""))

    log(f"  VP merged — commit: {state.vp_commit[:10]}, version: {state.vp_version}")


# ---------------------------------------------------------------------------
# Step 10 — Sync release branch from workspace
# ---------------------------------------------------------------------------

def step10_sync_release_branch(state: BackportState) -> None:
    log_step(10, "Sync release branch from workspace")

    run_git(["fetch", "upstream"])
    run_git(["checkout", state.release_branch])
    run_git(["reset", "--hard", f"upstream/{state.workspace_branch}"])

    result = run_git(
        ["push", "upstream", state.release_branch, "--force-with-lease"],
        check=False,
    )
    if result.returncode != 0:
        die(
            f"Force push to {state.release_branch} rejected.\n"
            "Someone may have pushed concurrently.\n"
            + result.stderr.strip()
        )

    log(f"  Synced {state.release_branch} ← {state.workspace_branch}")


# ---------------------------------------------------------------------------
# Step 11 — Update overlays repository
# ---------------------------------------------------------------------------

def update_source_json(path: Path, new_commit: str) -> None:
    with open(path) as f:
        data = json.load(f)
    data["repo-ref"] = new_commit
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def update_metadata_version(metadata_dir: Path, version: str) -> list[str]:
    updated: list[str] = []
    if not metadata_dir.is_dir():
        return updated
    for ext in ("*.yaml", "*.yml"):
        for yaml_file in sorted(metadata_dir.glob(ext)):
            content = yaml_file.read_text()
            new_content = re.sub(
                r"^version: .*$",
                f'version: "{version}"',
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                yaml_file.write_text(new_content)
                updated.append(yaml_file.name)
    return updated


def poll_publish_result(
    pr_num: int,
    overlays_repo: str,
    *,
    timeout: int = 300,
    interval: int = 15,
) -> tuple[bool, str]:
    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval

        result = run_gh_json([
            "pr", "view", str(pr_num),
            "--repo", overlays_repo,
            "--json", "comments",
        ])
        if not result or not result.get("comments"):
            continue

        latest = result["comments"][-1].get("body", "")
        if "validation error" in latest.lower():
            return False, latest
        if any(kw in latest.lower() for kw in ("success", "published", "completed")):
            return True, latest

        log(f"  Waiting for /publish result... ({elapsed}s)")

    return False, ""


def fix_metadata_from_publish_errors(
    plugin: str,
    error_text: str,
    overlays_dir: Path,
) -> list[str]:
    fixed: list[str] = []
    for line in error_text.split("\n"):
        if "mismatch" not in line.lower():
            continue
        parts = line.split()
        if not parts:
            continue
        yaml_file = parts[0]
        m = re.search(r'expected "([^"]+)"', line)
        if not m:
            continue
        expected_ver = m.group(1)
        metadata_path = overlays_dir / "workspaces" / plugin / "metadata" / yaml_file
        if metadata_path.exists():
            content = metadata_path.read_text()
            new_content = re.sub(
                r"^version: .*$",
                f'version: "{expected_ver}"',
                content,
                flags=re.MULTILINE,
            )
            metadata_path.write_text(new_content)
            fixed.append(yaml_file)
            log(f"    Fixed {yaml_file}: version → {expected_ver}")
    return fixed


def step11_update_overlays(state: BackportState) -> None:
    log_step(11, "Update overlays repository")

    overlays_dir = Path(state.overlays_dir)
    run_git(["fetch", "origin"], cwd=overlays_dir)
    run_git(["checkout", state.overlays_branch], cwd=overlays_dir)
    run_git(["pull", "origin", state.overlays_branch], cwd=overlays_dir)

    existing = run_gh_json(
        [
            "pr", "list",
            "--repo", state.overlays_repo,
            "--base", state.overlays_branch,
            "--search", f"{state.plugin} in:title",
            "--state", "open",
            "--json", "number,headRefName",
            "--jq", ".[0]",
        ],
        check=False,
    )

    source_path = overlays_dir / "workspaces" / state.plugin / "source.json"
    metadata_dir = overlays_dir / "workspaces" / state.plugin / "metadata"

    if existing and isinstance(existing, dict) and existing.get("number"):
        existing_pr_num = existing["number"]
        existing_branch = existing["headRefName"]
        log(f"  Existing overlays PR found: #{existing_pr_num}")

        run_git(["checkout", existing_branch], cwd=overlays_dir)
        run_git(["pull", "origin", existing_branch], cwd=overlays_dir, check=False)

        update_source_json(source_path, state.vp_commit)
        updated_meta = update_metadata_version(metadata_dir, state.vp_version)

        run_git(["add", f"workspaces/{state.plugin}/"], cwd=overlays_dir)
        run_git([
            "commit", "-m",
            f"chore: update {state.plugin} repo-ref to {state.vp_commit[:10]}\n\n"
            f"Backport of {state.repo}#{state.pr_num} to {state.release}\n"
            f"Version Packages commit: {state.vp_commit}",
        ], cwd=overlays_dir)
        run_git(["push", "origin", existing_branch], cwd=overlays_dir)

        state.overlays_pr_num = existing_pr_num
        log(f"  Updated existing overlays PR #{existing_pr_num}")
    else:
        log("  Creating new overlays PR...")

        update_source_json(source_path, state.vp_commit)
        updated_meta = update_metadata_version(metadata_dir, state.vp_version)

        log(f"  Updated source.json: repo-ref → {state.vp_commit[:10]}")
        if updated_meta:
            log(f"  Updated metadata: {', '.join(updated_meta)}")

        branch_name = f"update-{state.plugin}-{state.release}-pr{state.pr_num}"
        run_git(["checkout", "-b", branch_name], cwd=overlays_dir)
        run_git(["add", f"workspaces/{state.plugin}/"], cwd=overlays_dir)
        run_git([
            "commit", "-m",
            f"chore: update {state.plugin} to {state.vp_version}\n\n"
            f"Backport of {state.repo}#{state.pr_num} to {state.release}\n\n"
            f"Changes:\n"
            f"- Updated source.json repo-ref: {state.vp_commit}\n"
            f"- Updated metadata files version: {state.vp_version}\n\n"
            f"Version Packages commit: {state.vp_commit}",
        ], cwd=overlays_dir)
        run_git(["push", "origin", branch_name], cwd=overlays_dir)

        fork_owner_result = run_gh_json(["api", "user", "--jq", ".login"])
        fork_owner = fork_owner_result.strip() if isinstance(fork_owner_result, str) else str(fork_owner_result)

        body = (
            f"Updates {state.plugin} source to Version Packages commit\n\n"
            f"**Backport details:**\n"
            f"- Original PR: {state.repo}#{state.pr_num}\n"
            f"- Release: {state.release}\n"
            f"- Version Packages commit: `{state.vp_commit[:10]}`\n\n"
            f"**Changes:**\n"
            f"- Updated `workspaces/{state.plugin}/source.json`\n"
            f"- Updated `workspaces/{state.plugin}/metadata/*.yaml`\n\n"
            "---\nAuto-generated by backport skill."
        )

        run_gh([
            "pr", "create",
            "--repo", state.overlays_repo,
            "--base", state.overlays_branch,
            "--head", f"{fork_owner}:{branch_name}",
            "--title", f"chore: update {state.plugin} for {state.release} release",
            "--body", body,
        ])

        pr_result = run_gh_json([
            "pr", "list",
            "--repo", state.overlays_repo,
            "--head", f"{fork_owner}:{branch_name}",
            "--json", "number",
            "--jq", ".[0].number",
        ])
        state.overlays_pr_num = int(pr_result) if pr_result else 0
        log(f"  Overlays PR created: #{state.overlays_pr_num}")

    # /publish
    log("  Issuing /publish...")
    run_gh([
        "pr", "comment", str(state.overlays_pr_num),
        "--repo", state.overlays_repo,
        "--body", "/publish",
    ])

    publish_ok, publish_output = poll_publish_result(
        state.overlays_pr_num, state.overlays_repo,
    )

    if not publish_ok and publish_output:
        log("  /publish failed — fixing metadata versions...")
        fixed = fix_metadata_from_publish_errors(
            state.plugin, publish_output, overlays_dir,
        )
        if fixed:
            run_git(["add", f"workspaces/{state.plugin}/metadata/"], cwd=overlays_dir)
            run_git([
                "commit", "-m",
                f"fix: update metadata versions for {state.plugin}\n\n"
                "Fixed version mismatches reported by /publish validation",
            ], cwd=overlays_dir)
            run_git(["push", "origin", "HEAD"], cwd=overlays_dir)

            log("  Retrying /publish...")
            run_gh([
                "pr", "comment", str(state.overlays_pr_num),
                "--repo", state.overlays_repo,
                "--body", "/publish",
            ])
            publish_ok, _ = poll_publish_result(
                state.overlays_pr_num, state.overlays_repo,
            )

    if publish_ok:
        log("  /publish succeeded — waiting for all CI (may take 30+ min)...")
        poll_ci(state.overlays_pr_num, state.overlays_repo, timeout=3600)
        merge_pr(state.overlays_pr_num, state.overlays_repo)
        wait_for_merged(state.overlays_pr_num, state.overlays_repo)
        log(f"  Overlays PR #{state.overlays_pr_num} merged")
    else:
        log(f"  Warning: /publish did not succeed — PR #{state.overlays_pr_num} left open")
        log("  Manual intervention required")


# ---------------------------------------------------------------------------
# Step 12 — Changelog PR
# ---------------------------------------------------------------------------

def step12_changelog_pr(state: BackportState) -> None:
    log_step(12, "Create changelog PR to main")

    run_git(["fetch", "upstream"])

    changelog_branch = f"changelog/{state.plugin}-{state.release}-pr{state.pr_num}"
    run_git(["checkout", "-b", changelog_branch, "upstream/main"])

    changelog_file = None
    for candidate in (
        f"workspaces/{state.plugin}/CHANGELOG.md",
        f"workspaces/{state.plugin}/plugins/{state.plugin}/CHANGELOG.md",
    ):
        if Path(candidate).exists():
            changelog_file = candidate
            break

    if not changelog_file:
        log(f"  Warning: CHANGELOG.md not found for {state.plugin}, skipping")
        return

    content = Path(changelog_file).read_text()
    entry = (
        f"\n## {state.vp_version}\n\n"
        f"### Backports\n\n"
        f"- Backported #{state.pr_num}: {state.pr_title} "
        f"([#{state.vp_pr_num}](https://github.com/{state.repo}/pull/{state.vp_pr_num}))\n"
    )

    lines = content.split("\n")
    insert_idx = 0
    heading_count = 0
    for i, line in enumerate(lines):
        if line.startswith("## "):
            heading_count += 1
            if heading_count == 1:
                insert_idx = i
                break
    if insert_idx == 0:
        insert_idx = len(lines)

    lines.insert(insert_idx, entry)
    Path(changelog_file).write_text("\n".join(lines))

    run_git(["add", changelog_file])
    run_git([
        "commit", "-m",
        f"docs: add {state.plugin} {state.release} changelog for PR #{state.pr_num}",
    ])
    run_git(["push", "origin", changelog_branch])

    body = (
        f"Adds changelog entry for backported PR #{state.pr_num}\n\n"
        f"**Backport details:**\n"
        f"- Original PR: #{state.pr_num}\n"
        f"- Release: {state.release}\n"
        f"- Version: {state.vp_version}\n"
        f"- Plugin: {state.plugin}\n\n"
        f"This tracks what was backported to the {state.release} release."
    )

    run_gh([
        "pr", "create",
        "--repo", state.repo,
        "--base", "main",
        "--head", f"{state.fork_owner}:{changelog_branch}",
        "--title", f"docs: add {state.plugin} {state.release} changelog for backport #{state.pr_num}",
        "--body", body,
    ])

    pr_result = run_gh_json([
        "pr", "list",
        "--repo", state.repo,
        "--head", f"{state.fork_owner}:{changelog_branch}",
        "--json", "number",
        "--jq", ".[0].number",
    ])
    state.changelog_pr_num = int(pr_result) if pr_result else 0
    log(f"  Changelog PR created: #{state.changelog_pr_num}")

    log("  Monitoring CI...")
    poll_ci(state.changelog_pr_num, state.repo)
    merge_pr(state.changelog_pr_num, state.repo)
    wait_for_merged(state.changelog_pr_num, state.repo)
    log(f"  Changelog PR #{state.changelog_pr_num} merged")


# ---------------------------------------------------------------------------
# Step 13 — Summary
# ---------------------------------------------------------------------------

def step13_summary(state: BackportState, *, json_output: bool = False) -> None:
    log_step(13, "Summary")

    if json_output:
        result = {
            "plugin": state.plugin,
            "release": state.release,
            "original_pr": state.pr_num,
            "pr1": state.pr1_num,
            "pr2": state.pr2_num,
            "vp_pr": state.vp_pr_num,
            "vp_commit": state.vp_commit,
            "vp_version": state.vp_version,
            "overlays_pr": state.overlays_pr_num,
            "changelog_pr": state.changelog_pr_num,
            "status": "completed",
        }
        json.dump(result, sys.stdout, indent=2)
        print()
    else:
        log("")
        log("=" * 40)
        log("BACKPORT COMPLETED SUCCESSFULLY")
        log("=" * 40)
        log("")
        log(f"Plugin: {state.plugin}")
        log(f"Release: {state.release}")
        log(f"Original PR: #{state.pr_num}")
        log("")
        log("All PRs merged:")
        log(f"  1. Backport PR #1:    #{state.pr1_num}")
        log(f"  2. Sync PR #2:        #{state.pr2_num}")
        log(f"  3. Version Packages:  #{state.vp_pr_num}")
        log(f"  4. Overlays:          #{state.overlays_pr_num}")
        log(f"  5. Changelog:         #{state.changelog_pr_num}")
        log("")
        log(f"VP commit: {state.vp_commit}")
        log("")
        log("=" * 40)


def print_create_summary(
    state: BackportState, *, json_output: bool = False,
) -> None:
    if json_output:
        result = {
            "plugin": state.plugin,
            "release": state.release,
            "original_pr": state.pr_num,
            "pr1": state.pr1_num,
            "pr2": state.pr2_num,
            "status": "prs_created",
        }
        json.dump(result, sys.stdout, indent=2)
        print()
    else:
        log("")
        log("=" * 40)
        log("BACKPORT PRs CREATED")
        log("=" * 40)
        log("")
        log(f"Plugin: {state.plugin}")
        log(f"Release: {state.release}")
        log(f"Original PR: #{state.pr_num}")
        log("")
        log("PRs created:")
        log(f"  1. Backport to release: #{state.pr1_num}")
        log(f"     {state.backport_branch} → {state.release_branch}")
        log(f"  2. Sync to workspace:   #{state.pr2_num}")
        log(f"     {state.release_branch} → {state.workspace_branch}")
        log("")
        log("NEXT STEPS (manual):")
        log(f"  1. Review and merge PR #{state.pr1_num}")
        log(f"  2. Review and merge PR #{state.pr2_num}")
        log("  3. Wait for Version Packages PR")
        log(f"  4. Run: python scripts/backport.py {state.release} {state.pr_num} --mode finish")
        log("")
        log("=" * 40)


# ---------------------------------------------------------------------------
# Finish mode prerequisites
# ---------------------------------------------------------------------------

def validate_finish_prerequisites(state: BackportState) -> None:
    run_git(["fetch", "upstream"])
    result = run_git(
        ["branch", "-r", "--contains", state.commit_sha],
        check=False,
    )
    if f"upstream/{state.release_branch}" not in result.stdout:
        log(
            f"  Warning: commit {state.commit_sha[:10]} not found in {state.release_branch}\n"
            f"  Expected: backport-create was run and PRs were merged"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log("=" * 16 + " Using Backport Skill " + "=" * 16)

    if args.continue_from:
        state = BackportState.load(args.continue_from)
        state.mode = args.mode
        step5_continue(state)
        step6_push_to_fork(state)

        merge = args.mode == "auto"
        step7_create_pr1(state, merge=merge)
        step8_create_pr2(state, merge=merge)

        if args.mode == "create":
            print_create_summary(state, json_output=args.json_output)
            return EXIT_SUCCESS

        step9_detect_version_packages(state)
        step10_sync_release_branch(state)
        step11_update_overlays(state)
        step12_changelog_pr(state)
        step13_summary(state, json_output=args.json_output)
        return EXIT_SUCCESS

    pr_num, commit_sha = parse_pr_source(args.pr_source)

    state = BackportState(
        release=args.release,
        repo=args.repo,
        overlays_repo=args.overlays_repo,
        mode=args.mode,
    )
    if pr_num:
        state.pr_num = pr_num
    if commit_sha:
        state.commit_sha = commit_sha

    if args.mode in ("auto", "create"):
        step1_fetch_pr(state)
        step2_detect_plugin(state)
        step3_check_backported(state, force=args.force)
        step4_reset_workspace(state)
        step5_cherry_pick(state)
        step6_push_to_fork(state)

        merge = args.mode == "auto"
        step7_create_pr1(state, merge=merge)
        step8_create_pr2(state, merge=merge)

        if args.mode == "create":
            print_create_summary(state, json_output=args.json_output)
            return EXIT_SUCCESS

    if args.mode == "finish":
        step1_fetch_pr(state)
        step2_detect_plugin(state)
        validate_finish_prerequisites(state)

    step9_detect_version_packages(state)
    step10_sync_release_branch(state)
    step11_update_overlays(state)
    step12_changelog_pr(state)
    step13_summary(state, json_output=args.json_output)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
