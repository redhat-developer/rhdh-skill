# Check AKS Kubernetes Version Lifecycle

Query the AKS release status API and cross-verify with endoflife.date.

## Run

```bash
uv run scripts/check_aks_lifecycle.py \
  --test-pattern "^e2e-aks-" \
  --mapt-ref ci-operator/step-registry/redhat-developer/rhdh/aks/mapt/create/redhat-developer-rhdh-aks-mapt-create-ref.yaml
```

Override repo location with `--repo-dir /path/to/openshift/release`.

## Output

1. **Configured MAPT_KUBERNETES_VERSION per branch** -- what each RHDH release branch is using
2. **AKS Release Status** -- supported versions marked GA, LTS, or Preview
3. **Cross-verify (endoflife.date)** -- independent EOL dates

## Action

**Always update the main branch to the newest GA version.** For release branches, ask the user before updating.

If the API call fails, fall back to the vendor docs:

```text
WebFetch https://learn.microsoft.com/en-us/azure/aks/supported-kubernetes-versions
```
