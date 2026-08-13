# CGW binary vs vendored Helm source

The bump script probes `hack/check-helm-binary-available.sh <version>` against `mirror.openshift.com/pub/cgw/helm/`.

## Decision table

| CGW mirror has linux amd64/arm64? | Upstream action | Konflux prefetch | Containerfile |
|-----------------------------------|-----------------|------------------|---------------|
| **Yes** (preferred) | `hack/update-helm-lockfile.sh` | `generic` on distgit root (`artifacts.lock.yaml`) | Stage **2a** active (CGW binary) |
| **No** | `hack/update-vendor.sh helm` | `gomod` on `vendor/helm` | Stage **2b** active (go-toolset build) — swap 2a/2b by hand |

## CGW tarball layout

CGW publishes flat tarballs: member `helm-linux-amd64` (or `helm-linux-arm64`) at the archive root, **not** `linux-amd64/helm`. Upstream `hack/install-helm-binary.sh` extracts the correct member; lockfile entries use filenames `helm-linux-amd64.tar.gz` and `helm-linux-arm64.tar.gz`.

If Konflux prefetch install fails after a bump, verify tarball layout before blaming Hermeto.

## Vendored path manual steps

When `mode=vendor`, the script prints reminders. Also required:

1. In upstream `Containerfile` and `.rhdh/docker/Containerfile`:
   - Comment out Stage 2a (CGW helm-builder)
   - Uncomment Stage 2b (go-toolset + `vendor/helm`)
2. Re-sync distgit Containerfiles after editing upstream `.rhdh/docker/Containerfile`
3. Confirm `distgit/vendor/helm` is present and helm is not fetched via `artifacts.lock.yaml`
