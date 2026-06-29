# Workflow: Retrieve Release and Key Dates

Table of release versions with five critical dates: Feature Freeze, Code Freeze, Doc Freeze, Go/No Go, GA Announce.

<prerequisites>

| Requirement | Check |
|-------------|-------|
| **Jira** | `python ~/.claude/skills/rhdh-jira/scripts/setup.py --json` → `"overall": "pass"` |

If Jira check fails: load `~/.claude/skills/rhdh-jira/SKILL.md` and follow its Prerequisites section.

</prerequisites>

<process>

## Step 1: Run CLI

```bash
python scripts/release.py --json dates
```

If the CLI succeeds, use its output directly. If it fails, follow the manual steps below.

## Step 2 (fallback): Find active release issues

Use the `active_release` JQL from `references/jql-release.md`:

```bash
acli jira workitem search --jql "project=rhdhplan AND issuetype=feature AND component=release AND status != closed" --json
```

## Step 3 (fallback): Extract dates from each release issue

For each release issue returned, fetch full details:

```bash
acli jira workitem view {{ISSUE_KEY}} --json
```

Extract from the description:

- Feature Freeze date
- Code Freeze date
- Doc Freeze date
- Go/No Go date
- GA Announce date

## Step 4 (fallback): Format output

Present as a table:

| Release | Feature Freeze | Code Freeze | Doc Freeze | Go/No Go | GA Announce | Source |
|---------|---------------|-------------|------------|----------|-------------|--------|
| {{VERSION}} | {{DATE}} | {{DATE}} | {{DATE}} | {{DATE}} | {{DATE}} | [{{ISSUE_KEY}}](https://issues.redhat.com/browse/{{ISSUE_KEY}}) |

</process>

<gotchas>

- Dates are embedded in the Jira issue description, not in custom fields — parse the description text.
- Some releases may have dates marked as TBD.
- Include the Jira issue link for traceability.

</gotchas>

<success_criteria>

- [ ] Table with one row per active release
- [ ] Each row has all five dates (or TBD) and a Jira source link

</success_criteria>
