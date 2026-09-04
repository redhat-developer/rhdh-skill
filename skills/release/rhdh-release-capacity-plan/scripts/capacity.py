#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Compute RHDH release-horizon capacity ledgers.

Reads a JSON snapshot (stdin or --input). Does not call Jira. The agent gathers
sprint samples, roster availability, remaining sprints, and candidate Features,
then this script does the arithmetic.

Usage:
  uv run scripts/capacity.py --help
  uv run scripts/capacity.py --input snapshot.json
  uv run scripts/capacity.py < snapshot.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

COMPLETED_STATUSES = frozenset({"closed", "release pending"})
COVERAGE_FLOOR = 0.5
DEFAULT_MEETING_FACTOR = 0.4
SPRINT_LENGTH_DAYS = 14

# Placeholder Fibonacci buckets until Size→SP is calibrated. Same map for
# Feature and Epic T-shirts. Never treat the Size field's 1–5 as SP, and never
# multiply T-shirt sprint-effort by whole-team velocity (XS is not 2 × 85).
TSHIRT_PLACEHOLDER_SP = {
    "XS": 3.0,
    "S": 5.0,
    "M": 8.0,
    "L": 13.0,
    "XL": 21.0,
}
TSHIRT_PLACEHOLDER_NOTE = (
    "placeholder: T-shirt→SP is XS=3, S=5, M=8, L=13, XL=21; not sprint-effort "
    "× team velocity and not the Size field's 1–5"
)


def _fail(message: str, code: int = 1) -> None:
    json.dump({"ok": False, "error": message}, sys.stdout)
    sys.stdout.write("\n")
    raise SystemExit(code)


def emit(payload: dict[str, Any], stream=None) -> None:
    target = sys.stdout if stream is None else stream
    indent = 2 if target.isatty() else None
    json.dump(payload, target, indent=indent)
    target.write("\n")


def parse_date(value: str) -> date:
    text = value.strip()
    if "T" in text:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    return date.fromisoformat(text[:10])


def remaining_sprints(
    today: date,
    code_freeze: date,
    *,
    sprint_days: int = SPRINT_LENGTH_DAYS,
) -> int:
    if code_freeze <= today:
        return 0
    return math.ceil((code_freeze - today).days / sprint_days)


def _is_completed(status: str | None) -> bool:
    return (status or "").strip().lower() in COMPLETED_STATUSES


def _points(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _size_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    return text or None


def _estimate_from_greenhopper_issue(issue: dict[str, Any]) -> float | None:
    current = issue.get("currentEstimate")
    if current is not None:
        return _points(current)
    stat = issue.get("estimateStatistic") or {}
    field = stat.get("statFieldValue") or {}
    return _points(field.get("value"))


def empty_sprint_metrics() -> dict[str, Any]:
    return {
        "completed_sp": 0.0,
        "interrupt_sp": 0.0,
        "planned_completed_sp": 0.0,
        "completed_count": 0,
        "interrupt_count": 0,
        "planned_completed_count": 0,
        "pointed_count": 0,
        "issue_count": 0,
        "interrupt_rate": 0.0,
    }


def sprint_from_issues(issues: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = empty_sprint_metrics()
    metrics["issue_count"] = len(issues)
    for issue in issues:
        points = _points(issue.get("story_points"))
        if points is not None:
            metrics["pointed_count"] += 1
        else:
            points = 0.0
        added = bool(issue.get("added_after_start"))
        completed = _is_completed(str(issue.get("status") or ""))
        if added:
            metrics["interrupt_sp"] += points
            metrics["interrupt_count"] += 1
        if completed:
            metrics["completed_sp"] += points
            metrics["completed_count"] += 1
            if not added:
                metrics["planned_completed_sp"] += points
                metrics["planned_completed_count"] += 1
    metrics["interrupt_rate"] = metrics["interrupt_sp"] / max(metrics["completed_sp"], 1.0)
    return metrics


def sprint_from_greenhopper(report: dict[str, Any]) -> dict[str, Any]:
    contents = report.get("contents") or {}
    added = {
        str(key) for key, flag in (contents.get("issueKeysAddedDuringSprint") or {}).items() if flag
    }
    completed = list(contents.get("completedIssues") or [])
    incomplete = list(contents.get("issuesNotCompletedInCurrentSprint") or [])
    punted = list(contents.get("puntedIssues") or [])
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in (*completed, *incomplete, *punted):
        key = str(raw.get("key") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        status = raw.get("statusName") or ("Closed" if raw in completed else "To Do")
        issues.append(
            {
                "key": key,
                "story_points": _estimate_from_greenhopper_issue(raw),
                "status": status,
                "added_after_start": key in added,
            }
        )
    for key in added:
        if key in seen:
            continue
        issues.append(
            {
                "key": key,
                "story_points": None,
                "status": "Unknown",
                "added_after_start": True,
            }
        )
    return sprint_from_issues(issues)


def normalize_sprint(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("greenhopper_sprintreport"):
        metrics = sprint_from_greenhopper(raw["greenhopper_sprintreport"])
        source = "greenhopper"
    elif raw.get("issues") is not None:
        metrics = sprint_from_issues(list(raw["issues"]))
        source = str(raw.get("source") or "reconstructed")
    else:
        metrics = empty_sprint_metrics()
        for key in metrics:
            if key in raw:
                metrics[key] = raw[key]
        completed_sp = float(metrics["completed_sp"] or 0)
        metrics["interrupt_rate"] = float(metrics.get("interrupt_rate") or 0)
        if not metrics["interrupt_rate"]:
            metrics["interrupt_rate"] = float(metrics["interrupt_sp"] or 0) / max(completed_sp, 1.0)
        source = str(raw.get("source") or "precomputed")
    sprint = {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "source": source,
        "burndown_url": raw.get("burndown_url"),
        **metrics,
    }
    return sprint


def tshirt_sp(size: str | None) -> float | None:
    key = _size_key(size)
    if key is None or key not in TSHIRT_PLACEHOLDER_SP:
        return None
    return TSHIRT_PLACEHOLDER_SP[key]


def demand_from_features(features: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    unsized: list[str] = []
    total = 0.0
    required = 0.0
    stretch_total = 0.0
    used_placeholder = False
    for feature in features:
        key = str(feature.get("key") or "")
        stretch = bool(feature.get("stretch"))
        epics = list(feature.get("epics") or [])
        basis: str
        sp: float | None = 0.0
        placeholder = False
        if epics:
            basis = "epics"
            epic_sp = 0.0
            any_estimate = False
            for epic in epics:
                child = _points(epic.get("story_points"))
                if child is not None:
                    epic_sp += child
                    any_estimate = True
                    continue
                sized = tshirt_sp(epic.get("size"))
                if sized is None:
                    unsized.append(str(epic.get("key") or key))
                    continue
                epic_sp += sized
                any_estimate = True
                placeholder = True
            sp = epic_sp if any_estimate else None
        else:
            sized = tshirt_sp(feature.get("size"))
            if sized is None:
                basis = "unsized"
                sp = None
                if key:
                    unsized.append(key)
            else:
                basis = "feature_tshirt"
                sp = sized
                placeholder = True
        used_placeholder = used_placeholder or placeholder
        row = {
            "key": key,
            "summary": feature.get("summary"),
            "size": feature.get("size"),
            "stretch": stretch,
            "basis": basis,
            "sp": sp,
            "tshirt_placeholder": placeholder,
            "epics": [
                {
                    "key": epic.get("key"),
                    "summary": epic.get("summary"),
                    "size": epic.get("size"),
                    "story_points": _points(epic.get("story_points")),
                }
                for epic in epics
            ],
        }
        items.append(row)
        if sp is None:
            continue
        total += sp
        if stretch:
            stretch_total += sp
        else:
            required += sp
    return {
        "items": items,
        "total_sp": total,
        "required_sp": required,
        "stretch_sp": stretch_total,
        "unsized": sorted(set(unsized)),
        "tshirt_placeholder": used_placeholder,
        "tshirt_placeholder_note": TSHIRT_PLACEHOLDER_NOTE if used_placeholder else None,
        "tshirt_placeholder_sp": dict(TSHIRT_PLACEHOLDER_SP) if used_placeholder else None,
    }


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.4g}"


def compute(snapshot: dict[str, Any]) -> dict[str, Any]:
    team = snapshot.get("team")
    version = snapshot.get("version")
    if not team:
        _fail("snapshot.team is required")
    if not version:
        _fail("snapshot.version is required")

    meeting_factor = float(snapshot.get("meeting_factor", DEFAULT_MEETING_FACTOR))
    if meeting_factor < 0 or meeting_factor >= 1:
        _fail("meeting_factor must be in [0, 1)")

    members = list(snapshot.get("members") or [])
    if not members:
        _fail("snapshot.members must list FULL_MEMBER roster entries")
    available_people = 0.0
    for member in members:
        availability = float(member.get("availability", 1.0))
        if availability < 0:
            _fail("member availability cannot be negative")
        available_people += availability
    headcount = len(members)
    availability_factor = available_people / headcount if headcount else 0.0

    remaining = snapshot.get("remaining_sprints")
    today_raw = snapshot.get("today")
    freeze_raw = snapshot.get("code_freeze")
    if remaining is None:
        if not today_raw or not freeze_raw:
            _fail("remaining_sprints, or both today and code_freeze, is required")
        remaining = remaining_sprints(parse_date(str(today_raw)), parse_date(str(freeze_raw)))
    remaining_n = int(remaining)
    if remaining_n < 0:
        _fail("remaining_sprints cannot be negative")

    sprints = [normalize_sprint(raw) for raw in (snapshot.get("sprints") or [])]
    if not sprints:
        _fail("snapshot.sprints must include at least one sample sprint")

    pointed = sum(int(s["pointed_count"]) for s in sprints)
    issues = sum(int(s["issue_count"]) for s in sprints)
    coverage = (pointed / issues) if issues else 0.0
    use_counts = coverage < COVERAGE_FLOOR
    unit = "issues" if use_counts else "sp"

    if use_counts:
        planned_samples = [float(s["planned_completed_count"]) for s in sprints]
        completed_samples = [float(s["completed_count"]) for s in sprints]
        interrupt_total = sum(float(s["interrupt_count"]) for s in sprints)
        completed_total = sum(float(s["completed_count"]) for s in sprints)
    else:
        planned_samples = [float(s["planned_completed_sp"]) for s in sprints]
        completed_samples = [float(s["completed_sp"]) for s in sprints]
        interrupt_total = sum(float(s["interrupt_sp"]) for s in sprints)
        completed_total = sum(float(s["completed_sp"]) for s in sprints)

    mean_planned = _mean(planned_samples)
    mean_completed = _mean(completed_samples)
    interrupt_rate = interrupt_total / max(completed_total, 1.0)

    historical_net = mean_planned * remaining_n * availability_factor
    historical_arithmetic = (
        f"{_fmt(mean_planned)} × {_fmt(remaining_n)} × {_fmt(availability_factor)}"
        f" = {_fmt(historical_net)}"
    )

    user_rate = snapshot.get("sp_per_person_sprint")
    if user_rate is not None:
        full_focus = float(user_rate)
        rate_source = "user_full_focus"
    else:
        observed = mean_completed / headcount if headcount else 0.0
        denominator = (1.0 - meeting_factor) * (1.0 - interrupt_rate)
        if denominator <= 0:
            _fail(
                "cannot back out a full-focus rate: meeting_factor and interrupt_rate leave no remainder"
            )
        full_focus = observed / denominator
        rate_source = "inferred_backed_out"

    theoretical_net = (
        available_people
        * remaining_n
        * full_focus
        * (1.0 - meeting_factor)
        * (1.0 - interrupt_rate)
    )
    theoretical_arithmetic = (
        f"{_fmt(available_people)} × {_fmt(remaining_n)} × {_fmt(full_focus)}"
        f" × {_fmt(1.0 - meeting_factor)} × {_fmt(1.0 - interrupt_rate)}"
        f" = {_fmt(theoretical_net)}"
    )

    demand = demand_from_features(list(snapshot.get("features") or []))
    required = float(demand["required_sp"])
    total_demand = float(demand["total_sp"])

    return {
        "ok": True,
        "team": team,
        "version": version,
        "board_id": snapshot.get("board_id"),
        "unit": unit,
        "coverage": coverage,
        "coverage_warning": use_counts,
        "meeting_factor": meeting_factor,
        "interrupt_rate": interrupt_rate,
        "remaining_sprints": remaining_n,
        "feature_freeze": snapshot.get("feature_freeze"),
        "code_freeze": snapshot.get("code_freeze"),
        "available_people": available_people,
        "headcount": headcount,
        "availability_factor": availability_factor,
        "sprints": sprints,
        "demand": demand,
        "ledgers": {
            "historical": {
                "mean_planned_completed": mean_planned,
                "remaining_sprints": remaining_n,
                "availability_factor": availability_factor,
                "net": historical_net,
                "arithmetic": historical_arithmetic,
            },
            "theoretical": {
                "available_people": available_people,
                "remaining_sprints": remaining_n,
                "sp_per_person_sprint": full_focus,
                "sp_per_person_sprint_source": rate_source,
                "meeting_factor": meeting_factor,
                "interrupt_rate": interrupt_rate,
                "net": theoretical_net,
                "arithmetic": theoretical_arithmetic,
            },
        },
        "fit": {
            "required_vs_historical": theoretical_delta(required, historical_net),
            "required_vs_theoretical": theoretical_delta(required, theoretical_net),
            "total_vs_historical": theoretical_delta(total_demand, historical_net),
            "total_vs_theoretical": theoretical_delta(total_demand, theoretical_net),
        },
        "stretch_first_cuts": [
            item["key"] for item in demand["items"] if item.get("stretch") and item.get("key")
        ],
    }


def theoretical_delta(demand: float, capacity: float) -> dict[str, Any]:
    slack = capacity - demand
    return {
        "demand": demand,
        "capacity": capacity,
        "slack": slack,
        "fits": slack >= 0,
    }


def load_snapshot(path: str | None) -> dict[str, Any]:
    if path and path != "-":
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            _fail(f"could not read {path}: {exc}")
    else:
        if sys.stdin.isatty():
            _fail("pass a JSON snapshot on stdin or with --input")
        text = sys.stdin.read()
    if not text.strip():
        _fail("snapshot JSON is empty")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        _fail(f"snapshot is not JSON: {exc}")
    if not isinstance(payload, dict):
        _fail("snapshot must be a JSON object")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compute RHDH release-horizon capacity from a JSON snapshot."
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Snapshot JSON file. Omit or use - to read stdin.",
    )
    args = parser.parse_args(argv)
    snapshot = load_snapshot(args.input)
    emit(compute(snapshot))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
