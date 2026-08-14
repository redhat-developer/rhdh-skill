---
name: rhdh-jira-update
description: >-
  Changes an RHDH Jira issue you already have a key for, in RHIDP, RHDHPLAN,
  RHDHBUGS, or RHDHSUPP: post a progress comment, transition status, add an
  issue link or a web link to a PR, close with a resolution and rationale, and
  pick and set the assignee from team roster, recent expertise, and sprint
  capacity. Use for "update jira", "update RHIDP-1234", "log my progress on
  this", "move this to Review", "close this out", "who should take this", or
  "assign RHIDP-1234". Edits existing work — it does not create issues, audit a
  backlog, or build a sprint.
compatibility: "acli on PATH with a Jira session; git and gh optional for issue detection; an authenticated host Atlassian adapter for web links and roster reads."
---

# Update RHDH Jira work

Small, precise changes to an issue that already exists. Two jobs live here
because they are the same job: a field mutation on a known key.

## Route

| Intent | Load |
|---|---|
| Log progress, transition status, link a PR, close something out | `workflows/update-issue.md` |
| Decide who should take the work, then assign it | `workflows/assign-work.md` |

Both may run in one session — an update that ends "and hand this to someone" is
the second workflow, not a new conversation.

## Every change is an external write

Invoke `/mutation-gate` and follow it, then read back the fields you claimed
to set.

A caller handing over a pull request usually wants three writes at once — a
comment, a transition to `Review`, and a web link to the PR URL. Put all three in
one stated set so one approval covers them, rather than asking three times.

## Boundary with the neighbouring skills

- Opening new work is `/rhdh-jira-create`.
- Auditing many issues for readiness is `/rhdh-jira-refine`. This skill changes
  one issue you already named.
- Sprint carryover, velocity, and fill suggestions are `/rhdh-jira-sprint-plan`;
  it invokes this skill for per-issue assignee recommendations rather than
  scoring them itself.
- `acli` flags, field IDs, JQL, GraphQL roster queries, and workflow exit
  criteria are `/rhdh-jira-api`.
- Creating a PR and attaching the Jira web link in one step is
  `/rhdh-jira-link`.

## Completion

Complete when every issue key the answer mentions was read back after the change
and reported with its resulting status, assignee, and links. Name every operation
that ran and every one that failed — a comment that posted followed by a
transition that was rejected is a partial update, not a success. A transition
blocked by unmet exit criteria is reported with the specific fields that blocked
it. An assignee recommendation names the evidence behind it and says plainly when
component or sprint metadata was missing, rather than implying certainty it does
not have.
