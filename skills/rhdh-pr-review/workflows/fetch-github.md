# Workflow: Fetch GitHub PR Context

Fetch PR metadata, diff, linked issues, existing comments, and CI status from GitHub. Produces a **context artifact** consumed by `review-code.md` and `review-operator-pr.md`.

## Script

Run the fetch script to collect all PR context in one call:

```bash
python skills/rhdh-pr-review/scripts/fetch_pr_context.py <PR_URL_OR_NUMBER> [--repo owner/repo]
```

The path is relative to the repo root.

The script accepts:

- A full URL: `https://github.com/owner/repo/pull/123`
- A number (detects repo from git remote): `123`
- A shorthand: `owner/repo#123`

Optional flags:

- `--repo owner/repo` — override repo detection
- `--no-diff` — skip diff (metadata-only queries)
- `--no-comments` — skip existing review comments
- `--no-issues` — skip fetching linked GitHub issues

Consume the full JSON output. Do not pipe through `head`, `tail`, or `grep`.

## Context artifact

The script outputs this structure as JSON:

```
context artifact
├── forge: "github"
├── repo: "owner/repo"
├── pr_number: 123
├── head_sha: "abc123..."
├── base_ref: "main"
├── head_ref: "feat/my-change"
├── title, body, author, state, url
├── labels: ["bug", "area/api"]
├── files: [{path, additions, deletions}, ...]
├── total_additions, total_deletions
├── diff: "full unified diff text"
├── linked_issues: [{number, title, body, labels, state}, ...]
├── jira_keys: ["RHIDP-1234", ...]
├── existing_comments: [{user, path, line, body, created_at}, ...]
├── existing_reviews: [{user, state, body}, ...]
└── ci_status: "pass" | "fail" | "pending" | "unknown"
```

## Jira keys

The script extracts Jira keys (e.g., `RHIDP-1234`) from the PR body but does not fetch them — GitHub's API can't query Jira. If `acli` or `mcp-atlassian` is available, fetch each key separately. Otherwise note them and move on — do not block the review.

## After fetching

Proceed to the workflow the router selected (typically `review-code.md`). Pass the full context artifact — downstream workflows depend on its structure.
