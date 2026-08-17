# Check EKS Kubernetes Version Lifecycle

Query the AWS EKS docs source and cross-verify with endoflife.date.

## Run

```bash
uv run scripts/check_eks_lifecycle.py \
  --test-pattern "^e2e-eks-" \
  --mapt-ref ci-operator/step-registry/redhat-developer/rhdh/eks/mapt/create/redhat-developer-rhdh-eks-mapt-create-ref.yaml
```

Override repo location with `--repo-dir /path/to/openshift/release`.

## Output

1. **Configured MAPT_KUBERNETES_VERSION per branch** -- what each RHDH release branch is using
2. **Supported minor versions** -- Standard or Extended support tier
3. **Release calendar** -- upstream release, EKS release, end dates
4. **Cross-verify (endoflife.date)** -- independent EOL and extended support dates

## Action

**Always update the main branch to the newest Standard version.** Prefer Standard over Extended to avoid extra costs. For release branches, ask the user before updating.

If the API call fails, fall back to the vendor docs:

```text
WebFetch https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html
```
