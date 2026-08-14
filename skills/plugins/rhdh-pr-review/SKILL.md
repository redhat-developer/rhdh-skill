---
name: rhdh-pr-review
description: >-
  Reviews the code in a Red Hat Developer Hub pull request: fetch its diff,
  linked issues and CI status, analyze the changes, draft inline comments, post
  the review to GitHub, and for an rhdh-operator PR optionally deploy its
  CI-built bundle onto a live OpenShift cluster and verify the change there. Use
  for a GitHub PR URL or number, "review this PR", analysis-only review, inline
  comments, posting a review, testing operator PR images or bundles on a
  cluster, or a combined code and cluster review. For label and merge-readiness
  triage of the overlay PR backlog, use /rhdh-overlay.
compatibility: "GitHub CLI and Python 3; oc plus an accessible cluster for operator testing."
---

# RHDH Pull Request Review

Keep forge I/O at the edges: fetch produces the PR context, analysis works from
that context and checked-out code alone, and posting sends only findings already
verified against the head SHA. Cluster testing reads the same context
independently.

## Route by outcome

| Outcome | Workflow sequence |
|---|---|
| Code review and post | `workflows/fetch-github.md` → `workflows/review-code.md` → `workflows/post-to-github.md` |
| Analysis only | `workflows/fetch-github.md` → `workflows/review-code.md`; stop after the humanized draft |
| Test an rhdh-operator PR | `workflows/fetch-github.md` → `workflows/review-operator-pr.md` |
| Full review | fetch → review code → confirm and post → operator cluster test |

A bare PR URL or number defaults to code review and post. For an
`rhdh-operator` PR, offer full review because code and deployable bundle changes
can diverge, but respect an explicit route.

## Review invariants

- Verify every finding against code at the fetched head SHA. Drop stale,
  duplicated, speculative, or convention-conflicting findings.
- Prefer actionable inline comments. Reserve top-level prose for context and
  merge blockers; do not repeat every inline finding.
- Ask which installed specialist skills, if any, the user wants applied after
  fetch and before deep analysis. Invoke chosen skills by name and give them the
  fetched PR context; never load their files.
- `/humanizer` is required before any review draft is shown, including
  analysis-only. If unavailable, say that `humanizer` is missing, name
  `/setup-rhdh-skills install`, and stop the draft path. Do not implement a local
  locator or substitute prose rewriting.
- Present the complete humanized draft and review event for confirmation before
  stating any post operation. An explicit request to post is intent, not approval
  of the exact write.
- For cluster testing, deploy the full PR bundle or manifests, not only the
  operator binary image. Preserve and report the original cluster state and
  cleanup result.

## Write gate

Fetch and analysis are read-only. Posting a GitHub review, posting a test-request
comment, or changing cluster resources is an external write: invoke the named
skill `mutation-gate` and follow the gate it owns rather than restating it
here.

A review operation's target pins the head SHA; a cluster operation's target names
the namespace. An earlier confirmation of findings approves no write. Report each
outcome with the changed resources or review URL, the verification done, the
cleanup state, and any recovery still owed.

## What each stage carries forward

Every stage passes its result to the next in conversation. The field names are
defined once, where they are produced:

| Stage | Result | Defined in |
|---|---|---|
| Fetch | PR context: repository, changeRequest, files, diff, linkedIssues, jiraKeys, existingComments, existingReviews, ciStatus | `workflows/fetch-github.md` |
| Analysis | Review draft: changeRequest, summary, verdict, findings, humanized | `workflows/review-code.md` |
| Operator testing | Subject, per-check results, verdict, cluster state, cleanup | `workflows/review-operator-pr.md` |

## Scripts and references

- `scripts/fetch_pr_context.py` deterministically builds the PR context as one
  JSON object with no envelope.
- `references/review-perspectives.md` routes optional specialist review lenses.
- `references/humanizer.md` defines the named `/humanizer` gate.
- `references/operator-pr-images.md` defines operator bundle/image extraction.

## Completion

Complete when the report names the head SHA reviewed, presents the humanized
draft, gives the outcome of every approved write with its target, includes the
cluster check results when operator testing ran, and states every skipped check
or cleanup action with its reason.
