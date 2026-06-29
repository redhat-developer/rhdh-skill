# Workflow: Retrieve Active Release Status by Issue Type

Compile status of all active releases with open issue counts by type.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json status {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Find active releases

Use the `active_release` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql "project=rhdhplan AND issuetype=feature AND component=release AND status != closed" --json
```

Extract the release versions from the results (from `fixVersions` or issue summary).

## Step 3 (fallback): Count issues by type for each release

For each release version, query issue counts per type using the `open_issues_by_type` JQL:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Feature"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Epic"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Story"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Task"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Sub-task"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Bug"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Vulnerability"' --count
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = "Weakness"' --count
```

## Step 4 (fallback): Get total open issue count

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --count
```

## Step 5 (fallback): Format output

For each release version, present a table:

### RHDH {{RELEASE_VERSION}}

| Issue Type | Count | Jira Link |
|-----------|-------|-----------|
| Feature | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Epic | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Story | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Task | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Sub-task | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Bug | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Vulnerability | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| Weakness | {{COUNT}} | [View](https://issues.redhat.com/issues/?jql=...) |
| **Total** | **{{TOTAL}}** | [View](https://issues.redhat.com/issues/?jql=...) |

Include Jira search links by URL-encoding the JQL.

</process>

<gotchas>

- Use `--count` for efficiency — don't fetch full issue data just for counts.
- URL-encode the JQL when building Jira search links: `https://issues.redhat.com/issues/?jql=<URL_ENCODED_JQL>`.
- Optionally include scope changes using the `features_added_to_release` JQL from `references/jql-release.md` to flag recent additions (last 14 days).

</gotchas>

<success_criteria>

- [ ] One table per active release with counts for each issue type
- [ ] Total count per release with Jira search link
- [ ] All counts use `--count` (no full issue fetch)

</success_criteria>
