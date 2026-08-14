#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check PostgreSQL version lifecycle across cloud providers.

Usage:
  check_pg_lifecycle.py                  # Show all versions
  check_pg_lifecycle.py --active-only    # Show only supported versions
  check_pg_lifecycle.py --json           # Output as JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from rhdh_lifecycle.pg import fetch_pg_lifecycle


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check PostgreSQL version lifecycle across cloud providers."
    )
    parser.add_argument("--active-only", action="store_true", help="Show only supported versions")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    versions = fetch_pg_lifecycle(today)

    if args.active_only:
        versions = [v for v in versions if v["any_supported"]]

    if args.json_output:
        json.dump({"checked_at": today, "versions": versions}, sys.stdout, indent=2)
        print()
        return

    print("=== PostgreSQL Version Lifecycle ===")
    print()
    print(
        f"  {'VERSION':<8s} {'SUPPORTED':<10s} {'UPSTREAM_EOL':<14s} "
        f"{'RDS_EOL':<14s} {'AZURE_EOL':<14s} {'RELEASE':<12s}"
    )
    print(
        f"  {'-------':<8s} {'---------':<10s} {'------------':<14s} "
        f"{'-------':<14s} {'---------':<14s} {'-------':<12s}"
    )
    for v in versions:
        sup = "yes" if v["any_supported"] else "no"
        print(
            f"  {v['major_version']:<8s} {sup:<10s} {v['upstream_eol']:<14s} "
            f"{v['rds_eol']:<14s} {v['azure_eol']:<14s} {v['upstream_release']:<12s}"
        )
    print()


if __name__ == "__main__":
    main()
