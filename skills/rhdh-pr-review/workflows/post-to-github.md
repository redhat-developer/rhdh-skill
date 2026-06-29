# Workflow: Post Review to GitHub

Consumes a **findings artifact** (from `review-code.md`) and posts it as an inline review via the GitHub API. This workflow is GitHub-specific.

## Prerequisites

- `gh` CLI authenticated with write access to the target repo
- A findings artifact with `pr.repo`, `pr.number`, `pr.head_sha`, `summary`, `event`, and `findings[]`

## Step 1: Confirm before posting

If the user already reviewed and approved the findings during `review-code.md`, a brief confirmation is enough: "About to post N comments as COMMENT to PR #123. Proceed?"

If the findings haven't been shown yet (e.g., posting a previously saved artifact), present the full draft first:

```
## Review for PR #<number>

**Event:** COMMENT / APPROVE / REQUEST_CHANGES
**Summary:** <top-level text>

### Inline comments (<count>)

1. `<path>:<line>` [<type>] — <body preview>
2. ...
```

Proceed only when the user confirms.

## Step 2: Find exact line numbers

GitHub's review API needs line numbers in the file at HEAD, not diff-relative positions. For each finding, verify the line number:

```bash
gh api repos/<repo>/contents/<path>?ref=<head_sha> \
  -H "Accept: application/vnd.github.raw+json" | grep -n "<target string>"
```

Update `line` (and `start_line` for multi-line comments) to match the actual file.

## Step 3: Build the payload

Write the review payload to a temp file — avoids shell escaping issues with suggestion blocks and markdown.

**Single-line comment:**

```json
{
  "path": "src/file.ts",
  "line": 42,
  "side": "RIGHT",
  "body": "Comment text\n\n```suggestion\nreplacement code\n```"
}
```

**Multi-line comment:**

```json
{
  "path": "src/file.ts",
  "start_line": 10,
  "line": 12,
  "start_side": "RIGHT",
  "side": "RIGHT",
  "body": "Multi-line suggestion\n\n```suggestion\nreplacement for lines 10-12\n```"
}
```

**Full payload:**

```json
{
  "commit_id": "<head_sha>",
  "body": "<summary text>",
  "event": "COMMENT",
  "comments": [ ... ]
}
```

Write to a temp file:

Write to a temp file (use a platform-appropriate temp directory):

```bash
REVIEW_FILE=$(mktemp)
cat > "$REVIEW_FILE" << 'REVIEW_EOF'
<payload JSON>
REVIEW_EOF
```

## Step 4: Post the review

```bash
gh api repos/<repo>/pulls/<number>/reviews \
  --input "$REVIEW_FILE"
```

## Step 5: Clean up

```bash
rm -f "$REVIEW_FILE"
```

Report the result to the user: link to the review on GitHub, number of comments posted, event type.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using diff line numbers for the API | Grep the actual file at HEAD for correct line numbers |
| Shell-escaping suggestion blocks in `gh api` | Write JSON to a temp file, use `--input` |
| Posting without user confirmation | Always show draft first |
| Including `start_line` when not needed | Only set `start_line` for multi-line comments; omit for single-line |
