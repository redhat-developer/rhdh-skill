#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Verify acli installation and Jira API capabilities for RHDH."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

RHDH_PROJECTS = ["RHIDP", "RHDHPLAN", "RHDHBUGS", "RHDHSUPP"]


def find_acli():
    """Return the path to the Atlassian CLI, or None.

    PATH wins. The extra candidates cover Windows installers that do not amend
    PATH, which otherwise makes a working acli look absent.
    """
    on_path = shutil.which("acli")
    if on_path:
        return on_path
    home = Path.home()
    for candidate in (
        home / ".path" / "acli.exe",
        home / "AppData" / "Local" / "acli" / "acli.exe",
    ):
        if candidate.is_file():
            return str(candidate)
    return None


def smoke_test(acli_path):
    """Run a smoke test to verify Jira connectivity."""
    try:
        result = subprocess.run(
            [acli_path, "jira", "project", "list", "--recent", "1"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if result.returncode == 0 and stdout.strip():
            return True, stdout.strip()
        return False, stderr.strip() or "empty response"
    except subprocess.TimeoutExpired:
        return False, "timeout after 30s"
    except OSError as e:
        return False, str(e)


def check_projects(acli_path):
    """Check which RHDH projects are accessible."""
    accessible = []
    inaccessible = []

    for project in RHDH_PROJECTS:
        try:
            result = subprocess.run(
                [acli_path, "jira", "project", "view", "--key", project],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            if result.returncode == 0:
                accessible.append(project)
            else:
                stderr = result.stderr or ""
                inaccessible.append((project, stderr.strip()))
        except (subprocess.TimeoutExpired, OSError) as e:
            inaccessible.append((project, str(e)))

    return accessible, inaccessible


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify acli installation and Jira API capabilities for RHDH."
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--quick", action="store_true", help="Skip project accessibility check")
    args = parser.parse_args(argv)

    results = {
        "acli_found": False,
        "acli_path": None,
        "adapters": [],
        "connectivity": False,
        "connectivity_detail": None,
        "projects_accessible": [],
        "projects_inaccessible": [],
        "overall": "fail",
    }

    # Step 1: Find acli
    acli_path = find_acli()
    if acli_path:
        results["acli_found"] = True
        results["acli_path"] = acli_path
    else:
        results["connectivity_detail"] = "acli not found on PATH"
        _output(results, args.json)
        sys.exit(1)

    # The smoke test is the credential-store boundary. Do not inspect acli's store.
    ok, detail = smoke_test(acli_path)
    results["connectivity"] = ok
    results["connectivity_detail"] = detail

    if not ok:
        _output(results, args.json)
        sys.exit(1)

    results["adapters"] = ["acli"]

    # Check project access
    if not args.quick:
        accessible, inaccessible = check_projects(acli_path)
        results["projects_accessible"] = accessible
        results["projects_inaccessible"] = [{"project": p, "error": e} for p, e in inaccessible]

    results["overall"] = "pass"
    _output(results, args.json)
    sys.exit(0)


def _output(results, as_json):
    """Print results in JSON or human-readable format."""
    if as_json:
        json.dump(results, sys.stdout, indent=2)
        print()
        return

    print("=" * 50)
    print("RHDH Jira Setup Check")
    print("=" * 50)

    # acli
    if results["acli_found"]:
        print(f"  [PASS] acli found: {results['acli_path']}")
    else:
        print("  [FAIL] acli not found on PATH")
        print("         Setup required: /setup-rhdh-skills jira")
        return

    # Connectivity
    if results["connectivity"]:
        print("  [PASS] Jira connectivity verified through acli's native credential store")
    else:
        print(f"  [FAIL] Jira connectivity failed: {results['connectivity_detail']}")
        return

    # Projects
    if results["projects_accessible"]:
        print(f"  [PASS] Projects accessible: {', '.join(results['projects_accessible'])}")
    if results["projects_inaccessible"]:
        for item in results["projects_inaccessible"]:
            print(f"  [WARN] {item['project']}: {item['error']}")

    print()
    print(f"Overall: {results['overall'].upper()}")


if __name__ == "__main__":
    main()
