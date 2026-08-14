# Upstream repo reference

## redhat-developer/rhdh

- Clone: `https://github.com/redhat-developer/rhdh.git`
- Branches: `main`, `release-1.9`, `release-1.10`, …
- Base images: `build/containerfiles/Containerfile`, `.ci/images/Dockerfile`, and other `Dockerfile`/`Containerfile` paths within `-maxdepth 5`
- RPM lock: `build/containerfiles/Containerfile` + `rpms.in.yaml` → `rpms.lock.yaml`
- Node headers: when builder image Node version changes, update `.nvm/releases/node-v*-headers.tar.gz`, `.nvmrc`, and `.nvm/releases/README.adoc` (see `.nvm/releases/README.adoc`)
- Workflow reference: `.github/workflows/update-rpm-lockfile.yaml`

## redhat-developer/rhdh-must-gather

- Clone: `https://github.com/redhat-developer/rhdh-must-gather.git`
- Branches: `main`, `release-1.10`, …
- Base images: root `Containerfile`, `.rhdh/docker/Containerfile`
- RPM lock: root `Containerfile` + `rpms.in.yaml` → `rpms.lock.yaml`
- Marker for auto-detection: `collection-scripts/` directory

## redhat-developer/rhdh-operator

- Clone: `https://github.com/redhat-developer/rhdh-operator.git`
- Branches: `main`, `release-1.9`, `release-1.10`, …
- Base images: `.rhdh/docker/Dockerfile`, root `Dockerfile`
- RPM lock: `.rhdh/docker/Dockerfile` + `rpms.in.yaml` → `rpms.lock.yaml`
- Workflow reference: `.github/workflows/update-rpm-lockfile.yaml`

## Midstream script source

When `--update-base-images-script` is omitted, the bundled script downloads from:

`https://gitlab.cee.redhat.com/rhidp/rhdh/-/raw/<scripts-branch>/build/scripts/updateBaseImages.sh`

`createPR.sh` is fetched into the same directory when missing.
