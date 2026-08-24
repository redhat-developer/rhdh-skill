# rhdh-operator PR container images

How to recognize and validate CI-built images for operator PRs. The workflow
definition lives in the rhdh-operator repo at
`.github/workflows/pr-container-build.yaml` — read it for the authoritative
build behavior.

## Facts

- CI builds three images per PR: `operator`, `operator-bundle`, `operator-catalog`
- Registry: `quay.io/rhdh-community/`
- Tag format includes PR number plus commit SHA. Only CI knows the exact tag —
  never construct it.
- Images expire after 14 days (`quay.expires-after=14d` label)

## Extract URLs from PR comments

`/rhdh-forge` already returned the PR comments. Take the latest comment body
that contains `quay.io/rhdh-community/operator:` and parse the three image URLs
from it.

If no such comment exists, ask `/rhdh-forge` for the `pr-container-build.yaml`
run on the PR head branch:

- `in_progress` — wait for it to finish
- `failure` — build failed; read the workflow logs through `/rhdh-forge`
- No runs — CI may not have triggered (draft PR, docs-only change, external
  contributor)

## Validate the operator image exists

```bash
skopeo inspect docker://quay.io/rhdh-community/operator:TAG --raw 2>/dev/null \
  && echo "Image exists" || echo "Image not found or expired"
```

If expired (14-day TTL), the PR author needs to push a new commit to retrigger
CI.
