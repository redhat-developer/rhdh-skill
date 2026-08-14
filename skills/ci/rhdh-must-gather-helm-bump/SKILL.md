---
name: rhdh-must-gather-helm-bump
description: >-
  Bumps the Helm CLI baked into redhat-developer/rhdh-must-gather, mirrors
  helm-related files into gitlab.cee.redhat.com/rhidp/rhdh distgit, patches
  Konflux Tekton prefetch (CGW generic vs vendored gomod), and updates
  sync/upstream_SHA. Use when bumping must-gather's HELM_VERSION (upstream or
  downstream), switching between CGW binary and vendored Helm build paths, or
  diagnosing a Konflux rhdh-must-gather prefetch failure after a Helm release.
---

# RHDH must-gather Helm bump

## Goal

Propagate a **Helm CLI** version bump across upstream GitHub and midstream GitLab:

| Repo | Path | What changes |
|------|------|--------------|
| [`redhat-developer/rhdh-must-gather`](https://github.com/redhat-developer/rhdh-must-gather) | repo root | `Makefile` `HELM_VERSION`, `artifacts.lock.yaml` **or** `vendor/helm/`, Stage 2a/2b, hack scripts |
| [`gitlab.cee.redhat.com/rhidp/rhdh`](https://gitlab.cee.redhat.com/rhidp/rhdh) | `distgit/containers/rhdh-must-gather/` | Mirror helm-related files; regenerate hermetic `Containerfile` from `.rhdh/docker/Containerfile` |
| Same (midstream) | `.tekton/rhdh-must-gather-2-{pull,push}.yaml` | `prefetch-input` (`generic` vs `gomod`) |
| Same | `.tekton-templates/components.yaml` | `must-gather.prefetch_input` only |
| Same | `sync/upstream_SHA_rhdh-must-gather` | Upstream commit SHA after sync |

## Essential principles

- **Helm CLI ≠ RHDH chart version.** This skill only bumps the CLI in the must-gather image, not `oci://quay.io/rhdh/chart`.
- **CGW binary path is preferred** when `mirror.openshift.com/pub/cgw/helm/<version>/` has linux amd64/arm64 tarballs — smaller tree, faster Konflux builds.
- **Execute the bundled script** ([scripts/bump-must-gather-helm.sh](scripts/bump-must-gather-helm.sh)); do not reimplement lockfile, Stage flip, or Tekton edits inline.
- **Commit / PR / MR only when the user asks.**

## Prerequisites

- `curl`, `git`, `rsync`
- Network access to CGW mirror and both repo checkouts
- Clean git trees in upstream and downstream (or pass `--allow-dirty`)
- Upstream checkout on a branch that contains `hack/update-helm-lockfile.sh`

## Usage

```bash
SKILL=skills/ci/rhdh-must-gather-helm-bump   # under rhdh-skill checkout
chmod +x "${SKILL}/scripts/bump-must-gather-helm.sh"

# Probe CGW + planned install path
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --check --parent-dir ~/RHDH

# Dry-run, then apply
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --dry-run --parent-dir ~/RHDH
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --parent-dir ~/RHDH
```

Full flag reference: `"${SKILL}/scripts/bump-must-gather-helm.sh" --help`.

**Default:** updates upstream, syncs helm-related paths into distgit, flips Stage 2a/2b, regenerates distgit `Containerfile`, patches Tekton prefetch, writes `sync/upstream_SHA_rhdh-must-gather`. Does **not** commit, push, or open PR/MR.

## Workflow

1. Confirm target `--to` version against [Helm releases](https://github.com/helm/helm/releases).
2. Resolve `--upstream` / `--downstream` (or `--parent-dir`).
3. Run `--check`; read `mode=cgw` or `mode=vendor`.
4. Run `--dry-run`, then the script without `--dry-run`.
5. Review `git diff` in **both** repos.
6. Run every verification gate — read [references/verification.md](references/verification.md).
7. Commit / PR·MR only when the user asks.

## Completion

A bump is done when `--check`/`--dry-run` (if used) and the real run finish,
leaving behind:

- upstream `HELM_VERSION` plus lockfile or `vendor/helm/` matching `--to`
- Stage 2a active on `mode=cgw`, Stage 2b on `mode=vendor` (upstream + distgit)
- distgit helm-related files synced; `vendor/helm` absent on `mode=cgw`
- Tekton `prefetch-input` matching install path (`generic` vs `gomod`) for
  must-gather only (other `components.yaml` entries untouched)
- `sync/upstream_SHA_rhdh-must-gather` pointing at the upstream commit used

Report `mode=`, paths touched, and any verification still pending
([references/verification.md](references/verification.md)). Working trees stay
uncommitted; if the user asks for a commit, PR, or MR, follow `/mutation-gate`
and attach Jira via `/rhdh-jira-link`.

## Anti-patterns

- Blaming a Helm bump when only GitHub E2E fails — triage chart/E2E harness first ([references/verification.md](references/verification.md)).

## Reference index

| Reference | Load when... |
|-----------|--------------|
| [references/install-paths.md](references/install-paths.md) | Choosing or switching CGW binary vs vendored source (Stage 2a/2b) |
| [references/tekton-prefetch.md](references/tekton-prefetch.md) | Editing or debugging Konflux `prefetch-input` JSON |
| [references/verification.md](references/verification.md) | Validating the bump (unit tests, Konflux, E2E triage) |
| [references/helm4-notes.md](references/helm4-notes.md) | Debugging E2E after a major Helm version bump |

## Related

- Upstream `make vendor` / `make helm-lockfile-update` — same logic, upstream only
- `/rhdh-base-images` — UBI/RPM bumps for overlapping repos
- `/rhdh-konflux-tasks` — task-bundle digest bumps in the same midstream `.tekton` trees
- CGW binary approach: [rhdh-must-gather#284](https://github.com/redhat-developer/rhdh-must-gather/pull/284)
- Vendored fallback reference: [rhdh-must-gather#282](https://github.com/redhat-developer/rhdh-must-gather/pull/282)
