#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check OCP version lifecycle status using the Red Hat Product Life Cycles API.

Shows OCP version support phases (Full, Maintenance, EUS, EOL) and
cross-references with RHDH compatibility.

Usage:
  check_ocp_lifecycle.py                  # Show all OCP versions
  check_ocp_lifecycle.py --version 4.16   # Check a specific OCP version
  check_ocp_lifecycle.py --json           # Output as JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from rhdh_lifecycle.ocp import classify_ocp_versions
from rhdh_lifecycle.rhdh import (
    fetch_lifecycle_api,
    parse_rhdh_versions,
    rhdh_supported_ocp_versions,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check OCP version lifecycle status.")
    parser.add_argument("--version", "-v", help="Check a specific OCP version (e.g., 4.16)")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Fetch OCP lifecycle data
    ocp_response = fetch_lifecycle_api("Red Hat OpenShift Container Platform")
    if ocp_response is None:
        print("ERROR: Failed to fetch OCP lifecycle data", file=sys.stderr)
        sys.exit(1)
    ocp_data = classify_ocp_versions(ocp_response, today)

    if args.version:
        ocp_data = [v for v in ocp_data if v["version"] == args.version]
        if not ocp_data:
            print(f"ERROR: OCP version '{args.version}' not found", file=sys.stderr)
            sys.exit(1)

    # Fetch RHDH data for the RHDH_SUPP cross-reference column
    rhdh_response = fetch_lifecycle_api("Red Hat Developer Hub")
    if rhdh_response is None:
        print("ERROR: Failed to fetch RHDH lifecycle data", file=sys.stderr)
        sys.exit(1)
    rhdh_data = parse_rhdh_versions(rhdh_response)
    supported_ocp = rhdh_supported_ocp_versions(rhdh_data)

    if args.json_output:
        for v in ocp_data:
            v["rhdh_supported"] = v["version"] in supported_ocp
        output = {
            "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "versions": ocp_data,
            "rhdh_supported_ocp": supported_ocp,
        }
        json.dump(output, sys.stdout, indent=2)
        print()
        return

    print("=== OCP Lifecycle ===")
    print()
    print(
        f"{'VERSION':<10s} {'OCP_SUPP':<10s} {'RHDH_SUPP':<10s} "
        f"{'PHASE':<35s} {'GA_DATE':<12s} {'END_DATE':<12s}"
    )
    print(
        f"{'-------':<10s} {'--------':<10s} {'---------':<10s} "
        f"{'-----':<35s} {'-------':<12s} {'--------':<12s}"
    )
    for v in ocp_data:
        ocp_sup = "yes" if v["ocp_supported"] else "no"
        rhdh_sup = "yes" if v["version"] in supported_ocp else "no"
        print(
            f"{v['version']:<10s} {ocp_sup:<10s} {rhdh_sup:<10s} "
            f"{v['phase']:<35s} {v['ga_date']:<12s} {v['end_of_support_date']:<12s}"
        )
    print()


if __name__ == "__main__":
    main()
