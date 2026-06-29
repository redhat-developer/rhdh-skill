# Workflow: Review rhdh-chart PR on Live Cluster

Check out a PR's chart changes, validate locally, deploy the full chart to a running RHDH cluster, and generate a targeted review checklist from the diff.

<required_reading>

Read these reference files before starting:

1. `../references/shared-pr-fetch.md` — Shared Phase 1 (PR context fetching)
2. `../references/shared-verification.md` — Shared Phase 6 (active verification)
3. `../references/shared-findings-structure.md` — Shared Phase 7 (findings structure)
4. `../references/chart-pr-testing.md` — Chart CI behavior, local validation, deployment commands
5. `../../rhdh/references/github-reference.md` — gh CLI patterns

</required_reading>

<prerequisites>

| Requirement | Details |
|-------------|---------|
| **Input** | PR number for rhdh-chart (or full PR URL) |
| **Access** | Read access to `redhat-developer/rhdh-chart` |
| **Tools** | `gh` CLI authenticated, `helm` CLI available, `oc` or `kubectl` available |
| **Cluster** | Running OpenShift or Kubernetes cluster (will offer to deploy if no RHDH instance) |

</prerequisites>

<process>

## Phase 1: Fetch PR Context

```bash
REPO="redhat-developer/rhdh-chart"
PR_NUMBER=<number>
```

Read `../references/shared-pr-fetch.md` and follow the `<fetch_pr>` instructions using the `REPO` and `PR_NUMBER` variables above.

---

## Phase 2: Local Chart Validation

Chart CI does NOT build container images — it runs `ct lint` + `ct install` on KIND. To test on a real cluster, check out the PR branch and validate locally first.

### 2.1 Check out the PR branch

```bash
# Use an existing rhdh-chart clone if available, otherwise clone fresh
CHART_DIR=""
for candidate in "../rhdh-chart" "$HOME/rhdh-chart" "$HOME/src/rhdh-chart"; do
  if [ -d "$candidate/.git" ]; then
    CHART_DIR="$candidate"
    break
  fi
done

if [ -z "$CHART_DIR" ]; then
  gh repo clone $REPO /tmp/rhdh-chart-pr-$PR_NUMBER
  CHART_DIR="/tmp/rhdh-chart-pr-$PR_NUMBER"
fi

cd "$CHART_DIR"
PR_BRANCH=$(gh pr view $PR_NUMBER --repo $REPO --json headRefName --jq '.headRefName')
git fetch origin $PR_BRANCH
git checkout FETCH_HEAD
```

### 2.2 Update Helm dependencies

Follow the dependency update steps in `../references/chart-pr-testing.md` (`<getting_pr_chart>` section):

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null
helm dependency update charts/backstage
```

### 2.3 Validate chart rendering

```bash
helm template rhdh charts/backstage/ --debug 2>&1 | head -50
```

If `helm template` fails, the chart has rendering errors that must be fixed before deployment.

### 2.4 Check Chart.yaml version bump

The PR checklist requires a version bump for each changed chart:

```bash
TARGET_BRANCH=$(gh pr view $PR_NUMBER --repo $REPO --json baseRefName --jq '.baseRefName')
git diff origin/$TARGET_BRANCH -- charts/backstage/Chart.yaml | grep '^[+-]version:'
```

If no version change is found, flag it — the PR checklist explicitly requires a bump per Semantic Versioning.

### 2.5 Check pre-commit hooks (optional)

If `pre-commit` is available:

```bash
pre-commit run --all-files 2>&1
```

This validates:
- `README.md` is regenerated (helm-docs)
- `values.schema.json` is regenerated (jsonschema-dereference)
- Helm dependencies are up to date

---

## Phase 3: Ensure a Running RHDH Cluster

### 3.1 Verify cluster access

```bash
# Try OpenShift first, fall back to kubectl
oc whoami 2>&1 || kubectl cluster-info 2>/dev/null | head -2
```

### 3.2 Check for existing RHDH Helm release

```bash
helm list -A 2>/dev/null | grep -E 'backstage|rhdh|redhat-developer-hub'
```

### 3.3 Check for existing RHDH pods

```bash
# kubectl works on both OCP and vanilla K8s
kubectl get pods -A --no-headers 2>/dev/null | grep -i backstage
```

### 3.4 Decision tree

| Cluster state | Action |
|---------------|--------|
| Helm release exists + RHDH pods running | Skip to Phase 4 |
| Cluster accessible but no RHDH | Deploy RHDH via Helm on existing cluster (see 3.5) |
| No cluster access | Provision a cluster via rhdh-test-instance (see 3.5) |

### 3.5 Provision or deploy RHDH

Use `redhat-developer/rhdh-test-instance` — see `../../rhdh/references/rhdh-repos.md` for its capabilities, Makefile targets, and `/test deploy` slash commands. Read the repo's own README for full usage.

- **No cluster at all** → use rhdh-test-instance PR workflow: comment `/test deploy helm <version> 4h` on a PR. Use a 4h TTL (reviews are short-lived). Match the version to the PR's target branch.
- **Cluster accessible but no RHDH** → use rhdh-test-instance locally: `make deploy-helm VERSION=<version>`. Read the repo's README for `.env` setup.

Once RHDH pods are running, proceed to Phase 4.

---

## Phase 4: Deploy PR Chart

### 4.1 Detect existing install method

```bash
# Check if current RHDH was deployed via Helm
HELM_RELEASE=$(helm list -A --no-headers 2>/dev/null | grep -E 'backstage|rhdh|redhat-developer-hub' | awk '{print $1}')
HELM_NS=$(helm list -A --no-headers 2>/dev/null | grep -E 'backstage|rhdh|redhat-developer-hub' | awk '{print $2}')

# Check if deployed via operator instead
OLM_MANAGED=$(oc get subscription -A 2>/dev/null | grep -i rhdh)
```

- If Helm release found → proceed with `helm upgrade` (use 4.3)
- If OLM-managed (operator) → warn: "This cluster has RHDH deployed via operator. Use the `review-operator-pr` workflow instead, or install a separate Helm-based RHDH in a different namespace."

### 4.2 Record current state (for rollback)

```bash
HELM_REVISION=$(helm history $HELM_RELEASE -n $HELM_NS --max 1 --no-headers 2>/dev/null | awk '{print $1}')
echo "Current Helm release: $HELM_RELEASE in namespace $HELM_NS, revision $HELM_REVISION"

# Save current values for reference
helm get values $HELM_RELEASE -n $HELM_NS -o yaml > /tmp/rollback-chart-values.yaml
echo "Saved current values to /tmp/rollback-chart-values.yaml"
```

### 4.3 Deploy PR chart from local checkout

**IMPORTANT:** Deploy the full chart from the PR branch — not just a values override. PR changes to templates, helpers, schema, or dependencies are baked into the chart itself. A values-only change would miss them.

**OpenShift:**

```bash
CLUSTER_ROUTER_BASE=$(oc get route console -n openshift-console \
  -o jsonpath='{.status.ingress[0].host}' | sed 's/^console-openshift-console\.//')

helm upgrade $HELM_RELEASE "$CHART_DIR/charts/backstage/" \
  -n $HELM_NS \
  --set global.clusterRouterBase=$CLUSTER_ROUTER_BASE \
  --set route.enabled=true \
  --reuse-values
```

**Vanilla Kubernetes:**

```bash
helm upgrade $HELM_RELEASE "$CHART_DIR/charts/backstage/" \
  -n $HELM_NS \
  --set route.enabled=false \
  --set upstream.ingress.enabled=true \
  --set global.host=rhdh.127.0.0.1.sslip.io \
  --reuse-values
```

The `--reuse-values` flag preserves any existing user configuration (dynamic plugins, app-config, secrets) while applying the PR's chart changes (templates, defaults, schema).

**Fallback:** If the upgrade fails because the PR introduces new required values or renames existing ones, retry with `--reset-values` instead of `--reuse-values`. This starts from the chart's default values — you'll need to re-supply any custom configuration via `--set` or `-f values-override.yaml`.

### 4.4 Wait for rollout

```bash
# Wait for the RHDH deployment to roll out
RHDH_DEPLOY=$(kubectl get deployment -n $HELM_NS --no-headers \
  -o custom-columns=NAME:.metadata.name 2>/dev/null | grep -E 'backstage|rhdh')

kubectl rollout status deployment/$RHDH_DEPLOY -n $HELM_NS --timeout=300s
```

### 4.5 Verify the deployment

```bash
# Check pods are running
kubectl get pods -n $HELM_NS

# Check RHDH is accessible
RHDH_URL=""
# OpenShift: check route
ROUTE_HOST=$(oc get route -n $HELM_NS --no-headers -o custom-columns=HOST:.spec.host 2>/dev/null | head -1)
if [ -n "$ROUTE_HOST" ]; then
  RHDH_URL="https://$ROUTE_HOST"
fi

# Kubernetes: check ingress
if [ -z "$RHDH_URL" ]; then
  INGRESS_HOST=$(kubectl get ingress -n $HELM_NS --no-headers -o custom-columns=HOST:.spec.rules[0].host 2>/dev/null | head -1)
  if [ -n "$INGRESS_HOST" ]; then
    RHDH_URL="http://$INGRESS_HOST"
  fi
fi

if [ -n "$RHDH_URL" ]; then
  echo "RHDH accessible at: $RHDH_URL"
  curl -sI "$RHDH_URL" | head -5
fi

# Check logs for startup errors
kubectl logs deployment/$RHDH_DEPLOY -n $HELM_NS --tail=20
```

### 4.6 Record rollback commands

Record for Phase 7. Do not present them yet.

```bash
helm rollback $HELM_RELEASE $HELM_REVISION -n $HELM_NS
```

---

## Phase 5: Generate Review Checklist

Analyze the diff from Phase 1 and categorize changed files:

| File pattern | Category | Review focus |
|-------------|----------|--------------|
| `charts/backstage/templates/` | Helm Templates | Resource definitions, conditionals, helper usage |
| `values.yaml` | Values/Config | Default values, breaking changes, schema alignment |
| `values.schema.tmpl.json`, `values.schema.json` | JSON Schema | OpenShift form compatibility, required fields |
| `Chart.yaml`, `Chart.lock` | Chart Metadata | Version bump, dependency updates |
| `charts/backstage/vendor/` | Upstream Subchart | Upstream sync, compatibility with wrapper chart |
| `charts/backstage/templates/tests/` | Chart Tests | Helm test coverage |
| `ct-*.yaml`, `.pre-commit-config.yaml` | CI/Tooling | Lint and test config changes |
| `.github/workflows/` | Build/CI | Workflow changes, release triggers |
| `docs/`, `README.md`, `*.gotmpl` | Documentation | Accuracy, helm-docs template sync |
| `.rhdh/` | RHDH-specific | Install scripts, CI integration |
| `charts/must-gather/`, `charts/orchestrator-*` | Other Charts | Separate chart changes (non-backstage) |

### Generate the checklist

For each category with changes, generate specific verification items.

**Always include these baseline checks:**

```markdown
### Baseline Checks
- [ ] RHDH pods started successfully with PR chart (no crash loops)
- [ ] RHDH logs show no errors (`kubectl logs deployment/$RHDH_DEPLOY -n $HELM_NS --tail=50`)
- [ ] RHDH UI is accessible via route/ingress
- [ ] Dynamic plugins init container completed successfully
```

**Template changes — add:**

```markdown
### Template Verification
- [ ] `helm template` renders without errors
- [ ] Changed templates produce correct Kubernetes resources (`helm template | kubectl apply --dry-run=client -f -`)
- [ ] Conditional logic handles both enabled and disabled paths
- [ ] Helper functions in `_helpers.tpl` are used consistently
- [ ] Network policies (if changed) allow required traffic
```

**Values/Config changes — add:**

```markdown
### Values Verification
- [ ] New values have sensible defaults in `values.yaml`
- [ ] Values are documented with `# --` comments (helm-docs format)
- [ ] Existing values are backward compatible (no breaking renames)
- [ ] `upstream:` prefixed values correctly pass through to subchart
- [ ] Dynamic plugin configuration works (`global.dynamic.plugins`)
```

**JSON Schema changes — add:**

```markdown
### Schema Verification
- [ ] `values.schema.tmpl.json` template is updated (not just the generated file)
- [ ] `pre-commit run jsonschema-dereference` regenerates `values.schema.json` cleanly
- [ ] Schema validates against actual values.yaml defaults
- [ ] OpenShift console form renders correctly with new schema fields
```

**Chart metadata changes — add:**

```markdown
### Chart Metadata
- [ ] Chart version bumped in `Chart.yaml` per Semantic Versioning
- [ ] Dependency versions are compatible (`Chart.lock` updated)
- [ ] `kubeVersion` constraint is correct
```

**Upstream subchart changes — add:**

```markdown
### Upstream Subchart
- [ ] Changes in `vendor/backstage/` are from an upstream sync (not manual edits)
- [ ] Wrapper chart values still override subchart correctly
- [ ] Custom templates don't conflict with upstream template names
```

**Documentation changes — add:**

```markdown
### Documentation
- [ ] `README.md` is regenerated via `pre-commit run helm-docs`
- [ ] `README.md.gotmpl` template is updated if new sections are needed
- [ ] Docs reflect the actual values and defaults
```

**End the checklist with:**

```markdown
### Rollback
When done testing, rollback the chart:
[rollback command from Phase 4.6]
```

---

## Phase 6: Active Verification

Typical chart verification actions: apply values overrides, check rendered resources, curl endpoints, verify ConfigMap data, test toggle behavior (enabled/disabled), check network policies.

Read `../references/shared-verification.md` and follow the `<verification_process>` instructions, applying them to the specific chart changes in this PR.

---

## Phase 7: Findings & Recommendations

Read `../references/shared-findings-structure.md` and follow the `<findings_structure>` instructions, using the chart-specific context below.

### Chart best-practice bullets (for 7.2)

- Does the change follow the subchart architecture (upstream values under `upstream:` key)?
- Are dynamic plugin configurations handled via `global.dynamic.includes` / `global.dynamic.plugins`?
- Is Route vs Ingress detection handled correctly for both OpenShift and vanilla K8s?
- Are backend auth secrets auto-generated when `global.auth.backend.enabled: true`?
- Do new values follow the existing naming conventions and nesting patterns?
- Is the `_helpers.tpl` used for reusable template logic instead of inline duplication?
- Are values documented with `# --` comments so helm-docs generates correct README?

### Chart security bullets (for 7.3)

- Are secrets handled safely (no plaintext in values.yaml defaults, proper Secret resources)?
- Are new network policies restrictive enough?
- Do new ServiceAccount configurations avoid unnecessary permissions?

### Chart rollback commands (for 7.5)

```bash
helm rollback $HELM_RELEASE $HELM_REVISION -n $HELM_NS
helm history $HELM_RELEASE -n $HELM_NS --max 3
kubectl rollout status deployment/$RHDH_DEPLOY -n $HELM_NS --timeout=300s
```

</process>

<action_triggers>

| Trigger | Type | What | Resume When |
|---------|------|------|-------------|
| `helm template` fails | Stop | Chart has rendering errors | PR author fixes template syntax |
| Chart.yaml version not bumped | Warn | PR checklist requires version bump | Author updates Chart.yaml |
| No cluster access | Stop | User needs to `oc login` or configure kubeconfig | User logs in and re-runs skill |
| No RHDH Helm release | Deploy | Deploy RHDH via rhdh-test-instance `make deploy-helm` | RHDH pods are running |
| OLM-managed RHDH found | Redirect | Wrong deployment type for chart review | Use `review-operator-pr` workflow or deploy Helm-based RHDH in separate namespace |

</action_triggers>

<tracking>

## Activity Logging

```bash
$RHDH log add "Review PR #<number> (rhdh-chart): deployed PR chart from branch <branch>, generated checklist" \
  --tag review-pr --tag rhdh-chart

$RHDH log add "PR #<number> active verification: <categories tested>, results: <pass/fail summary>" \
  --tag review-pr --tag rhdh-chart

$RHDH log add "PR #<number> review findings: <summary>" \
  --tag review-pr --tag rhdh-chart
```

## Follow-up Todos

```bash
$RHDH todo add "Follow up on PR #<number> finding: <description>" --context "review-pr"

$RHDH todo add "Rollback chart on cluster after PR #<number> review" --context "review-pr"
```

</tracking>

<success_criteria>

Review is complete when:

- [ ] PR branch checked out and Helm dependencies updated
- [ ] Local validation passed (`helm template`, Chart.yaml version bump check)
- [ ] Cluster has RHDH deployed from PR chart (full chart, not just values override)
- [ ] RHDH pods are running and healthy (no crash loops)
- [ ] RHDH UI is accessible via route/ingress
- [ ] Review checklist generated from diff analysis
- [ ] Active verification plan proposed and accepted by user
- [ ] Verification executed with evidence captured
- [ ] Findings summary with pass/fail
- [ ] Best practice and security assessment completed
- [ ] Rollback instructions documented and shared with user
- [ ] Activity logged

</success_criteria>
