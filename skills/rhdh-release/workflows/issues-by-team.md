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

Filter to category "Engineering" and status "Active". This gives team names and `team_id` values.

## Step 3 (fallback): Query issues and filter by team

Fetch all open issues for the release, enriched with team data:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --limit 200 --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status,team
```

To filter to a specific team by team ID:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --limit 200 --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -f team_id={{TEAM_ID}} -s key,summary,status
```

**Important:** Always use `parse_issues.py --enrich` for team counts — the Team field is a custom field that cannot be queried via JQL directly.

## Step 4 (fallback): Build per-team counts

For each active engineering team, count the matching issues and build a Jira search link.

## Step 5 (fallback): Format output

| Team | Team ID | Issue Count | Lead | Jira Link |
|------|---------|-------------|------|-----------|
| {{TEAM_NAME}} | {{TEAM_ID}} | {{COUNT}} | @{{LEAD_SLACK}} | [View](https://issues.redhat.com/issues/?jql=...) |

</process>

<gotchas>

- The Team custom field **cannot** be used in JQL. Always use `parse_issues.py --enrich` to filter by team.
- Use `--limit 200` or `--paginate` to get all results — default page size is 30.
- For announcement workflows, use the specific freeze-scoped JQL (e.g., `feature_freeze_issues`) as the base query instead of `open_issues`.

</gotchas>

<success_criteria>

- [ ] Per-team issue counts from `parse_issues.py --enrich`
- [ ] Jira search link per team
- [ ] Total count across all teams

</success_criteria>
