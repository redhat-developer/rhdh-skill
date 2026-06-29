# Workflow: Retrieve Outstanding Release Notes

Compile features and bugs missing Release Note Type field.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json notes {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Count issues missing Release Note Type

Use the `release_notes` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql 'project in (RHIDP, "Red Hat Developer Hub Bugs", "RHDH Support", rhdhplan) and issuetype in (Feature, bug) and "Release Note Type" is EMPTY and fixVersion = "{{RELEASE_VERSION}}"' --count
```

## Step 3 (fallback): Get details (if needed)

```bash
acli jira workitem search --jql 'project in (RHIDP, "Red Hat Developer Hub Bugs", "RHDH Support", rhdhplan) and issuetype in (Feature, bug) and "Release Note Type" is EMPTY and fixVersion = "{{RELEASE_VERSION}}"' --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status,issuetype
```

## Step 4 (fallback): Format output

**{{COUNT}} issues missing Release Note Type** — [View in Jira](https://issues.redhat.com/issues/?jql=...)

Also link to the [Release Notes Dashboard](https://issues.redhat.com/secure/Dashboard.jspa?selectPageId=12382090) for full details.

</process>

<gotchas>

- Release Notes must be filled before release — this is a documentation blocker.
- Refer to [RHDH Release Notes Process](https://docs.google.com/document/d/1KFMkRVTkbDIhyZviZcuVn9UfJp64lKmokzT4ftMrj4w/edit) for the full process.

</gotchas>

<success_criteria>

- [ ] Count of issues missing Release Note Type
- [ ] Jira search link to the outstanding items
- [ ] Link to Release Notes Dashboard

</success_criteria>
