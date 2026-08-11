# Reference: rhdh-chart PR Testing

How to validate and deploy chart changes from a PR. The CI workflow definition lives in the rhdh-chart repo at `.github/workflows/test.yaml` and `.github/actions/test-charts/action.yml` — read them for the authoritative CI behavior.

<what_to_know>

## Key Facts

- Chart CI does NOT build container images — it runs `ct lint` + `ct install` on a KIND cluster
- Charts are published to `oci://quay.io/rhdh/chart` only on merge (via `chart-releaser-action`)
- To test a PR's chart changes, you must check out the PR branch and deploy from the local checkout
- Pre-commit hooks auto-generate `README.md` (helm-docs), `values.schema.json` (jsonschema-dereference), and update Helm dependencies
- Chart architecture details are in `../../rhdh/references/rhdh-repos.md` under the `rhdh-chart` section — do not re-document here

</what_to_know>

<getting_pr_chart>

## Getting the PR Chart Locally

**Requires a local clone of rhdh-chart.** `gh pr checkout` operates on the current git repo — it will fail if CWD is not inside an rhdh-chart clone.

```bash
REPO="redhat-developer/rhdh-chart"
PR_NUMBER=<number>

# Ensure you're inside a local rhdh-chart clone (clone first if needed)
# gh repo clone $REPO && cd rhdh-chart

# Checkout the PR branch
gh pr checkout $PR_NUMBER --repo $REPO --detach

# Update Helm dependencies (required before template/install)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency update charts/backstage
```

If you already have a local clone:

```bash
PR_BRANCH=$(gh pr view $PR_NUMBER --repo $REPO --json headRefName --jq '.headRefName')
git fetch origin $PR_BRANCH
git checkout FETCH_HEAD
helm dependency update charts/backstage
```

</getting_pr_chart>

<local_validation>

## Local Validation

```bash
# Lint the chart
ct lint --config ct-lint.yaml

# Render templates to verify they produce valid YAML
helm template rhdh charts/backstage/ --debug

# Run pre-commit hooks (schema regen, helm-docs, dependency update)
pre-commit run --all-files
```

**Check Chart.yaml version was bumped** — the PR checklist requires it:

```bash
# Compare with base branch
git diff origin/main -- charts/backstage/Chart.yaml | grep '^[+-]version:'
```

</local_validation>

<deploying_to_cluster>

## Deploying to a Cluster

**OpenShift:**

```bash
CLUSTER_ROUTER_BASE=$(oc get route console -n openshift-console -o jsonpath='{.status.ingress[0].host}' | sed 's/^console-openshift-console\.//')

helm upgrade -i redhat-developer-hub charts/backstage/ \
  --set global.clusterRouterBase=$CLUSTER_ROUTER_BASE \
  --set route.enabled=true
```

**Vanilla Kubernetes:**

```bash
helm upgrade -i redhat-developer-hub charts/backstage/ \
  --set route.enabled=false \
  --set upstream.ingress.enabled=true \
  --set global.host=rhdh.127.0.0.1.sslip.io
```

</deploying_to_cluster>
