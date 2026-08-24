---
name: rhdh-pr-review
description: >-
  Reviews Red Hat Developer Hub pull request code on GitHub in rhdh,
  rhdh-operator, rhdh-plugins, or community-plugins. Use for a GitHub PR URL
  or number, "review this PR", analysis-only review, or posting inline
  comments. For label and merge-readiness triage of the overlay PR backlog,
  use /rhdh-overlay.
compatibility: "GitHub CLI and Python 3. Requires the external /code-review skill — analysis is blocked without it."
---

# RHDH Pull Request Review

Keep forge I/O at the edges: fetch produces the PR context, analysis works from
that context and checked-out code alone, and posting sends only findings already
verified against the head SHA.

## Route by outcome

| Outcome | Workflow sequence |
|---|---|
| Code review and post | `workflows/fetch-github.md` → `workflows/review-code.md` → `workflows/post-to-github.md` |
| Analysis only | `workflows/fetch-github.md` → `workflows/review-code.md`; stop after the edited draft |

A bare PR URL or number defaults to code review and post.

## Review invariants

- `/code-review` is required on every draft-review path, including
  analysis-only. If it is missing, stop, say that `code-review` is missing,
  name `/setup-rhdh-skills install`, and do not substitute a local two-axis
  review.
- Every `/code-review` run also dispatches Adversarial. Team, worktree, and
  draft steps live in `workflows/review-code.md`.
- Present the complete edited draft before stating any post operation. An
  explicit request to post is intent, not approval of the exact write.

## Write gate

Fetch and analysis are read-only. Posting a GitHub review is an external write:
invoke the named skill `mutation-gate` and follow the gate it owns rather than
restating it here. Creating or removing a local git worktree is not that gate.

A review operation's target pins the head SHA. An earlier confirmation of
findings approves no write. Report each outcome with the review URL, the
verification done, and any recovery still owed.

## What each stage carries forward

Every stage passes its result to the next in conversation. The field names are
defined once, where they are produced:

| Stage | Result | Defined in |
|---|---|---|
| Fetch | PR context: repository, changeRequest, files, diff, linkedIssues, jiraKeys, existingComments, existingReviews, ciStatus, specSource | `workflows/fetch-github.md` |
| Analysis | Review draft: changeRequest, summary, verdict, findings, edited, worktreePath | `workflows/review-code.md` |

## Completion

Complete when the report names the head SHA reviewed, has presented the
`/code-review` Standards and Spec reports, and presents the edited draft.
On the post route, also give the outcome of every approved write with its
target.
