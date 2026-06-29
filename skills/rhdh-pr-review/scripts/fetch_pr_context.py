#!/usr/bin/env python3
"""Fetch PR context from GitHub and output a structured context artifact as JSON.

Runs gh CLI commands to collect PR metadata, diff, linked issues,
existing review comments, and CI status. Output is consumed by
review-code.md and review-operator-pr.md workflows.

Examples:
    python scripts/fetch_pr_context.py https://github.com/redhat-developer/rhdh-operator/pull/123
    python scripts/fetch_pr_context.py 123
    python scripts/fetch_pr_context.py 123 --repo redhat-developer/rhdh-operator
"""

import argparse
import json
import os
import re
import subprocess
import sys

_no_color = os.environ.get("NO_COLOR") is not None
_is_tty = sys.stderr.isatty() and not _no_color


def log(msg):
    """Write to stderr — keeps stdout clean for JSON output."""
    if _is_tty:
        print(msg, file=sys.stderr)


def error_exit(error_key, detail=None):
    result = {"error": error_key}
    if detail:
        result["detail"] = detail
    json.dump(result, sys.stdout, indent=2)
    print()
    sys.exit(1)


def run_gh(args, check=True):
    """Run a gh CLI command and return stdout. Exits on failure if check=True."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )
    except FileNotFoundError:
        error_exit("gh_not_found", "gh CLI is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        error_exit("gh_timeout", f"Command timed out: {' '.join(cmd)}")

    if check and result.returncode != 0:
        stderr = result.stderr.strip()
        error_exit("gh_error", f"{' '.join(cmd)}: {stderr}")

    return result.stdout


def run_gh_json(args):
    """Run a gh CLI command and parse stdout as JSON."""
    raw = run_gh(args)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        error_exit("gh_json_parse", f"Failed to parse JSON from: {' '.join(['gh'] + args)}")


def parse_pr_input(pr_input):
    """Parse a PR URL or number into (repo, number). Returns (None, number) if no repo in input."""
    # Full URL: https://github.com/owner/repo/pull/123
    url_match = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_input)
    if url_match:
        return url_match.group(1), int(url_match.group(2))

    # Plain number
    if pr_input.isdigit():
        return None, int(pr_input)

    # owner/repo#123
    ref_match = re.match(r"([^/]+/[^#]+)#(\d+)", pr_input)
    if ref_match:
        return ref_match.group(1), int(ref_match.group(2))

    error_exit("invalid_input", f"Cannot parse PR reference: {pr_input}")


def detect_repo():
    """Detect repo from current git remote."""
    raw = run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    repo = raw.strip()
    if not repo:
        error_exit("no_repo", "Could not detect repo. Pass --repo or use a full PR URL.")
    return repo


def extract_issue_refs(body):
    """Extract GitHub issue references and Jira keys from PR body text."""
    if not body:
        return [], []

    # GitHub: Fixes #123, Closes #456, Resolves #789, refs #101
    gh_pattern = r"(?:fix(?:es|ed)?|clos(?:es|ed)?|resolv(?:es|ed)?|refs?)\s+#(\d+)"
    gh_issues = [int(m) for m in re.findall(gh_pattern, body, re.IGNORECASE)]

    # Also catch bare #N references not already captured.
    # This is intentionally broad — may catch "step #1" or cross-repo refs.
    # Cross-repo refs (org/repo#N) will fail gh issue view against the wrong
    # repo, so we filter those out below.
    bare_pattern = r"(?<!\w)(?<![/\w])#(\d+)"
    bare_issues = [int(m) for m in re.findall(bare_pattern, body)]
    gh_issues = sorted(set(gh_issues + bare_issues))

    # Jira keys: RHIDP-1234, RHDHBUGS-567, etc.
    jira_keys = re.findall(r"[A-Z][A-Z0-9]+-\d+", body)
    jira_keys = sorted(set(jira_keys))

    return gh_issues, jira_keys


def fetch_linked_issues(repo, issue_numbers):
    """Fetch GitHub issue details for each linked issue number."""
    issues = []
    for num in issue_numbers:
        log(f"  Fetching issue #{num}...")
        data = run_gh_json(
            ["issue", "view", str(num), "--repo", repo, "--json", "number,title,body,labels,state"]
        )
        issues.append(
            {
                "number": data.get("number", num),
                "title": data.get("title", ""),
                "body": data.get("body", ""),
                "labels": [label.get("name", "") for label in data.get("labels", [])],
                "state": data.get("state", ""),
            }
        )
    return issues


def fetch_review_comments(repo, pr_number):
    """Fetch existing inline review comments."""
    raw = run_gh(
        [
            "api",
            f"repos/{repo}/pulls/{pr_number}/comments",
            "--paginate",
            "-q",
            ".[] | {user: .user.login, path: .path, line: .line, body: .body, created_at: .created_at}",
        ],
        check=False,
    )
    if not raw.strip():
        return []

    comments = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            comments.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return comments


def fetch_reviews(repo, pr_number):
    """Fetch top-level review comments (review bodies, not inline)."""
    raw = run_gh(
        [
            "api",
            f"repos/{repo}/pulls/{pr_number}/reviews",
            "--paginate",
            "-q",
            ".[] | {user: .user.login, state: .state, body: .body}",
        ],
        check=False,
    )
    if not raw.strip():
        return []

    reviews = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            reviews.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return reviews


def fetch_ci_status(repo, pr_number):
    """Fetch CI check status. Returns 'pass', 'fail', or 'pending'."""
    raw = run_gh(
        ["pr", "checks", str(pr_number), "--repo", repo, "--json", "name,state,conclusion"],
        check=False,
    )
    if not raw.strip():
        return "unknown"

    try:
        checks = json.loads(raw)
    except json.JSONDecodeError:
        return "unknown"

    if not checks:
        return "unknown"

    states = [c.get("conclusion", c.get("state", "")) for c in checks]
    if any(s in ("FAILURE", "failure", "ERROR", "error") for s in states):
        return "fail"
    if any(s in ("PENDING", "pending", "IN_PROGRESS", "in_progress", "") for s in states):
        return "pending"
    return "pass"


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GitHub PR context and output a structured JSON artifact."
    )
    parser.add_argument(
        "pr",
        help="PR number, URL (https://github.com/owner/repo/pull/123), or owner/repo#123",
    )
    parser.add_argument(
        "--repo",
        help="Repository (owner/repo). Auto-detected from git remote if omitted.",
    )
    parser.add_argument(
        "--no-diff",
        action="store_true",
        help="Skip fetching the diff (useful for metadata-only queries).",
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Skip fetching existing review comments.",
    )
    parser.add_argument(
        "--no-issues",
        action="store_true",
        help="Skip fetching linked GitHub issues.",
    )
    args = parser.parse_args()

    # Parse input
    parsed_repo, pr_number = parse_pr_input(args.pr)
    repo = args.repo or parsed_repo
    if not repo:
        log("No repo specified, detecting from git remote...")
        repo = detect_repo()

    log(f"Fetching PR #{pr_number} from {repo}...")

    # Step 1: PR metadata
    log("  Fetching metadata...")
    pr_data = run_gh_json(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            "number,title,body,state,author,labels,headRefName,baseRefName,"
            "headRefOid,files,additions,deletions,url,commits",
        ]
    )

    # Step 2: Diff
    diff = ""
    if not args.no_diff:
        log("  Fetching diff...")
        diff = run_gh(["pr", "diff", str(pr_number), "--repo", repo])

    # Step 3: Linked issues
    gh_issue_nums, jira_keys = extract_issue_refs(pr_data.get("body", ""))
    linked_issues = []
    if not args.no_issues and gh_issue_nums:
        log(f"  Found {len(gh_issue_nums)} linked GitHub issue(s)...")
        linked_issues = fetch_linked_issues(repo, gh_issue_nums)

    # Step 4: Existing comments
    existing_comments = []
    existing_reviews = []
    if not args.no_comments:
        log("  Fetching existing review comments...")
        existing_comments = fetch_review_comments(repo, pr_number)
        existing_reviews = fetch_reviews(repo, pr_number)

    # Step 5: CI status
    log("  Checking CI status...")
    ci_status = fetch_ci_status(repo, pr_number)

    # Assemble context artifact
    files = []
    for f in pr_data.get("files", []):
        files.append(
            {
                "path": f.get("path", ""),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
            }
        )

    labels = [label.get("name", "") for label in pr_data.get("labels", [])]

    artifact = {
        "forge": "github",
        "repo": repo,
        "pr_number": pr_number,
        "head_sha": pr_data.get("headRefOid", ""),
        "base_ref": pr_data.get("baseRefName", ""),
        "head_ref": pr_data.get("headRefName", ""),
        "title": pr_data.get("title", ""),
        "body": pr_data.get("body", ""),
        "author": pr_data.get("author", {}).get("login", ""),
        "state": pr_data.get("state", ""),
        "url": pr_data.get("url", ""),
        "labels": labels,
        "files": files,
        "total_additions": pr_data.get("additions", 0),
        "total_deletions": pr_data.get("deletions", 0),
        "diff": diff,
        "linked_issues": linked_issues,
        "jira_keys": jira_keys,
        "existing_comments": existing_comments,
        "existing_reviews": existing_reviews,
        "ci_status": ci_status,
    }

    # Output
    if sys.stdout.isatty():
        json.dump(artifact, sys.stdout, indent=2)
    else:
        json.dump(artifact, sys.stdout)
    print()

    log(
        f"Done. {len(files)} files, {len(linked_issues)} linked issues, "
        f"{len(existing_comments)} comments, CI: {ci_status}"
    )


if __name__ == "__main__":
    main()
