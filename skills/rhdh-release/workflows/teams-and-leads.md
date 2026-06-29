# Workflow: Retrieve Teams and Leads

Structured list of all active RHDH teams with leads and Slack handles.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **gog CLI** | `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json` succeeds |

If gog check fails: run `gog auth add <email>`.

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json teams
```

To filter by category:

```bash
python scripts/release.py --json teams --category Engineering
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Fetch team data via gog

```bash
gog sheets get 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM Team --json --results-only
```

Filter the JSON output to active teams only (status column = "Active"). To filter by category, match the category column.

## Step 3 (fallback): Format output

Present as a table:

| Category | Team Name | Team ID | Leads | Slack Handles | Status |
|----------|-----------|---------|-------|---------------|--------|
| {{CATEGORY}} | {{TEAM_NAME}} | {{TEAM_ID}} | {{LEADS}} | {{SLACK_HANDLES}} | {{STATUS}} |

Include link to source: [RHDH Team Mapping](https://docs.google.com/spreadsheets/d/1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM/edit)

</process>

<gotchas>

- By default only active teams are returned. The CLI filters by `status = Active` in the Google Sheet.
- The `team_id` is the numeric ID used by `parse_issues.py --enrich` for team-based filtering — the Team custom field cannot be queried via JQL directly.

</gotchas>

<success_criteria>

- [ ] Table with team name, lead, category, and team ID
- [ ] Only active teams shown by default

</success_criteria>
