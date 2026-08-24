# Workflow: Review Code

Platform-agnostic code analysis. Reads the PR context from `fetch-github.md`
and produces the review draft a posting workflow sends.

Work from that context. The one exception is reading full file contents at HEAD
to verify findings (see Reading source at HEAD).

## Mindset

You are a senior team member reviewing a contribution. Your goal is to help the author ship confidently, not demonstrate expertise. Every comment should either prevent a real problem or teach something useful — if it does neither, don't leave it.

## Step 0: `/code-review` prerequisite

`/code-review` is required on every run, including analysis-only. If the named skill is absent, stop. Say that `code-review` is missing, name `/setup-rhdh-skills install`, and do not substitute a local two-axis review.

## Step 1: Team

`/code-review`'s Standards and Spec agents run on every draft-review path.
Dispatch **Adversarial** on every `/code-review` run. Load
`../references/review-perspectives.md` for that prompt and for any further lens.

Specialists named in the original request join that set. Add another perspective
from that reference when you recommend it from the diff, or when the user named
it. Do not re-ask.

Use `specSource` from fetch as the Spec contract for `/code-review`. Spec still runs.

## Step 2: Worktree, then `/code-review`

If `git rev-parse HEAD` is not `changeRequest.headSha`, create a git worktree at
that SHA. For an RHDH repository, `/rhdh-context` locates the checkout to branch
from. Pass the worktree path into `/code-review` and any other subagents. Remove
the worktree after the GitHub post, or after the analysis-only draft.

Invoke `/code-review` with the PR base as the fixed point and `specSource` as the spec. Present the Standards and Spec reports as their own reports. Do not paste them as the GitHub review. Draft later from verified findings.

When dispatching Adversarial or extra reviewers, each receives:

- The worktree path when one exists
- The diff from `diff`
- `files[]`
- `specSource`
- Their focus area

They verify against HEAD. They do not write GitHub review prose.

### Reading source at HEAD

When the diff alone is insufficient to judge a finding, read the full file at HEAD. Prefer the worktree when one exists. Otherwise use `repository` and `changeRequest.headSha` from the fetched context:

- **GitHub**: `gh api repos/{repo}/contents/{path}?ref={head_sha} -H "Accept: application/vnd.github.raw+json"`

Prefer the diff when it is enough.

## Step 3: Verify every finding (critical)

Reviewers will produce false positives. Verify each finding against actual code at HEAD.

**Drop any finding that:**

- References code that doesn't exist at HEAD
- References files that are not in the PR's changed files list (check `files[]` — don't assume a file exists in the PR just because it exists on the branch)
- Was already raised and resolved in `existingComments` or `existingReviews`
- Misreads what the code actually does
- Matches existing codebase conventions (the PR follows the project's style, not the reviewer's preference)

**For each finding `/code-review` Spec reported**, verify it against code at
HEAD. Note anything from the issue's scope that is missing; the author may be
intentionally splitting work — note, don't block.

Present a **finding inventory** to the user before drafting: `file:line`, category (`question` / `observation` / `fix`), and a one-line label only. This is a triage list for what to include — **not** review prose and **not** the GitHub draft. Do not write full comment bodies here. Skip the inventory only when the user already said to proceed to a draft.

## Step 4: Draft the review

The posted review should read like a person wrote it, not a report generator. Step 3 only decides which findings to keep; this step writes the actual comments.

Prefer **inline comments** for findings. Put substance on the line; do not duplicate inline content in the top-level comment.

### Top-level comment

Reserved for **important issues to resolve before merge** — not a summary or roll-up of the inlines. Do not restate what is already inline. A brief thanks is fine when needed. No performative praise.

If `existingReviews` shows you've already left a top-level comment on this PR, a new one is often unnecessary — consider posting only the inline findings. A follow-up top-level is still warranted if there are new merge-blocking issues or the prior review was on a different revision.

**If nothing significant survives verification:** draft a short approving top-level (thanks is enough). Don't manufacture issues.

### Inline comments

One inline per merge-shaped problem or lasting rule. Group nits into one comment or a single top-level "also" paragraph. A finding that neither prevents a wrong write nor teaches something that will still be true next month does not get its own inline.

Write each comment as natural prose — a short paragraph explaining the issue and why it matters. Avoid bullet lists, bold headers, and over-structured formatting.

**Guide, don't dictate.** Assume deliberate choices. When the design intent is unclear, ask why before proposing alternatives. Explain reasoning only when the fix isn't obvious. Finding `type: "fix"` means "propose a direction," not "paste a patch" — still guide unless a GitHub `suggestion` block applies below.

A `suggestion` fence is the full replacement for the commented range, or there is no fence.

### Edit before show-user

After drafting top-level + inlines, invoke `/prose-editing` on the whole draft — top-level comment and every inline body — in the **flavored** register. A review is a document, not a procedure, and the caller names the register so the editor does not have to guess it.

Preserve technical meaning, severity, file paths, line numbers, `suggestion` fences, and the review event. Present only what comes back. Never show the unedited prose as the review draft. Applies to posting and analysis-only routes.

## Step 5: Choose event type

Present the **edited** draft to the user. For posting routes, ask which event type to use:

| Event | When |
|-------|------|
| `COMMENT` | Default. Feedback without a verdict. |
| `APPROVE` | No issues, or only minor nits. |
| `REQUEST_CHANGES` | Critical issues that must be fixed. Use sparingly. |

For analysis-only (route 2), present the edited draft and stop — no event type, no post. Remove the worktree if this run created one.

## What this workflow hands on

Carry the finished review forward as:

```
changeRequest: {repository: "owner/repo", number: 123, headSha: "abc123..."}
summary: "top-level review text"
verdict: "COMMENT" | "APPROVE" | "REQUEST_CHANGES"
edited: true
worktreePath: null (or the path this run created)
findings[]
├── path: "src/file.ts"
├── line: 42
├── startLine: null (or number for a block the suggestion replaces)
├── type: "question" | "observation" | "fix"
└── body: "comment text, optionally with ```suggestion block when allowed"
```

`type` is the finding kind for triage. A GitHub `suggestion` fence inside `body`
is separate (see Step 4).

**Do not post the review.** If the router selected a posting workflow, hand that draft to it. If analysis-only, stop after presenting the edited draft (Step 5).
