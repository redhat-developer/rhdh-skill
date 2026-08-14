# Tekton prefetch for rhdh-must-gather

Konflux `prefetch-dependencies` input is a JSON array on PipelineRun param `prefetch-input` and in `.tekton-templates/components.yaml` under `must-gather.prefetch_input` only (other components in that file must not change).

## CGW binary (Stage 2a — default)

Helm linux-amd64/arm64 tarballs are listed in `artifacts.lock.yaml`. Hermeto **generic** fetcher prefetches them.

CGW tarballs use a flat layout (`helm-linux-amd64` at archive root). See [install-paths.md](install-paths.md) for Stage 2a/2b and distgit sync rules.

```json
[
  {"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},
  {"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},
  {"type": "generic", "path": "distgit/containers/rhdh-must-gather"},
  {"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}
]
```

Files the script patches in `rhidp/rhdh`:

- `.tekton/rhdh-must-gather-2-pull.yaml` — `spec.params` → `prefetch-input`
- `.tekton/rhdh-must-gather-2-push.yaml` — same
- `.tekton-templates/components.yaml` — `must-gather.prefetch_input` only

## Vendored source (Stage 2b)

When CGW has no binaries, helm is built from `vendor/helm` with go-toolset. Use **gomod** prefetch:

```json
[
  {"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},
  {"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},
  {"type": "gomod", "path": "distgit/containers/rhdh-must-gather/vendor/helm"},
  {"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}
]
```

Stage 2a/2b Containerfile swap is owned by the bump script — see [install-paths.md](install-paths.md). Regenerating PLRs from templates is **not** required for prefetch-only edits — patch the three files above directly.
