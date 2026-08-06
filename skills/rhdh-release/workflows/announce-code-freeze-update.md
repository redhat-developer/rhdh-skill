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

Use its `slack_message` field directly. This workflow depends on the Rich
Filter for release-note and Code Freeze JQL. If either template is unavailable,
run `python scripts/release.py --json check`, configure the Rich Filter as shown
in `references/config.md`, and retry. Do not substitute hardcoded queries.

</process>

<gotchas>

- Team counts and Jira links come from the CLI's Cloud ID-scoped Rich Filter queries.
- Code Freeze scope is defined by the Rich Filter; do not replace it with `status != closed`.

</gotchas>

<success_criteria>

- [ ] Slack message in triple-backtick code block
- [ ] All team lines filled with count, Jira link, and lead Slack handle
- [ ] Release notes and feature subtask counts filled
- [ ] Code Freeze date filled

</success_criteria>
