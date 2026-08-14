# Reference: rhdh-operator PR Container Images

How to find and validate CI-built images for operator PRs. The CI workflow definition lives in the rhdh-operator repo at `.github/workflows/pr-container-build.yaml` — read it for the authoritative build behavior.

<what_to_know>

## Key Facts

- CI builds three images per PR: `operator`, `operator-bundle`, `operator-catalog`
- Registry: `quay.io/rhdh-community/`
- Tag format includes PR number + commit SHA (only CI knows the exact tag — never construct manually)
- Images expire after 14 days (`quay.expires-after=14d` label)

</what_to_know>

<extracting_from_pr>

## Finding Image URLs

CI posts a comment on the PR with built image URLs. Extract the latest one:

```bash
REPO="redhat-developer/rhdh-operator"
PR_NUMBER=<number>

gh pr view $PR_NUMBER --repo $REPO --json comments \
  --jq '.comments[] | select(.body | test("quay.io/rhdh-community/operator:")) | .body' \
  | tail -1
```

**If no comment found**, the CI workflow may not have run yet. Check status:

```bash
BRANCH=$(gh pr view $PR_NUMBER --repo $REPO --json headRefName --jq '.headRefName')
gh run list --repo $REPO --branch $BRANCH --workflow pr-container-build.yaml --limit 1 \
  --json status,conclusion
```

- `in_progress` — wait for it to finish
- `failure` — build failed, check workflow logs
- No runs — CI may not have triggered (draft PR, docs-only change, external contributor)

</extracting_from_pr>

<validation>

## Validating Images Exist

```bash
skopeo inspect docker://quay.io/rhdh-community/operator:TAG --raw 2>/dev/null \
  && echo "Image exists" || echo "Image not found or expired"
```

If expired (14-day TTL), the PR author needs to push a new commit to retrigger CI.

</validation>
