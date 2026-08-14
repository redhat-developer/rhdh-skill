"""RHDH release lifecycle data -- wrapper around the generic Red Hat API client.

Usage:
    from rhdh_lifecycle.rhdh import fetch_rhdh_lifecycle
    versions = fetch_rhdh_lifecycle()
"""

from __future__ import annotations

from rhdh_lifecycle.redhat import fetch_api, fetch_product_lifecycle, parse_versions
from rhdh_lifecycle.versions import ver_sort_key


def _enrich_rhdh_version(v):
    """Flatten RHDH-specific fields into top-level for convenience."""
    v["ocp_versions"] = v.get("extra", {}).get("ocp_versions", [])
    v["full_support_end"] = v.get("phases", {}).get("Full support", "N/A")
    v["maintenance_end"] = v.get("phases", {}).get("Maintenance support", "N/A")


def fetch_rhdh_lifecycle(filter_version=None):
    """Fetch and parse RHDH lifecycle data."""
    versions = fetch_product_lifecycle("rhdh", filter_version)
    for v in versions:
        _enrich_rhdh_version(v)
    return versions


def fetch_lifecycle_api(product_name):
    """Fetch raw API data. Delegates to redhat module."""
    return fetch_api(product_name)


def parse_rhdh_versions(api_data, filter_version=None):
    """Parse RHDH versions from raw API data."""
    versions = parse_versions(api_data, filter_version)
    for v in versions:
        _enrich_rhdh_version(v)
    return versions


def rhdh_supported_ocp_versions(rhdh_data):
    """Return sorted list of OCP versions supported by any active RHDH release."""
    return sorted(
        {ocp for v in rhdh_data if v["supported"] for ocp in v.get("ocp_versions", [])},
        key=ver_sort_key,
    )
