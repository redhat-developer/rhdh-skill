---
name: rhdh-plugin-export
description: >-
  Turns a Backstage plugin you are developing into a deployable Red Hat
  Developer Hub dynamic plugin artifact: run @red-hat-developer-hub/cli plugin
  export to produce dist-dynamic and dist-scalprum, choose shared, embedded and
  bundled dependencies, package as an OCI image, tgz archive or npm package,
  push to quay.io or another registry, and generate the SHA-512 or sha256
  digest integrity values a deployment needs. Use for "export my plugin",
  "package the plugin as OCI", "push the plugin to a registry",
  --shared-package, --embed-package, plugin-manifest.json, or integrity hashes.
  For a failing export in the rhdh-plugin-export-overlays repository, use
  /rhdh-overlay instead.
compatibility: "Node.js 22+, Yarn, Python 3, and podman, docker, or buildah for OCI images; registry credentials for a push."
---

# RHDH Plugin Export

Own the step between working source and a deployable artifact. The plugin
builds, exports to `dist-dynamic/`, gets packaged in one of three formats, and
optionally lands in a registry with an integrity value the deployment can pin.

## Scope against /rhdh-overlay

This skill exports **a plugin you are developing**, from its own workspace, on
your machine. `/rhdh-overlay` repairs **the overlay repository's CI export** —
`source.json`, `plugins-list.yaml`, and the export jobs that
`rhdh-plugin-export-overlays` runs for the Extensions Catalog. If the failing
export is a GitHub Actions run in that repository, it is not this skill.

## Start here

1. Confirm the plugin builds: `yarn build` and `yarn tsc` from the plugin
   directory.
2. Read `package.json` for the plugin role, name, and version, and check that a
   backend plugin has a default export from `src/index.ts`.
3. Decide the target format before running anything: OCI image, tgz archive, or
   npm package.

## Route by outcome

| Outcome | Load and follow |
|---|---|
| Export and package in one pass | `references/export.md`; run `scripts/export-plugin.py` |
| Choose shared, embedded, or bundled dependencies | `references/export-options.md` |
| Compare or produce a specific artifact format | `references/packaging-formats.md` |
| Produce or verify an integrity value | `references/integrity-hashes.md` |
| See a complete deployment configuration | `examples/dynamic-plugins.yaml` |

The bundled script covers the common path:

```bash
python scripts/export-plugin.py --plugin-dir plugins/my-plugin \
  --tag quay.io/ns/my-plugin:v0.1.0 --push --clean
```

Run it with `--help` for the full option set. Follow `references/export.md`
step by step when the script's defaults do not fit.

## Boundaries

- This skill produces artifacts. It does not write plugin source, generate
  deployment configuration, or run RHDH.
- `/rhdh-plugin-authoring` owns plugin source, including a missing default
  export or a broken build that surfaces here.
- `/rhdh-plugin-wiring` owns the `dynamic-plugins.yaml` configuration that
  consumes the artifact this skill produces.
- `/rhdh-local` owns installing the artifact into a running local RHDH.
- `/rhdh-overlay` owns the overlay repository and the Extensions Catalog.

Invoke a named skill and describe the handoff in the conversation. Never open
another skill's files.

## Invariants

- Never invent a registry reference. Derive the package name, tag, and digest
  from the export output and the registry response.
- A push to a registry is an external write. Invoke the named skill
  `mutation-gate` and follow it; the operation's target is the exact
  registry, repository, and tag.
- Prefer a digest over a tag when a deployment needs a stable artifact.
- Report the produced paths and references verbatim; a deployment that pins a
  guessed value fails at install time, far from here.

## Completion

Report the export command run, the artifact format and its exact reference or
path, the shared and embedded dependency decisions, any integrity value
produced, whether a push happened and to where, and the named skill to invoke
next for wiring or local verification.
