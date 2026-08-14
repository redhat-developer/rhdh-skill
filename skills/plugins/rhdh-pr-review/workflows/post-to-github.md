# Workflow: Post Review to GitHub

Takes the review draft from `review-code.md` and posts it as an inline review via the GitHub API. This workflow is GitHub-specific.

## Prerequisites

- `gh` CLI authenticated with write access to the target repo
- A review draft carrying `changeRequest`, `summary`, `verdict`, and `findings[]`

## Step 1: Finalize the draft

If the findings have not been shown yet, present the full humanized draft first:

```
## Review for PR #<number>

**Event:** COMMENT / APPROVE / REQUEST_CHANGES
**Summary:** <top-level text>

### Inline comments (<count>)

1. `<path>:<line>` [<type>] — <body preview>
2. ...
```

Resolve requested edits and freeze the review event, head SHA, summary, and
inline bodies. Approval of the prose is not approval to post it.

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

## Step 4: State and post the review

Follow the write gate in `SKILL.md`. State one operation: the target repo and PR
number, the exact `gh api` command below, the complete JSON payload as the
preview, the expected head SHA as a precondition, and — on failure — deleting the
partial review or following up manually. State it only once the payload file is
final.

Run the command below only after the user approves that stated operation. A prior
request to review or post, or approval of the prose draft, does not open this
gate.

```bash
gh api repos/<repo>/pulls/<number>/reviews \
  --input "$REVIEW_FILE"
```

## Step 5: Clean up

```bash
rm -f "$REVIEW_FILE"
```

Report the outcome: review URL, number of comments posted, event type, API
status, and whether it verified against the current head SHA.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using diff line numbers for the API | Grep the actual file at HEAD for correct line numbers |
| Shell-escaping suggestion blocks in `gh api` | Write JSON to a temp file, use `--input` |
| Posting after prose approval but before gate approval | State the exact operation and wait for approval of it |
| Including `start_line` when not needed | Only set `start_line` for multi-line comments; omit for single-line |
