# Workflow: Retrieve Issues by Engineering Teams

Compile open issues for a release broken down by engineering team.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |
| **gog CLI** | `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json` succeeds |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json team-breakdown {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Get active engineering teams

```bash
gog sheets get 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM Team --json --results-only
```

Filter to category "Engineering" and status "Active". This gives team names and `cloud_id` values.

## Step 3 (fallback): Query issues by team using Cloud ID

Use the `open_issues_by_team` JQL template with the team's Cloud ID:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND "Team[Team]" = "{{CLOUD_ID}}"' --count
```

To get full issue details for a team:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND "Team[Team]" = "{{CLOUD_ID}}"' --json
```

The Cloud ID for each team is in the "Cloud ID" column of the RHDH Team Mapping spreadsheet (e.g., `ec74d716-af36-4b3c-950f-f79213d08f71-4403` for COPE).

## Step 4 (fallback): Build per-team counts

For each active engineering team, count the matching issues and build a Jira search link.

## Step 5 (fallback): Format output

| Team | Cloud ID | Issue Count | Lead | Jira Link |
|------|----------|-------------|------|-----------|
| {{TEAM_NAME}} | {{CLOUD_ID}} | {{COUNT}} | @{{LEAD_SLACK}} | [View](https://issues.redhat.com/issues/?jql=...) |

</process>

<gotchas>

- Use `--limit 500` or `--paginate` to get all results — default page size is 30.
- For announcement workflows, use the specific freeze-scoped JQL (e.g., `feature_freeze_issues_by_team`) as the base query instead of `open_issues_by_team`.

</gotchas>

<success_criteria>

- [ ] Per-team issue counts using Cloud ID JQL filter
- [ ] Jira search link per team
- [ ] Total count across all teams

</success_criteria>
