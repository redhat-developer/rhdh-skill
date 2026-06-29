# Workflow: Review Code

Platform-agnostic code analysis. Consumes a **context artifact** (from `fetch-github.md` or a future `fetch-gitlab.md`), produces a **findings artifact** consumed by a posting workflow.

This workflow works primarily from the context artifact. The one exception is reading full file contents at HEAD to verify findings, which requires forge-specific commands (see Step 2).

## Mindset

You are a senior team member reviewing a contribution. Your goal is to help the author ship confidently, not demonstrate expertise. Every comment should either prevent a real problem or teach something useful — if it does neither, don't leave it.

## Step 1: Choose review perspectives

Read `../references/review-perspectives.md` for examples of review perspectives and the signals that suggest them. Pick the perspectives that fit this PR — the reference is a starting point, not a mandatory checklist. Invent new perspectives when the PR calls for it.

For small PRs, reviewing directly from a single perspective is often enough. For larger or more complex PRs, multiple perspectives help catch different classes of issues.

## Step 2: Analyze the diff

Review the diff through each chosen perspective. When dispatching subagent reviewers, each receives:

- The diff from the context artifact
- Linked requirements (`linked_issues`)
- Their focus area and prompt guidance

### Reading source at HEAD

When the diff alone is insufficient to judge a finding, read the full file at HEAD. Use the forge-specific method from the context artifact:

- **GitHub**: `gh api repos/{repo}/contents/{path}?ref={head_sha} -H "Accept: application/vnd.github.raw+json"`
- **GitLab**: `glab api projects/{id}/repository/files/{path}/raw?ref={head_sha}`

This is the one place where forge awareness leaks into the analysis — prefer the diff when possible.

## Step 3: Verify every finding (critical)

Reviewers will produce false positives. Verify each finding against actual code at HEAD.

**Drop any finding that:**

- References code that doesn't exist at HEAD
- References files that are not in the PR's changed files list (check the context artifact's `files[]` — don't assume a file exists in the PR just because it exists on the branch)
- Was already raised and resolved in `existing_comments` or `existing_reviews`
- Misreads what the code actually does
- Matches existing codebase conventions (the PR follows the project's style, not the reviewer's preference)

**For each linked requirement, verify:**

- Addressed in the diff?
- Tested?
- Anything from the issue's scope missing? (Author may be intentionally splitting work — note, don't block.)

Present verified findings and dropped findings (with reasoning) to the user before drafting. Use a structured format here — categorized by type (suggestion, question, observation), with `file:line` references and short descriptions. This is for the user to scan and approve, not the final comment text.

## Step 4: Draft the review

The posted review should read like a person wrote it, not a report generator. The structured presentation in Step 3 helps the user decide what to include; the actual GitHub comments use a different voice.

### Top-level comment

Keep it short and direct — frame what the inline comments are about so the author knows the scope at a glance. Include a requirements coverage note if linked issues were checked. Skip performative praise; it reads as filler.

If `existing_reviews` shows you've already left a top-level comment on this PR, a new one is often unnecessary — consider posting only the inline findings. A follow-up summary is still warranted if the scope of feedback changed significantly or the prior review was on a different revision.

### Inline comments

Post one inline comment per finding worth raising — no artificial cap. Never leave a comment just to show you noticed something. Not every finding needs the same weight — substantial issues get a full comment, nits can be grouped into a single comment as one-liners.

Write each comment as natural prose — a short paragraph explaining the issue and why it matters. Avoid bullet lists, bold headers, and over-structured formatting. Keep just enough information for the author to understand the problem and act on it. Code suggestions and code blocks are fine since they're functional, not formatting.

Assume deliberate choices. Ask why before suggesting alternatives. Explain reasoning only when the fix isn't obvious. Call out specific things done well when genuine — name the pattern or decision, not generic praise.

**If nothing significant survives verification**, that's a valid outcome. Produce a short approving review. Don't manufacture issues.

## Step 5: Choose event type

Present the draft to the user and ask which event type to use:

| Event | When |
|-------|------|
| `COMMENT` | Default. Feedback without a verdict. |
| `APPROVE` | No issues, or only minor nits. |
| `REQUEST_CHANGES` | Critical issues that must be fixed. Use sparingly. |

## Findings artifact

Assemble the review into this structure for the posting workflow:

```
findings artifact
├── pr
│   ├── repo: "owner/repo"
│   ├── number: 123
│   └── head_sha: "abc123..."
├── summary: "top-level review text"
├── event: "COMMENT" | "APPROVE" | "REQUEST_CHANGES"
└── findings[]
    ├── path: "src/file.ts"
    ├── line: 42
    ├── start_line: null (or number for multi-line)
    ├── type: "suggestion" | "question" | "observation"
    └── body: "comment text, optionally with ```suggestion block"
```

**Do not post the review.** If the router selected a posting workflow, hand the findings artifact to it. If the router selected analysis-only (route 2), present the findings to the user and stop here.
