"""Version sorting, date helpers, and endoflife.date filtering.

Bundled with this skill so the scripts run installed alone. A
sibling skill carrying something similar is expected, not a defect.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request


def fetch_json(url):
    """Fetch JSON from a URL.

    Returns the parsed JSON, or None on failure.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "rhdh-skills"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as exc:
        print(f"ERROR: Failed to fetch {url}: {exc}", file=sys.stderr)
        return None


def is_date(val):
    """Return True if val looks like a YYYY-MM-DD date string."""
    if not val or not isinstance(val, str):
        return False
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", val))


def to_date(val):
    """Extract YYYY-MM-DD from a date string, or None."""
    if is_date(val):
        return val[:10]
    return None


def ver_sort_key(version_str):
    """Sort key for version strings like '4.16' or '26.2'."""
    try:
        return [int(x) for x in version_str.split(".")]
    except ValueError:
        return [0]


def filter_supported_eol_entries(eol_data, today):
    """Filter endoflife.date entries to those still supported.

    Considers both ``eol`` and ``extendedSupport`` fields. Returns the
    filtered list sorted by cycle version (newest first).
    """
    supported = []
    for entry in eol_data:
        eol = entry.get("eol", "N/A")
        ext = entry.get("extendedSupport", "N/A")
        has_support = False
        if eol == "N/A":
            has_support = True
        elif isinstance(eol, bool):
            has_support = not eol
        elif isinstance(eol, str) and eol > today:
            has_support = True
        if not has_support and isinstance(ext, str) and ext > today:
            has_support = True
        if has_support:
            supported.append(entry)
    supported.sort(key=lambda e: ver_sort_key(e["cycle"]), reverse=True)
    return supported
