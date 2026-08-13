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

## Checksum verification (required)

`hack/install-helm-binary.sh` (curl path) and `hack/install-helm-local.sh` call `hack/verify-helm-tarball.sh`:

1. Prefer SHA256 pinned in `artifacts.lock.yaml` when the filename is listed (linux amd64/arm64).
2. Otherwise verify against `https://mirror.openshift.com/pub/cgw/helm/<version>/sha256sum.txt` (darwin / non-locked).

Always sync `hack/verify-helm-tarball.sh` into distgit with the other install scripts. The bump script includes it in `SYNC_REL_PATHS`.

## TARGETPLATFORM arch parsing

In Containerfile Stage 2a, `TARGETPLATFORM` may be three-part (`linux/arm64/v8`). Install scripts take **field 2** (`cut -d/ -f2`), not `${TARGETPLATFORM##*/}` (which would yield `v8`).

## Midstream: keep `hack/` in sync

`Containerfile` Stage 2a does `COPY hack/install-helm-binary.sh`. Bot sync alone is not enough if `upstream_repos.yml` lists `hack/` under must-gather `exclude_root` — Hermeto prefetch then has a Containerfile that references missing scripts ([rhidp/rhdh !697](https://gitlab.cee.redhat.com/rhidp/rhdh/-/merge_requests/697)).

The bump script:

1. Copies helm `hack/*.sh` into `distgit/containers/rhdh-must-gather/hack/`
2. Removes `- hack/` from the must-gather `exclude_root` in `upstream_repos.yml` when present

## Vendored path manual steps

When `mode=vendor`, the script prints reminders. Also required:

1. In upstream `Containerfile` and `.rhdh/docker/Containerfile`:
   - Comment out Stage 2a (CGW helm-builder)
   - Uncomment Stage 2b (go-toolset + `vendor/helm`)
2. Re-sync distgit Containerfiles after editing upstream `.rhdh/docker/Containerfile`
3. Confirm `distgit/vendor/helm` is present and helm is not fetched via `artifacts.lock.yaml`
