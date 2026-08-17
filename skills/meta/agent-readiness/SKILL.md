---
name: agent-readiness
description: >-
  Assesses and improves a git repository's readiness for AI coding agents with
  the agentready tool, and reports the score, the certification level, the
  failing findings, and where the report was written. Covers one repository or
  every RHDH repository under a directory, and applies the fixes the report
  supports. Use for "assess agent readiness", "run agentready", "improve our
  agent readiness score", "prepare this repository for coding agents", or
  "assess all the RHDH repositories".
compatibility: "The agentready CLI, plus git and Python 3. Windows, macOS, Linux."
---

# RHDH Agent Readiness

Use an agentready report as the source of truth for repository-readiness work.
The skill supports any git repository and adds RHDH context when the repository
belongs to the RHDH ecosystem.

## Principles

- Write assessment output to the OS temporary directory so reports never
  pollute the target repository.
- Apply only fixes supported by the report. Ask for project-specific facts;
  never invent architecture or design rationale.
- For a recognized RHDH repository, use `/rhdh-context` for repository
  ownership, technology, key paths, and conventions. Continue generically when
  RHDH context is unavailable.
- Treat a fresh post-change assessment as the completion criterion for every
  remediation run.

## Route the request

| Request | Reference |
|---|---|
| Assess or improve one repository | [references/assessment.md](references/assessment.md), then [references/remediation.md](references/remediation.md) when fixes are requested |
| Assess all RHDH repositories under a directory | [references/batch.md](references/batch.md) |

When no path or mode is given, recommend the current repository as the default
and offer batch assessment as the alternative.

## Completion

- Assessment-only work is complete when the current score, certification,
  failing findings, and report location have been presented.
- Remediation work is complete when a fresh assessment shows the before/after
  result and every remaining failure is identified as unresolved, deferred, or
  inapplicable.
