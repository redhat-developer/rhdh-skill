# Workflow: Retrieve Engineering EPICs

Compile all open Engineering EPICs not in Dev Complete or Release Pending.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json epics {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Count outstanding EPICs

Use the `epics` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql 'project IN (RHIDP) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype = epic and status not in (closed, "Release Pending", "Dev Complete")' --count
```

## Step 3 (fallback): Get EPIC details (if needed)

```bash
acli jira workitem search --jql 'project IN (RHIDP) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype = epic and status not in (closed, "Release Pending", "Dev Complete")' --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status,assignee
```

## Step 4 (fallback): Format output

**{{COUNT}} Engineering EPICs outstanding** — [View in Jira](https://issues.redhat.com/issues/?jql=...)

If detailed output requested:

| Key | Summary | Status | Assignee |
|-----|---------|--------|----------|
| [{{KEY}}](https://issues.redhat.com/browse/{{KEY}}) | {{SUMMARY}} | {{STATUS}} | {{ASSIGNEE}} |

</process>

<gotchas>

- EPICs in "Dev Complete" or "Release Pending" are excluded — they're considered done for release tracking purposes.
- If no release version is specified, ask the user.

</gotchas>

<success_criteria>

- [ ] Table with key, summary, status, and assignee per EPIC
- [ ] Only EPICs not in Dev Complete / Release Pending / Closed

</success_criteria>
