#!/usr/bin/env python3
"""Analyze a single overlay repository PR.

Consolidates ~8 sequential gh API calls into one script.
Gathers PR metadata, checks, workspace, CODEOWNERS, and produces
a structured analysis with priority, assignment, and merge readiness.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime, timezone

DEFAULT_REPO = "redhat-developer/rhdh-plugin-export-overlays"

STALENESS_THRESHOLDS = {
    "critical": {"warn": 2, "alert": 5},
    "medium": {"warn": 5, "alert": 10},
    "low": {"warn": 14, "alert": 30},
    "skip": {"warn": 999, "alert": 999},
    "unknown": {"warn": 7, "alert": 14},
}


def run_gh(args, check=True):
    """Run a gh CLI command and return parsed JSON output."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=30)
        if result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.CalledProcessError as exc:
        print(f"Error running: {' '.join(cmd)}", file=sys.stderr)
        print(exc.stderr, file=sys.stderr)
        if check:
            sys.exit(1)
        return None
    except json.JSONDecodeError:
        return result.stdout.strip()
    except FileNotFoundError:
        print("Error: gh CLI not found. Install from https://cli.github.com/", file=sys.stderr)
        sys.exit(1)


def run_gh_raw(args, check=True):
    """Run a gh CLI command and return raw stdout."""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=30)
        return result.stdout.strip()
    except subprocess.CalledProcessError as exc:
        print(f"Error running: {' '.join(cmd)}", file=sys.stderr)
        print(exc.stderr, file=sys.stderr)
        if check:
            sys.exit(1)
        return ""
    except FileNotFoundError:
        print("Error: gh CLI not found.", file=sys.stderr)
        sys.exit(1)


def fetch_pr_context(pr_number, repo):
    """Fetch full PR context in one gh call."""
    fields = (
        "number,title,state,author,labels,assignees,reviewRequests,"
        "reviews,statusCheckRollup,files,updatedAt,createdAt,mergeable,body"
    )
    return run_gh(
        [
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repo,
            "--json",
            fields,
        ]
    )


def fetch_codeowners(repo):
    """Fetch CODEOWNERS file content."""
    result = run_gh_raw(
        [
            "api",
            f"repos/{repo}/contents/CODEOWNERS",
            "--jq",
            ".content",
        ],
        check=False,
    )
    if result:
        try:
            return base64.b64decode(result).decode("utf-8", errors="replace")
        except Exception:
            pass
    return ""


def classify_priority(labels):
    """Classify PR priority based on labels."""
    names = [lbl["name"] for lbl in labels] if labels else []

    if "do-not-merge" in names:
        return "skip", "⚫ Skip (do-not-merge)"

    is_mandatory = "mandatory-workspace" in names
    is_update = "workspace-update" in names
    is_addition = "workspace-addition" in names

    if is_mandatory and is_update:
        return "critical", "🔴 Critical (mandatory-workspace + workspace-update)"
    if is_mandatory and is_addition:
        return "medium", "🟡 Medium (mandatory-workspace + workspace-addition)"
    if is_addition:
        return "low", "🟢 Low (workspace-addition)"
    return "unknown", "❓ Unknown (manual review needed)"


def extract_workspaces(files):
    """Extract workspace names from changed files."""
    workspaces = set()
    for f in files or []:
        path = f.get("path", "")
        if path.startswith("workspaces/"):
            parts = path.split("/")
            if len(parts) >= 2:
                workspaces.add(parts[1])
    return sorted(workspaces)


def assess_assignment(pr_data):
    """Assess assignment status."""
    assignees = [a.get("login", "") for a in (pr_data.get("assignees") or [])]
    review_requests = pr_data.get("reviewRequests") or []
    individual_reviewers = [r.get("login", "") for r in review_requests if r.get("login")]
    team_reviewers = [
        r.get("name", "") for r in review_requests if r.get("name") and not r.get("login")
    ]

    if assignees:
        status = "✅ Clear ownership"
        verdict = "assigned"
    elif individual_reviewers:
        status = "⚠️ Reviewer but no assignee"
        verdict = "reviewer_only"
    elif team_reviewers:
        status = "⚠️ Only team requested — responsibility diluted"
        verdict = "team_only"
    else:
        status = "❌ Orphan — no assignee or reviewer"
        verdict = "orphan"

    return {
        "assignees": assignees,
        "individual_reviewers": individual_reviewers,
        "team_reviewers": team_reviewers,
        "status": status,
        "verdict": verdict,
    }


def find_codeowner(workspaces, codeowners_content):
    """Find CODEOWNERS entry for workspaces."""
    results = {}
    for ws in workspaces:
        matches = []
        for line in codeowners_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ws in line:
                matches.append(line)
        results[ws] = matches
    return results


def assess_checks(pr_data):
    """Assess status checks."""
    checks = pr_data.get("statusCheckRollup") or []
    result = {}
    for c in checks:
        name = c.get("name", c.get("context", "unknown"))
        conclusion = c.get("conclusion", "")
        status = c.get("status", "")
        if conclusion == "SUCCESS" or conclusion == "success":
            icon = "✅"
        elif conclusion == "FAILURE" or conclusion == "failure":
            icon = "❌"
        elif status == "IN_PROGRESS" or status == "QUEUED":
            icon = "⏳"
        else:
            icon = "⚪"
        result[name] = {
            "conclusion": conclusion,
            "status": status,
            "icon": icon,
            "display": f"{icon} {conclusion or status}",
        }
    return result


def check_codeowners_modified(files):
    """Check if CODEOWNERS file is in the changeset."""
    return any(f.get("path", "") == "CODEOWNERS" for f in (files or []))


def check_source_json_modified(files):
    """Check if any source.json is modified."""
    return [f.get("path", "") for f in (files or []) if f.get("path", "").endswith("source.json")]


def compute_staleness(updated_at, priority_key):
    """Compute staleness from updatedAt timestamp."""
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - updated).days
    except (ValueError, AttributeError):
        days = -1

    thresholds = STALENESS_THRESHOLDS.get(priority_key, STALENESS_THRESHOLDS["unknown"])
    if days >= thresholds["alert"]:
        level = "🚨 ALERT"
    elif days >= thresholds["warn"]:
        level = "⚠️ WARN"
    else:
        level = "✅ Fresh"

    return {"days": days, "level": level}


def get_approvals(pr_data):
    """Extract approval reviews."""
    reviews = pr_data.get("reviews") or []
    approvals = []
    for r in reviews:
        if r.get("state") == "APPROVED":
            author = r.get("author", {}).get("login", "unknown")
            approvals.append(author)
    return approvals


def determine_merge_readiness(
    pr_data, checks, assignment, priority_key, codeowners_modified, is_addition
):
    """Determine merge readiness checklist."""
    items = []

    # PR is open
    is_open = pr_data.get("state") == "OPEN"
    items.append(("PR is open", is_open))

    # Publish passed
    publish = checks.get("publish", {})
    publish_passed = publish.get("conclusion", "").lower() == "success"
    items.append(("Publish passed", publish_passed))

    # Smoke tests (optional)
    smoke_keys = [k for k in checks if "smoke" in k.lower() or "workspace-test" in k.lower()]
    if smoke_keys:
        smoke_passed = all(checks[k].get("conclusion", "").lower() == "success" for k in smoke_keys)
        items.append(("Smoke tests passed", smoke_passed))

    # Has individual assignee
    has_assignee = len(assignment["assignees"]) > 0
    items.append(("Assignee present", has_assignee))

    # CODEOWNERS for additions
    if is_addition:
        items.append(("CODEOWNERS entry (addition)", codeowners_modified))

    # Approved
    approvals = get_approvals(pr_data)
    has_approval = len(approvals) > 0
    items.append(("Approved", has_approval))

    # No conflicts
    mergeable = pr_data.get("mergeable", "UNKNOWN")
    no_conflicts = mergeable != "CONFLICTING"
    items.append(("No conflicts", no_conflicts))

    all_pass = all(ok for _, ok in items)
    blockers = [name for name, ok in items if not ok]

    if all_pass:
        badge = "✅ Ready to merge — all checks passing"
    elif len(blockers) <= 2:
        badge = f"⚠️ Almost ready — needs: {', '.join(blockers)}"
    else:
        badge = f"❌ Blocked — {', '.join(blockers)}"

    return {
        "badge": badge,
        "items": items,
        "approvals": approvals,
        "blockers": blockers,
        "ready": all_pass,
    }


def format_relative_time(iso_str):
    """Format ISO timestamp as relative time."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        days = delta.days
        if days == 0:
            hours = delta.seconds // 3600
            return f"{hours} hours ago" if hours > 0 else "just now"
        if days == 1:
            return "1 day ago"
        return f"{days} days ago"
    except (ValueError, AttributeError):
        return iso_str or "unknown"


def suggest_action(readiness, assignment, priority_key, staleness, checks):
    """Generate suggested action."""
    if readiness["ready"]:
        return "Merge when ready, or wait for additional review if desired."

    suggestions = []
    for name, ok in readiness["items"]:
        if ok:
            continue
        if name == "Publish passed":
            publish_check = checks.get("publish", {})
            if not publish_check:
                suggestions.append("Trigger `/publish` comment on the PR.")
            else:
                suggestions.append("Investigate publish failure.")
        elif name == "Assignee present":
            suggestions.append("Assign an individual owner from CODEOWNERS.")
        elif name == "CODEOWNERS entry (addition)":
            suggestions.append("Request CODEOWNERS entry from contributor.")
        elif name == "Approved":
            suggestions.append("Request review from assigned reviewer.")
        elif name == "No conflicts":
            suggestions.append("Rebase PR to resolve merge conflicts.")
        elif name == "Smoke tests passed":
            suggestions.append("Investigate smoke test failures.")

    if staleness["days"] >= STALENESS_THRESHOLDS.get(priority_key, {}).get("alert", 14):
        suggestions.append(f"PR is {staleness['days']} days stale — consider pinging the author.")

    return "\n".join(f"- {s}" for s in suggestions) if suggestions else "Review blockers above."


def build_analysis(pr_number, repo):
    """Build full analysis data structure."""
    pr_data = fetch_pr_context(pr_number, repo)
    if not pr_data:
        print(f"Error: Could not fetch PR #{pr_number}", file=sys.stderr)
        sys.exit(1)

    labels = pr_data.get("labels") or []
    files = pr_data.get("files") or []
    priority_key, priority_label = classify_priority(labels)
    workspaces = extract_workspaces(files)
    assignment = assess_assignment(pr_data)
    checks = assess_checks(pr_data)
    codeowners_content = fetch_codeowners(repo)
    codeowner_entries = find_codeowner(workspaces, codeowners_content)
    codeowners_modified = check_codeowners_modified(files)
    source_json_files = check_source_json_modified(files)
    is_addition = any(lbl["name"] == "workspace-addition" for lbl in labels)
    staleness = compute_staleness(pr_data.get("updatedAt", ""), priority_key)
    approvals = get_approvals(pr_data)
    readiness = determine_merge_readiness(
        pr_data, checks, assignment, priority_key, codeowners_modified, is_addition
    )
    action = suggest_action(readiness, assignment, priority_key, staleness, checks)

    author = pr_data.get("author", {}).get("login", "unknown")

    return {
        "pr_number": pr_data.get("number", pr_number),
        "title": pr_data.get("title", ""),
        "author": author,
        "state": pr_data.get("state", ""),
        "priority_key": priority_key,
        "priority_label": priority_label,
        "labels": [lbl["name"] for lbl in labels],
        "workspaces": workspaces,
        "created_at": pr_data.get("createdAt", ""),
        "updated_at": pr_data.get("updatedAt", ""),
        "created_relative": format_relative_time(pr_data.get("createdAt", "")),
        "updated_relative": format_relative_time(pr_data.get("updatedAt", "")),
        "staleness": staleness,
        "assignment": assignment,
        "codeowner_entries": codeowner_entries,
        "codeowners_modified": codeowners_modified,
        "source_json_modified": source_json_files,
        "checks": {
            name: {"conclusion": v["conclusion"], "status": v["status"], "display": v["display"]}
            for name, v in checks.items()
        },
        "approvals": approvals,
        "mergeable": pr_data.get("mergeable", "UNKNOWN"),
        "readiness": {
            "badge": readiness["badge"],
            "ready": readiness["ready"],
            "checklist": [{"item": name, "passed": ok} for name, ok in readiness["items"]],
            "blockers": readiness["blockers"],
        },
        "suggested_action": action,
    }


def format_markdown(analysis):
    """Format analysis as human-readable markdown."""
    a = analysis
    lines = []
    lines.append(f"## PR #{a['pr_number']} Analysis\n")
    lines.append(f"**Title:** {a['title']}")
    lines.append(f"**Author:** @{a['author']}")
    lines.append(f"**Priority:** {a['priority_label']}")
    lines.append(f"**Created:** {a['created_relative']}")
    lines.append(f"**Last Activity:** {a['updated_relative']}")
    if a["workspaces"]:
        lines.append(f"**Workspaces:** {', '.join(a['workspaces'])}")
    lines.append(f"**Staleness:** {a['staleness']['level']} ({a['staleness']['days']} days)")
    lines.append("")

    # Assignment
    lines.append("### Assignment")
    lines.append("| Status | Details |")
    lines.append("|--------|---------|")
    asgn = a["assignment"]
    lines.append(f"| Assignees | {', '.join('@' + u for u in asgn['assignees']) or '(none)'} |")
    lines.append(
        f"| Individual Reviewers | {', '.join('@' + u for u in asgn['individual_reviewers']) or '(none)'} |"
    )
    if asgn["team_reviewers"]:
        lines.append(f"| Team Reviewers | {', '.join(asgn['team_reviewers'])} |")
    lines.append(f"| Verdict | {asgn['status']} |")
    lines.append("")

    # CODEOWNERS
    if a["codeowner_entries"]:
        lines.append("### CODEOWNERS")
        for ws, entries in a["codeowner_entries"].items():
            if entries:
                lines.append(f"- `{ws}`: {', '.join(entries)}")
            else:
                lines.append(f"- `{ws}`: ❌ No entry found")
        if a.get("source_json_modified"):
            lines.append(
                f"- CODEOWNERS modified in PR: {'✅ Yes' if a['codeowners_modified'] else '❌ No'}"
            )
        lines.append("")

    # Checks
    lines.append("### Checks")
    if a["checks"]:
        lines.append("| Check | Status |")
        lines.append("|-------|--------|")
        for name, info in a["checks"].items():
            lines.append(f"| {name} | {info['display']} |")
    else:
        lines.append("No status checks found.")
    lines.append("")

    # Merge readiness
    lines.append("### Merge Readiness")
    lines.append(f"{a['readiness']['badge']}\n")
    for item in a["readiness"]["checklist"]:
        check = "x" if item["passed"] else " "
        lines.append(f"- [{check}] {item['item']}")
    if a["approvals"]:
        lines.append(f"\nApproved by: {', '.join('@' + u for u in a['approvals'])}")
    lines.append("")

    # Suggested action
    lines.append("### Suggested Action")
    lines.append(a["suggested_action"])
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze a single overlay repository PR.",
        epilog="Example: %(prog)s 1234 --json",
    )
    parser.add_argument("pr_number", type=int, help="PR number to analyze")
    parser.add_argument(
        "--repo",
        default=DEFAULT_REPO,
        help=f"GitHub repository (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output structured JSON instead of markdown",
    )
    args = parser.parse_args()

    # Ensure UTF-8 output on Windows (emoji in priority labels)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    analysis = build_analysis(args.pr_number, args.repo)

    if args.json_output:
        print(json.dumps(analysis, indent=2))
    else:
        print(format_markdown(analysis))


if __name__ == "__main__":
    main()
