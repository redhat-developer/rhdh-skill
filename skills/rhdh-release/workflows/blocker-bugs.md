# Workflow: Retrieve Blocker Bugs

Compile all open blocker bugs for a release.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json blockers {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Query blocker bugs

Use the `open_issues` JQL from `references/jql-release.md` with a priority filter:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = bug AND priority = Blocker' --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich
```

## Step 3 (fallback): Format output

Present full details for each blocker:

| Key | Summary | Status | Priority | Assignee | Team |
|-----|---------|--------|----------|----------|------|
| [{{KEY}}](https://issues.redhat.com/browse/{{KEY}}) | {{SUMMARY}} | {{STATUS}} | Blocker | {{ASSIGNEE}} | {{TEAM}} |

**Total:** {{COUNT}} blocker bugs — [View in Jira](https://issues.redhat.com/issues/?jql=...)

</process>

<gotchas>

- If no release version is specified, ask the user. Default to the latest active release from the `active_release` query.
- Include the full Jira link for each issue for quick access.

</gotchas>

<success_criteria>

- [ ] Each blocker listed with key, summary, status, and assignee
- [ ] Total count with Jira search link

</success_criteria>
