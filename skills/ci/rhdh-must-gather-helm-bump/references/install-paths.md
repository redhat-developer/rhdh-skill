# CGW binary vs vendored Helm source

The bump script probes `hack/check-helm-binary-available.sh <version>` against `mirror.openshift.com/pub/cgw/helm/`.

## Decision table

| CGW mirror has linux amd64/arm64? | Upstream action | Konflux prefetch | Containerfile |
|-----------------------------------|-----------------|------------------|---------------|
| **Yes** (preferred) | `hack/update-helm-lockfile.sh` | `generic` on distgit root (`artifacts.lock.yaml`) | Stage **2a** active (CGW binary) |
| **No** | `hack/update-vendor.sh helm` | `gomod` on `vendor/helm` | Stage **2b** active (go-toolset build) |

The script flips Stage 2a/2b bidirectionally on:

- upstream `Containerfile`
- upstream `.rhdh/docker/Containerfile`
- distgit `Containerfile` (after regenerating it from `.rhdh/docker/Containerfile`)

## Distgit sync (what the script copies)

- `Makefile`, `artifacts.lock.yaml`
- entire `hack/`
- `.rhdh/docker/Containerfile`
- entire `vendor/` — on `mode=cgw`, **omit/delete** `vendor/helm` (other vendor trees such as `websocat` stay)

It does **not** copy upstream root `Containerfile` onto distgit. Distgit root `Containerfile` is regenerated from `.rhdh/docker/Containerfile`, preserving existing `RHDH_MUST_GATHER_VERSION` and the Brew/Konflux metadata footer (`ENV SUMMARY=` / `LABEL` block) that `sync-midstream.sh` appends. On each regenerate it increments `release="N"` → `N+1` and updates `konflux.additional-tags` so the `version-release` suffix matches with a numeric boundary (`2.0-1` → `2.0-2`, and `2.0-10` → `2.0-11` not `2.0-20`).

## CGW tarball layout

CGW publishes flat tarballs: member `helm-linux-amd64` (or `helm-linux-arm64`) at the archive root, **not** `linux-amd64/helm`. Upstream `hack/install-helm-binary.sh` extracts the correct member; lockfile entries use filenames `helm-linux-amd64.tar.gz` and `helm-linux-arm64.tar.gz`.

If Konflux prefetch install fails after a bump, verify tarball layout before blaming Hermeto.

## Stage 2a / 2b (script-owned)

When `mode=vendor`, Stage 2a lines are commented and Stage 2b lines are uncommented. When `mode=cgw`, the reverse. Doc-only comments (`# Comment this out…`, `# https://…`, `# update via…`) stay commented.
