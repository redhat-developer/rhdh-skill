# Catalog surgical update (one workspace)

How to approximate `sync-midstream.sh --force-clone '<ws>'` for a **single** workspace without a full midstream sync.

## Paths sync-midstream touches (per workspace)

| Path | Role |
|------|------|
| `overlay-repo/workspaces/<ws>/source.json` | Upstream repo + `repo-ref` SHA |
| `overlay-repo/workspaces/<ws>/plugins-list.yaml` | Plugins to export |
| `overlay-repo/workspaces/<ws>/metadata/*.yaml` | Package versions + OCI `dynamicArtifact` |
| `overlay-repo/workspaces/<ws>/` overlays/patches | Applied onto clone when present |
| `workspaces/<ws>/` | Sparse-ish clone of upstream at `repo-ref`, then transform/export |
| `plugin_builds/<ws>/*.json` | `registryReference`, `io.backstage.dynamic-packages` |
| `.tekton/rhdh-bsp-*-<stream>-push.{yaml,Containerfile}` | PLRs; tags from plugin `package.json` version |
| `catalog-index/` | Usually regen only on full sync / index jobs — skip unless asked |

Root overlay files (`overlay-repo/versions.json`, package lists) change only when overlays root changes — not required for a single-workspace version bump.

## Sync overlay-repo slice

From a local overlays checkout on the merged branch. Resolve paths with **dot-notation** keys and JSON (shorthand like `overlay` works for `config set` only; bare `$($RHDH config get overlay)` captures a JSON blob or errors):

```bash
WS=app-defaults
# /rhdh-context owns the rhdh CLI; invoke it by name and use the paths it reports.
# To run the wrapper directly, RHDH is the path to that skill's scripts/rhdh.
OVERLAY="$("$RHDH" --json config get repos.overlay | jq -r '.data.value')"
CATALOG="$("$RHDH" --json config get repos.catalog | jq -r '.data.value')"
# Or set OVERLAY=/CATALOG to absolute checkouts if config is unset

mkdir -p "$CATALOG/overlay-repo/workspaces/$WS"
cp -a "$OVERLAY/workspaces/$WS/source.json" \
      "$OVERLAY/workspaces/$WS/plugins-list.yaml" \
      "$CATALOG/overlay-repo/workspaces/$WS/"
rm -rf "$CATALOG/overlay-repo/workspaces/$WS/metadata"
cp -a "$OVERLAY/workspaces/$WS/metadata" "$CATALOG/overlay-repo/workspaces/$WS/"
# Also copy overlay/ / patches/ trees if the workspace has them
```

Or pull from GitHub `main` at the overlays merge SHA if no local checkout.

## Apply upstream SHA into `workspaces/<ws>/`

Resolve `SHA` from npm `gitHead` / Version Packages merge.

**Lock / resolutions / package versions only** (common for pins):

1. Diff upstream `workspaces/<ws>/{package.json,yarn.lock}` and plugin `package.json` files between catalog’s previous `repo-ref` and `$SHA`.
2. Apply the same edits under `workspaces/<ws>/` at the **workspace root that owns `yarn.lock`** (not under `plugins/<name>/` alone — that reintroduces the RHIDP-16097 pin footgun). Catalog may already have midstream transforms — preserve existing `update-workspace.js` outcomes; do not blindly overwrite the whole tree with a raw upstream sparse clone unless you re-run transforms.

**Larger source churn:** prefer scoped sync (below) or sparse-checkout upstream at `$SHA`, copy plugin trees, then re-run the workspace transform/export pieces you need.

Verify Hermeto-sensitive pins:

```bash
rg -n 'electron-to-chromium|resolutions' workspaces/<ws>/package.json workspaces/<ws>/yarn.lock
```

## Nested vs flat workspaces

Read `overlay-repo/workspaces/<ws>/source.json` `repo-flat`:

| `repo-flat` | Layout | `pluginVersion` / generator path |
|-------------|--------|----------------------------------|
| `false` (nested) | `workspaces/<ws>/plugins/<name>/` | `plugins/<name>/package.json`; `--path '<ws>/plugins/<name>'` |
| `true` (flat) | packages at workspace root | root / package `package.json`; prefer `--package '<name>'` (no `plugins/` segment) |

## PLR / Containerfile tag bumps

Tag shape (from `.tekton/updatePLRs.sh`):

```text
konflux.additional-tags="<xy>--<pluginVersion>,<x.y.z>--<pluginVersion>"
# e.g. 2.0--0.0.3,2.0.0--0.0.3
```

Also update:

- `DESCRIPTION="… plugin <short-name> <pluginVersion>"`
- `plugin_builds/.../registryReference` → `quay.io/rhdh/<image>:2.0.0--0.0.3`
- Optional: `UPSTREAM_REPO="…/rhdh-plugin-export-overlays/tree/main @ <overlays-sha>"`

For a full-stream regen, invoke the named skill `/rhdh-konflux-tasks`; that skill owns stream-wide PipelineRun regeneration. For the **scoped** regen this skill owns after surgical version bumps, use flags from `.tekton/updatePLRs.sh --help` (they include `--next`, `--package`/`--path`, `--nopush`; do not invent others):

```bash
cd "$CATALOG"
# nested example (repo-flat: false); drop --next unless targeting main/next stream
.tekton/updatePLRs.sh -v 2.0.0 --next --nopush \
  --package 'app-defaults|app-auth|app-integrations'
# or: --path 'app-defaults/plugins/app-defaults'
# flat (repo-flat: true): use --package '<name>', not --path '.../plugins/...'
```

Commit PLR churn with the midstream content change (or a follow-up commit on the same MR). Commit messages can include `[skip-gitlab]` to save running a full sync-midstream pipeline.

## Scoped sync-midstream fallback

**SSOT for the fallback invocation** (SKILL.md links here — do not diverge):

```bash
./build/ci/sync-midstream.sh --nopush \
  --force-clone 'app-defaults' \
  --skip-clone 'workspaces/'
```

- `--nopush`: review locally; agent opens the MR.
- Optional: `--no` / `--nocommit` to skip the local commit as well; `--debug` for verbose logs.
- Full `--always-clone` is almost never wanted for a single-workspace promote.
- `--force-clone` alone still walks every `source.json`; pair with skip/force so only the target workspace is re-cloned.

## Prior art

| MR | Pattern |
|----|---------|
| [catalog !824](https://gitlab.cee.redhat.com/rhidp/rhdh-plugin-catalog/-/merge_requests/824) | Surgical overlay-repo sync + workspace lock pin (no force-clone) |
| !806 / !762 | Same surgical pin style |

When versions bump (not only a lock pin), include `plugin_builds` + `.tekton` tag updates in the same MR so Konflux retags `2.0.0--<new>`.
