"""Version-string helpers.

Bundled with this skill so the scripts run installed alone.
"""

from __future__ import annotations


def ver_sort_key(version_str):
    """Sort key for version strings like '4.16' or '26.2'."""
    try:
        return [int(x) for x in version_str.split(".")]
    except ValueError:
        return [0]
