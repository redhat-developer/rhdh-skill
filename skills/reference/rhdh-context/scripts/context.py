#!/usr/bin/env python3
"""Resolve RHDH repositories, tools, and configuration into one JSON document."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).parent.parent
VERSIONS_FILE = SKILL_ROOT / "references" / "versions.md"
sys.path.insert(0, str(SKILL_ROOT))

from rhdh import config  # noqa: E402


def _version_matrix() -> list[dict[str, str]]:
    """Read the checked-in RHDH/Backstage compatibility table."""
    rows: list[dict[str, str]] = []
    try:
        lines = VERSIONS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in {"RHDH Version", ""} or set(cells[0]) <= set("-: "):
            continue
        rows.append({"rhdh": cells[0], "backstage": cells[1], "status": cells[3]})
    return rows


def _repository_backstage_version(project_root: Path) -> str | None:
    """Read `backstage.json` when the checkout pins its own Backstage version."""
    pinned = project_root / "backstage.json"
    if not pinned.is_file():
        return None
    try:
        version = json.loads(pinned.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None
    return version if isinstance(version, str) else None


def resolve_versions(project_root: Path, requested_rhdh: str | None) -> dict[str, Any]:
    """Resolve the target RHDH and Backstage versions and where they came from."""
    matrix = _version_matrix()

    if requested_rhdh:
        row = next((entry for entry in matrix if entry["rhdh"] == requested_rhdh), None)
        return {
            "targetRhdh": requested_rhdh,
            "targetBackstage": row["backstage"] if row else None,
            "source": "user",
        }

    pinned = _repository_backstage_version(project_root)
    if pinned:
        row = next((entry for entry in matrix if entry["backstage"] == pinned), None)
        return {
            "targetRhdh": row["rhdh"] if row else None,
            "targetBackstage": pinned,
            "source": "repository",
        }

    current = next((entry for entry in matrix if entry["status"].lower() == "current"), None)
    return {
        "targetRhdh": current["rhdh"] if current else None,
        "targetBackstage": current["backstage"] if current else None,
        "source": "rhdh-context",
    }


def _tool_status(probe: bool) -> dict[str, str]:
    tools = ("git", "gh", "node", "yarn", "uv", "podman", "docker", "oc")
    if not probe:
        return {tool: "not-probed" for tool in tools}
    return {tool: "installed" if shutil.which(tool) else "missing" for tool in tools}


def build_context(
    project_root: Path, probe_tools: bool, requested_rhdh: str | None = None
) -> dict[str, Any]:
    previous_cwd = Path.cwd()
    try:
        os.chdir(project_root)
        info = config.get_config_info()
        repositories = [
            {"name": name, "path": str(Path(value).resolve()) if value else None}
            for name, value in sorted(info["resolved"].items())
        ]
        configuration = {
            "dataDirectory": str(config.get_data_dir().resolve()),
            "projectConfig": str(config.get_project_config_path().resolve()),
            "userConfig": str(config.get_user_config_path().resolve()),
            **resolve_versions(project_root, requested_rhdh),
        }
    finally:
        os.chdir(previous_cwd)

    return {
        "repositories": repositories,
        "tools": _tool_status(probe_tools),
        "configuration": configuration,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve repositories, tools, and configuration into one JSON document."
    )
    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Project root to inspect"
    )
    parser.add_argument(
        "--no-tool-probes", action="store_true", help="Skip PATH-based tool discovery"
    )
    parser.add_argument(
        "--target-rhdh",
        help="Explicit target RHDH version; otherwise read backstage.json or the version matrix",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON output")
    args = parser.parse_args(argv)

    try:
        context = build_context(
            args.project_root.resolve(), not args.no_tool_probes, args.target_rhdh
        )
    except (OSError, ValueError) as exc:
        error = {"valid": False, "errors": [{"code": "CONTEXT_ERROR", "message": str(exc)}]}
        json.dump(error, sys.stdout, indent=2 if args.json else None)
        sys.stdout.write("\n")
        return 1

    if args.json or not sys.stdout.isatty():
        json.dump(context, sys.stdout, indent=2 if args.json else None)
        sys.stdout.write("\n")
    else:
        repositories = context["repositories"]
        configured = sum(entry["path"] is not None for entry in repositories)
        versions = context["configuration"]
        print(
            f"RHDH context: {configured} repositories configured; "
            f"target RHDH {versions['targetRhdh']} on Backstage {versions['targetBackstage']} "
            f"({versions['source']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
