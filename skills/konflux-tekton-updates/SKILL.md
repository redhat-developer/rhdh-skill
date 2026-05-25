---
name: konflux-tekton-updates
description: >-
  Bumps Konflux Tekton task digests with .tekton/updateDigests.sh --minor --no-push,
  applies konflux-ci/build-definitions MIGRATION.md pipeline fixes, and regenerates
  PipelineRuns. Use for rhdh-plugin-catalog, RHDH midstream (4-rhdh), Konflux task
  minor bumps, prefetch-dependencies-oci-ta, build-image-index, or updateDigests.sh.
---

# Konflux Tekton updates

## Goal

After a **minor** Konflux task tag bump, update `.tekton` pipelines and generators so builds keep working. Apply what each `MIGRATION.md` says; do **not** add drift tests that block future Konflux updates.

## Prerequisites

`skopeo`, `jq` (>= 1.7), `yq`. Optional: `gh` for PR creation from scripts.

## Commit locally; never push without human review

| Script | Flag | Effect |
|--------|------|--------|
| `updateDigests.sh` | `--no-push` / `--nopush` (`-p`) | Commit locally; no push/PR |
| `updateDigests.sh` | `--minor` | Disables push; use with `--no-push` for clarity |
| `updateDigests.sh` | `--no-commit` / `-n` | Preview only |
| `generatePipelineRunsForPlugins.sh` | `--nopush` | Commit locally; no push |
| `generatePipelineRunsForPlugins.sh` | `--nocommit` | Write YAML only |

`generatePipelineRuns.sh` does not commit or push.

**Do not** run digest/generator scripts without `--no-push` / `--nopush` unless the user explicitly requests a push.

## Detect repo layout

| Marker in repo | Read |
|----------------|------|
| `.tekton/generatePipelineRunsForPlugins.sh` | [references/plugin-catalog.md](references/plugin-catalog.md) |
| `.tekton-templates/rhdh-pipeline.yaml` | [references/rhdh-midstream.md](references/rhdh-midstream.md) |

If both exist, apply changes for the repo you are working in.

## Workflow

### 1. Bump digests

```bash
cd .tekton
./updateDigests.sh --minor --no-push
```

- Updates `tag@sha256` in `*.yaml` (and `.tekton-templates/*.yaml` in RHDH midstream).
- Tag changes list `MIGRATION.md` URLs under `konflux-ci/build-definitions`.
- Digest-only: `./updateDigests.sh --no-push -q`

Review `git diff` for `quay.io/konflux-ci/tekton-catalog/task-*` changes.

### 2. Apply migrations

For each URL from `updateDigests.sh` (or from the diff):

1. Read `MIGRATION.md`.
2. Apply **only** documented user actions.
3. Skip “no action required” sections.

### 3. Regenerate (optional)

After fixing shared pipelines/templates and generator scripts:

- **plugin-catalog:** `./generatePipelineRunsForPlugins.sh -v <x.y.z> --nopush`
- **RHDH midstream:** `./generatePipelineRuns.sh -t <x.y>`

### 4. Human review and push

Human reviews the full diff, then `git push` or opens a PR.

## Known migration patterns

Use live `MIGRATION.md` as source of truth. Common cases:

| Task | Action |
|------|--------|
| `prefetch-dependencies-oci-ta` 0.2→0.3 | Remove `dev-package-managers`; add pipeline param `enable-package-registry-proxy` (default `"true"`) and pass to prefetch task |
| `build-image-index` 0.2→0.3 | Remove `COMMIT_SHA` / `IMAGE_EXPIRES_AFTER` from **build-image-index** task only; keep `image-expires-after` on buildah/prefetch |
| `init` 0.3→0.4 | No pipeline changes |
| `init` 0.4.1→0.4.2 | Remove broken auto-added `sast-target-dirs` pipeline param if present |

## Anti-patterns

- Pushing without `--no-push` / `--nopush` and human sign-off.
- Leaving removed task params (`dev-package-managers`, `COMMIT_SHA` on `build-image-index`).
- Adding `verify_*` guards that fail on the next Konflux bump.
- Dropping `image-expires-after` from PLRs only because `build-image-index` no longer uses it.
- Hardcoding `1-` in `generatePipelineRunsForPlugins.sh` Containerfile comments; use `${RHDH_XY_VERSION}` so `1.10.0` becomes `1-10`, not `1`.
