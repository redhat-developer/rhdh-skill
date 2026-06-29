# Workflow: Announce Code Freeze Update

Generate a Slack message announcing Code Freeze status update.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |
| **gog CLI** | `gog sheets metadata 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM --json` succeeds |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json slack code-freeze-update {{RELEASE_VERSION}}
```

If the CLI succeeds, use its `slack_message` field directly (it's the filled template). If it fails, follow the manual steps below.

## Step 2 (fallback): Get Code Freeze date

Run the `release-dates` workflow or fetch directly:

```bash
acli jira workitem search --jql "project=rhdhplan AND issuetype=feature AND component=release AND status != closed" --json
```

Then for the matching release issue:

```bash
acli jira workitem view {{RELEASE_ISSUE_KEY}} --json
```

Extract the Code Freeze date from the description.

## Step 3 (fallback): Get active engineering teams

```bash
gog sheets get 1vQXfvID72qwqvLb17eyGOvnZXrZG7NBzTGv6RP9wvyM Team --json --results-only
```

Filter to category "Engineering" and status "Active".

## Step 4 (fallback): Get outstanding release notes count

```bash
acli jira workitem search --jql 'project in (RHIDP, "Red Hat Developer Hub Bugs", "RHDH Support", rhdhplan) and issuetype in (Feature, bug) and "Release Note Type" is EMPTY and fixVersion = "{{RELEASE_VERSION}}"' --count
```

## Step 5 (fallback): Get feature subtasks count

Use the `feature_subtasks` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql 'project in (RHDHPlan) AND issuetype = sub-task AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --count
```

## Step 6 (fallback): Get per-team issue counts

Use the `code_freeze_issues` JQL (all open issues), then filter by team:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --limit 200 --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status,team
```

Group results by team and count per team.

## Step 7 (fallback): Fill template and output

Load the **Code Freeze Update** template from `references/slack-templates.md`.

Fill all placeholders:

- `{{RELEASE_VERSION}}` — the release version
- `{{CODE_FREEZE_DATE}}` — from Step 1
- `{{TEAM_NAME}}`, `{{TEAM_ISSUE_COUNT}}`, `{{JIRA_LINK}}`, `{{LEAD_SLACK}}` — repeated per team from Steps 2 and 5
- `{{OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT}}` — from Step 3
- `{{FEATURE_SUBTASK_ISSUE_COUNT}}` — from Step 4

**Output the filled template in a triple-backtick code block** for copy-paste into Slack.

</process>

<gotchas>

- Always use `parse_issues.py --enrich` for team counts — never count manually.
- The Code Freeze Update uses ALL open issues for team breakdown (unlike Feature Freeze Update which excludes infra/ops).

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] All team lines filled with count, Jira link, and lead Slack handle
- [ ] Release notes and feature subtask counts filled
- [ ] Code Freeze date filled

</success_criteria>
