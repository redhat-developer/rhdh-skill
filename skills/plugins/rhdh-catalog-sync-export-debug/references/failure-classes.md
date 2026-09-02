# Failure classes for catalog sync-midstream export

Load this file when `classify_export_log.py` has returned a `failureClass`, or
when the job log is too large to reason about by eye.

## Classes

| `failureClass` | What matched | First place to look |
|---|---|---|
| `yarn_lock_body_drift` | `[DRIFT] BODY DRIFT for pkg@ver` (not embedded) | `plugins-list.yaml` embed list vs npm/workspace `package.json` |
| `yarn_lock_embedded_drift` | `BODY DRIFT (embedded/workspace)` | catalog comparator / embedded pack contents |
| `export_command_failed` | non-empty `FAILED_EXPORTS` | upstream build, missing default export |
| `missing_types` | `TS2307` / cannot find module, no BODY DRIFT | `packages/type-shims`, scrubbed `*.test.ts` |
| `loop3_validation_failed` | `Loop 3 had N failure(s)` only | re-fetch a fuller trace |
| `unknown` | none of the above | read the last 80 lines of the job |

`nativeGypNoise: true` is a **note**, not a class. Optional native rebuilds of
`ssh2` / `cpu-features` fail on Node 24 in CI and locally; backend export still
succeeds.

## How Loop 1 vs Loop 3 produces BODY DRIFT

1. Loop 1 clones `source.json` `repo-ref`, exports every `plugins-list.yaml` row.
2. After export, `sync-midstream.sh` deletes plugin folders that are neither in
   `plugins-list.yaml` nor present as `dist-dynamic/embedded/*/package.json`.
3. `update-workspace.js` rewrites remaining `workspace:^` ranges to npm versions
   from `manifest.json` / the registry.
4. Loop 3 re-exports. For a **scrubbed** library the CLI resolves the npm
   tarball. The lockfile body is the published `dependencies` + checksum.
5. Comparator requires identical bodies for non-embedded `name@version`.

Loop 1 body comes from the workspace copy (or from the CLI rewriting
`workspace:^` using the local package.json). Loop 3 body comes from npm when
the folder is gone. If those manifests disagree at the same semver, CI fails.

## Worked example: orchestrator 2026-09-02

GitLab job `60069298` (`sync-midstream` on catalog `main`):

- Final line: `Loop 3 had 1 failure(s): orchestrator:validation-failed`
- Drift: `@red-hat-developer-hub/backstage-plugin-orchestrator-form-api@2.10.0`
  and `...-form-react@2.11.0` on `orchestrator` and `orchestrator-form-widgets`
- Backend plugins that `--embed-package` `orchestrator-common` / `orchestrator-node` passed
- Clone SHA in the job: `279803cf52e79040fc776c08d73ac57f748c5cab`

At that SHA, workspace form-api is still version `2.10.0` but
`@backstage/core-plugin-api` is `^1.12.9` and common is `workspace:^`. npm
`form-api@2.10.0` has `core-plugin-api ^1.12.7` and common `^3.9.0`.

`plugins-list.yaml` did not embed form-api / form-react. Sync scrubbed those
directories. Loop 3 hit the published 2.10.0/2.11.0 tarballs.

Overlays later pointed `repo-ref` at `f715573e` (npm `gitHead` of form-api
`2.11.0` / form-react `2.12.0`). A local scoped sync against that SHA produced
identical lockfile **bodies** (only `npm:2.11.0` vs `npm:^2.11.0` keys, which
the comparator allows).

Durable overlays hardening still applies: embed the unexported web-libraries
so a future SHA between a dep bump and Version Packages cannot fail the same way.

```yaml
plugins/orchestrator: --embed-package @red-hat-developer-hub/backstage-plugin-orchestrator-form-api --embed-package @red-hat-developer-hub/backstage-plugin-orchestrator-form-react --embed-package @red-hat-developer-hub/backstage-plugin-orchestrator-common
plugins/orchestrator-form-widgets: --embed-package @red-hat-developer-hub/backstage-plugin-orchestrator-form-api --embed-package @red-hat-developer-hub/backstage-plugin-orchestrator-form-react --embed-package @red-hat-developer-hub/backstage-plugin-orchestrator-common
```

Keep the existing backend `--embed-package` lines.

## Reading clone SHA and plugins-list from a job

Search the trace for:

```text
git clone -q https://github.com/redhat-developer/rhdh-plugins -b <sha>
```

and

```text
Include plugins/<name>: --embed-package ...
not found in overlay-repo/workspaces/<ws>/plugins-list.yaml. Remove!
Keep (embedded: @scope/pkg)!
```

The `Remove!` lines are the scrubbed libraries. The `Keep (embedded:` lines
are why backend common/node survive Loop 3.
