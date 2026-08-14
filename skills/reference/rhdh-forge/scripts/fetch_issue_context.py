#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# ///
"""Fetch a GitHub issue and print its context as a plain JSON document.

Resolves an issue URL, a bare number, or an owner/repo#number shorthand,
reads the issue with the gh CLI, and resolves the plugin workspace the issue
belongs to. Consumers include the pull-request, plugin-development, and
pr-review skills.

Stdlib only. GitLab issues and merge requests are read through
`glab`; see references/glab-cli.md.

Examples:
    uv run scripts/fetch_issue_context.py https://github.com/redhat-developer/rhdh-plugins/issues/607
    uv run scripts/fetch_issue_context.py 607 --repo redhat-developer/rhdh-plugins
    uv run scripts/fetch_issue_context.py backstage/community-plugins#3574
"""

import argparse
import json
import os
import re
import subprocess
import sys

WORKSPACE_LABEL = re.compile(r"^workspace/(?P<name>[A-Za-z0-9._-]+)$")
WORKSPACE_HEADING = re.compile(
    r"^#{1,6}\s*workspace\s*$\s*(?P<name>[^\r\n]+)", re.IGNORECASE | re.MULTILINE
)
TITLE_PREFIX = re.compile(r"^\s*(?P<prefix>[A-Za-z0-9][A-Za-z0-9._-]*)\s*:")
PACKAGE_NAME = re.compile(
    r"@(?:red-hat-developer-hub/backstage-plugin|backstage-community/plugin)-(?P<name>[a-z0-9-]+)"
)
SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def log(msg):
    """Write progress to stderr, keeping stdout clean for the JSON document."""
    if sys.stderr.isatty() and os.environ.get("NO_COLOR") is None:
        print(msg, file=sys.stderr)


def error_exit(error_key, detail=None):
    """Print a JSON error object to stdout and exit 1."""
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


def parse_issue_input(issue_input):
    """Parse an issue reference into (repo, number).

    Returns (None, number) when the reference carries no repository.
    """
    text = issue_input.strip()

    url_match = re.match(
        r"(?:https?://)?(?:www\.)?github\.com/([^/]+/[^/]+)/issues/(\d+)", text, re.IGNORECASE
    )
    if url_match:
        return url_match.group(1), int(url_match.group(2))

    ref_match = re.fullmatch(r"([^/\s]+/[^/#\s]+)#(\d+)", text)
    if ref_match:
        return ref_match.group(1), int(ref_match.group(2))

    bare_match = re.fullmatch(r"#?(\d+)", text)
    if bare_match:
        return None, int(bare_match.group(1))

    error_exit("invalid_input", f"Cannot parse GitHub issue reference: {issue_input}")


def detect_repo():
    """Detect the repository from the current checkout."""
    raw = run_gh(["repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    repo = raw.strip()
    if not repo:
        error_exit("no_repo", "Could not detect a repository. Pass --repo or a full issue URL.")
    return repo


def resolve_workspace(title, body, labels):
    """Resolve the workspace an issue belongs to, reporting which strategy answered."""
    for label in labels:
        match = WORKSPACE_LABEL.match(label)
        if match:
            return match.group("name"), "label"

    heading = WORKSPACE_HEADING.search(body or "")
    if heading:
        candidate = heading.group("name").strip().strip("`*_ ")
        if SLUG.match(candidate):
            return candidate, "body"

    prefix_match = TITLE_PREFIX.match(title or "")
    if prefix_match:
        candidate = prefix_match.group("prefix")
        if candidate.lower().startswith("plugin-"):
            candidate = candidate[len("plugin-") :]
        if candidate:
            return candidate, "title"

    package = PACKAGE_NAME.search(body or "")
    if package:
        return package.group("name"), "package"

    return None, "unresolved"


def fetch_comments(data):
    """Normalize the comment list returned by gh issue view."""
    comments = []
    for comment in data.get("comments") or []:
        author = comment.get("author") or {}
        comments.append(
            {
                "author": author.get("login", ""),
                "body": comment.get("body", ""),
                "createdAt": comment.get("createdAt", ""),
            }
        )
    return comments


def main():
    parser = argparse.ArgumentParser(
        description="Fetch a GitHub issue and print its context as JSON."
    )
    parser.add_argument(
        "issue",
        help="Issue number, URL (https://github.com/owner/repo/issues/607), or owner/repo#607",
    )
    parser.add_argument(
        "--repo",
        help="Repository (owner/repo). Detected from the current checkout if omitted.",
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Skip the issue comment thread.",
    )
    args = parser.parse_args()

    parsed_repo, number = parse_issue_input(args.issue)
    repo = args.repo or parsed_repo
    if not repo:
        log("No repository specified, detecting from the current checkout...")
        repo = detect_repo()

    fields = ["number", "title", "body", "labels", "state", "url"]
    if not args.no_comments:
        fields.append("comments")

    log(f"Fetching issue #{number} from {repo}...")
    raw = run_gh(["issue", "view", str(number), "--repo", repo, "--json", ",".join(fields)])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        error_exit("gh_json_parse", f"Failed to parse JSON for {repo}#{number}")

    title = data.get("title", "")
    body = data.get("body", "") or ""
    labels = [label.get("name", "") for label in data.get("labels") or []]
    workspace, strategy = resolve_workspace(title, body, labels)

    context = {
        "key": f"{repo}#{number}",
        "summary": title,
        "source": "github",
        "url": f"https://github.com/{repo}/issues/{number}",
        "repository": repo,
        "number": number,
        "state": data.get("state", ""),
        "labels": labels,
        "description": body,
        "workspace": {"name": workspace, "strategy": strategy},
        "comments": fetch_comments(data),
    }

    if sys.stdout.isatty():
        json.dump(context, sys.stdout, indent=2)
    else:
        json.dump(context, sys.stdout)
    print()

    log(f"Done. state={context['state']} workspace={workspace or 'unresolved'}")


if __name__ == "__main__":
    main()
