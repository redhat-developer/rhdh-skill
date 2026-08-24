---
name: rhdh-konflux-rpa
description: >-
  Updates the RHDH ReleasePlanAdmission tag values in konflux-release-data for
  one patch release while preserving stream tags and plugin version suffixes.
  Use for "update the RHDH RPA tags for 1.9.7".
compatibility: "Git 2.x and Python 3.9+; glab authenticated to gitlab.cee.redhat.com for an approved GitLab merge request; tox is optional for schema validation."
---

# RHDH Konflux ReleasePlanAdmission updates

Update one RHDH patch stream in a user-provided `konflux-release-data` checkout.
The deterministic script edits only the four hub/operator and plugin-catalog RPA
files for that stream. It never commits, pushes, or opens a merge request.

## Route

Load `workflows/update-rpa.md` and follow it end to end. Execute the bundled
`scripts/update_rpa_tags.py` by path relative to this installed skill; do not
copy its replacement logic into the conversation.

## Boundaries

- `/rhdh-konflux-tasks` owns Tekton task bundle digests, migrations, templates,
  and PipelineRun regeneration.
- `/rhdh-plugin-midstream-propagate` owns a single plugin workspace and its
  surgical PLR tag edits.
- This skill owns RHDH patch tags in release-data ReleasePlanAdmissions. It does
  not edit FBC, `1.next`, `1-stage`, builder RPAs, tenant snapshots, or Konflux
  components.

## Write boundary

Inspection, `--dry-run`, the requested local branch, `--local-only` file edits,
validation, and `git diff` stay in the user's checkout and need no write gate.
The gate starts at commit: before a commit, push, or merge-request creation,
invoke `/mutation-gate` with the exact target, command, payload preview,
verification, and failure behavior for each operation. The user's request to
update tags authorizes those named local edits, not publication.

The merge-request body is a fixed repository template. Fill only its named
placeholders; do not invoke a runtime prose editor.

## Completion

Name the old and new patch tags, every changed RPA file, validation results, the
local branch and commit state, and the outcome or skipped state of the commit,
push, and merge-request operations. Report explicitly when nothing was pushed.
