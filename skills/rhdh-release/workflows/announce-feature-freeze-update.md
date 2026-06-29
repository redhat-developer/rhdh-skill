# Workflow: Announce Feature Freeze Update

Generate a Slack message announcing Feature Freeze status update.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |
| **gog CLI** | `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json` succeeds |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json slack feature-freeze-update {{RELEASE_VERSION}}
```

If the CLI succeeds, use its `slack_message` field directly (it's the filled template). If it fails, follow the manual steps below.

## Step 2 (fallback): Get Feature Freeze date

Run the `release-dates` workflow or fetch directly:

```bash
acli jira workitem search --jql "project=rhdhplan AND issuetype=feature AND component=release AND status != closed" --json
```

Then for the matching release issue:

```bash
acli jira workitem view {{RELEASE_ISSUE_KEY}} --json
```

Extract the Feature Freeze date from the description.

## Step 3 (fallback): Get active engineering teams

```bash
gog sheets get 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM Team --json --results-only
```

Filter to category "Engineering" and status "Active".

## Step 4 (fallback): Get outstanding release notes count

Use the `release_notes` JQL:

```bash
acli jira workitem search --jql 'project in (RHIDP, "Red Hat Developer Hub Bugs", "RHDH Support", rhdhplan) and issuetype in (Feature, bug) and "Release Note Type" is EMPTY and fixVersion = "{{RELEASE_VERSION}}"' --count
```

## Step 5 (fallback): Get per-team issue counts

Use the `feature_freeze_issues` JQL as the base, then filter by team using `parse_issues.py`:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" and resolution is EMPTY AND component not in (AI, Build, Certification, "Continuous Improvement", Documentation, Knowledge, Performance, Quality, Quickstart, Release, "RHDH Local", Security, Segment, Serviceability, Support, "Team Operations", "Test Framework", "Test Infrastructure", "Upstream & Community", UX) AND Type not in (Bug, Vulnerability, sub-task) AND status not in ("Dev Complete", "Release Pending", Done, Closed) AND (labels is EMPTY OR labels != stretch-goal)' --limit 200 --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status,team
```

Group results by team and count per team.

## Step 6 (fallback): Fill template and output

Load the **Feature Freeze Update** template from `references/slack-templates.md`.

Fill all placeholders:

- `{{RELEASE_VERSION}}` — the release version
- `{{FEATURE_FREEZE_DATE}}` — from Step 1
- `{{TEAM_NAME}}`, `{{ISSUE_COUNT}}`, `{{JIRA_LINK}}`, `{{LEAD_SLACK}}` — repeated per team from Steps 2 and 4
- `{{OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT}}` — from Step 3

**Output the filled template in a triple-backtick code block** for copy-paste into Slack.

</process>

<gotchas>

- Always use `parse_issues.py --enrich` for team counts — never count manually.
- Build Jira search links by URL-encoding the JQL scoped to each team.
- The `feature_freeze_issues` JQL excludes infrastructure/ops components and bugs — this is intentional for Feature Freeze tracking.

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] All team lines filled with count, Jira link, and lead Slack handle
- [ ] Release notes count filled
- [ ] Feature Freeze date filled

</success_criteria>
