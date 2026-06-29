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

## gog CLI Setup

Google Sheets and Docs access uses the [gog CLI](https://gogcli.sh).

1. Install: `brew install gogcli` (requires Homebrew; `brew trust openclaw/tap` if prompted)
2. Get OAuth credentials: request `client_secret.json` from <mhild@redhat.com>
3. Import credentials: `gog auth credentials client_secret.json`
4. Authenticate: `gog auth add <your-email> --services sheets,docs,drive`
5. Verify: `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json`
