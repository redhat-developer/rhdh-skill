#!/usr/bin/env python3
"""RHDH Release CLI — deterministic data gathering for release management.

Gathers facts from Jira, Google Sheets, and local config. The agent routes
to this CLI first, then adds judgment (flag risks, suggest actions).

Usage:
    python scripts/release.py status 1.9.0
    python scripts/release.py status 1.9.0 --json
    python scripts/release.py check
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import jql as jql_mod  # noqa: E402
import slack_templates as slack_mod  # noqa: E402
from formatters import OutputFormatter  # noqa: E402

JIRA_BASE = "https://issues.redhat.com"
SCHEDULE_SHEET_ID = "1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc"
TEAM_SHEET_ID = "1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM"


def _find_parse_issues() -> Path | None:
    """Discover parse_issues.py from installed rhdh-jira skill or sibling directory."""
    candidates = [
        Path.home() / ".claude/skills/rhdh-jira/scripts/parse_issues.py",
        Path(__file__).resolve().parent / "../../rhdh-jira/scripts/parse_issues.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


ISSUE_TYPES = ["Feature", "Epic", "Story", "Task", "Sub-task", "Bug", "Vulnerability", "Weakness"]


def _normalize_team_name(name: str) -> str:
    """Normalize team name for comparison: strip 'RHDH ' prefix, lowercase."""
    n = name.strip()
    if n.lower().startswith("rhdh "):
        n = n[5:]
    return n.lower()


# ---------------------------------------------------------------------------
# Google Sheets helpers (via gog CLI)
# ---------------------------------------------------------------------------


def _gog_sheets_get(sheet_id: str, range_name: str) -> list[list[str]]:
    """Fetch sheet values via gog sheets get --json --results-only."""
    result = subprocess.run(
        ["gog", "sheets", "get", sheet_id, range_name, "--json", "--results-only"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gog sheets get failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _gog_sheets_tabs(sheet_id: str) -> list[str]:
    """Fetch tab names via gog sheets metadata."""
    result = subprocess.run(
        ["gog", "sheets", "metadata", sheet_id, "--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gog sheets metadata failed: {result.stderr.strip()}")
    meta = json.loads(result.stdout)
    return [s["properties"]["title"] for s in meta.get("sheets", [])]


# ---------------------------------------------------------------------------
# Team mapping (from Google Sheets)
# ---------------------------------------------------------------------------


def _parse_teams(
    rows: list[list[str]], category_filter: str | None = None, include_all: bool = False
) -> list[dict]:
    if not rows:
        return []

    header = [h.strip().lower() for h in rows[0]]
    col = {}
    for name in (
        "category",
        "team name",
        "team id",
        "description",
        "status",
        "leads",
        "slack handles",
        "cloud id",
    ):
        for i, h in enumerate(header):
            if h == name:
                col[name] = i
                break

    teams = []
    for row in rows[1:]:

        def cell(name: str) -> str:
            idx = col.get(name)
            if idx is None or idx >= len(row):
                return ""
            return row[idx].strip()

        status = cell("status")
        if not include_all and status.lower() != "active":
            continue

        category = cell("category")
        if category_filter and category.lower() != category_filter.lower():
            continue

        team_id: int | str = cell("team id")
        try:
            team_id = int(team_id)
        except (ValueError, TypeError):
            pass

        slack_handles = cell("slack handles")
        slack_list = (
            [s.strip() for s in slack_handles.split(",") if s.strip()] if slack_handles else []
        )

        teams.append(
            {
                "category": category,
                "team_name": cell("team name"),
                "team_id": team_id,
                "description": cell("description"),
                "status": status,
                "leads": cell("leads"),
                "slack_handles": slack_list,
                "cloud_id": cell("cloud id"),
            }
        )

    return teams


# ---------------------------------------------------------------------------
# Schedule parsing (from Google Sheets)
# ---------------------------------------------------------------------------


def _normalize_version(v: str) -> str:
    """Extract major.minor from strings like 'RHDH 1.6', 'rhdh-1.6', 'v1.6', '1.6'."""
    m = re.search(r"(\d+)\.(\d+)", v)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    return v.strip()


def _parse_date(raw: str) -> str | None:
    """Try common date formats found in Google Sheets."""
    raw = raw.strip()
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%m/%d/%y",
    ):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _row_date(cells: list[str]) -> str | None:
    """Return the first parseable date found in a row's cells, or None."""
    for cell in cells:
        parsed = _parse_date(str(cell))
        if parsed:
            return parsed
    return None


def _find_schedule_tab(tabs: list[str]) -> str | None:
    """Find the best 'Schedule' tab — tries current year, then next, then previous."""
    current_year = datetime.now().year
    for year in [current_year, current_year + 1, current_year - 1]:
        candidates = [t for t in tabs if str(year) in t and "schedule" in t.lower()]
        if candidates:
            return candidates[0]
    fallback = [t for t in tabs if "schedule" in t.lower()]
    return fallback[0] if fallback else None


def _find_milestones(rows: list[list[str]], version: str) -> dict[str, str | None]:
    """Search sheet rows for RHDH version milestones.

    Strategy:
    1. Find the GA row for the target version.
    2. Walk backwards to find Code Freeze and Feature Freeze rows.
    """
    ver = _normalize_version(version)

    ga_keywords = ["ga ", "ga\t", "ga\n", "ga announce", "general availability", "ga date"]
    freeze_keywords = {
        "code_freeze": ["code freeze", "code-freeze", "codefreeze"],
        "feature_freeze": ["feature freeze", "feature-freeze", " ff "],
    }

    ga_index = None
    for i, row in enumerate(rows):
        cells = [str(c) for c in row]
        row_text = " " + " ".join(cells).lower() + " "
        version_match = ver in row_text or (version.lower().replace("rhdh", "").strip() in row_text)
        ga_match = any(kw in row_text for kw in ga_keywords)
        if version_match and ga_match:
            ga_index = i
            break

    if ga_index is None:
        return {}

    ga_date = _row_date([str(c) for c in rows[ga_index]])
    milestones: dict[str, str | None] = {"ga_date": ga_date} if ga_date else {}

    found: dict[str, str] = {}
    for i in range(ga_index - 1, -1, -1):
        cells = [str(c) for c in rows[i]]
        row_text = " " + " ".join(cells).lower() + " "

        if any(kw in row_text for kw in ga_keywords):
            break

        for milestone, keywords in freeze_keywords.items():
            if milestone in found:
                continue
            if any(kw in row_text for kw in keywords):
                d = _row_date(cells)
                if d:
                    found[milestone] = d

        if len(found) == len(freeze_keywords):
            break

    milestones.update(found)
    return milestones


def _fetch_schedule(sheet_id: str, version: str) -> dict:
    """Fetch milestones for a version from a Google Sheets schedule.

    Returns dict with version, tab, feature_freeze, code_freeze, ga_date.
    On error, returns dict with 'error' key.
    """
    try:
        tabs = _gog_sheets_tabs(sheet_id)
    except RuntimeError as e:
        return {"error": str(e)}

    tab = _find_schedule_tab(tabs)
    if not tab:
        return {"error": "no_schedule_tab_found", "tabs": tabs, "spreadsheet_id": sheet_id}

    try:
        rows = _gog_sheets_get(sheet_id, tab)
    except RuntimeError as e:
        return {"error": str(e)}

    milestones = _find_milestones(rows, version)

    ver = _normalize_version(version)
    if not milestones.get("code_freeze") and not milestones.get("ga_date"):
        return {
            "error": "version_not_found",
            "version": ver,
            "tab": tab,
            "spreadsheet_id": sheet_id,
            "hint": "Check that the version string matches the sheet exactly",
        }

    return {
        "version": ver,
        "tab": tab,
        "feature_freeze": milestones.get("feature_freeze"),
        "code_freeze": milestones.get("code_freeze"),
        "ga_date": milestones.get("ga_date"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(
    cmd: list[str], *, check: bool = True, capture: bool = True
) -> subprocess.CompletedProcess:
    """Run a subprocess, capturing output."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


def _parse_acli_count(output: str) -> int:
    """Parse acli --count output like '✓ Number of work items in the search: 42'."""
    for line in reversed(output.strip().splitlines()):
        m = re.search(r"(\d+)\s*$", line)
        if m:
            return int(m.group(1))
    raise ValueError(f"Could not parse count from acli output: {output!r}")


def _acli_count(jql: str, fmt: OutputFormatter) -> int:
    """Run acli --count and return the parsed integer."""
    result = _run(["acli", "jira", "workitem", "search", "--jql", jql, "--count"])
    if fmt.verbose:
        fmt.add_debug("acli_cmd", f"acli jira workitem search --jql {jql!r} --count")
    return _parse_acli_count(result.stdout)


def _acli_json_enriched(
    jql: str,
    *,
    select: str = "key,summary,status,assignee,priority,team",
    limit: int = 1000,
) -> list[dict]:
    """Run acli --json | parse_issues.py --enrich and return parsed list."""
    parse_issues = _find_parse_issues()
    if parse_issues is None:
        raise RuntimeError(
            "parse_issues.py not found. Install the rhdh-jira skill: npx skills add rhdh-jira"
        )
    acli = subprocess.Popen(
        ["acli", "jira", "workitem", "search", "--jql", jql, "--json", "--limit", str(limit)],
        stdout=subprocess.PIPE,
        text=True,
    )
    parse = subprocess.Popen(
        [sys.executable, str(parse_issues), "--enrich", "-s", select, "--json"],
        stdin=acli.stdout,
        stdout=subprocess.PIPE,
        text=True,
    )
    if acli.stdout:
        acli.stdout.close()
    stdout, _ = parse.communicate()
    acli.wait()
    if parse.returncode != 0:
        raise RuntimeError(f"parse_issues.py failed (exit {parse.returncode})")
    issues = json.loads(stdout)
    if len(issues) >= limit:
        print(f"WARNING: Results may be truncated at limit={limit}", file=sys.stderr)
    return issues


def _acli_view_json(issue_key: str) -> dict:
    """Fetch a single Jira issue as JSON."""
    result = _run(["acli", "jira", "workitem", "view", issue_key, "--json"])
    return json.loads(result.stdout)


def _fetch_teams(category: str | None = None) -> list[dict]:
    """Fetch team mapping from Google Sheets via gog."""
    rows = _gog_sheets_get(TEAM_SHEET_ID, "Team")
    if not rows:
        raise RuntimeError("Team sheet is empty")
    return _parse_teams(rows, category_filter=category)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_check(_args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Verify prerequisites: acli, .jira-token, gog, gog-auth."""
    checks = []

    acli_path = shutil.which("acli")
    checks.append(
        {
            "name": "acli",
            "status": "pass" if acli_path else "fail",
            "message": acli_path or "not found on PATH",
        }
    )

    token_file = Path.home() / ".jira-token"
    checks.append(
        {
            "name": ".jira-token",
            "status": "pass" if token_file.exists() else "warn",
            "message": str(token_file)
            if token_file.exists()
            else "missing (optional — acli may authenticate via other methods)",
        }
    )

    gog_path = shutil.which("gog")
    checks.append(
        {
            "name": "gog",
            "status": "pass" if gog_path else "warn",
            "message": gog_path or "not found (needed for Google Sheets/Docs)",
        }
    )

    gog_auth_ok = False
    if gog_path:
        try:
            result = _run(
                ["gog", "sheets", "metadata", TEAM_SHEET_ID, "--json"],
                check=False,
            )
            gog_auth_ok = result.returncode == 0
        except Exception:
            gog_auth_ok = False
    checks.append(
        {
            "name": "gog-auth",
            "status": "pass" if gog_auth_ok else "warn",
            "message": "authenticated" if gog_auth_ok else "run: gog auth add <email>",
        }
    )

    if acli_path:
        try:
            result = _run(
                ["acli", "jira", "workitem", "search", "--jql", "project=RHIDP", "--count"],
                check=False,
            )
            jira_ok = result.returncode == 0
        except Exception:
            jira_ok = False
        checks.append(
            {
                "name": "jira-connectivity",
                "status": "pass" if jira_ok else "fail",
                "message": "connected" if jira_ok else "acli cannot reach Jira",
            }
        )

    all_pass = all(c["status"] == "pass" for c in checks)
    has_fail = any(c["status"] == "fail" for c in checks)

    for c in checks:
        if c["status"] == "pass":
            fmt.log_ok(f"{c['name']}: {c['message']}")
        elif c["status"] == "warn":
            fmt.log_warn(f"{c['name']}: {c['message']}")
        else:
            fmt.log_fail(f"{c['name']}: {c['message']}")

    next_steps = []
    if has_fail:
        next_steps.append("Fix failing checks before running other commands")
    if not all_pass:
        next_steps.append("See: references/config.md for setup instructions")

    fmt.success({"checks": checks, "all_pass": all_pass}, next_steps=next_steps or None)
    if has_fail:
        sys.exit(1)


def cmd_dates(_args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Retrieve active release dates from Jira."""
    jql = jql_mod.render("active_release")
    result = _run(["acli", "jira", "workitem", "search", "--jql", jql, "--json"])
    issues = json.loads(result.stdout)

    releases = []
    for issue in issues:
        key = issue.get("key", "")
        summary = issue.get("fields", {}).get("summary", "")

        detail = _acli_view_json(key)
        desc = ""
        desc_field = detail.get("fields", {}).get("description", {})
        if isinstance(desc_field, dict):
            desc = json.dumps(desc_field)
        elif isinstance(desc_field, str):
            desc = desc_field

        dates = {}
        for label in ["Feature Freeze", "Code Freeze", "Doc Freeze", "Go/No Go", "GA Announce"]:
            m = re.search(rf"{re.escape(label)}[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})", desc)
            dates[label.lower().replace(" ", "_").replace("/", "_")] = m.group(1) if m else "TBD"

        version_m = re.search(r"(\d+\.\d+(?:\.\d+)?)", summary)
        if not version_m:
            continue
        version = version_m.group(1)

        releases.append(
            {
                "version": version,
                "issue_key": key,
                "issue_url": f"{JIRA_BASE}/browse/{key}",
                **dates,
            }
        )

    fmt.header("Active Release Dates")
    for r in releases:
        fmt.log_info(f"RHDH {r['version']} ({r['issue_key']})")
        for dk in ["feature_freeze", "code_freeze", "doc_freeze", "go_no_go", "ga_announce"]:
            label = dk.replace("_", " ").title()
            fmt.log_ok(f"  {label}: {r[dk]}") if r[dk] != "TBD" else fmt.log_warn(f"  {label}: TBD")

    fmt.success({"releases": releases})


def cmd_future_dates(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Retrieve future release dates from Google Sheets schedule."""
    version = args.version

    schedule = _fetch_schedule(SCHEDULE_SHEET_ID, version)
    if "error" in schedule:
        fmt.error(
            "SCHEDULE_ERROR",
            str(schedule["error"]),
            next_steps=[
                schedule.get("hint", "Check gog auth: gog auth add <email>"),
            ],
        )
        sys.exit(1)

    fmt.header(f"RHDH {version} Schedule")
    for key in ["feature_freeze", "code_freeze", "ga_date"]:
        label = key.replace("_", " ").title()
        val = schedule.get(key, "N/A")
        fmt.log_info(f"{label}: {val}")

    schedule["schedule_url"] = f"https://docs.google.com/spreadsheets/d/{SCHEDULE_SHEET_ID}/edit"
    fmt.success({"schedule": schedule})


def cmd_status(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Show open issue counts by type for a release version."""
    version = args.version
    rows = []

    fmt.header(f"RHDH {version} — Release Status")

    total = 0
    for issue_type in ISSUE_TYPES:
        jql, url = jql_mod.render_with_url(
            "open_issues_by_type", version=version, issue_type=issue_type
        )
        count = _acli_count(jql, fmt)
        total += count
        rows.append(
            {
                "issue_type": issue_type,
                "count": count,
                "jira_url": url,
            }
        )
        fmt.log_info(f"{issue_type:<15} {count:>5}  {url}")

    _, total_url = jql_mod.render_with_url("open_issues", version=version)
    fmt.log_info(f"{'Total':<15} {total:>5}  {total_url}")

    recently_jql, recently_url = jql_mod.render_with_url(
        "features_added_to_release", version=version
    )
    recently_count = _acli_count(recently_jql, fmt)

    fmt.success(
        {
            "version": version,
            "issue_counts": rows,
            "total": total,
            "total_jira_url": total_url,
            "recently_added_features": recently_count,
            "recently_added_url": recently_url,
        }
    )


def cmd_teams(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """List teams and leads from Google Sheets."""
    teams = _fetch_teams(category=args.category)

    fmt.header("RHDH Teams")
    for t in teams:
        slack = ", ".join(t.get("slack_handles", []))
        fmt.log_info(f"{t['team_name']:<25} {t.get('leads', ''):<20} {slack}")

    fmt.success(
        {
            "teams": teams,
            "count": len(teams),
            "source_url": "https://docs.google.com/spreadsheets/d/1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM/edit",
        }
    )


def cmd_team_breakdown(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Per-team issue counts for a release (requires parse_issues.py --enrich)."""
    version = args.version
    jql = jql_mod.render("open_issues", version=version)
    issues = _acli_json_enriched(jql, select="key,summary,status,team")

    teams = _fetch_teams(category="Engineering")

    counts: dict[str, int] = {}
    for issue in issues:
        team = issue.get("team", "Unassigned") or "Unassigned"
        norm = _normalize_team_name(team)
        counts[norm] = counts.get(norm, 0) + 1

    rows = []
    for t in teams:
        name = t["team_name"]
        norm = _normalize_team_name(name)
        count = counts.pop(norm, 0)
        rows.append(
            {
                "team_name": name,
                "team_id": t.get("team_id"),
                "count": count,
                "leads": t.get("leads", ""),
                "slack_handles": t.get("slack_handles", []),
            }
        )

    matched_norms = {_normalize_team_name(t["team_name"]) for t in teams}
    for norm_name, count in sorted(counts.items()):
        if norm_name not in matched_norms:
            rows.append({"team_name": norm_name, "count": count})

    fmt.header(f"RHDH {version} — Issues by Team")
    for r in rows:
        fmt.log_info(f"{r['team_name']:<25} {r['count']:>5}")

    _, total_url = jql_mod.render_with_url("open_issues", version=version)
    fmt.success(
        {
            "version": version,
            "team_breakdown": rows,
            "total": sum(r["count"] for r in rows),
            "total_jira_url": total_url,
        }
    )


def cmd_blockers(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """List open blocker bugs for a release."""
    version = args.version
    jql, url = jql_mod.render_with_url("blockers", version=version)
    issues = _acli_json_enriched(jql, select="key,summary,status,assignee,priority,team")
    count = len(issues)

    fmt.header(f"RHDH {version} — Blocker Bugs")
    for issue in issues:
        fmt.log_info(
            f"[{issue['key']}]({JIRA_BASE}/browse/{issue['key']}) "
            f"{issue.get('summary', '')[:60]} — {issue.get('assignee', 'Unassigned')}"
        )
    fmt.success(
        {
            "version": version,
            "blockers": issues,
            "count": count,
            "jira_url": url,
        }
    )


def cmd_epics(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """List outstanding Engineering EPICs for a release."""
    version = args.version
    jql, url = jql_mod.render_with_url("epics", version=version)
    issues = _acli_json_enriched(jql, select="key,summary,status,assignee")
    count = len(issues)

    fmt.header(f"RHDH {version} — Outstanding EPICs")
    for issue in issues:
        fmt.log_info(
            f"[{issue['key']}]({JIRA_BASE}/browse/{issue['key']}) "
            f"{issue.get('summary', '')[:60]} — {issue.get('status', '')}"
        )

    fmt.success(
        {
            "version": version,
            "epics": issues,
            "count": count,
            "jira_url": url,
        }
    )


def cmd_cves(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """List CVE issues for a release."""
    version = args.version
    jql, url = jql_mod.render_with_url("cves", version=version)
    issues = _acli_json_enriched(jql, select="key,summary,status,priority,assignee,issuetype")
    count = len(issues)

    fmt.header(f"RHDH {version} — CVEs")
    for issue in issues:
        fmt.log_info(
            f"[{issue['key']}]({JIRA_BASE}/browse/{issue['key']}) "
            f"{issue.get('summary', '')[:60]} — {issue.get('priority', '')}"
        )

    fmt.success(
        {
            "version": version,
            "cves": issues,
            "count": count,
            "jira_url": url,
        }
    )


def cmd_notes(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Count issues missing Release Note Type."""
    version = args.version
    jql, url = jql_mod.render_with_url("release_notes", version=version)
    count = _acli_count(jql, fmt)

    dashboard_url = "https://issues.redhat.com/secure/Dashboard.jspa?selectPageId=12382090"

    fmt.header(f"RHDH {version} — Release Notes")
    fmt.log_info(f"Outstanding: {count} issues missing Release Note Type")
    fmt.log_info(f"Dashboard: {dashboard_url}")

    fmt.success(
        {
            "version": version,
            "outstanding_count": count,
            "jira_url": url,
            "dashboard_url": dashboard_url,
        }
    )


# ---------------------------------------------------------------------------
# Slack subcommands
# ---------------------------------------------------------------------------


def _get_freeze_date(version: str, date_key: str) -> str:
    """Get a freeze date from active release issues. Returns date or 'TBD'."""
    jql = jql_mod.render("active_release")
    result = _run(["acli", "jira", "workitem", "search", "--jql", jql, "--json"])
    issues = json.loads(result.stdout)

    for issue in issues:
        summary = issue.get("fields", {}).get("summary", "")
        if version in summary:
            detail = _acli_view_json(issue["key"])
            desc_field = detail.get("fields", {}).get("description", {})
            desc = json.dumps(desc_field) if isinstance(desc_field, dict) else str(desc_field or "")
            m = re.search(rf"{re.escape(date_key)}[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})", desc)
            if m:
                return m.group(1)
    return "TBD"


def cmd_slack_feature_freeze_update(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Generate Feature Freeze Update Slack message."""
    version = args.version

    ff_date = _get_freeze_date(version, "Feature Freeze")
    teams = _fetch_teams(category="Engineering")

    rn_jql, rn_url = jql_mod.render_with_url("release_notes", version=version)
    rn_count = _acli_count(rn_jql, fmt)

    ff_jql = jql_mod.render("feature_freeze_issues", version=version)
    issues = _acli_json_enriched(ff_jql, select="key,summary,status,team")

    team_counts: dict[str, int] = {}
    for issue in issues:
        team = issue.get("team", "Unassigned") or "Unassigned"
        norm = _normalize_team_name(team)
        team_counts[norm] = team_counts.get(norm, 0) + 1

    team_lines = []
    for t in teams:
        name = t["team_name"]
        norm = _normalize_team_name(name)
        count = team_counts.get(norm, 0)
        slack_handles = t.get("slack_handles", [])
        lead_slack = slack_handles[0] if slack_handles else t.get("leads", "")
        team_lines.append(
            {
                "TEAM_NAME": name,
                "ISSUE_COUNT": str(count),
                "JIRA_LINK": jql_mod.jira_url(ff_jql),
                "LEAD_SLACK": lead_slack,
            }
        )

    template = slack_mod.get_template("feature_freeze_update")
    template = slack_mod.fill_placeholders(
        template,
        {
            "RELEASE_VERSION": version,
            "FEATURE_FREEZE_DATE": ff_date,
            "OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT": str(rn_count),
            "RELEASE_NOTES_JIRA_LINK": rn_url,
        },
    )
    message = slack_mod.expand_team_lines(template, team_lines)

    fmt.render_raw(f"```slack\n{message}\n```")
    fmt.success(
        {
            "version": version,
            "feature_freeze_date": ff_date,
            "outstanding_release_notes": rn_count,
            "team_counts": {t["TEAM_NAME"]: int(t["ISSUE_COUNT"]) for t in team_lines},
            "slack_message": message,
        }
    )


def cmd_slack_feature_freeze(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Generate Feature Freeze Announcement Slack message."""
    version = args.version

    epics_jql, epics_url = jql_mod.render_with_url("epics", version=version)
    epics_count = _acli_count(epics_jql, fmt)

    cves_jql, cves_url = jql_mod.render_with_url("cves", version=version)
    cves_count = _acli_count(cves_jql, fmt)

    rn_jql, rn_url = jql_mod.render_with_url("release_notes", version=version)
    rn_count = _acli_count(rn_jql, fmt)

    template = slack_mod.get_template("feature_freeze")

    lines = template.splitlines()
    filled: list[str] = []
    for line in lines:
        if "{{EPIC_ISSUE_COUNT}}" in line:
            line = line.replace("{{EPIC_ISSUE_COUNT}}", str(epics_count))
            line = line.replace("{{JIRA_LINK}}", epics_url)
        elif "{{CVE_ISSUE_COUNT}}" in line:
            line = line.replace("{{CVE_ISSUE_COUNT}}", str(cves_count))
            line = line.replace("{{JIRA_LINK}}", cves_url)
        elif "{{OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT}}" in line:
            line = line.replace("{{OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT}}", str(rn_count))
            line = line.replace("{{JIRA_LINK}}", rn_url)
        line = line.replace("{{RELEASE_VERSION}}", version)
        filled.append(line)
    message = "\n".join(filled)

    fmt.render_raw(f"```slack\n{message}\n```")
    fmt.success(
        {
            "version": version,
            "epics_count": epics_count,
            "cves_count": cves_count,
            "outstanding_release_notes": rn_count,
            "slack_message": message,
        }
    )


def cmd_slack_code_freeze_update(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Generate Code Freeze Update Slack message."""
    version = args.version

    cf_date = _get_freeze_date(version, "Code Freeze")
    teams = _fetch_teams(category="Engineering")

    rn_jql, rn_url = jql_mod.render_with_url("release_notes", version=version)
    rn_count = _acli_count(rn_jql, fmt)

    fs_jql, fs_url = jql_mod.render_with_url("feature_subtasks", version=version)
    fs_count = _acli_count(fs_jql, fmt)

    cf_jql = jql_mod.render("code_freeze_issues", version=version)
    issues = _acli_json_enriched(cf_jql, select="key,summary,status,team")

    team_counts: dict[str, int] = {}
    for issue in issues:
        team = issue.get("team", "Unassigned") or "Unassigned"
        norm = _normalize_team_name(team)
        team_counts[norm] = team_counts.get(norm, 0) + 1

    team_lines = []
    for t in teams:
        name = t["team_name"]
        norm = _normalize_team_name(name)
        count = team_counts.get(norm, 0)
        slack_handles = t.get("slack_handles", [])
        lead_slack = slack_handles[0] if slack_handles else t.get("leads", "")
        team_lines.append(
            {
                "TEAM_NAME": name,
                "TEAM_ISSUE_COUNT": str(count),
                "JIRA_LINK": jql_mod.jira_url(cf_jql),
                "LEAD_SLACK": lead_slack,
            }
        )

    template = slack_mod.get_template("code_freeze_update")
    template = slack_mod.fill_placeholders(
        template,
        {
            "RELEASE_VERSION": version,
            "CODE_FREEZE_DATE": cf_date,
            "OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT": str(rn_count),
            "RELEASE_NOTES_JIRA_LINK": rn_url,
            "FEATURE_SUBTASK_ISSUE_COUNT": str(fs_count),
            "FEATURE_SUBTASK_JIRA_LINK": fs_url,
        },
    )
    message = slack_mod.expand_team_lines(template, team_lines)

    fmt.render_raw(f"```slack\n{message}\n```")
    fmt.success(
        {
            "version": version,
            "code_freeze_date": cf_date,
            "outstanding_release_notes": rn_count,
            "feature_subtasks": fs_count,
            "team_counts": {t["TEAM_NAME"]: int(t["TEAM_ISSUE_COUNT"]) for t in team_lines},
            "slack_message": message,
        }
    )


def cmd_slack_code_freeze(args: argparse.Namespace, fmt: OutputFormatter) -> None:
    """Generate Code Freeze Announcement Slack message."""
    version = args.version

    blocker_jql, blocker_url = jql_mod.render_with_url("blockers", version=version)
    blocker_count = _acli_count(blocker_jql, fmt)

    demos_jql, demos_url = jql_mod.render_with_url("feature_demos", version=version)
    demos_count = _acli_count(demos_jql, fmt)

    testday_jql, testday_url = jql_mod.render_with_url("test_day_features", version=version)
    testday_count = _acli_count(testday_jql, fmt)

    open_jql, open_url = jql_mod.render_with_url("open_issues", version=version)
    open_count = _acli_count(open_jql, fmt)

    template = slack_mod.get_template("code_freeze")

    lines = template.splitlines()
    filled: list[str] = []
    for line in lines:
        if "{{BLOCKER_BUG_ISSUE_COUNT}}" in line:
            line = line.replace("{{BLOCKER_BUG_ISSUE_COUNT}}", str(blocker_count))
            line = line.replace("{{JIRA_LINK}}", blocker_url)
        elif "{{FEATURE_DEMO_ISSUE_COUNT}}" in line:
            line = line.replace("{{FEATURE_DEMO_ISSUE_COUNT}}", str(demos_count))
            line = line.replace("{{JIRA_LINK}}", demos_url)
        elif "{{TEST_DAY_FEATURE_ISSUE_COUNT}}" in line:
            line = line.replace("{{TEST_DAY_FEATURE_ISSUE_COUNT}}", str(testday_count))
            line = line.replace("{{JIRA_LINK}}", testday_url)
        elif "{{OPEN_ISSUE_COUNT}}" in line:
            line = line.replace("{{OPEN_ISSUE_COUNT}}", str(open_count))
            line = line.replace("{{JIRA_LINK}}", open_url)
        line = line.replace("{{RELEASE_VERSION}}", version)
        filled.append(line)
    message = "\n".join(filled)

    fmt.render_raw(f"```slack\n{message}\n```")
    fmt.success(
        {
            "version": version,
            "blocker_bugs": blocker_count,
            "feature_demos": demos_count,
            "test_day_features": testday_count,
            "open_issues": open_count,
            "slack_message": message,
        }
    )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release",
        description="RHDH Release CLI — deterministic data gathering for release management.",
    )
    parser.add_argument("--json", action="store_const", const="json", dest="output_mode")
    parser.add_argument("--human", action="store_const", const="human", dest="output_mode")
    parser.add_argument("--verbose", "-v", action="store_true")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Verify prerequisites")

    sub.add_parser("dates", help="Active release dates from Jira")

    p = sub.add_parser("future-dates", help="Schedule from Google Sheets")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = sub.add_parser("status", help="Issue counts by type")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = sub.add_parser("teams", help="Team mapping from Google Sheets")
    p.add_argument("--category", help="Filter by category (e.g. Engineering)")

    p = sub.add_parser("team-breakdown", help="Per-team issue counts")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = sub.add_parser("blockers", help="Blocker bug details")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = sub.add_parser("epics", help="Outstanding EPICs")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = sub.add_parser("cves", help="CVE list")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = sub.add_parser("notes", help="Missing release notes count")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    slack_parser = sub.add_parser("slack", help="Slack announcement templates")
    slack_sub = slack_parser.add_subparsers(dest="slack_command")

    p = slack_sub.add_parser("feature-freeze-update", help="Feature Freeze status update")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = slack_sub.add_parser("feature-freeze", help="Feature Freeze announcement")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = slack_sub.add_parser("code-freeze-update", help="Code Freeze status update")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    p = slack_sub.add_parser("code-freeze", help="Code Freeze announcement")
    p.add_argument("version", help="Release version (e.g. 1.9.0)")

    return parser


COMMANDS = {
    "check": cmd_check,
    "dates": cmd_dates,
    "future-dates": cmd_future_dates,
    "status": cmd_status,
    "teams": cmd_teams,
    "team-breakdown": cmd_team_breakdown,
    "blockers": cmd_blockers,
    "epics": cmd_epics,
    "cves": cmd_cves,
    "notes": cmd_notes,
}

SLACK_COMMANDS = {
    "feature-freeze-update": cmd_slack_feature_freeze_update,
    "feature-freeze": cmd_slack_feature_freeze,
    "code-freeze-update": cmd_slack_code_freeze_update,
    "code-freeze": cmd_slack_code_freeze,
}


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    mode = args.output_mode or "auto"
    fmt = OutputFormatter(mode=mode, verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        if fmt.is_human:
            print("\nQuick start:")
            print("  release check              # verify prerequisites")
            print("  release status 1.9.0       # issue counts by type")
            print("  release dates              # active release dates")
        sys.exit(0)

    if args.command == "slack":
        if not args.slack_command:
            fmt.error(
                "MISSING_SUBCOMMAND",
                "slack requires a subcommand: " + ", ".join(sorted(SLACK_COMMANDS)),
            )
            sys.exit(1)
        handler = SLACK_COMMANDS.get(args.slack_command)
    else:
        handler = COMMANDS.get(args.command)

    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args, fmt)
    except subprocess.CalledProcessError as e:
        fmt.error(
            "COMMAND_FAILED",
            f"{' '.join(e.cmd)} exited {e.returncode}: {(e.stderr or '').strip()}",
            next_steps=["Run: python scripts/release.py check"],
        )
        sys.exit(1)
    except RuntimeError as e:
        fmt.error("RUNTIME_ERROR", str(e), next_steps=["Run: python scripts/release.py check"])
        sys.exit(1)


if __name__ == "__main__":
    main()
