# RHDH midstream layout (4-rhdh)

`updateDigests.sh` also updates `.tekton-templates/*.yaml` via `TEMPLATEPATH`.

## Files to update

Edit **templates first**, then regenerate or patch PLRs.

| Location | When to edit |
|----------|----------------|
| `.tekton-templates/rhdh-pipeline.yaml` | hub, operator, must-gather |
| `.tekton-templates/rhdh-operator-bundle.yaml` | operator-bundle (different task set) |
| `.tekton-templates/components.yaml` | Metadata for `generatePipelineRuns.sh` |
| `.tekton/rhdh-hub-<N>-{push,pull}.yaml` | From `rhdh-pipeline.yaml` |
| `.tekton/rhdh-operator-<N>-{push,pull}.yaml` | From `rhdh-pipeline.yaml` |
| `.tekton/rhdh-must-gather-<N>-{push,pull}.yaml` | From `rhdh-pipeline.yaml` |
| `.tekton/rhdh-operator-bundle-<N>-{push,pull}.yaml` | From `rhdh-operator-bundle.yaml` |
| `.tekton/rhdh-rag-content-<N>-{push,pull}.yaml` | Inline `pipelineSpec` — edit directly |
| `.tekton/fbc-<version>-push.yaml` | FBC pipelines; often `build-image-index` without prefetch |
| `.tekton/images-mirror-set.yaml` | Only if task bundles are referenced |

## Regenerate

```bash
cd .tekton
./generatePipelineRuns.sh -t <x.y>
```

Updates `rhdh-*-{push,pull}.yaml` and FBC `target_branch` placeholders in `fbc-*-push.yaml`.

## Generator: template changes

- Edit `pipelineSpec.params` and task `params` in `rhdh-pipeline.yaml` / `rhdh-operator-bundle.yaml`.
- `components.yaml` only if extending `generatePipelineRuns.sh` placeholders for per-component PLR params.
