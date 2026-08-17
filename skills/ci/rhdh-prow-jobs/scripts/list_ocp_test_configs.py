#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""List OCP versions used in RHDH CI test configs.

Extracts OCP versions from cluster_claim.version (the source of truth),
not from test names. This catches all OCP-targeted tests, including ones
that don't encode the version in their name.
"""

from __future__ import annotations

import argparse
import sys

from rhdh_prow.openshift_release import (
    extract_branch,
    fetch_yaml,
    list_yaml_files,
    resolve_repo_root,
)
from rhdh_prow.versions import ver_sort_key

CONFIG_DIR = "ci-operator/config/redhat-developer/rhdh"
PREFIX = "redhat-developer-rhdh-"


def main(argv=None):
    parser = argparse.ArgumentParser(description="List OCP test configs in RHDH CI config files.")
    parser.add_argument("--branch", "-b", help="Filter by branch name")
    parser.add_argument("--config-dir", "-d", default=CONFIG_DIR, help="CI config directory")
    parser.add_argument("--repo-dir", help="Path to openshift/release checkout")
    args = parser.parse_args(argv)

    root, is_remote = resolve_repo_root(args.repo_dir)

    files = list_yaml_files(args.config_dir, f"{PREFIX}*.yaml", root, is_remote)
    if not files:
        print("ERROR: No config files found", file=sys.stderr)
        sys.exit(1)

    for filepath in files:
        branch = extract_branch(PREFIX, filepath)
        if args.branch and branch != args.branch:
            continue

        data = fetch_yaml(filepath, root, is_remote)
        if not data or "tests" not in data:
            continue

        # Extract tests with cluster_claim.version (OCP tests)
        entries = [t for t in data["tests"] if t.get("cluster_claim", {}).get("version")]
        if not entries:
            continue

        # Unique OCP versions
        versions = sorted(
            {t["cluster_claim"]["version"] for t in entries},
            key=ver_sort_key,
        )

        print()
        print(f"=== Branch: {branch} ===")
        print(f"  {'TEST_NAME':<45s} {'OCP_VERSION':<13s} {'CRON':<30s} {'OPTIONAL':<10s}")
        print(f"  {'---------':<45s} {'-----------':<13s} {'----':<30s} {'--------':<10s}")

        for t in sorted(entries, key=lambda x: x.get("as", "")):
            name = t.get("as", "")
            ver = t["cluster_claim"]["version"]
            cron = t.get("cron", "N/A")
            opt = str(t.get("optional", False)).lower()
            print(f"  {name:<45s} {ver:<13s} {cron:<30s} {opt:<10s}")

        print()
        print(f"  OCP versions tested: {' '.join(versions)}")


if __name__ == "__main__":
    main()
