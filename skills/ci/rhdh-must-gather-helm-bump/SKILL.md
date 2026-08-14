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
- **Execute the bundled script** ([scripts/bump-must-gather-helm.py](scripts/bump-must-gather-helm.py)); do not reimplement lockfile, Stage flip, or Tekton edits inline.
- **`--check` and `--dry-run` are the preview.** Apply is a write: follow `/mutation-gate`. Approval to preview is not approval to write.
- **Commit / PR / MR only when the user asks.**

## Prerequisites

- Python 3.9+, `bash`, `curl`, `git`, `rsync`
- Network access to CGW mirror and both repo checkouts
- Clean git trees in upstream and downstream (or pass `--allow-dirty`)
- Upstream checkout on a branch that contains `hack/update-helm-lockfile.sh`

## Usage

```bash
SKILL=<this skill's directory>

# Probe CGW + planned install path
python3 "${SKILL}/scripts/bump-must-gather-helm.py" --to 4.3.0 --check --parent-dir ~/RHDH

# Dry-run, then apply (apply only after /mutation-gate)
python3 "${SKILL}/scripts/bump-must-gather-helm.py" --to 4.3.0 --dry-run --parent-dir ~/RHDH
python3 "${SKILL}/scripts/bump-must-gather-helm.py" --to 4.3.0 --parent-dir ~/RHDH
```

Full flag reference: `python3 "${SKILL}/scripts/bump-must-gather-helm.py" --help`.

**Default:** updates upstream, syncs helm-related paths into distgit, flips Stage 2a/2b, regenerates distgit `Containerfile`, patches Tekton prefetch, writes `sync/upstream_SHA_rhdh-must-gather`. Does **not** commit, push, or open PR/MR.

## Workflow

1. Confirm target `--to` version against [Helm releases](https://github.com/helm/helm/releases).
2. Resolve `--upstream` / `--downstream` (or `--parent-dir`).
3. Run `--check` and `--dry-run`. That pair is the preview.
4. Apply only after `/mutation-gate` approval, with upstream and distgit/Tekton as separate operations. Approval to dry-run is not approval to write.
5. Review `git diff` in both repos, then the gates in [references/verification.md](references/verification.md).
6. Commit / PR or MR only when the user asks, again through `/mutation-gate`.

## Completion

`--check` and `--dry-run` are the preview. They are not a write and do not
approve an apply.

An apply is done when `/mutation-gate` approved the writes (upstream and
distgit/Tekton as separate operations), the script ran without `--dry-run`,
and the trees contain:

- upstream `HELM_VERSION` plus lockfile or `vendor/helm/` matching `--to`
- Stage 2a active on `mode=cgw`, Stage 2b on `mode=vendor` (upstream + distgit)
- distgit helm-related files synced; `vendor/helm` absent on `mode=cgw`
- Tekton `prefetch-input` matching install path (`generic` vs `gomod`) for
  must-gather only (other `components.yaml` entries untouched)
- `sync/upstream_SHA_rhdh-must-gather` pointing at a **committed** upstream HEAD
  (the script refuses to pin a dirty HEAD)

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
