# Duplicate Detection

Search for potentially duplicate issues before creating a new one or during refinement audits. Runs automatically — no user prompt.

Uses GraphQL for bulk reads (skip acli). Authentication setup: see `references/auth.md`.

## Modes

### Pre-creation check

Run before creating any issue. The goal is to prevent duplicates, not to find them retroactively.

Input: proposed issue summary + project + type.

### Audit check

Run during refinement (`refine` Check 2). The goal is to flag existing issues that may be duplicates of each other.

Input: an existing issue's key + summary.

## Detection Steps

### Step 1 — Extract keywords

Extract 2-3 distinctive keywords from the issue summary:

- Skip stop words (the, a, an, is, for, to, in, of, and, or, with)
- Skip project names (RHDH, Backstage, Red Hat)
- Skip generic action words (update, fix, add, remove, implement, create)
- Keep domain-specific terms (catalog, RBAC, dynamic plugins, CI/CD, operator, helm)

If fewer than 2 distinctive keywords remain, the summary is too generic for reliable detection. Skip the check and note: "Summary too generic for duplicate detection — verify manually."

### Step 2 — Search

```bash
curl -s -u "$AUTH" "$GRAPHQL_URL" -X POST \
  -H 'Content-Type: application/json' \
  -H 'X-ExperimentalApi: JiraIssueSearch' \
  -d '{
    "query": "query FindDuplicates { jira { issueSearchStable(cloudId: \"'"$CLOUD_ID"'\", issueSearchInput: {jql: \"project in (RHIDP, RHDHPLAN, RHDHSUPP, RHDHBUGS) AND summary ~ \\\"KEYWORD1 KEYWORD2\\\" AND status != Closed ORDER BY updated DESC\"}, first: 10) { edges { node { key summary status { name } assignee { name } issueType { name } } } } } }"
  }'
```

For pre-creation checks, also add `AND key != \"CURRENT_KEY\"` if comparing against an existing issue.

For type-scoped checks, add `AND issuetype = \"TYPE\"` to narrow results (e.g., only search Features when creating a Feature).

### Step 3 — Score overlap

For each result, compute word overlap with the proposed/source summary:

```
overlap = (shared_words / max(words_in_source, words_in_candidate)) × 100
```

Case-insensitive. Ignore stop words in the overlap calculation.

### Step 4 — Classify

| Overlap | Classification | Action |
|---------|---------------|--------|
| >80% | Likely duplicate | **Pre-creation:** "This likely already exists as {KEY}: {summary}. Use the existing issue?" **Audit:** Flag as "likely duplicate — review." |
| 40-80% | Possibly related | **Pre-creation:** "Possibly related to {KEY}: {summary}. Still create?" **Audit:** Flag as "possibly related — check for overlap." |
| <40% | Not a match | Skip silently. |

### Step 5 — Check existing links

Before flagging, check if a `Duplicate` issue link already exists between the two issues. If already linked, skip — it's a known duplicate.

## Limits

- Surface at most 3 candidates. If more than 3 match above 40%, the keywords are too generic.
- Exclude Closed issues from results (already resolved).
- Do not flag sub-tasks as duplicates of their parent (common false positive).

## Pre-creation flow

The duplicate check is automatic and does not prompt the user before searching. The flow:

1. Agent prepares to create an issue
2. Run duplicate detection with the proposed summary
3. If likely duplicate found: present it and ask "Use the existing issue instead?"
4. If possibly related found: present candidates and ask "Still create?"
5. If no matches: proceed with creation silently

## Sibling Scope Check

In addition to summary-keyword duplicate detection, check for functional scope overlap between sibling issues under the same parent. This catches cases where two issues have different summaries but overlapping implementation scope.

### When to run

Run when creating an Epic under a Feature (or a Story under an Epic) that already has sibling issues of the same type.

### Steps

1. **Fetch siblings**: Query `parent = PARENT-KEY AND issuetype = TYPE AND status != Closed` to get existing sibling issues.
2. **Fetch sibling descriptions**: For each sibling, fetch its full description (not just summary). Use `acli jira workitem view KEY --json` or REST API.
3. **Compare scope dimensions**: Check the proposed issue's scope against each sibling across these dimensions:

   | Dimension | Overlap signal |
   |-----------|---------------|
   | User Scenarios | Same user journey described in both |
   | Dependencies | Same upstream or internal dependencies listed |
   | Target artifacts | Same codebase, package, or module targeted |
   | Acceptance Criteria | ACs that would be verified by the same tests |

4. **Flag overlap**: If 2+ dimensions overlap with a sibling:
   > "This overlaps with {KEY} ({summary}): same [target artifacts / user scenarios / dependencies]. Should this scope be added as ACs on {KEY} instead of creating a new issue?"

5. **No overlap**: Proceed silently — don't report "no siblings overlap" unless asked.

### Limits

- Check at most 10 siblings. If a Feature has more than 10 open Epics, that's itself a signal worth flagging (see `references/sizing.md`).
- Description-based comparison is fuzzy — present findings as "appears to overlap" rather than "is a duplicate."
- This supplements, not replaces, the keyword-based pre-creation check above.

## Error Handling

| Error | Action |
|-------|--------|
| `issueSearchStable` fails | See SKILL.md Error Handling. Skip duplicate check, proceed with creation. |
| GraphQL rate limit (429) | Wait 5 seconds, retry once. If still fails, skip check and note "duplicate check skipped." |
| Summary has <2 distinctive keywords | Skip check. Note "summary too generic for duplicate detection." |
