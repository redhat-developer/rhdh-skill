# Helm 4 notes for must-gather

Helm 4 (currently installed from CGW in must-gather) differs from Helm 3 in ways that affect **E2E**, not the bump script itself.

## OCI pull status on stdout

When templating `oci://` charts, Helm 4 prints lines like:

```text
Pulled: quay.io/rhdh/chart:2.0-59-CI
Digest: sha256:...
---
apiVersion: v1
```

Piping `helm template … | kubectl apply` fails validation (`apiVersion not set, kind not set`) unless those status lines are stripped. Upstream E2E uses `helm_template_yaml()` in `tests/e2e/lib/test-utils.sh`.

Must-gather **collection** scripts do not pipe template output to kubectl today. If a future collector adds that pattern, filter pull lines or use `--output-dir` + `kubectl apply -f`.

## When this matters for a bump

- Major Helm upgrades (3 → 4): re-run upstream E2E; expect harness fixes separate from lockfile bumps.
- Patch/minor bumps within Helm 4: unlikely to need E2E changes unless CGW tarball layout or CLI flags change.
