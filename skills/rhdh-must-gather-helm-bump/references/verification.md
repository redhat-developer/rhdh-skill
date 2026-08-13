# Verification after a must-gather Helm bump

## Upstream (GitHub)

| Gate | Command / location | Pass when |
|------|-------------------|-----------|
| Unit tests | `make test` in `rhdh-must-gather` | BATS suite green |
| Local helm | `make local-setup && ./bin/helm version` | Version matches `HELM_VERSION` |
| Image build | GitHub Actions “Build PR Container Image” | Image builds; `helm version` works in container |
| E2E | GitHub Actions “E2E Tests” | Kind E2E completes |

Konflux hermetic builds are validated downstream; upstream CI is the primary gate for script and E2E harness changes.

## Downstream (GitLab midstream)

| Gate | Command / location | Pass when |
|------|-------------------|-----------|
| Distgit sync | `git diff distgit/containers/rhdh-must-gather` | Helm files match upstream |
| Upstream SHA | `sync/upstream_SHA_rhdh-must-gather` | Matches upstream commit synced |
| Konflux | `rhdh-must-gather-2-on-pull` PipelineRun | Prefetch + build succeed |

## E2E triage (upstream only)

If unit tests and image build pass but **E2E fails**, the Helm bump may be unrelated. Common false positives from [rhdh-must-gather#284](https://github.com/redhat-developer/rhdh-must-gather/pull/284):

- Chart resolution from `oci://quay.io/rhdh/chart` (not GitHub Releases)
- RHDH 2.x chart values and init-container pod lifecycle in E2E waits
- Helm 4 printing `Pulled:` / `Digest:` to stdout on `helm template oci://…` (see [helm4-notes.md](helm4-notes.md))

Check E2E job logs for the first `ERROR` or `make: ***` line — ignore debug must-gather SUCCESS lines from the EXIT trap.
