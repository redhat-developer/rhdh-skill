"""OCP lifecycle phase classification.

Classifies OCP versions from the Red Hat Product Life Cycles API into
lifecycle phases (Full Support, Maintenance, EUS, End of life).

Usage:
    from rhdh_lifecycle.ocp import classify_ocp_versions
    from rhdh_lifecycle.redhat import fetch_api
    api_data = fetch_api("Red Hat OpenShift Container Platform")
    versions = classify_ocp_versions(api_data, "2025-05-13")
"""

import re

from rhdh_lifecycle.versions import is_date, to_date, ver_sort_key


def classify_ocp_versions(api_data, today):
    """Classify OCP versions from the Red Hat Product Life Cycles API.

    Args:
        api_data: Raw API response dict (the full JSON response).
        today: Date string in YYYY-MM-DD format.

    Returns:
        List of dicts with keys: version, ocp_supported, phase,
        ga_date, end_of_support_date. Sorted by version.
    """
    data_list = api_data.get("data", [])
    if not data_list:
        return []
    versions = data_list[0].get("versions", [])

    # Keep only clean X.Y version names, skip variants like "4.6 EUS" or "3"
    versions = [v for v in versions if re.match(r"^\d+\.\d+$", v.get("name", ""))]

    # Filter to OCP 4.x and above (future-proof for 5.x+)
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

        # Find latest end-of-support date across all support phases
        end_dates = []
        for pname in phase_order:
            for p in phases:
                if p.get("name") == pname:
                    d = to_date(p.get("end_date"))
                    if d:
                        end_dates.append(d)
        end_of_support = max(end_dates) if end_dates else None

        # GA date
        ga_raw = None
        for p in phases:
            if p.get("name") == "General availability":
                ga_raw = p.get("end_date", "N/A")
                break

        # Determine current phase
        current_phase = "End of life"
        for pname in phase_order:
            for p in phases:
                if p.get("name") != pname:
                    continue
                start = to_date(p.get("start_date"))
                end_raw = p.get("end_date")
                end = to_date(end_raw)
                if start and start <= today:
                    if end and end >= today:
                        current_phase = pname
                        break
                    elif not is_date(end_raw) and end_raw not in (
                        "N/A",
                        "",
                        None,
                    ):
                        # Non-date end value (e.g., "Ongoing") means still active
                        current_phase = pname
                        break
            if current_phase != "End of life":
                break

        results.append(
            {
                "version": ver["name"],
                "ocp_supported": current_phase != "End of life",
                "phase": current_phase,
                "ga_date": to_date(ga_raw) if is_date(ga_raw) else "N/A",
                "end_of_support_date": end_of_support or "N/A",
            }
        )

    # Sort by version
    results.sort(key=lambda v: ver_sort_key(v["version"]))
    return results
