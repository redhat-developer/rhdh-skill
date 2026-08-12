# Tekton prefetch for rhdh-must-gather

Konflux `prefetch-dependencies` input is a JSON array on PipelineRun param `prefetch-input` and in `.tekton-templates/components.yaml` under `must-gather.prefetch_input`.

## CGW binary (Stage 2a — default)

Helm linux-amd64/arm64 tarballs are listed in `artifacts.lock.yaml`. Hermeto **generic** fetcher prefetches them.

```json
[
  {"type": "rpm", "path": "distgit/containers/rhdh-must-gather"},
  {"type": "pip", "path": "distgit/containers/rhdh-must-gather", "allow_binary": "false"},
  {"type": "generic", "path": "distgit/containers/rhdh-must-gather"},
  {"type": "cargo", "path": "distgit/containers/rhdh-must-gather/vendor/websocat"}
]
```

Files to patch in `rhidp/rhdh`:

- `.tekton/rhdh-must-gather-2-pull.yaml` — `spec.params` → `prefetch-input`
- `.tekton/rhdh-must-gather-2-push.yaml` — same
- `.tekton-templates/components.yaml` — `must-gather.prefetch_input`

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

Also comment Stage 2a and uncomment Stage 2b in `Containerfile` and `.rhdh/docker/Containerfile` (see upstream comments). Regenerating PLRs from templates is **not** required for prefetch-only edits — patch the three files above directly.
