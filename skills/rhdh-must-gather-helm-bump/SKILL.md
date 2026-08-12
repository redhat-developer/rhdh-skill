---
name: rhdh-must-gather-helm-bump
description: >-
  Bumps Helm in redhat-developer/rhdh-must-gather and mirrors the change into
  gitlab.cee.redhat.com/rhidp/rhdh distgit plus .tekton prefetch config (CGW
  generic vs vendored gomod). Use when upgrading must-gather Helm, refreshing
  artifacts.lock.yaml, or syncing rhdh-must-gather downstream after an upstream
  helm version change.
---

# RHDH must-gather Helm bump

## Goal

Propagate a **Helm CLI** version bump across:

| Repo | Path | What changes |
|------|------|--------------|
| [`redhat-developer/rhdh-must-gather`](https://github.com/redhat-developer/rhdh-must-gather) | repo root | `Makefile` `HELM_VERSION`, `artifacts.lock.yaml` **or** `vendor/helm/`, hack scripts |
| [`gitlab.cee.redhat.com/rhidp/rhdh`](https://gitlab.cee.redhat.com/rhidp/rhdh) | `distgit/containers/rhdh-must-gather/` | Mirror upstream helm-related files |
| Same (midstream) | `.tekton/rhdh-must-gather-2-{pull,push}.yaml` | `prefetch-input` (`generic` vs `gomod`) |
| Same | `.tekton-templates/components.yaml` | `must-gather.prefetch_input` (keep in sync with PLRs) |

Helm is **not** the RHDH chart version — only the CLI baked into the must-gather image.

## Two install paths (auto-detected)

| CGW mirror has linux amd64/arm64? | Upstream action | Konflux prefetch | Containerfile |
|-----------------------------------|-----------------|------------------|---------------|
| **Yes** (preferred) | `hack/update-helm-lockfile.sh` | `generic` on distgit root (`artifacts.lock.yaml`) | Stage **2a** active (CGW binary) |
| **No** | `hack/update-vendor.sh helm` | `gomod` on `vendor/helm` | Stage **2b** active (go-toolset build) — swap 2a/2b by hand |

Probe: `hack/check-helm-binary-available.sh <version>` against `mirror.openshift.com/pub/cgw/helm/`.

## Script

**Execute** [scripts/bump-must-gather-helm.sh](scripts/bump-must-gather-helm.sh); do not reimplement inline.

```bash
SKILL=skills/rhdh-must-gather-helm-bump   # under 1-rhdh-skill checkout
chmod +x "${SKILL}/scripts/bump-must-gather-helm.sh"

# Discover ~/RHDH/1-must-gather + ~/RHDH/4-rhdh (or aliases)
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --parent-dir ~/RHDH

# Explicit paths
"${SKILL}/scripts/bump-must-gather-helm.sh" --to v4.3.0 \
  --upstream ~/RHDH/1-must-gather \
  --downstream ~/RHDH/4-rhdh

# Probe only
"${SKILL}/scripts/bump-must-gather-helm.sh" --to 4.3.0 --check --parent-dir ~/RHDH
```

### Flags

| Flag | Purpose |
|------|---------|
| `--to VERSION` | **Required.** Target Helm version (`4.3.0` or `v4.3.0`) |
| `--upstream PATH` | `rhdh-must-gather` checkout |
| `--downstream PATH` | `rhidp/rhdh` midstream checkout |
| `--parent-dir PATH` | Auto-discover `1-must-gather` / `rhdh-must-gather` and `4-rhdh` / `rhdh` |
| `--check` | Probe CGW and print planned path; no file changes |
| `--skip-upstream` | Only sync downstream + Tekton (upstream already bumped) |
| `--skip-downstream` | Only bump upstream |
| `--dry-run` | Print actions without writing |
| `--allow-dirty` | Proceed with dirty git trees |

**Default:** updates upstream, rsyncs helm-related paths into distgit, patches Tekton prefetch. Does **not** commit, push, or open PR/MR.

## Agent workflow

1. Confirm target `--to` version (match [Helm releases](https://github.com/helm/helm/releases)).
2. Resolve `--upstream` / `--downstream` (or `--parent-dir`).
3. Run `--check`, then `--dry-run` if unfamiliar.
4. Run the script; review `git diff` in **both** repos.
5. **Vendored path only:** verify Containerfile Stage 2a/2b swap in upstream **and** `.rhdh/docker/Containerfile` (downstream copies root `Containerfile` from `.rhdh/docker/` during midstream sync).
6. Run `make test` in upstream when available.
7. Commit / PR·MR only when the user asks ([`jira-pr-mr-link`](../jira-pr-mr-link/SKILL.md)).

## Checklist

- [ ] CGW path: `artifacts.lock.yaml` + `HELM_VERSION` updated upstream and in distgit
- [ ] CGW path: Tekton uses `generic` prefetch (not `gomod` for helm)
- [ ] Vendored path: `vendor/helm/` synced; Tekton uses `gomod`; Stage 2b active
- [ ] `.tekton-templates/components.yaml` `must-gather.prefetch_input` matches PLRs
- [ ] No stale `vendor/helm/` left in distgit when on CGW path

## Related

- Upstream `make vendor` / `make helm-lockfile-update` — same logic, upstream only
- [base-images-and-rpms](../base-images-and-rpms/SKILL.md) — UBI/RPM bumps for the same repos
- Draft reference for vendored helm: [rhdh-must-gather#282](https://github.com/redhat-developer/rhdh-must-gather/pull/282)
- CGW binary approach: [rhdh-must-gather#284](https://github.com/redhat-developer/rhdh-must-gather/pull/284)
