#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""Generate a new RHDH Hive ClusterPool YAML for a target OCP version.

The imageSetRef is looked up from existing cluster pools across the entire
openshift/release repository (not just RHDH pools) to ensure alignment.
If no pool for the target version exists anywhere in the repo, the script
errors out rather than guessing a patch version.

Requires a local openshift/release checkout (writes files).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

POOL_DIR = "clusters/hosted-mgmt/hive/pools/rhdh"
ALL_POOLS_DIR = "clusters/hosted-mgmt/hive/pools"

_yaml = YAML()
_yaml.preserve_quotes = True


def find_image_set_ref(all_pools_dir: Path, major: str, minor: str) -> str | None:
    """Find imageSetRef for an OCP version by scanning ALL cluster pools."""
    pattern = f"ocp-release-{major}.{minor}."
    matches = []
    for pool_file in all_pools_dir.rglob("*_clusterpool.yaml"):
        try:
            text = pool_file.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("name:") and pattern in stripped:
                ref = stripped.split("name:", 1)[1].strip()
                matches.append(ref)
    if not matches:
        return None
    # Return the latest (highest patch version)
    matches.sort()
    return matches[-1]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a new RHDH Hive ClusterPool YAML.")
    parser.add_argument("--version", "-v", required=True, help="Target OCP version (e.g., 4.22)")
    parser.add_argument("--reference", "-r", help="Reference OCP version to use as template")
    parser.add_argument("--pool-dir", "-d", default=POOL_DIR, help="RHDH pool directory")
    parser.add_argument("--all-pools-dir", default=ALL_POOLS_DIR, help="All pools directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args(argv)

    if not re.match(r"^\d+\.\d+$", args.version):
        print(f"ERROR: Version must be in X.Y format, got: {args.version}", file=sys.stderr)
        sys.exit(1)

    if args.reference:
        if not re.match(r"^\d+\.\d+$", args.reference):
            print(f"ERROR: Reference must be in X.Y format, got: {args.reference}", file=sys.stderr)
            sys.exit(1)

    major, minor = args.version.split(".")
    next_minor = str(int(minor) + 1)
    dash_ver = f"{major}-{minor}"

    pool_dir = Path(args.pool_dir)
    all_pools_dir = Path(args.all_pools_dir)

    if not pool_dir.is_dir():
        print(f"ERROR: Pool directory not found: {pool_dir}", file=sys.stderr)
        sys.exit(1)

    target_file = pool_dir / f"rhdh-ocp-{dash_ver}-0-amd64-aws-us-east-2_clusterpool.yaml"
    if target_file.exists():
        print(f"ERROR: Cluster pool already exists: {target_file}", file=sys.stderr)
        sys.exit(1)

    # 1. Find imageSetRef
    print(
        f"Looking up imageSetRef for OCP {args.version} across {all_pools_dir}/ ...",
        file=sys.stderr,
    )
    image_set_ref = find_image_set_ref(all_pools_dir, major, minor)
    if not image_set_ref:
        print(f"ERROR: No existing cluster pool uses OCP {args.version}.", file=sys.stderr)
        print("Cannot determine the correct imageSetRef.", file=sys.stderr)
        sys.exit(1)
    print(f"Found imageSetRef: {image_set_ref}", file=sys.stderr)

    # 2. Find reference pool
    if args.reference:
        ref_major, ref_minor = args.reference.split(".")
        ref_file = (
            pool_dir / f"rhdh-ocp-{ref_major}-{ref_minor}-0-amd64-aws-us-east-2_clusterpool.yaml"
        )
        if not ref_file.exists():
            print(f"ERROR: Reference pool not found: {ref_file}", file=sys.stderr)
            sys.exit(1)
    else:
        pool_files = sorted(pool_dir.glob("*_clusterpool.yaml"))
        if not pool_files:
            print(f"ERROR: No existing cluster pool files in {pool_dir}", file=sys.stderr)
            sys.exit(1)
        ref_file = pool_files[-1]

    print(f"Using reference pool: {ref_file.name}", file=sys.stderr)

    # 3. Generate new pool
    with open(ref_file) as fh:
        pool_data = _yaml.load(fh)

    # Update version-specific fields
    pool_data["metadata"]["name"] = f"rhdh-ocp-{dash_ver}-0-amd64-aws-us-east-2"
    pool_data["metadata"]["labels"]["version"] = args.version
    pool_data["metadata"]["labels"]["version_lower"] = args.version
    pool_data["metadata"]["labels"]["version_upper"] = f"{major}.{next_minor}"
    pool_data["spec"]["imageSetRef"]["name"] = image_set_ref
    pool_data["spec"]["size"] = 1
    pool_data["spec"]["maxSize"] = 2

    # Remove runningCount if present (conservative sizing)
    if "runningCount" in pool_data.get("spec", {}):
        del pool_data["spec"]["runningCount"]

    # Write or preview
    if args.dry_run:
        _yaml.dump(pool_data, sys.stdout)
    else:
        with open(target_file, "w") as fh:
            _yaml.dump(pool_data, fh)
        print(f"\nGenerated: {target_file}", file=sys.stderr)
        _yaml.dump(pool_data, sys.stdout)

    # Print summary
    print(file=sys.stderr)
    print("Fields updated:", file=sys.stderr)
    print(f"  metadata.name: {pool_data['metadata']['name']}", file=sys.stderr)
    print(f"  metadata.labels.version: {args.version}", file=sys.stderr)
    print(f"  metadata.labels.version_lower: {args.version}", file=sys.stderr)
    print(f"  metadata.labels.version_upper: {major}.{next_minor}", file=sys.stderr)
    print(f"  spec.imageSetRef.name: {image_set_ref}", file=sys.stderr)
    print("  spec.size: 1", file=sys.stderr)
    print("  spec.maxSize: 2", file=sys.stderr)


if __name__ == "__main__":
    main()
