#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""List RHDH Hive ClusterPool configurations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rhdh_prow.openshift_release import fetch_yaml, list_yaml_files, resolve_repo_root
from rhdh_prow.versions import ver_sort_key

POOL_DIR = "clusters/hosted-mgmt/hive/pools/rhdh"


def main(argv=None):
    parser = argparse.ArgumentParser(description="List RHDH Hive ClusterPool configurations.")
    parser.add_argument("--pool-dir", "-d", default=POOL_DIR, help="Pool directory")
    parser.add_argument("--repo-dir", help="Path to openshift/release checkout")
    args = parser.parse_args(argv)

    root, is_remote = resolve_repo_root(args.repo_dir)

    print("=== RHDH Cluster Pools ===")
    print()
    print(
        f"  {'VERSION':<8s}  {'POOL_NAME':<50s}  {'SIZE':<5s}  {'MAX':<5s}  "
        f"{'RUNNING':<8s}  {'IMAGE_SET':<70s}  FILENAME"
    )
    print(
        f"  {'-------':<8s}  {'---------':<50s}  {'----':<5s}  {'---':<5s}  "
        f"{'-------':<8s}  {'---------':<70s}  --------"
    )

    files = list_yaml_files(args.pool_dir, "*_clusterpool.yaml", root, is_remote)
    if not files:
        print("ERROR: No pool files found", file=sys.stderr)
        sys.exit(1)

    rows = []
    for filepath in files:
        data = fetch_yaml(filepath, root, is_remote)
        if not data:
            continue

        labels = data.get("metadata", {}).get("labels", {})
        ver = labels.get("version")
        if not ver:
            continue

        spec = data.get("spec", {})
        pool_name = data.get("metadata", {}).get("name", "unknown")
        size = str(spec.get("size", 0))
        max_size = str(spec.get("maxSize", 0))
        running = str(spec.get("runningCount", 0))
        image_set = spec.get("imageSetRef", {}).get("name", "N/A")
        filename = Path(filepath).name

        rows.append((ver, pool_name, size, max_size, running, image_set, filename))

    # Sort by version
    rows.sort(key=lambda r: ver_sort_key(r[0]))
    for ver, pool_name, size, max_size, running, image_set, filename in rows:
        print(
            f"  {ver:<8s}  {pool_name:<50s}  {size:<5s}  {max_size:<5s}  "
            f"{running:<8s}  {image_set:<70s}  {filename}"
        )


if __name__ == "__main__":
    main()
