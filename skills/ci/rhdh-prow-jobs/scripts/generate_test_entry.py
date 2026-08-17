#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""Generate a new e2e-ocp-vX-Y-helm-nightly test entry YAML block.

Clones a reference entry and substitutes the OCP version in:
  - as (test name)
  - cluster_claim.version
  - steps.env.OC_CLIENT_VERSION

Outputs the block to stdout for review before insertion.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from io import StringIO

from rhdh_prow.openshift_release import fetch_yaml, list_yaml_files, resolve_repo_root
from ruamel.yaml import YAML

CONFIG_DIR = "ci-operator/config/redhat-developer/rhdh"
PREFIX = "redhat-developer-rhdh-"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a new OCP test entry YAML block.")
    parser.add_argument("--version", "-v", required=True, help="Target OCP version (e.g., 4.22)")
    parser.add_argument("--branch", "-b", required=True, help="Product branch (e.g., main)")
    parser.add_argument("--reference", "-r", help="Reference OCP version to clone from")
    parser.add_argument("--config-dir", "-d", default=CONFIG_DIR, help="CI config directory")
    parser.add_argument("--repo-dir", help="Path to openshift/release checkout")
    args = parser.parse_args(argv)

    if not re.match(r"^\d+\.\d+$", args.version):
        print(f"ERROR: Version must be in X.Y format, got: {args.version}", file=sys.stderr)
        sys.exit(1)

    major, minor = args.version.split(".")
    root, is_remote = resolve_repo_root(args.repo_dir)

    # Find the config file for the target branch
    config_filename = f"{PREFIX}{args.branch}.yaml"
    files = list_yaml_files(args.config_dir, config_filename, root, is_remote)
    if not files:
        print(f"ERROR: Config file not found for branch '{args.branch}'", file=sys.stderr)
        sys.exit(1)

    data = fetch_yaml(files[0], root, is_remote)
    if not data or "tests" not in data:
        print(f"ERROR: Failed to read config for branch '{args.branch}'", file=sys.stderr)
        sys.exit(1)

    new_name = f"e2e-ocp-v{major}-{minor}-helm-nightly"

    # Check if entry already exists
    if any(t.get("as") == new_name for t in data["tests"]):
        print(f"ERROR: Test entry {new_name} already exists in {args.branch}", file=sys.stderr)
        sys.exit(1)

    # Find reference entry
    if args.reference:
        if not re.match(r"^\d+\.\d+$", args.reference):
            print(f"ERROR: Reference must be in X.Y format, got: {args.reference}", file=sys.stderr)
            sys.exit(1)
        ref_major, ref_minor = args.reference.split(".")
        ref_name = f"e2e-ocp-v{ref_major}-{ref_minor}-helm-nightly"
    else:
        # Find the latest versioned OCP helm-nightly entry
        versioned = [
            t.get("as", "")
            for t in data["tests"]
            if re.match(r"^e2e-ocp-v\d+-\d+-helm-nightly$", t.get("as", ""))
        ]
        if not versioned:
            print(f"ERROR: No reference OCP test entry found in {args.branch}", file=sys.stderr)
            sys.exit(1)
        ref_name = sorted(versioned)[-1]

    # Extract reference entry
    ref_entry = None
    for t in data["tests"]:
        if t.get("as") == ref_name:
            ref_entry = copy.deepcopy(t)
            break

    if ref_entry is None:
        print(f"ERROR: Reference entry '{ref_name}' not found", file=sys.stderr)
        sys.exit(1)

    # Substitute version fields
    ref_entry["as"] = new_name
    if "cluster_claim" in ref_entry:
        ref_entry["cluster_claim"]["version"] = args.version
    if "steps" in ref_entry and "env" in ref_entry["steps"]:
        ref_entry["steps"]["env"]["OC_CLIENT_VERSION"] = f"stable-{args.version}"

    # Output as YAML
    print(f"# Generated test entry for OCP {args.version}", file=sys.stderr)
    print(f"# Based on reference: {ref_name}", file=sys.stderr)
    print(f"# Insert this block into the tests: list in {config_filename}", file=sys.stderr)
    print("# Place it adjacent to other e2e-ocp-v*-helm-nightly entries", file=sys.stderr)
    print("# Then run: make update", file=sys.stderr)
    print(file=sys.stderr)

    yaml_out = YAML()
    yaml_out.default_flow_style = False
    buf = StringIO()
    yaml_out.dump(dict(ref_entry), buf)
    print(buf.getvalue())


if __name__ == "__main__":
    main()
