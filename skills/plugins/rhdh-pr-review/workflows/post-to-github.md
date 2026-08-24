# Workflow: Post Review to GitHub

Takes the review draft from `review-code.md` and posts it as an inline review via the GitHub API. This workflow is GitHub-specific.

## Prerequisites

- `gh` CLI authenticated with write access to the target repo
- A review draft carrying `changeRequest`, `summary`, `verdict`, `edited: true`, and `findings[]`

## Step 1: Finalize the draft

If the findings have not been shown yet, present the full edited draft first:

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

GitHub's review API needs line numbers in the file at HEAD, not diff-relative positions. For each finding, grep the file at HEAD for the target string:

```bash
gh api repos/<repo>/contents/<path>?ref=<head_sha> \
  -H "Accept: application/vnd.github.raw+json" | grep -n "<target string>"
```

Comment on the line that contains the claim. A folded YAML or wrapped prose
sentence (`description: >-`) can start on one line and land the claim on the
next.

Set `start_line` when the suggestion replaces a block, not only when the comment
is multi-line prose. A suggestion must be the full replacement for the commented
range. If the fix spans a later line, extend the range or drop the fence and
leave guidance.

Update `line` (and `start_line` when the range is a block) to match the file at
the frozen SHA.

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

**Multi-line comment** (use `start_line` when the suggestion replaces a block):

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

Write to a temp file (use a platform-appropriate temp directory):

```bash
REVIEW_FILE=$(mktemp)
cat > "$REVIEW_FILE" << 'REVIEW_EOF'
<payload JSON>
REVIEW_EOF
```

Scan that payload file through `/mutation-gate` before showing the plan.
Describe leftover credential-shaped fields without quoting an example value.

## Step 4: State and post the review

Invoke `/mutation-gate` and follow it. State one operation: the target repo and
PR number, the exact `gh api` command below, the complete JSON payload as the
preview, the frozen head SHA as a precondition, and — on failure — deleting the
partial review or following up manually. State it only once the payload file is
final and has been scanned.

Run the command below only after the user approves that stated operation. A prior
request to review or post, or approval of the prose draft, does not open this
gate.

Immediately before posting, re-read the live head:

```bash
gh api repos/<repo>/pulls/<number> --jq .head.sha
```

If it differs from the frozen `commit_id`, stop. Do not post a stale review.

```bash
gh api repos/<repo>/pulls/<number>/reviews \
  --input "$REVIEW_FILE"
```

## Step 5: Clean up

```bash
rm -f "$REVIEW_FILE"
```

Remove the worktree when this run created one (`worktreePath` from
`review-code.md`).

Report the outcome: review URL, number of comments posted, event type, API
status, and whether it verified against the current head SHA.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Using diff line numbers for the API | Grep the actual file at HEAD for correct line numbers |
| Commenting the fold opener of wrapped YAML or prose | Comment the line that contains the claim |
| Shell-escaping suggestion blocks in `gh api` | Write JSON to a temp file, use `--input` |
| Posting after prose approval but before gate approval | State the exact operation and wait for approval of it |
| Incomplete suggestion for the commented range | Extend `start_line`…`line` to cover the whole fix, or drop the fence |
| Posting after a push landed during prose approval | Re-read live `head.sha` immediately before `gh api`; stop on drift |
| Credential-shaped leftovers in a comment body | Describe the leftover field; scan the payload via `/mutation-gate` |
| Including `start_line` when the comment is one line with no block replacement | Omit `start_line` for a single-line comment |
