---
name: rhdh-must-gather-helm-bump
description: >-
  Bumps the Helm CLI baked into redhat-developer/rhdh-must-gather, mirrors helm
  files into gitlab.cee.redhat.com/rhidp/rhdh distgit, patches Konflux Tekton
  prefetch (CGW generic vs vendored gomod), and updates sync/upstream_SHA. Use
  when upgrading must-gather Helm, running helm-lockfile-update,
  refresh artifacts.lock.yaml, syncing rhdh-must-gather downstream, switching
  CGW binary vs vendor/helm build paths, or bumping HELM_VERSION for RHIDP-16046.
  Also use when Konflux rhdh-must-gather prefetch fails after a Helm release.
---

# RHDH must-gather Helm bump

## Goal

Propagate a **Helm CLI** version bump across upstream GitHub and midstream GitLab:

| Repo | Path | What changes |
|------|------|--------------|
| [`redhat-developer/rhdh-must-gather`](https://github.com/redhat-developer/rhdh-must-gather) | repo root | `Makefile` `HELM_VERSION`, `artifacts.lock.yaml` **or** `vendor/helm/`, hack scripts |
| [`gitlab.cee.redhat.com/rhidp/rhdh`](https://gitlab.cee.redhat.com/rhidp/rhdh) | `distgit/containers/rhdh-must-gather/` | Mirror upstream helm-related files |
| Same (midstream) | `.tekton/rhdh-must-gather-2-{pull,push}.yaml` | `prefetch-input` (`generic` vs `gomod`) |
| Same | `.tekton-templates/components.yaml` | `must-gather.prefetch_input` (keep in sync with PLRs) |
| Same | `sync/upstream_SHA_rhdh-must-gather` | Upstream commit SHA after sync |

## Essential principles

- **Helm CLI ≠ RHDH chart version.** This skill only bumps the CLI in the must-gather image, not `oci://quay.io/rhdh/chart`.
- **CGW binary path is preferred** when `mirror.openshift.com/pub/cgw/helm/<version>/` has linux amd64/arm64 tarballs — smaller tree, faster Konflux builds.
- **Execute the bundled script** ([scripts/bump-must-gather-helm.sh](scripts/bump-must-gather-helm.sh)); do not reimplement lockfile or Tekton edits inline.
- **Commit / PR / MR only when the user asks** ([jira-pr-mr-link](../jira-pr-mr-link/SKILL.md)).

## Prerequisites

- `curl`, `git`, `rsync` (vendor path only)
- Network access to CGW mirror and both repo checkouts
- Clean git trees in upstream and downstream (or pass `--allow-dirty`)
- Upstream checkout on a branch that contains `hack/update-helm-lockfile.sh`

## Quick start

```bash
SKILL=skills/rhdh-must-gather-helm-bump   # under rhdh-skill checkout
chmod +x "${SKILL}/scripts/bump-must-gather-helm.sh"

# Probe CGW + planned install path
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --check --parent-dir ~/RHDH

# Bump upstream, sync distgit, patch Tekton, update upstream SHA
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --parent-dir ~/RHDH
```

## Run the bundled script

```bash
# Explicit repo paths
"${SKILL}/scripts/bump-must-gather-helm.sh" --to v4.3.0 \
  --upstream ~/RHDH/1-must-gather \
  --downstream ~/RHDH/4-rhdh

# Dry-run first when unfamiliar
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --dry-run --parent-dir ~/RHDH
```

### Flags

| Flag | Purpose |
|------|---------|
| `--to VERSION` | **Required.** Target Helm version (`4.3.0` or `v4.3.0`) |
| `--upstream PATH` | `rhdh-must-gather` checkout |
| `--downstream PATH` | `rhidp/rhdh` midstream checkout |
| `--parent-dir PATH` | Auto-discover `1-must-gather` / `rhdh-must-gather` and `4-rhdh` / `rhdh` |
| `--check` | Probe CGW; print `helm_version=`, `mode=`, paths; no file changes |
| `--skip-upstream` | Sync downstream + Tekton only (upstream already bumped) |
| `--skip-downstream` | Bump upstream only |
| `--dry-run` | Print actions without writing |
| `--allow-dirty` | Proceed with uncommitted changes |

**Default:** updates upstream, rsyncs helm-related paths into distgit, patches Tekton prefetch, writes `sync/upstream_SHA_rhdh-must-gather`. Does **not** commit, push, or open PR/MR.

## Workflow

1. Confirm target `--to` version against [Helm releases](https://github.com/helm/helm/releases).
2. Resolve `--upstream` / `--downstream` (or `--parent-dir`).
3. Run `--check`; read `mode=cgw` or `mode=vendor`.
4. Run `--dry-run`, then the script without `--dry-run`.
5. Review `git diff` in **both** repos.
6. **Vendor path only:** swap Containerfile Stage 2a/2b — read [references/install-paths.md](references/install-paths.md).
7. Run verification gates — read [references/verification.md](references/verification.md).
8. Commit / PR·MR only when the user asks.

## Success criteria

- [ ] Upstream `HELM_VERSION` and lockfile or `vendor/helm/` match `--to`
- [ ] Distgit mirror matches upstream helm-related files
- [ ] Tekton `prefetch-input` matches install path (`generic` vs `gomod`)
- [ ] `sync/upstream_SHA_rhdh-must-gather` points at the upstream commit used for sync
- [ ] No stale `vendor/helm/` in distgit when `mode=cgw`
- [ ] Upstream `make test` passes; Konflux on-pull PLR succeeds downstream

## Anti-patterns

- Reimplementing `update-helm-lockfile.sh` or Tekton JSON edits by hand instead of running the script.
- Confusing Helm CLI bumps with RHDH chart version changes (chart lives on Quay OCI, not in this skill).
- Leaving `vendor/helm/` in distgit after switching to CGW binaries.
- Blaming a Helm bump when only GitHub E2E fails — triage chart/E2E harness first ([references/verification.md](references/verification.md)).
- Committing or opening PR/MR without the user requesting it.

## Reference index

| Reference | Load when... |
|-----------|--------------|
| [references/install-paths.md](references/install-paths.md) | Choosing or switching CGW binary vs vendored source (Stage 2a/2b) |
| [references/tekton-prefetch.md](references/tekton-prefetch.md) | Editing or debugging Konflux `prefetch-input` JSON |
| [references/verification.md](references/verification.md) | Validating the bump (unit tests, Konflux, E2E triage) |
| [references/helm4-notes.md](references/helm4-notes.md) | Helm 4 behavior changes affect must-gather or E2E after a major bump |

## Related

- Upstream `make vendor` / `make helm-lockfile-update` — same logic, upstream only
- [base-images-and-rpms](../base-images-and-rpms/SKILL.md) — UBI/RPM bumps for overlapping repos
- CGW binary approach: [rhdh-must-gather#284](https://github.com/redhat-developer/rhdh-must-gather/pull/284)
- Vendored fallback reference: [rhdh-must-gather#282](https://github.com/redhat-developer/rhdh-must-gather/pull/282)
