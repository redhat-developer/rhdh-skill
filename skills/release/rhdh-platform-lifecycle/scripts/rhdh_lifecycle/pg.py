"""PostgreSQL lifecycle data from endoflife.date.

Aggregates PostgreSQL version lifecycle from three providers:
  - upstream PostgreSQL (endoflife.date/api/postgresql.json)
  - Amazon RDS for PostgreSQL (endoflife.date/api/amazon-rds-postgresql.json)
  - Azure Database for PostgreSQL (endoflife.date/api/azure-database-for-postgresql.json)

Usage:
    from rhdh_lifecycle.pg import fetch_pg_lifecycle
    versions = fetch_pg_lifecycle()
"""

from __future__ import annotations

from rhdh_lifecycle.versions import fetch_json

PROVIDERS = {
    "upstream": "https://endoflife.date/api/postgresql.json",
    "rds": "https://endoflife.date/api/amazon-rds-postgresql.json",
    "azure": "https://endoflife.date/api/azure-database-for-postgresql.json",
}


def _normalize_eol(val):
    """Normalize EOL value to a date string or 'N/A'."""
    if val is None or val == "N/A":
        return "N/A"
    if isinstance(val, bool):
        return "N/A" if val else "active"
    return str(val)


def fetch_pg_lifecycle(today=None):
    """Fetch PostgreSQL lifecycle data from all providers.

    Returns a list of dicts per major version:
        {major_version, upstream_eol, rds_eol, azure_eol,
         upstream_release, any_supported}

    any_supported is True if the version is not EOL on at least one provider.
    """
    # Fetch all providers
    provider_data = {}
    for provider, url in PROVIDERS.items():
        data = fetch_json(url)
        if data:
            provider_data[provider] = {str(e["cycle"]): e for e in data}
        else:
            provider_data[provider] = {}

    # Collect all major versions across providers
    all_versions = set()
    for pdata in provider_data.values():
        all_versions.update(pdata.keys())

    # Filter to numeric major versions only
    all_versions = {v for v in all_versions if v.isdigit()}

    results = []
    for ver in sorted(all_versions, key=int):
        upstream = provider_data.get("upstream", {}).get(ver, {})
        rds = provider_data.get("rds", {}).get(ver, {})
        azure = provider_data.get("azure", {}).get(ver, {})

        upstream_eol = _normalize_eol(upstream.get("eol"))
        rds_eol = _normalize_eol(rds.get("eol"))
        azure_eol = _normalize_eol(azure.get("eol"))

        # Check if any provider still supports this version
        any_supported = False
        if today:
            for eol in [upstream_eol, rds_eol, azure_eol]:
                if eol == "active":
                    any_supported = True
                elif eol != "N/A" and eol > today:
                    any_supported = True
        else:
            # Without a date, just check if any EOL is in the future or unknown
            for eol in [upstream_eol, rds_eol, azure_eol]:
                if eol in ("active", "N/A"):
                    any_supported = True
                    break

        results.append(
            {
                "major_version": ver,
                "upstream_eol": upstream_eol,
                "rds_eol": rds_eol,
                "azure_eol": azure_eol,
                "upstream_release": upstream.get("releaseDate", "N/A"),
                "any_supported": any_supported,
            }
        )

    return results
