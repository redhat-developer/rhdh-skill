"""Unified client for the Red Hat Product Life Cycles API.

Fetches lifecycle data for any Red Hat product (RHDH, OCP, RHBK, Quay, etc.)
and returns a consistent structure. Product-specific post-processing functions
handle cases like RHBK major version grouping or RHDH OCP compatibility.

Usage:
    from rhdh_lifecycle.redhat import fetch_product_lifecycle

    versions = fetch_product_lifecycle("rhbk")
    versions = fetch_product_lifecycle("Red Hat Quay")
    versions = fetch_product_lifecycle("ocp", filter_version="4.16")
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from rhdh_lifecycle.versions import is_date, to_date, ver_sort_key

LIFECYCLE_API_URL = "https://access.redhat.com/product-life-cycles/api/v1/products"

PRODUCT_ALIASES = {
    "rhdh": "Red Hat Developer Hub",
    "ocp": "Red Hat OpenShift Container Platform",
    "rhbk": "Red Hat build of Keycloak",
    "quay": "Red Hat Quay",
    "rosa": "Red Hat OpenShift Service on AWS",
    "osd": "Red Hat OpenShift Dedicated",
}


def _phase_date(phases, phase_name):
    """Extract the end_date for a named phase, formatted as YYYY-MM-DD or raw string."""
    for p in phases:
        if p.get("name") == phase_name:
            d = p.get("end_date", "N/A")
            if d and isinstance(d, str) and is_date(d):
                return d[:10]
            return str(d) if d else "N/A"
    return "N/A"


def resolve_product_name(product):
    """Resolve a product alias to the full API product name."""
    return PRODUCT_ALIASES.get(product.lower(), product)


def fetch_api(product_name):
    """Fetch raw lifecycle data from the Red Hat Product Life Cycles API.

    Returns the parsed JSON response, or None on failure.
    """
    url = f"{LIFECYCLE_API_URL}?name={urllib.parse.quote_plus(product_name)}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "rhdh-skills"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: Failed to fetch lifecycle data for {product_name}: {exc}", file=sys.stderr)
        return None


def parse_versions(api_data, filter_version=None):
    """Parse raw API response into a consistent list of version dicts.

    Returns a list of dicts with keys: version, type, supported, ga_date,
    end_date, phases (dict of phase_name -> end_date), extra (dict for
    product-specific fields like ocp_versions).
    """
    data_list = api_data.get("data", [])
    if not data_list:
        return []
    versions_raw = data_list[0].get("versions", [])

    results = []
    for ver in versions_raw:
        name = ver.get("name", "")
        if filter_version and name != filter_version:
            continue
        vtype = ver.get("type", "")
        raw_phases = ver.get("phases", [])

        # Build phases dict
        phases = {}
        for p in raw_phases:
            pname = p.get("name", "")
            if pname:
                phases[pname] = _phase_date(raw_phases, pname)

        # GA date
        ga_date = phases.get("General availability", "N/A")

        # Latest end-of-support date across all non-GA phases
        end_dates = [to_date(d) for d in phases.values() if to_date(d) and d != ga_date]
        end_date = max(end_dates) if end_dates else "N/A"

        # Product-specific extra fields
        extra = {}
        ocp_compat = ver.get("openshift_compatibility", "")
        if ocp_compat:
            extra["ocp_versions"] = [v.strip() for v in ocp_compat.split(",") if v.strip()]

        results.append(
            {
                "version": name,
                "type": vtype,
                "supported": vtype != "End of life",
                "ga_date": ga_date,
                "end_date": end_date,
                "phases": phases,
                "extra": extra,
            }
        )

    results.sort(key=lambda v: ver_sort_key(v["version"]))
    return results


def fetch_product_lifecycle(product, filter_version=None):
    """Fetch and parse lifecycle data for a Red Hat product.

    Args:
        product: Product alias ("rhbk", "quay", "rhdh", "ocp") or full name.
        filter_version: Optional version string to filter to.

    Returns:
        List of version dicts with consistent shape.
    """
    full_name = resolve_product_name(product)
    api_data = fetch_api(full_name)
    if api_data is None:
        return []
    return parse_versions(api_data, filter_version)


def rhbk_major_versions(versions):
    """Group RHBK minor versions into major version summaries.

    A major version is "active" if at least one of its minor releases
    is not end-of-life.

    Returns:
        List of dicts: {major_version, active, ga_date, end_date, minor_releases}
    """
    groups = {}
    for v in versions:
        # Skip umbrella entries like "26.x"
        if "x" in v["version"] or not re.match(r"^\d+\.\d+$", v["version"]):
            continue
        major = v["version"].split(".")[0]
        if major not in groups:
            groups[major] = {
                "minor_releases": [],
                "any_active": False,
                "ga_dates": [],
                "end_dates": [],
            }
        groups[major]["minor_releases"].append(v["version"])
        if v["supported"]:
            groups[major]["any_active"] = True
        if v["ga_date"] != "N/A":
            groups[major]["ga_dates"].append(v["ga_date"])
        if v["end_date"] != "N/A":
            groups[major]["end_dates"].append(v["end_date"])

    results = []
    for major, info in sorted(groups.items(), key=lambda x: int(x[0])):
        results.append(
            {
                "major_version": major,
                "active": info["any_active"],
                "ga_date": min(info["ga_dates"]) if info["ga_dates"] else "N/A",
                "end_date": max(info["end_dates"]) if info["end_dates"] else "N/A",
                "minor_releases": sorted(info["minor_releases"], key=ver_sort_key),
            }
        )
    return results


def list_known_products():
    """Return sorted list of known product aliases and their full names."""
    return sorted(PRODUCT_ALIASES.items())
