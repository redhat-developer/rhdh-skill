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

The repo is discovered via `rhdh.config.get_repo("private-data")`. Register it with `rhdh config set private-data /path/to/rhdh-skills-private-data`.

**Override:** Set `RHDH_RICH_FILTER_PATH=/path/to/file.json` to use a specific file.

Validate and inspect it with:

```bash
uv run scripts/release.py --json check
uv run scripts/release.py --json rich-filter inventory
uv run scripts/release.py --json rich-filter query static "Feature Freeze" --version 2.1.0 --count
uv run scripts/release.py --json rich-filter query smart AI --group "Scrum Team" --version 2.1.0 --count
uv run scripts/release.py --json rich-filter query queue "RNs Proposed" --version 2.1.0 --count
uv run scripts/release.py --json rich-filter query time-series "Last week" --version 2.1.0 --count
uv run scripts/release.py --json rich-filter query ratio-numerator "1.10 Plan to Commit" --count
```

See `rich-filter-coverage.md` for the complete coverage contract and exclusions.

## Google Workspace capability

Google Sheets and Docs reads use `gog`. This model-invoked skill may run a read-only capability
check, but installation and OAuth belong exclusively to `/setup-rhdh-skills`:

```bash
gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json
```

If `gog`, authentication, or target access is unavailable, name which of the three is
missing and point the user at `/setup-rhdh-skills google-workspace`. Do not install the
tool, start login, request credential files, or duplicate setup instructions in this skill.
