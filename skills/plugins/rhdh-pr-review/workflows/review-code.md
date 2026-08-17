# Workflow: Review Code

Platform-agnostic code analysis. Reads the PR context from `fetch-github.md` (or a future `fetch-gitlab.md`) and produces the review draft a posting workflow sends.

Work from that context. The one exception is reading full file contents at HEAD to verify findings, which needs forge-specific commands (see Step 3).

## Mindset

You are a senior team member reviewing a contribution. Your goal is to help the author ship confidently, not demonstrate expertise. Every comment should either prevent a real problem or teach something useful — if it does neither, don't leave it.

## Step 0: Humanizer prerequisite

Load `../references/humanizer.md`. If the named `/humanizer` skill is absent, say
that `humanizer` is missing, name `/setup-rhdh-skills install` as the human's next
step, and stop. This applies to every draft path, including analysis-only.

## Step 1: Ask which specialist skills to invoke

Read `../references/review-perspectives.md`. After fetch/context is available and **before deep analysis**, always ask the user which installed skills (if any) to invoke for this review. "None" is valid. Do not invent a hardcoded specialist roster — use whatever the user names, then follow those skills for domain knowledge.

Also choose review perspectives from the reference (Correctness, Security, etc.) as a thin router. The reference is a starting point, not a mandatory checklist. Invent new perspectives when the PR calls for it.

For small PRs, reviewing directly from a single perspective is often enough. For larger or more complex PRs, multiple perspectives help catch different classes of issues.

## Step 2: Analyze the diff

Review the diff through each chosen perspective (and any user-named specialist skills). When dispatching subagent reviewers, each receives:

- The diff from `diff`
- Linked requirements (`linkedIssues`)
- Their focus area and prompt guidance

### Reading source at HEAD

When the diff alone is insufficient to judge a finding, read the full file at HEAD. Use `repository` and `changeRequest.headSha` from the fetched context:

- **GitHub**: `gh api repos/{repo}/contents/{path}?ref={head_sha} -H "Accept: application/vnd.github.raw+json"`
- **GitLab**: `glab api projects/{id}/repository/files/{path}/raw?ref={head_sha}`

This is the one place where forge awareness leaks into the analysis — prefer the diff when possible.

## Step 3: Verify every finding (critical)

Reviewers will produce false positives. Verify each finding against actual code at HEAD.

**Drop any finding that:**

- References code that doesn't exist at HEAD
- References files that are not in the PR's changed files list (check `files[]` — don't assume a file exists in the PR just because it exists on the branch)
- Was already raised and resolved in `existingComments` or `existingReviews`
- Misreads what the code actually does
- Matches existing codebase conventions (the PR follows the project's style, not the reviewer's preference)

**For each linked requirement, verify:**

- Addressed in the diff?
- Tested?
- Anything from the issue's scope missing? (Author may be intentionally splitting work — note, don't block.)

Present a **finding inventory** to the user before drafting: `file:line`, category (`question` / `observation` / `fix`), and a one-line label only. This is a triage list for what to include — **not** review prose and **not** the GitHub draft. Do not write full comment bodies here.

## Step 4: Draft the review

The posted review should read like a person wrote it, not a report generator. Step 3 only decides which findings to keep; this step writes the actual comments.

Prefer **inline comments** for findings. Put substance on the line; do not duplicate inline content in the top-level comment.

### Top-level comment

Reserved for **important issues to resolve before merge** — not a summary or roll-up of the inlines. Do not restate what is already inline. A brief thanks is fine when needed. No performative praise.

If `existingReviews` shows you've already left a top-level comment on this PR, a new one is often unnecessary — consider posting only the inline findings. A follow-up top-level is still warranted if there are new merge-blocking issues or the prior review was on a different revision.

**If nothing significant survives verification:** draft a short approving top-level (thanks is enough). Don't manufacture issues.

### Inline comments

Post one inline comment per finding worth raising — no artificial cap. Never leave a comment just to show you noticed something. Not every finding needs the same weight — substantial issues get a full comment, nits can be grouped into a single comment as one-liners.

Write each comment as natural prose — a short paragraph explaining the issue and why it matters. Avoid bullet lists, bold headers, and over-structured formatting.

**Guide, don't dictate.** Assume deliberate choices. When the design intent is unclear, ask why before proposing alternatives. Explain reasoning only when the fix isn't obvious. Finding `type: "fix"` means "propose a direction," not "paste a patch" — still guide unless a GitHub `suggestion` block applies below.

**GitHub `suggestion` blocks:** use them **only** when the fix is small and obvious — one clear replacement hunk the author can apply as-is. Otherwise leave a question or guidance without a `suggestion` block.

### Humanize before show-user

After drafting top-level + inlines, follow `../references/humanizer.md` → When to invoke. Run humanizer on the full draft, then present the humanized draft. Never show pre-humanizer prose as the review draft. Applies to posting and analysis-only routes.

## Step 5: Choose event type

Present the **humanized** draft to the user. For posting routes, ask which event type to use:

| Event | When |
|-------|------|
| `COMMENT` | Default. Feedback without a verdict. |
| `APPROVE` | No issues, or only minor nits. |
| `REQUEST_CHANGES` | Critical issues that must be fixed. Use sparingly. |

For analysis-only (route 2), present the humanized draft and stop — no event type, no post.

## What this workflow hands on

Carry the finished review forward as:

```
changeRequest: {repository: "owner/repo", number: 123, headSha: "abc123..."}
summary: "top-level review text"
verdict: "COMMENT" | "APPROVE" | "REQUEST_CHANGES"
humanized: true
findings[]
├── path: "src/file.ts"
├── line: 42
├── startLine: null (or number for multi-line)
├── type: "question" | "observation" | "fix"
└── body: "comment text, optionally with ```suggestion block when allowed"
```

`type` is the finding kind for triage. A GitHub `suggestion` fence inside `body` is separate and only allowed for small obvious hunks (see Step 4).

**Do not post the review.** If the router selected a posting workflow, hand that draft to it. If analysis-only, stop after presenting the humanized draft (Step 5).
