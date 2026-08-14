#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""Check EKS Kubernetes version lifecycle using the official AWS EKS docs source.

Primary source: awsdocs/amazon-eks-user-guide raw AsciiDoc on GitHub
Cross-verify:   https://endoflife.date/api/amazon-eks.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

from rhdh_lifecycle.configured_versions import print_configured_versions
from rhdh_lifecycle.openshift_release import resolve_repo_root
from rhdh_lifecycle.versions import fetch_json, filter_supported_eol_entries

EKS_DOCS_URL = (
    "https://raw.githubusercontent.com/awsdocs/amazon-eks-user-guide"
    "/mainline/latest/ug/versioning/kubernetes-versions.adoc"
)
EOL_API_URL = "https://endoflife.date/api/amazon-eks.json"
CONFIG_DIR = "ci-operator/config/redhat-developer/rhdh"


def fetch_text(url):
    """Fetch text content from a URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "rhdh-skills"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: Failed to fetch {url}: {exc}", file=sys.stderr)
        return None


def parse_supported_versions(docs):
    """Extract supported versions and their tiers from the AsciiDoc."""
    section = ""
    versions = []
    for line in docs.splitlines():
        if "Available versions on standard support" in line:
            section = "Standard"
        elif "Available versions on extended support" in line:
            section = "Extended"
        elif "Amazon EKS Kubernetes release calendar" in line:
            section = ""
        elif section and re.match(r"^\* `\d+\.\d+`$", line):
            ver = line.strip("* `\n")
            versions.append((ver, section))
    return versions


def parse_release_calendar(docs):
    """Extract the release calendar table from the AsciiDoc."""
    lines = docs.splitlines()
    in_table = False
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "|===":
            in_table = not in_table
            i += 1
            continue
        if in_table and re.match(r"^\|`\d+\.\d+`", line):
            # Next 4 lines are: upstream, eks_release, end_std, end_ext
            version = line.lstrip("|").strip("`").strip()
            fields = []
            for j in range(1, 5):
                if i + j < len(lines):
                    fields.append(lines[i + j].lstrip("|").strip())
                else:
                    fields.append("N/A")
            entries.append((version, *fields))
            i += 5
            continue
        i += 1
    return entries


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check EKS K8s version lifecycle.")
    parser.add_argument("--mapt-ref", help="Path to MAPT ref YAML (repo-relative)")
    parser.add_argument("--test-pattern", help="Regex to match test names")
    parser.add_argument("--config-dir", default=CONFIG_DIR, help="CI config directory")
    parser.add_argument("--repo-dir", help="Path to openshift/release checkout")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    root, is_remote = resolve_repo_root(args.repo_dir)

    # Print configured versions if test pattern provided
    if args.test_pattern and not args.json_output:
        print_configured_versions(
            args.config_dir, args.test_pattern, root, is_remote, args.mapt_ref
        )

    # Fetch EKS docs source (primary)
    docs = fetch_text(EKS_DOCS_URL)
    if not docs:
        sys.exit(1)

    versions = parse_supported_versions(docs)
    calendar = parse_release_calendar(docs)

    # Cross-verify with endoflife.date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    eol_data = fetch_json(EOL_API_URL)
    eol_supported = filter_supported_eol_entries(eol_data, today) if eol_data else []

    # JSON output
    if args.json_output:
        result = {
            "versions": [{"version": ver, "tier": tier} for ver, tier in versions],
            "calendar": [
                {
                    "version": e[0],
                    "upstream_release": e[1],
                    "eks_release": e[2],
                    "end_standard": e[3],
                    "end_extended": e[4],
                }
                for e in calendar
            ],
            "endoflife_date": [
                {
                    "version": e["cycle"],
                    "eol": str(e.get("eol", "N/A")),
                    "extended_support": str(e.get("extendedSupport", "N/A")),
                }
                for e in eol_supported
            ],
        }
        json.dump(result, sys.stdout, indent=2)
        print()
        return

    # Human-readable output
    print("=== EKS Version Support (awsdocs/amazon-eks-user-guide) ===")
    print("Supported minor versions:")
    for ver, tier in versions:
        print(f"  {ver:<8s} {tier}")

    print()
    print("Release calendar:")
    print(
        f"  {'VERSION':<8s} {'UPSTREAM RELEASE':<22s} {'EKS RELEASE':<22s} "
        f"{'END STANDARD':<22s} {'END EXTENDED':<22s}"
    )
    print(
        f"  {'-------':<8s} {'----------------':<22s} {'-----------':<22s} "
        f"{'------------':<22s} {'------------':<22s}"
    )
    for entry in calendar:
        ver, upstream, eks_rel, end_std, end_ext = entry
        print(f"  {ver:<8s} {upstream:<22s} {eks_rel:<22s} {end_std:<22s} {end_ext:<22s}")

    print()
    print("=== Cross-verify (endoflife.date) ===")
    if not eol_data:
        print("WARNING: Failed to fetch endoflife.date", file=sys.stderr)
        return
    for entry in eol_supported:
        ext = entry.get("extendedSupport", "N/A")
        print(f"  {entry['cycle']}\tEOL: {entry.get('eol', 'N/A')}\tExtended: {ext}")


if __name__ == "__main__":
    main()
