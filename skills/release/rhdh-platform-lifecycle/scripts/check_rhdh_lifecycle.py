#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check RHDH release lifecycle status using the Red Hat Product Life Cycles API.

Usage:
  check_rhdh_lifecycle.py                  # Show all RHDH releases
  check_rhdh_lifecycle.py --version 1.9    # Check a specific version
  check_rhdh_lifecycle.py --active-only    # Show only active releases
  check_rhdh_lifecycle.py --json           # Output as JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from rhdh_lifecycle.rhdh import fetch_rhdh_lifecycle, rhdh_supported_ocp_versions


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check RHDH release lifecycle status.")
    parser.add_argument("--version", "-v", help="Check a specific RHDH version (e.g., 1.9)")
    parser.add_argument(
        "--active-only", action="store_true", help="Show only active (supported) releases"
    )
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    rhdh_data = fetch_rhdh_lifecycle(args.version)

    if args.version and not rhdh_data:
        print(f"ERROR: RHDH version '{args.version}' not found", file=sys.stderr)
        sys.exit(1)

    if args.active_only:
        rhdh_data = [v for v in rhdh_data if v["supported"]]

    if args.json_output:
        output = {
            "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "versions": rhdh_data,
            "ocp_versions_supported": rhdh_supported_ocp_versions(rhdh_data),
        }
        json.dump(output, sys.stdout, indent=2)
        print()
        return

    print("=== RHDH Lifecycle ===")
    print()
    print(
        f"{'VERSION':<10s} {'SUPPORTED':<10s} {'TYPE':<22s} {'GA_DATE':<12s} "
        f"{'FULL_SUPPORT_END':<25s} {'MAINTENANCE_END':<25s} SUPPORTED_OCP"
    )
    print(
        f"{'-------':<10s} {'---------':<10s} {'----':<22s} {'-------':<12s} "
        f"{'----------------':<25s} {'---------------':<25s} -------------"
    )
    for v in rhdh_data:
        sup = "yes" if v["supported"] else "no"
        ocp = ", ".join(v["ocp_versions"])
        print(
            f"{v['version']:<10s} {sup:<10s} {v['type']:<22s} {v['ga_date']:<12s} "
            f"{v['full_support_end']:<25s} {v['maintenance_end']:<25s} {ocp}"
        )
    print()

    supported_ocp = rhdh_supported_ocp_versions(rhdh_data)
    if supported_ocp:
        print(f"OCP versions supported by active RHDH releases: {' '.join(supported_ocp)}")
        print()
        print("Per-release OCP support:")
        for v in rhdh_data:
            if v["supported"]:
                print(f"  RHDH {v['version']}: {', '.join(v['ocp_versions'])}")
        print()


if __name__ == "__main__":
    main()
