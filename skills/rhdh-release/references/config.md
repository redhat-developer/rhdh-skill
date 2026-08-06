# Release Manager Configuration

Static configuration values for the RHDH Release Manager skill.

## JQL Scope

| Key | Value |
|-----|-------|
| `jira_default_base_jql` | `project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND status != closed` |

## Google Drive Resources

| Key | Value | Description |
|-----|-------|-------------|
| `team_mapping_gdrive_id` | `1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM` | RHDH Team Mapping spreadsheet (sheet: "Team") |
| `release_schedule_gdrive_id` | `1knVzlMW0l0X4c7gkoiuaGql1zuFgEGwHHBsj-ygUTnc` | RHDH Release Schedule spreadsheet |
| `release_process_doc_id` | `13OkypJ3u_7Jq6kEhKhjEFwHQ12oPFDKXVzFjYW4XLdk` | Release process Google Doc |

## Rich Filter

The Rich Filter JSON is sourced from the "RHIDP Operational" Rich Filter in Jira, maintained by Matt Reid and Jasper Chui. It is required for freeze, demo/Test Day, post-freeze, release-note lifecycle, Scrum Team, and exported ad hoc queries.

The repo is discovered via `rhdh.config.get_repo("private-data")`. Register it with `rhdh config set private-data /path/to/rhdh-skill-private-data`.

**Override:** Set `RHDH_RICH_FILTER_PATH=/path/to/file.json` to use a specific file.

Validate and inspect it with:

```bash
python scripts/release.py --json check
python scripts/release.py --json rich-filter inventory
python scripts/release.py --json rich-filter query static "Feature Freeze" --version 2.1.0 --count
python scripts/release.py --json rich-filter query smart AI --group "Scrum Team" --version 2.1.0 --count
python scripts/release.py --json rich-filter query queue "RNs Proposed" --version 2.1.0 --count
python scripts/release.py --json rich-filter query time-series "Last week" --version 2.1.0 --count
python scripts/release.py --json rich-filter query ratio-numerator "1.10 Plan to Commit" --count
```

See `rich-filter-coverage.md` for the complete coverage contract and exclusions.

## gog CLI Setup

Google Sheets and Docs access uses the [gog CLI](https://gogcli.sh).

1. Install: `brew install gogcli` (requires Homebrew; `brew trust openclaw/tap` if prompted)
2. Get OAuth credentials: request `client_secret.json` from <mhild@redhat.com>
3. Import credentials: `gog auth credentials client_secret.json`
4. Authenticate: `gog auth add <your-email> --services sheets,docs,drive`
5. Verify: `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json`
