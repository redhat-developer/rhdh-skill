# Jira Smoke Checks — rhdh-release

Requires `acli` on PATH with valid Jira credentials. All checks are read-only.

## How to run

```
read @skills/rhdh-release/tests/check-jira.md
```

Then follow the checks below, reporting PASS/FAIL for each.

## Prerequisites

Run the Jira prerequisite from SKILL.md first:

```bash
acli jira workitem search --jql "project=RHIDP" --count
```

If this fails, stop — Jira access is not configured.

## Checks

### 1. JQL syntax validation

Read `skills/rhdh-release/references/jql-release.md`. For each of the 12 query templates, substitute a real release version (discover it from check 2 below) and run with `--count` to verify the JQL parses without error.

Use the `active_release` query first (no placeholders) to discover the current release version:

```bash
acli jira workitem search --jql "project=rhdhplan AND issuetype=feature AND component=release AND status != closed" --count
```

- [ ] `active_release` — returns count (no placeholders needed)

Then for each remaining query, substitute `{{RELEASE_VERSION}}` with the discovered version:

- [ ] `open_issues` — returns count
- [ ] `open_issues_by_type` — substitute `{{ISSUE_TYPE}}` with `Bug`, returns count
- [ ] `epics` — returns count
- [ ] `cves` — returns count
- [ ] `feature_demos` — returns count
- [ ] `feature_subtasks` — returns count
- [ ] `test_day_features` — returns count
- [ ] `features_added_to_release` — returns count
- [ ] `release_notes` — returns count
- [ ] `feature_freeze_issues` — returns count
- [ ] `code_freeze_issues` — returns count

### 2. parse_issues.py integration

Run one query through the enrichment pipeline to verify `parse_issues.py` works:

```bash
acli jira workitem search --jql "project=rhdhplan AND issuetype=feature AND component=release AND status != closed" --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status
```

- [ ] Returns structured output with key, summary, status columns
- [ ] No Python errors

### 3. Team enrichment

Run the open_issues query with team enrichment (use `--limit 5` to keep it fast):

```bash
acli jira workitem search --jql 'project IN (RHIDP, RHDHBugs, RHDHPLAN, RHDHSUPP) AND fixVersion = "{{RELEASE_VERSION}}" AND status != closed' --limit 5 --json | python ~/.claude/skills/rhdh-jira/scripts/parse_issues.py --enrich -s key,summary,status,team
```

- [ ] Output includes a `team` column
- [ ] No Python errors

## Report format

```
Jira Smoke Checks — rhdh-release
==================================
 1. JQL syntax validation:    PASS/FAIL (N/12 queries valid)
 2. parse_issues.py:          PASS/FAIL (details)
 3. Team enrichment:          PASS/FAIL (details)

Release version tested: X.Y.Z
Result: X/3 passed
```
