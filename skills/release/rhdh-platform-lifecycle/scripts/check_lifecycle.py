#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check lifecycle status for any Red Hat product.

Usage:
  check_lifecycle.py --product rhbk
  check_lifecycle.py --product quay --active-only
  check_lifecycle.py --product rhbk --group-major
  check_lifecycle.py --product "Red Hat Quay" --version 3.15
  check_lifecycle.py --list-products
"""

from __future__ import annotations

import argparse
import json
import sys

from rhdh_lifecycle.redhat import (
    fetch_product_lifecycle,
    list_known_products,
    resolve_product_name,
    rhbk_major_versions,
)


def print_version_table(versions):
    """Print a human-readable version lifecycle table."""
    print(f"{'VERSION':<10s} {'SUPPORTED':<10s} {'TYPE':<25s} {'GA_DATE':<12s} {'END_DATE':<12s}")
    print(f"{'-------':<10s} {'---------':<10s} {'----':<25s} {'-------':<12s} {'--------':<12s}")
    for v in versions:
        sup = "yes" if v["supported"] else "no"
        print(
            f"{v['version']:<10s} {sup:<10s} {v['type']:<25s} "
            f"{v['ga_date']:<12s} {v['end_date']:<12s}"
        )


def print_major_table(majors):
    """Print RHBK major version grouping table."""
    print(f"{'MAJOR':<8s} {'ACTIVE':<8s} {'GA_DATE':<12s} {'END_DATE':<12s} MINOR_RELEASES")
    print(f"{'-----':<8s} {'------':<8s} {'-------':<12s} {'--------':<12s} --------------")
    for m in majors:
        active = "yes" if m["active"] else "no"
        minors = ", ".join(m["minor_releases"])
        print(
            f"{m['major_version']:<8s} {active:<8s} {m['ga_date']:<12s} "
            f"{m['end_date']:<12s} {minors}"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check lifecycle status for any Red Hat product.")
    parser.add_argument(
        "--product",
        "-p",
        help="Product alias (rhbk, quay, rhdh, ocp) or full name",
    )
    parser.add_argument("--version", "-v", help="Filter to a specific version")
    parser.add_argument(
        "--group-major",
        action="store_true",
        help="Group minor versions into major version summaries (useful for RHBK)",
    )
    parser.add_argument("--active-only", action="store_true", help="Show only active versions")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    parser.add_argument("--list-products", action="store_true", help="List known product aliases")
    args = parser.parse_args(argv)

    if args.list_products:
        if args.json_output:
            json.dump(dict(list_known_products()), sys.stdout, indent=2)
            print()
        else:
            print(f"{'ALIAS':<8s} PRODUCT NAME")
            print(f"{'-----':<8s} ------------")
            for alias, name in list_known_products():
                print(f"{alias:<8s} {name}")
        return

    if not args.product:
        parser.error("--product is required (or use --list-products)")

    full_name = resolve_product_name(args.product)
    versions = fetch_product_lifecycle(args.product, args.version)

    if args.version and not versions:
        print(f"ERROR: Version '{args.version}' not found for {full_name}", file=sys.stderr)
        sys.exit(1)

    if args.active_only:
        versions = [v for v in versions if v["supported"]]

    if args.group_major:
        majors = rhbk_major_versions(versions)
        if args.active_only:
            majors = [m for m in majors if m["active"]]
        if args.json_output:
            json.dump({"product": full_name, "major_versions": majors}, sys.stdout, indent=2)
            print()
        else:
            print(f"=== {full_name} (major versions) ===")
            print()
            print_major_table(majors)
        return

    if args.json_output:
        json.dump({"product": full_name, "versions": versions}, sys.stdout, indent=2)
        print()
        return

    print(f"=== {full_name} ===")
    print()
    print_version_table(versions)
    print()


if __name__ == "__main__":
    main()
