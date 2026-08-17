---
name: rhdh-test-placement
description: >-
  Advises where a permanent automated test for the Red Hat Developer Hub
  dynamic-plugin ecosystem should live: which repository (rhdh, rhdh-plugins,
  or rhdh-plugin-export-overlays), which layer (L1 unit, L2 startTestBackend
  integration, L3 React Testing Library component, L4a cluster-free Playwright,
  or L4b cluster e2e), which harness, and which neighbouring file to mirror.
  Use for "where should this test live", "which repo and layer for this test",
  "does this need a cluster", "is this e2e too expensive", or a review comment
  that a test sits at the wrong layer. Advice only — it recommends a placement
  and names a template; it writes no test and changes no file.
compatibility: "Read access to the target checkout on its current default branch; no build or cluster required."
---

# RHDH Test Placement

Advisory only. This skill answers *where a lasting test belongs* and *what it
should be modelled on*. It does not write the test, run it, or change a file.
The guiding rule: pick the cheapest environment that can actually catch the
bug. Most plugin validation needs no cluster, and a growing share needs no
Docker either.

## Prerequisite: /grilling

Placement is a tradeoff, not a lookup. Cost, feedback time, coverage overlap,
and what a layer can physically observe all pull in different directions, and
the person asking usually has a preferred answer already.

Invoke `/grilling` **before** recommending a placement, and use the constraints
it produces. If `/grilling` is not installed, stop: say the skill is required,
name `/setup-rhdh-skills install` as the human's next step, and do not guess a
placement in the meantime.

## Scope

| In scope | Out of scope |
|---|---|
| Where a permanent regression or coverage test belongs | Writing or running the test |
| Which repository and layer, and why not the others | Fixing the defect under test |
| Which existing file to mirror | A throwaway reproduction test |
| The rough feedback cost of each candidate | Reviewing an RHDH Jira test plan |

A one-off test that reproduces a defect and is then deleted is not this skill's
subject; `/rhdh-plugin-bug-fix` owns that and removes the file before handing
its change off. Come here for the durable test that stays behind afterwards.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Recommend a repository, layer, harness, and template | `references/test-placement.md` |

`references/test-placement.md` carries the context questions to settle first,
the repository decision table, the L1–L4b layer ladder, per-placement authoring
notes with the file to copy, the commands that run each layer, and the things
that are researched as not possible today.

## Boundaries

- `/grilling` is a hard prerequisite, not an option.
- `/rhdh-plugin-authoring` owns writing the recommended test once the placement
  is settled.
- `/rhdh-plugin-bug-fix` owns the throwaway reproduction and its evidence.
- `/rhdh-test-plan-review` reviews an RHDH release test plan in Jira. That is a
  release-readiness review, not a placement question.

Invoke a named skill and describe the handoff in the conversation. Never open
another skill's files.

## Invariants

- Verify every referenced path against the target repository's current default
  branch before recommending it. Harnesses in this domain move, and some cited
  here were still in review when they were written down.
- Justify the test by the failure it would catch, never by a coverage number.
  Codecov is informational on both `rhdh` and `rhdh-plugins`; no coverage delta
  can block a pull request, and a test argued that way gets rejected in review.
- If a defect is catchable at more than one layer, recommend the cheapest and
  say explicitly not to duplicate it downstream.
- Never recommend a UI-render test in `rhdh-plugin-export-overlays`; that
  repository has no app to render into.
- Say "no good placement exists" when that is the answer. Recommending an
  expensive layer that still cannot observe the failure is worse than none.

## Completion

Report the repository, the layer and harness, the directory or file the test
goes in, the existing neighbour to mirror, one line on each layer rejected and
why, and the rough feedback cost. Leave the test unwritten and no file changed.
