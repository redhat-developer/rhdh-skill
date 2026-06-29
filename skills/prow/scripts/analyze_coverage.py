#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = ["ruamel.yaml"]
# ///
"""Analyze RHDH OCP version coverage.

Cross-references cluster pools, CI test configs, RHDH lifecycle, and OCP
lifecycle data to identify coverage gaps and stale configurations.

Two dimensions are checked:
  1. OCP lifecycle -- is the OCP version itself still supported?
  2. RHDH compatibility -- does RHDH officially list this OCP version?
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from rhdh_prow.repo import resolve_repo_root
from rhdh_prow.utils import ver_sort_key
from rhdh_prow.yaml import extract_branch, fetch_yaml, list_yaml_files

POOL_DIR = "clusters/hosted-mgmt/hive/pools/rhdh"
CI_CONFIG_DIR = "ci-operator/config/redhat-developer/rhdh"
LIFECYCLE_API_URL = "https://access.redhat.com/product-life-cycles/api/v1/products"


def _fetch_lifecycle_json(script_name):
    """Run a lifecycle script with --json and return parsed output.

    Falls back to direct API call if the script is not available.
    """
    lifecycle_dir = Path(__file__).resolve().parent.parent.parent / "lifecycle" / "scripts"
    script = lifecycle_dir / script_name
    if script.exists():
        try:
            result = subprocess.run(
                ["uv", "run", str(script), "--json"],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            pass
    return None


def _first_versions(api_data):
    """Extract versions list from the first entry of API response data."""
    data = api_data.get("data", [])
    return data[0].get("versions", []) if data else []


def _fetch_api(product_name):
    """Fetch lifecycle data directly from the Red Hat API (fallback)."""
    url = f"{LIFECYCLE_API_URL}?name={urllib.parse.quote_plus(product_name)}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "rhdh-skill"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: Failed to fetch lifecycle data for {product_name}: {exc}", file=sys.stderr)
        return None


def _get_rhdh_lifecycle():
    """Get RHDH lifecycle data via subprocess or direct API call."""
    # Try subprocess first
    data = _fetch_lifecycle_json("check_rhdh_lifecycle.py")
    if data and "versions" in data:
        return data["versions"]

    # Fallback: direct API call + minimal parsing
    api_data = _fetch_api("Red Hat Developer Hub")
    if not api_data:
        return []
    versions_raw = _first_versions(api_data)
    results = []
    for ver in versions_raw:
        ocp_compat = ver.get("openshift_compatibility", "")
        ocp_versions = [v.strip() for v in ocp_compat.split(",") if v.strip()] if ocp_compat else []
        results.append(
            {
                "version": ver.get("name", ""),
                "type": ver.get("type", ""),
                "supported": ver.get("type", "") != "End of life",
                "ocp_versions": ocp_versions,
            }
        )
    results.sort(key=lambda v: ver_sort_key(v["version"]) if "." in v["version"] else [0])
    return results


def _get_ocp_lifecycle(today):
    """Get OCP lifecycle data via subprocess or direct API call."""
    import re

    # Try subprocess first
    data = _fetch_lifecycle_json("check_ocp_lifecycle.py")
    if data and "versions" in data:
        return data["versions"]

    # Fallback: direct API call + phase classification
    api_data = _fetch_api("Red Hat OpenShift Container Platform")
    if not api_data:
        return []

    def _is_date(val):
        return bool(val and isinstance(val, str) and re.match(r"^\d{4}-\d{2}-\d{2}", val))

    def _to_date(val):
        return val[:10] if _is_date(val) else None

    versions = _first_versions(api_data)
    versions = [v for v in versions if re.match(r"^\d+\.\d+$", v.get("name", ""))]
    versions = [v for v in versions if int(v["name"].split(".")[0]) >= 4]

    phase_order = [
        "Extended update support Term 2",
        "Extended update support",
        "Maintenance support",
        "Full support",
    ]
    results = []
    for ver in versions:
        phases = ver.get("phases", [])
        end_dates = []
        for pname in phase_order:
            for p in phases:
                if p.get("name") == pname:
                    d = _to_date(p.get("end_date"))
                    if d:
                        end_dates.append(d)

        current_phase = "End of life"
        for pname in phase_order:
            for p in phases:
                if p.get("name") != pname:
                    continue
                start = _to_date(p.get("start_date"))
                end_raw = p.get("end_date")
                end = _to_date(end_raw)
                if start and start <= today:
                    if end and end >= today:
                        current_phase = pname
                        break
                    elif end is None or (not _is_date(end_raw) and end_raw not in ("N/A", "")):
                        current_phase = pname
                        break
            if current_phase != "End of life":
                break
        results.append(
            {
                "version": ver["name"],
                "ocp_supported": current_phase != "End of life",
                "phase": current_phase,
            }
        )
    results.sort(key=lambda v: ver_sort_key(v["version"]))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze RHDH OCP version coverage.")
    parser.add_argument("--pool-dir", default=POOL_DIR, help="Pool directory")
    parser.add_argument("--config-dir", default=CI_CONFIG_DIR, help="CI config directory")
    parser.add_argument("--repo-dir", help="Path to openshift/release checkout")
    args = parser.parse_args(argv)

    root, is_remote = resolve_repo_root(args.repo_dir)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    mode_desc = "remote (GitHub API)" if is_remote else "local"

    print("=" * 56)
    print("  RHDH OCP Coverage Analysis")
    print("=" * 56)
    print()
    print(f"Pool directory:   {args.pool_dir}")
    print(f"Config directory: {args.config_dir}")
    print(f"Access mode:      {mode_desc}")
    print(f"Analysis time:    {now.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print()

    # ------- 1. Cluster pool versions -------
    print("--- Cluster Pools ---")
    pool_versions = []
    pool_files = list_yaml_files(args.pool_dir, "*_clusterpool.yaml", root, is_remote)
    for filepath in pool_files:
        data = fetch_yaml(filepath, root, is_remote)
        if not data:
            continue
        ver = data.get("metadata", {}).get("labels", {}).get("version")
        if not ver:
            continue
        pool_name = data.get("metadata", {}).get("name", "unknown")
        size = data.get("spec", {}).get("size", 0)
        max_size = data.get("spec", {}).get("maxSize", 0)
        pool_versions.append(ver)
        print(f"  {ver:<8s}  {pool_name:<25s}  size={size} max={max_size}")
    print()

    # ------- 2. Test config versions per branch -------
    print("--- Test Configs ---")
    prefix = "redhat-developer-rhdh-"
    branch_versions: dict[str, list[str]] = {}
    all_test_versions: list[str] = []

    config_files = list_yaml_files(args.config_dir, f"{prefix}*.yaml", root, is_remote)
    for filepath in config_files:
        branch = extract_branch(prefix, filepath)
        data = fetch_yaml(filepath, root, is_remote)
        if not data or "tests" not in data:
            continue
        versions = sorted(
            {
                t["cluster_claim"]["version"]
                for t in data["tests"]
                if t.get("cluster_claim", {}).get("version")
            },
            key=ver_sort_key,
        )
        if versions:
            branch_versions[branch] = versions
            all_test_versions.extend(versions)
            print(f"  {branch}: {' '.join(versions)}")
    print()

    unique_test_versions = sorted(set(all_test_versions), key=ver_sort_key)

    # ------- 3. RHDH lifecycle -------
    print("--- RHDH Lifecycle ---")
    print("  Fetching lifecycle data...")
    rhdh_data = _get_rhdh_lifecycle()
    if not rhdh_data:
        print("  ERROR: Failed to fetch RHDH lifecycle data", file=sys.stderr)
        sys.exit(1)

    for v in rhdh_data:
        if v["supported"]:
            print(
                f"  RHDH {v['version']} ({v['type']}): OCP {', '.join(v.get('ocp_versions', []))}"
            )

    rhdh_supported_ocp = sorted(
        {ocp for v in rhdh_data if v["supported"] for ocp in v.get("ocp_versions", [])},
        key=ver_sort_key,
    )
    print()
    print(f"  OCP versions supported by active RHDH releases: {' '.join(rhdh_supported_ocp)}")
    print()

    # Build per-RHDH-release -> OCP version mapping
    rhdh_branch_ocp: dict[str, list[str]] = {}
    latest_rhdh_ocp: list[str] = []
    for v in rhdh_data:
        if v["supported"]:
            branch = f"release-{v['version']}"
            rhdh_branch_ocp[branch] = v["ocp_versions"]
            latest_rhdh_ocp = v["ocp_versions"]

    # ------- 4. OCP lifecycle -------
    print("--- OCP Lifecycle ---")
    print("  Fetching lifecycle data...")
    ocp_lifecycle = _get_ocp_lifecycle(today)
    if not ocp_lifecycle:
        print("  ERROR: Failed to fetch OCP lifecycle data", file=sys.stderr)
        sys.exit(1)

    ocp_supported = [v["version"] for v in ocp_lifecycle if v["ocp_supported"]]
    ocp_eol = [v["version"] for v in ocp_lifecycle if not v["ocp_supported"]]
    print(f"  OCP supported:     {' '.join(ocp_supported)}")
    print(f"  OCP end-of-life:   {' '.join(ocp_eol)}")
    print()

    # Compute "main" branch OCP support
    if latest_rhdh_ocp:
        max_rhdh = max(latest_rhdh_ocp, key=ver_sort_key)
        max_parts = ver_sort_key(max_rhdh)
        main_ocp = list(latest_rhdh_ocp)
        for ocp_ver in ocp_supported:
            ocp_parts = ver_sort_key(ocp_ver)
            if ocp_parts > max_parts and ocp_ver not in main_ocp:
                main_ocp.append(ocp_ver)
        rhdh_branch_ocp["main"] = sorted(main_ocp, key=ver_sort_key)

    # ------- 5. OCP version matrix -------
    print("--- OCP Version Matrix ---")
    print()
    print(
        f"  {'OCP':<8s}  {'OCP_SUPP':<10s}  {'RHDH_SUPP':<10s}  {'OCP_PHASE':<30s}  RHDH_RELEASES"
    )
    print(
        f"  {'---':<8s}  {'--------':<10s}  {'---------':<10s}  {'---------':<30s}  -------------"
    )

    all_relevant = sorted(
        set(pool_versions + unique_test_versions + rhdh_supported_ocp + ocp_supported),
        key=ver_sort_key,
    )

    ocp_phase_map = {v["version"]: v for v in ocp_lifecycle}
    for ver in all_relevant:
        ocp_info = ocp_phase_map.get(ver, {})
        ocp_sup = "yes" if ocp_info.get("ocp_supported") else "no"
        ocp_phase = ocp_info.get("phase", "N/A")
        rhdh_sup = "yes" if ver in rhdh_supported_ocp else "no"
        rhdh_releases = ", ".join(
            v["version"] for v in rhdh_data if v["supported"] and ver in v["ocp_versions"]
        )
        print(f"  {ver:<8s}  {ocp_sup:<10s}  {rhdh_sup:<10s}  {ocp_phase:<30s}  {rhdh_releases}")
    print()

    # ------- 6. Cross-reference analysis -------
    print("=" * 56)
    print("  Analysis Results")
    print("=" * 56)
    print()

    has_actions = False
    eol_pool_count = 0
    notrhdh_pool_count = 0
    mismatch_test_count = 0
    missing_pool_count = 0
    missing_test_count = 0

    # 6a. Pools for OCP-EOL versions
    print("--- Pools for OCP-EOL Versions (REMOVE) ---")
    for ver in pool_versions:
        if ver in ocp_eol:
            print(f"  REMOVE pool: {ver} (OCP end-of-life)")
            eol_pool_count += 1
            has_actions = True
    if eol_pool_count == 0:
        print("  (none)")
    print()

    # 6b. Pools for non-RHDH-supported versions
    print("--- Pools for Non-RHDH-Supported OCP Versions (REVIEW) ---")
    for ver in pool_versions:
        if ver in ocp_eol:
            continue
        if ver not in rhdh_supported_ocp:
            print(f"  REVIEW pool: {ver} (OCP supported, but not in any active RHDH release)")
            notrhdh_pool_count += 1
            has_actions = True
    if notrhdh_pool_count == 0:
        print("  (none)")
    print()

    # 6c. Test entries mismatched with RHDH compatibility
    print("--- Test Entries Mismatched With RHDH Compatibility (REVIEW) ---")
    for branch, versions in branch_versions.items():
        branch_ocp = rhdh_branch_ocp.get(branch, [])
        for ver in versions:
            if ver in ocp_eol:
                print(f"  REMOVE test: {ver} from {branch} (OCP end-of-life)")
                mismatch_test_count += 1
                has_actions = True
            elif branch_ocp and ver not in branch_ocp:
                print(f"  REVIEW test: {ver} in {branch} (not in RHDH openshift_compatibility)")
                mismatch_test_count += 1
                has_actions = True
    if mismatch_test_count == 0:
        print("  (none)")
    print()

    # 6d. Missing pools
    print("--- RHDH-Supported OCP Versions Missing Pools (ADD) ---")
    all_rhdh_ocp = sorted(
        {ver for ocp_list in rhdh_branch_ocp.values() for ver in ocp_list},
        key=ver_sort_key,
    )
    for ver in all_rhdh_ocp:
        if ver in ocp_eol:
            continue
        if ver not in pool_versions:
            needed = ", ".join(
                v["version"] for v in rhdh_data if v["supported"] and ver in v["ocp_versions"]
            )
            print(f"  ADD pool: {ver} (needed by RHDH {needed})")
            missing_pool_count += 1
            has_actions = True
    if missing_pool_count == 0:
        print("  (none)")
    print()

    # 6e. Missing tests
    print("--- RHDH-Supported OCP Versions Missing Tests (ADD) ---")
    for branch, ocp_list in rhdh_branch_ocp.items():
        existing = branch_versions.get(branch, [])
        for ver in ocp_list:
            if ver in ocp_eol:
                continue
            if ver not in existing:
                print(f"  ADD test: {ver} to {branch}")
                missing_test_count += 1
                has_actions = True
    if missing_test_count == 0:
        print("  (none)")
    print()

    # ------- 7. Summary -------
    print("=" * 56)
    print("  Summary")
    print("=" * 56)
    print()
    print(f"  Pool versions:           {' '.join(pool_versions)}")
    print(f"  Test versions:           {' '.join(unique_test_versions)}")
    print(f"  OCP supported:           {' '.join(ocp_supported)}")
    print(f"  RHDH-supported OCP:      {' '.join(rhdh_supported_ocp)}")
    print()

    print("  RHDH branch -> OCP support (excluding OCP-EOL):")
    for branch in sorted(rhdh_branch_ocp.keys()):
        active = [v for v in rhdh_branch_ocp[branch] if v not in ocp_eol]
        eol_listed = [v for v in rhdh_branch_ocp[branch] if v in ocp_eol]
        line = f"    {branch}: {' '.join(active)}"
        if eol_listed:
            line += f"  (RHDH lists but OCP-EOL: {' '.join(eol_listed)})"
        print(line)
    print()

    print(f"  EOL pools to remove:         {eol_pool_count}")
    print(f"  Non-RHDH pools to review:    {notrhdh_pool_count}")
    print(f"  Mismatched tests to review:  {mismatch_test_count}")
    print(f"  Missing pools to add:        {missing_pool_count}")
    print(f"  Missing tests to add:        {missing_test_count}")
    print()

    if has_actions:
        print("  Data sources:")
        print("    RHDH lifecycle: https://access.redhat.com/support/policy/updates/developerhub")
        print(
            "    OCP lifecycle:  https://access.redhat.com/product-life-cycles/"
            "?product=OpenShift+Container+Platform+4"
        )
        print()
        print("  NOTE: The 'main' branch targets the next unreleased RHDH version.")
        print("  Its OCP support is estimated as: latest RHDH release's OCP list")
        print("  plus any newer OCP versions that have reached GA.")
        print("  REVIEW items require judgment; REMOVE/ADD items are actionable.")
    else:
        print("  All clear -- no coverage gaps or stale configurations found.")


if __name__ == "__main__":
    main()
