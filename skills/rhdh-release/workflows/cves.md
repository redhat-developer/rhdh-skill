# Workflow: Retrieve List of CVEs

Compile all CVE issues for a release.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json cves {{RELEASE_VERSION}}
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Query CVE issues

Use the `cves` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql 'project IN (RHIDP, rhdhbugs) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype in (weakness, Vulnerability, bug) and summary ~ "CVE*"' --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich
```

## Step 3 (fallback): Get count

```bash
acli jira workitem search --jql 'project IN (RHIDP, rhdhbugs) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype in (weakness, Vulnerability, bug) and summary ~ "CVE*"' --count
```

## Step 4 (fallback): Format output

Present full details for each CVE:

| Key | Summary | Type | Status | Priority | Assignee |
|-----|---------|------|--------|----------|----------|
| [{{KEY}}](https://issues.redhat.com/browse/{{KEY}}) | {{SUMMARY}} | {{TYPE}} | {{STATUS}} | {{PRIORITY}} | {{ASSIGNEE}} |

**Total:** {{COUNT}} CVEs — [View in Jira](https://issues.redhat.com/issues/?jql=...)

</process>

<gotchas>

- CVEs are critical for security tracking — after Code Freeze, only critical severity CVEs are considered for inclusion before GA.
- If no release version is specified, ask the user.

</gotchas>

<success_criteria>

- [ ] Each CVE listed with key, summary, severity, and status
- [ ] Total count with Jira search link

</success_criteria>
