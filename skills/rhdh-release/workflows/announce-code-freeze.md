# Workflow: Announce Code Freeze

Generate a Slack message announcing that Code Freeze milestone has been reached.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json slack code-freeze {{RELEASE_VERSION}}
```

If the CLI succeeds, use its `slack_message` field directly (it's the filled template). If it fails, follow the manual steps below.

## Step 2 (fallback): Get blocker bugs

Use the blocker bugs workflow query:

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed AND issuetype = bug AND priority = Blocker' --count
```

## Step 3 (fallback): Get feature demos count

Use the `feature_demos` template composed from the Rich Filter `demo` entry:

```bash
python scripts/release.py --json rich-filter query static demo --version "{{RELEASE_VERSION}}" --count
```

## Step 4 (fallback): Get test day features count

Use the `test_day_features` template composed from the Rich Filter `Test Day` entry:

```bash
python scripts/release.py --json rich-filter query static "Test Day" --version "{{RELEASE_VERSION}}" --count
```

## Step 5 (fallback): Get total open issues count

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --count
```

## Step 6 (fallback): Fill template and output

Load the **Code Freeze Announcement** template from `references/slack-templates.md`.

Fill all placeholders:

- `{{RELEASE_VERSION}}` — the release version
- `{{BLOCKER_BUG_ISSUE_COUNT}}` — from Step 1
- `{{FEATURE_DEMO_ISSUE_COUNT}}` — from Step 2
- `{{TEST_DAY_FEATURE_ISSUE_COUNT}}` — from Step 3
- `{{OPEN_ISSUE_COUNT}}` — from Step 4
- `{{JIRA_LINK}}` — URL-encoded Jira search link for each count

**Output the filled template in a triple-backtick code block** for copy-paste into Slack.

</process>

<gotchas>

- This is the milestone announcement (sent ON the Code Freeze date), not the update (sent BEFORE).
- After Code Freeze: no cherry-picks without explicit RM approval, only critical CVEs considered for GA.

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] Blocker bugs, feature demos, test day features, and open issue counts filled with Jira links

</success_criteria>
