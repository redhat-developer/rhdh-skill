#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""List K8s platform test entries in RHDH CI config files.

Shared script used by prow-aks-jobs, prow-eks-jobs, and prow-gke-jobs.
Supports both local openshift/release checkout and remote GitHub API access.

Usage:
  list_k8s_test_configs.py --pattern "^e2e-aks-"
  list_k8s_test_configs.py --pattern "^e2e-eks-" --branch main
  list_k8s_test_configs.py --pattern "^e2e-gke-"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Importable as ``rhdh_prow.k8s_configs`` and runnable directly. Direct
# execution puts this file's own directory on sys.path, not the scripts
# directory holding the package, so put it there before importing a sibling.
_scripts_dir = Path(__file__).resolve().parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from rhdh_prow.openshift_release import (  # noqa: E402
    extract_branch,
    fetch_yaml,
    list_yaml_files,
    resolve_repo_root,
)

CONFIG_DIR = "ci-operator/config/redhat-developer/rhdh"
PREFIX = "redhat-developer-rhdh-"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="List K8s platform test entries in RHDH CI config files."
    )
    parser.add_argument(
        "--pattern", "-p", required=True, help="Regex to match test names (e.g., '^e2e-aks-')"
    )
    parser.add_argument("--branch", "-b", help="Filter by branch name")
    parser.add_argument("--config-dir", "-d", default=CONFIG_DIR, help="CI config directory")
    parser.add_argument("--repo-dir", help="Path to openshift/release checkout")
    args = parser.parse_args(argv)

    root, is_remote = resolve_repo_root(args.repo_dir)
    pattern_re = re.compile(args.pattern)

    files = list_yaml_files(args.config_dir, f"{PREFIX}*.yaml", root, is_remote)
    if not files:
        print("ERROR: No config files found", file=sys.stderr)
        sys.exit(1)

    has_mapt_version = False

    for filepath in files:
        branch = extract_branch(PREFIX, filepath)
        if args.branch and branch != args.branch:
            continue

        data = fetch_yaml(filepath, root, is_remote)
        if not data or "tests" not in data:
            continue

        entries = [t for t in data["tests"] if pattern_re.search(t.get("as", ""))]
        if not entries:
            continue

        # Check if any entry has MAPT_KUBERNETES_VERSION
        has_ver = any(
            t.get("steps", {}).get("env", {}).get("MAPT_KUBERNETES_VERSION") for t in entries
        )

        print()
        print(f"=== Branch: {branch} ===")
        if has_ver:
            has_mapt_version = True
            print(f"  {'TEST_NAME':<40s} {'K8S_VERSION':<13s} {'CRON':<30s} {'OPTIONAL':<10s}")
            print(f"  {'---------':<40s} {'-----------':<13s} {'----':<30s} {'--------':<10s}")
            for t in sorted(entries, key=lambda x: x.get("as", "")):
                name = t.get("as", "")
                ver = t.get("steps", {}).get("env", {}).get("MAPT_KUBERNETES_VERSION", "N/A")
                cron = t.get("cron", "N/A")
                opt = str(t.get("optional", False)).lower()
                print(f"  {name:<40s} {ver:<13s} {cron:<30s} {opt:<10s}")
        else:
            print(f"  {'TEST_NAME':<40s} {'CRON':<30s} {'OPTIONAL':<10s}")
            print(f"  {'---------':<40s} {'----':<30s} {'--------':<10s}")
            for t in sorted(entries, key=lambda x: x.get("as", "")):
                name = t.get("as", "")
                cron = t.get("cron", "N/A")
                opt = str(t.get("optional", False)).lower()
                print(f"  {name:<40s} {cron:<30s} {opt:<10s}")

    print()
    if has_mapt_version:
        print(
            "K8s version source: MAPT_KUBERNETES_VERSION in steps.env per test entry",
            file=sys.stderr,
        )
    else:
        print("K8s version: managed outside CI config (static cluster)", file=sys.stderr)


if __name__ == "__main__":
    main()
