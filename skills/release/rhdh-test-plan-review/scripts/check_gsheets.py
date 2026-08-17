#!/usr/bin/env python3
"""Check whether the native gog adapter can read the RHDH schedule."""

import argparse
import json
import os
import sys

from fetch_schedule import DEFAULT_SHEET_ID, get_sheet_tabs, get_sheets_client

_no_color = os.environ.get("NO_COLOR") is not None
_is_tty = sys.stderr.isatty() and not _no_color


def colored(text, code):
    if _is_tty:
        return f"\033[{code}m{text}\033[0m"
    return text


def main():
    parser = argparse.ArgumentParser(
        description="Check whether gog can read the RHDH release schedule."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON (default: human-readable)",
    )
    args = parser.parse_args()

    client = get_sheets_client()
    tabs = get_sheet_tabs(client, DEFAULT_SHEET_ID)
    result = {"capability_ready": bool(tabs), "method": "gog", "error": None}

    if args.json_output:
        json.dump(result, sys.stdout, indent=2)
        print()
    else:
        if result["capability_ready"]:
            print(colored("✓", "32") + " gog can read the RHDH schedule")
        else:
            print(colored("✗", "31") + " Google Sheets capability is unavailable")

    sys.exit(0 if result["capability_ready"] else 1)


if __name__ == "__main__":
    main()
