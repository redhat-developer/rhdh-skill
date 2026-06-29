# Workflow: Announce Feature Freeze

Generate a Slack message announcing that Feature Freeze milestone has been reached.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json slack feature-freeze {{RELEASE_VERSION}}
```

If the CLI succeeds, use its `slack_message` field directly (it's the filled template). If it fails, follow the manual steps below.

## Step 2 (fallback): Get open EPICs count

Use the `epics` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql 'project IN (RHIDP) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype = epic and status not in (closed, "Release Pending", "Dev Complete")' --count
```

## Step 3 (fallback): Get CVE count

Use the `cves` JQL:

```bash
acli jira workitem search --jql 'project IN (RHIDP, rhdhbugs) AND fixVersion = "{{RELEASE_VERSION}}" and issuetype in (weakness, Vulnerability, bug) and summary ~ "CVE*"' --count
```

## Step 4 (fallback): Get outstanding release notes count

Use the `release_notes` JQL:

```bash
acli jira workitem search --jql 'project in (RHIDP, "Red Hat Developer Hub Bugs", "RHDH Support", rhdhplan) and issuetype in (Feature, bug) and "Release Note Type" is EMPTY and fixVersion = "{{RELEASE_VERSION}}"' --count
```

## Step 5 (fallback): Fill template and output

Load the **Feature Freeze Announcement** template from `references/slack-templates.md`.

Fill all placeholders:

- `{{RELEASE_VERSION}}` — the release version
- `{{EPIC_ISSUE_COUNT}}` — from Step 1
- `{{CVE_ISSUE_COUNT}}` — from Step 2
- `{{OUTSTANDING_RELEASE_NOTES_ISSUE_COUNT}}` — from Step 3
- `{{JIRA_LINK}}` — URL-encoded Jira search link for each count

**Output the filled template in a triple-backtick code block** for copy-paste into Slack.

</process>

<gotchas>

- This is the milestone announcement (sent ON the Feature Freeze date), not the update (sent BEFORE).
- Include Jira search links for all counts so recipients can drill down.

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] EPICs, CVEs, and release notes counts filled with Jira links

</success_criteria>
