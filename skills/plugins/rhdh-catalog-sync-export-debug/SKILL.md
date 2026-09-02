---
name: rhdh-catalog-sync-export-debug
description: >-
  Diagnoses rhdh-plugin-catalog sync-midstream export failures on GitLab CI or
  a local scoped clone: Loop 3 yarn.lock BODY DRIFT, dist-dynamic validation,
  missing types, and optional native gyp noise. Use when "export is failing
  for orchestrator", "sync-midstream validation-failed", "yarn.lock
  equivalence check failed", BODY DRIFT, or recreating
  `./build/ci/sync-midstream.sh --force-clone`. For overlay GitHub Actions
  publish failures, use /rhdh-overlay. To promote a known-good Version
  Packages SHA, use /rhdh-plugin-midstream-propagate.
compatibility: "Python 3, Git, glab or a job-trace file; optional npm and GitHub access to compare published package.json."
---

# RHDH catalog sync-midstream export debug

Own the question "why did this workspace fail Loop 3 in rhdh-plugin-catalog?"
The export command often succeeded. The job then dies on yarn.lock
equivalence between Loop 1 (`dist-dynamic.before-workspace-update`) and
Loop 3 (`dist-dynamic`).

## Start here

1. Get the GitLab job trace (`glab api projects/.../jobs/<id>/trace`) or the
   local `sync-midstream.sh` transcript.
2. Run the classifier:

```bash
python scripts/classify_export_log.py --log /tmp/job-trace.log
```

3. Follow the `failureClass` row in the [Reference index](#reference-index).
   Do not treat `ssh2` / `cpu-features` `node-gyp` lines as the failure when
   the classifier sets `nativeGypNoise: true` and `failureClass` is
   `yarn_lock_body_drift`.

## Reproduce locally

From an rhdh-plugin-catalog checkout on the failing branch:

```bash
./build/ci/sync-midstream.sh -b main --debug --no \
  --skip-clone workspaces/ --force-clone '<workspace>'
```

`--skip-clone workspaces/` still **walks** every `source.json` and Loop 3
re-exports every workspace that `CHANGED_WORKSPACES` collected. Overlay-repo
refresh at the start of the script often marks all workspaces changed. After
Loop 1+2 finish for the target workspace, stop a runaway Loop 3 and re-export
only that workspace:

```bash
cd workspaces/<ws>
find . -type d -name dist-dynamic -exec mv {} {}.before-workspace-update \;
INPUTS_PRE_EXPORT_HOOK="$ROOT/build/scripts/focused-install.js" \
  "$ROOT/build/scripts/batchExportPlugins.sh" -v 2.0.0 -w <ws> --focused --debug
node "$ROOT/build/scripts/compare-yarn-lock-equivalence.js" \
  plugins/<plugin>/dist-dynamic.before-workspace-update/yarn.lock \
  plugins/<plugin>/dist-dynamic/yarn.lock
```

`compare-yarn-lock-equivalence.js` allows checksum/resolution diffs only for
`file:./embedded/` and `@workspace:` blocks. Exact `npm:1.2.3` vs `npm:^1.2.3`
on the same resolved version is allowed. Any other body change on an npm
locator is `BODY DRIFT`.

## Classify the BODY DRIFT

For each drifted `name@version`, compare the workspace manifest at the cloned
SHA with the published npm tarball:

```bash
python scripts/compare_npm_workspace.py \
  --package @red-hat-developer-hub/backstage-plugin-orchestrator-form-api \
  --version 2.10.0 \
  --repo redhat-developer/rhdh-plugins \
  --sha <repo-ref from the job clone line> \
  --path workspaces/orchestrator/plugins/orchestrator-form-api/package.json
```

If `dependencyDiffs` is non-empty at the **same** semver, Loop 1 locked
unpublished workspace ranges and Loop 3 locked npm. That is not a missing
`@types/*` hole and not a yarn.lock "bad chain" in the workspace lockfile.

Also read `overlay-repo/workspaces/<ws>/plugins-list.yaml`. A library that is
not listed and not `--embed-package`'d is **scrubbed** after Loop 1
(`sync-midstream.sh` keeps only plugins-list entries plus packages found under
`dist-dynamic/embedded/`). Scrubbing is what forces Loop 3 onto npm.

## Where to fix (prefer upstream, then overlays, then catalog)

| Evidence | Layer | Fix |
|---|---|---|
| Workspace `package.json` deps changed but version not bumped / not published | **upstream** rhdh-plugins | Changeset + Version Packages so the SHA overlays pin has a matching npm tarball |
| Workspace library used by an exported plugin, not itself exported | **overlays** `plugins-list.yaml` | `--embed-package @scope/that-library` on each consumer plugin (same pattern as orchestrator-common on backend plugins) |
| Overlays `repo-ref` is between a dep bump and Version Packages | **overlays** `source.json` | Pin `repo-ref` to the Version Packages merge SHA (`gitHead` of the published version) |
| Comparator is wrong, type-shims missing, or scrub list too aggressive | **catalog** | Last resort; do not loosen BODY DRIFT to hide an unpublished workspace |

Invoke `/rhdh-overlay` to edit overlays `plugins-list.yaml` / `source.json`.
Invoke `/rhdh-plugin-midstream-propagate` once a Version Packages SHA exists
and npm `gitHead` matches. Do not open those skills' files from here.

## Anti-patterns

- Treating optional `ssh2` / `cpu-features` gyp errors as the job failure —
  they print `Failed to build optional crypto binding` and the export continues.
- Assuming "missing types" because focused-install mentions `@internal/type-shims`
  — that package is the catalog workaround for host React types, not this drift.
- Fixing catalog `compare-yarn-lock-equivalence.js` to ignore npm body diffs —
  that hides the workspace-vs-registry skew instead of embedding or publishing.
- Running `--always-clone` to debug one workspace — use `--skip-clone workspaces/
  --force-clone '<ws>'`, then a focused Loop 3 if overlay refresh dirties
  every workspace.

## Reference index

| Load when | File |
|---|---|
| Need the failure-class table and orchestrator worked example | `references/failure-classes.md` |

## Completion

Report the job URL or local command, `failureClass`, drifted packages, npm vs
workspace diffs, whether the library was scrubbed, and which of the three repos
should take the fix. Name the overlays `--embed-package` line or the Version
Packages SHA when that is the fix. Say if local Loop 3 on a newer `repo-ref`
already passes because overlays moved to a published SHA.
