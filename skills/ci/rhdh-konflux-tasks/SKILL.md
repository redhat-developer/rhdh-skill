---
name: rhdh-konflux-tasks
description: >-
  Bumps Konflux Tekton task bundle digests in `.tekton` and `.tekton-templates`,
  applies each task's MIGRATION.md, and regenerates PipelineRuns with
  `updateDigests.sh`, `generatePipelineRuns.sh`, and `updatePLRs.sh` on the RHDH
  midstream and rhdh-plugin-catalog trees. Use for "bump konflux task digests",
  "apply the tekton migration", `quay.io/konflux-ci/tekton-catalog/task-*` tag
  upgrades such as buildah-oci-ta, prefetch-dependencies-oci-ta, init, or
  build-image-index, and for build-definitions MIGRATION.md URLs that 404.
compatibility: "bash, skopeo, jq 1.7+, yq, and git; a checkout of the target Konflux branch. gh is optional, for PR creation."
---

# Konflux Tekton task updates

Keep builds working after a Konflux task tag bump: update the pinned
`tag@sha256` digests, apply what each task's `MIGRATION.md` documents, and
regenerate the PipelineRuns so they match the migrated templates.

## Route

Load `workflows/konflux-task-update.md`. It detects the repository layout and
sends you to the reference that matches:

- `references/konflux-plugin-catalog.md` — `rhdh-plugin-catalog`, marker
  `.tekton/updatePLRs.sh`.
- `references/konflux-rhdh-midstream.md` — RHDH midstream, variant A
  (`.tekton-templates/rhdh-pipeline.yaml`) and variant B
  (`.tekton-templates/rhdh-hub.yaml` with shared `build-pipeline-rhdh-*.yaml`).
- `references/konflux-migration-urls.md` — resolving a task name and tag to the
  live `MIGRATION.md`, since most tasks left `konflux-ci/build-definitions` and
  the versioned paths under it now 404.

## Boundary with plugin midstream propagation

Two skills touch `.tekton`, and they touch it for different reasons.

- This skill owns Konflux task maintenance across a whole stream: digest bumps,
  migrations to templates and shared pipelines, and full PipelineRun
  regeneration for every component on the branch.
- `/rhdh-plugin-midstream-propagate` owns promoting one plugin workspace
  through overlays and into the catalog, including the surgical per-workspace
  PLR tag edit that goes with it — deliberately without a full regeneration.

If the request is "this plugin version needs to reach midstream", it is
`/rhdh-plugin-midstream-propagate`. If the request is "the Konflux tasks moved
and the pipelines need to catch up", it is this skill. Never run a full
regeneration to deliver a single workspace bump; it rewrites every component's
PLR.

## Writing rules

Editing `.tekton` YAML, committing, pushing, and opening a pull request are
writes. Follow `/mutation-gate`.

- Always pass `--no-push` / `--nopush`. Do not push or open a PR unless the user
  explicitly asks. `generatePipelineRuns.sh` neither commits nor pushes.
- Edit templates and shared pipelines first, then regenerate. Editing only the
  PipelineRuns leaves the real source of truth stale.
- Apply only the user actions a live `MIGRATION.md` documents. Skip "no action
  required" sections, and do not invent drift checks or `verify_*` guards that
  will fail on the next Konflux bump.
- Review `git diff` for `quay.io/konflux-ci/tekton-catalog/task-*` changes before
  committing.
- The human reviews the whole diff across `.tekton/` and `.tekton-templates/`
  and decides when it is pushed.

## Completion

An update is complete when every task whose tag moved is named with its old and
new tag, each one is paired with the migration that was applied or with the
reason none was needed, the affected templates and shared pipelines are listed,
and `generatePipelineRuns.sh` or `updatePLRs.sh` has run wherever a template or
pipeline parameter changed. Say which files were regenerated and which were
edited by hand — inline `pipelineSpec` PLRs such as `rhdh-rag-content-*` and the
variant B `build-pipeline-*.yaml` files are never touched by the generator.

State the commit state and, explicitly, that nothing was pushed, unless the user
asked for a push. Name any migration document that could not be resolved rather
than assuming the bump needed no action.
