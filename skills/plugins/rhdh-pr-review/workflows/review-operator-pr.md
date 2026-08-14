# Workflow: Review rhdh-operator PR on Live Cluster

Deploy a PR's CI-built images onto a running RHDH cluster, actively verify the code changes, and report findings.

This workflow expects the PR context from `fetch-github.md` (or a future forge-specific fetch workflow). If it is not yet available, run the fetch workflow first.

<required_reading>

Read these reference files before starting:

1. `../references/operator-pr-images.md` — image naming, extraction, validation
2. `gh pr view --help` and `gh run view --help` — current forge interface

</required_reading>

<prerequisites>

| Requirement | Details |
|-------------|---------|
| **Input** | PR number for rhdh-operator (or full PR URL) |
| **Access** | Read access to `redhat-developer/rhdh-operator` |
| **Tools** | `gh` CLI authenticated, `oc` CLI available |
| **Cluster** | Running OpenShift cluster (will offer to deploy if no RHDH instance) |

</prerequisites>

<process>

## Phase 1: Use the fetched PR context

The fetched context provides `repository`, `changeRequest`, `files`, and `diff`. Extract:

```bash
REPO="redhat-developer/rhdh-operator"
PR_NUMBER=<from changeRequest.number>
```

Validate:

- PR belongs to `redhat-developer/rhdh-operator`
- PR state is `OPEN` (warn if merged or closed — images may still work but PR is not active)

The diff and changed file list are available in `diff` and `files`.

---

## Phase 2: Extract CI-Built Images

Follow `../references/operator-pr-images.md`:

1. Use `<extracting_from_pr>` to find CI-posted image URLs from the PR comments
2. Parse out the three image URLs (operator, operator-bundle, operator-catalog)
3. If no comment found, check CI workflow status using the fallback commands
4. Use `<validation>` to verify the operator image exists in the registry

---

## Phase 3: Ensure a Running RHDH Cluster

### 3.1 Verify cluster access

```bash
oc whoami 2>&1
oc cluster-info 2>/dev/null | head -2
```

### 3.2 Check for running RHDH operator

```bash
oc get deployment -A -o custom-columns=NAMESPACE:.metadata.namespace,NAME:.metadata.name \
  --no-headers 2>/dev/null | grep -i rhdh-operator
```

### 3.3 Check for Backstage CR

```bash
oc get backstage -A 2>/dev/null
```

### 3.4 Decision tree

| Cluster state | Action |
|---------------|--------|
| Operator running + Backstage CR exists | Skip to Phase 4 |
| Cluster accessible but no RHDH operator | Deploy RHDH on existing cluster (see 3.5b) |
| No cluster access (`oc whoami` fails) | Provision a cluster via rhdh-test-instance PR (see 3.5a) |

### 3.5 Provision or deploy RHDH

Use `redhat-developer/rhdh-test-instance` and read that checkout's current
README and Makefile for supported deployment commands.

- **No cluster at all** (`oc whoami` fails) → propose the rhdh-test-instance PR
  workflow: comment `/test deploy operator <version> 4h` on a PR. Match the
  version to the target branch. Before posting, state the comment as one
  operation with its exact body and target PR, get approval, then report the
  resulting workflow URL or status. The request to test does not itself approve
  the comment.
- **Cluster accessible but no RHDH** → render the exact rhdh-test-instance
  install/deploy and cleanup commands from its current README and Makefile,
  state them as operations, and run them only after approval.

Once the operator and Backstage CR are healthy, proceed to Phase 4.

---

## Phase 4: Deploy PR Operator

### 4.1 Detect install method

```bash
oc get subscription -A 2>/dev/null | grep -i rhdh
```

- If Subscription found → **OLM-managed** (use 4.4a)
- If no Subscription → **direct deployment** (use 4.4b)

### 4.2 Identify operator deployment and namespace

```bash
OPERATOR_NS_MATCHES=$(oc get deployment -A --no-headers \
  -o custom-columns=NS:.metadata.namespace,NAME:.metadata.name \
  | grep rhdh-operator | awk '{print $1}')

OPERATOR_NS_COUNT=$(printf '%s\n' "$OPERATOR_NS_MATCHES" | sed '/^$/d' | wc -l)
if [ "$OPERATOR_NS_COUNT" -ne 1 ]; then
  echo "Expected exactly 1 rhdh-operator namespace, found $OPERATOR_NS_COUNT"
  printf 'Matches:\n%s\n' "$OPERATOR_NS_MATCHES"
  exit 1
fi
OPERATOR_NS=$(printf '%s\n' "$OPERATOR_NS_MATCHES" | sed '/^$/d')

OPERATOR_DEPLOY_MATCHES=$(oc get deployment -n "$OPERATOR_NS" --no-headers \
  -o custom-columns=NAME:.metadata.name | grep rhdh-operator)

OPERATOR_DEPLOY_COUNT=$(printf '%s\n' "$OPERATOR_DEPLOY_MATCHES" | sed '/^$/d' | wc -l)
if [ "$OPERATOR_DEPLOY_COUNT" -ne 1 ]; then
  echo "Expected exactly 1 rhdh-operator deployment in $OPERATOR_NS, found $OPERATOR_DEPLOY_COUNT"
  printf 'Matches:\n%s\n' "$OPERATOR_DEPLOY_MATCHES"
  exit 1
fi
OPERATOR_DEPLOY=$(printf '%s\n' "$OPERATOR_DEPLOY_MATCHES" | sed '/^$/d')
```

### 4.3 Record current state (for rollback)

**OLM-managed — record Subscription for rollback:**

```bash
CURRENT_SUB=$(oc get subscription -n $OPERATOR_NS --no-headers \
  -o custom-columns=NAME:.metadata.name 2>/dev/null | grep rhdh)

# Record original source info (the CatalogSource is typically shared in openshift-marketplace)
ORIGINAL_SOURCE=$(oc get subscription $CURRENT_SUB -n $OPERATOR_NS \
  -o jsonpath='{.spec.source}')
ORIGINAL_SOURCE_NS=$(oc get subscription $CURRENT_SUB -n $OPERATOR_NS \
  -o jsonpath='{.spec.sourceNamespace}')
echo "Current Subscription: $CURRENT_SUB, source: $ORIGINAL_SOURCE in $ORIGINAL_SOURCE_NS"

# Export Subscription for rollback (do NOT touch the shared CatalogSource)
oc get subscription $CURRENT_SUB -n $OPERATOR_NS -o yaml > /tmp/rollback-subscription.yaml
```

**Non-OLM — save the original install.yaml for rollback:**

```bash
CURRENT_IMAGE=$(oc get deployment $OPERATOR_DEPLOY -n $OPERATOR_NS \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="manager")].image}')
echo "Current operator image: $CURRENT_IMAGE"

# Fetch the target branch's install.yaml as rollback manifest (includes CRDs, RBAC, ConfigMaps)
TARGET_BRANCH=$(gh pr view $PR_NUMBER --repo $REPO --json baseRefName --jq '.baseRefName')
curl -sL "https://raw.githubusercontent.com/redhat-developer/rhdh-operator/${TARGET_BRANCH}/dist/rhdh/install.yaml" \
  -o /tmp/rollback-install.yaml
echo "Saved rollback manifest from branch: $TARGET_BRANCH"
```

### 4.4a Deploy full bundle — OLM-managed install

Before the first `oc delete` or `oc apply`, finish rendering every manifest and
follow the write gate in `SKILL.md`. State the deletions and applies in the order
they will run, each with its namespace and resource target, the preconditions
captured, its rollout check, and the rollback or cleanup below as its failure
behaviour. Get approval, run only those operations, and report every outcome
including the skipped ones. If discovered state changes an operation, stop and
state the new set.

**IMPORTANT:** Do NOT patch the CSV image or the Deployment directly. PR changes to CRDs, RBAC, default config, or bundle metadata would be missed. Replace the CatalogSource with the PR's catalog image so OLM reinstalls the complete bundle.

**Step 1: Remove existing Subscription and CSV**

Do NOT delete the original CatalogSource — it is typically shared (e.g., `redhat-operators` in `openshift-marketplace`) and serves other operators.

```bash
PR_CATALOG_IMAGE="quay.io/rhdh-community/operator-catalog:<tag>"

# Delete Subscription first (stops OLM from managing the operator)
oc delete subscription $CURRENT_SUB -n $OPERATOR_NS

# Delete the CSV (removes the operator deployment)
CSV_NAME=$(oc get csv -n $OPERATOR_NS --no-headers \
  -o custom-columns=NAME:.metadata.name | grep rhdh)
oc delete csv $CSV_NAME -n $OPERATOR_NS
```

**Step 2: Create CatalogSource pointing to PR catalog image**

```bash
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
  name: rhdh-operator-pr-catalog
  namespace: $OPERATOR_NS
spec:
  sourceType: grpc
  image: $PR_CATALOG_IMAGE
  displayName: RHDH Operator PR Catalog
  publisher: PR Review
  updateStrategy:
    registryPoll:
      interval: 10m
EOF
```

**Step 3: Ensure OperatorGroup exists**

```bash
OG_EXISTS=$(oc get operatorgroup -n $OPERATOR_NS --no-headers 2>/dev/null | wc -l)
if [ "$OG_EXISTS" -eq 0 ]; then
  cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: rhdh-operator-group
  namespace: $OPERATOR_NS
EOF
fi
```

**Step 4: Create Subscription pointing to PR CatalogSource**

```bash
# Discover the package name and channel from the PR catalog
PACKAGE_NAME=$(oc get packagemanifest -l "catalog=rhdh-operator-pr-catalog" \
  --no-headers -o custom-columns=NAME:.metadata.name 2>/dev/null | head -1)
CHANNEL=$(oc get packagemanifest $PACKAGE_NAME \
  -o jsonpath='{.status.defaultChannel}' 2>/dev/null)

# Fall back to known defaults if discovery fails
PACKAGE_NAME=${PACKAGE_NAME:-rhdh}
CHANNEL=${CHANNEL:-fast}

cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: rhdh-operator-pr-subscription
  namespace: $OPERATOR_NS
spec:
  channel: $CHANNEL
  name: $PACKAGE_NAME
  source: rhdh-operator-pr-catalog
  sourceNamespace: $OPERATOR_NS
  installPlanApproval: Automatic
EOF
```

**Step 5: Wait for OLM to deploy the operator**

```bash
# Give OLM time to poll the CatalogSource and create the InstallPlan
echo "Waiting for OLM to process Subscription..."
sleep 30

# Wait for CSV to appear and reach Succeeded phase
echo "Waiting for CSV to succeed..."
for i in $(seq 1 6); do
  oc wait csv -n $OPERATOR_NS -l "operators.coreos.com/$PACKAGE_NAME.$OPERATOR_NS=" \
    --for=jsonpath='{.status.phase}'=Succeeded --timeout=30s 2>/dev/null && break
  echo "CSV not ready yet (attempt $i/6)..."
  sleep 10
done

# Re-detect the operator deployment name (may have changed)
OPERATOR_DEPLOY=$(oc get deployment -n $OPERATOR_NS --no-headers \
  -o custom-columns=NAME:.metadata.name | grep rhdh-operator)
```

OLM will apply the full bundle contents: updated CRDs, RBAC, default config, and the operator Deployment with the PR's operator image.

### 4.4b Deploy full manifests — direct deployment (non-OLM)

Apply the same write gate before changing a direct deployment. The rendered
install and rollback manifests are the previews the user approves; do not show
placeholders and do not regenerate the manifests after approval.

**IMPORTANT:** Do NOT use `oc set image` — it only swaps the binary and misses CRD, RBAC, and default config changes from the PR. Apply the full `install.yaml` from the PR branch instead.

**Step 1: Get the PR branch name**

```bash
PR_BRANCH=$(gh pr view $PR_NUMBER --repo $REPO --json headRefName --jq '.headRefName')
PR_IMAGE="quay.io/rhdh-community/operator:<tag>"
```

**Step 2: Fetch install.yaml from PR branch**

```bash
curl -sL "https://raw.githubusercontent.com/redhat-developer/rhdh-operator/${PR_BRANCH}/dist/rhdh/install.yaml" \
  -o /tmp/pr-install.yaml

# Verify the file was fetched successfully
if [ ! -s /tmp/pr-install.yaml ]; then
  echo "ERROR: Failed to fetch install.yaml from PR branch $PR_BRANCH"
  echo "The PR may not have regenerated dist/ — check if make build-installer was run"
fi

# Warn if the PR didn't modify dist/ — the install.yaml may be stale (base branch content)
PR_FILES=$(gh pr view $PR_NUMBER --repo $REPO --json files --jq '.files[].path')
if ! echo "$PR_FILES" | grep -q '^dist/'; then
  echo "WARNING: PR does not modify dist/ — install.yaml may not reflect this PR's changes"
  echo "CRDs, RBAC, and default config in the manifest are from the base branch"
  echo "Only the operator binary image will differ after substitution"
fi
```

**Step 3: Substitute the CI-built operator image**

```bash
sed -i "s|image: quay.io/rhdh/rhdh-rhel9-operator:.*|image: ${PR_IMAGE}|g" /tmp/pr-install.yaml

# Verify substitution
grep "image:.*operator" /tmp/pr-install.yaml
```

**Step 4: Apply the full manifests**

```bash
oc apply -f /tmp/pr-install.yaml
```

This applies the complete set of resources from the PR: CRDs, ClusterRoles, ClusterRoleBindings, ServiceAccount, ConfigMaps (including default config), and the operator Deployment.

### 4.5 Wait for rollout

```bash
# Re-detect deployment name in case it changed (OLM may use a different name)
OPERATOR_DEPLOY=$(oc get deployment -n $OPERATOR_NS --no-headers \
  -o custom-columns=NAME:.metadata.name | grep rhdh-operator)

oc rollout status deployment/$OPERATOR_DEPLOY -n $OPERATOR_NS --timeout=180s
```

### 4.6 Verify the deployment

```bash
# Confirm new image is running
oc get deployment $OPERATOR_DEPLOY -n $OPERATOR_NS \
  -o jsonpath='{.spec.template.spec.containers[?(@.name=="manager")].image}'

# Check pod is healthy
oc get pods -n $OPERATOR_NS -l control-plane=controller-manager

# Check operator logs for errors
oc logs deployment/$OPERATOR_DEPLOY -n $OPERATOR_NS --tail=20

# Check Backstage CR health
RHDH_NS=$(oc get backstage -A --no-headers 2>/dev/null | head -1 | awk '{print $1}')
if [ -n "$RHDH_NS" ]; then
  oc get backstage -n $RHDH_NS
  oc get pods -n $RHDH_NS
fi
```

### 4.7 Record rollback commands

Record rollback commands for Phase 7. Do not present them yet — they will be included in the findings report.

**OLM-managed — restore original Subscription:**

```bash
# Delete PR-specific OLM resources
oc delete subscription rhdh-operator-pr-subscription -n $OPERATOR_NS
CSV_NAME=$(oc get csv -n $OPERATOR_NS --no-headers \
  -o custom-columns=NAME:.metadata.name | grep rhdh)
oc delete csv $CSV_NAME -n $OPERATOR_NS 2>/dev/null
oc delete catalogsource rhdh-operator-pr-catalog -n $OPERATOR_NS

# Restore original Subscription (points back to the shared CatalogSource)
oc apply -f /tmp/rollback-subscription.yaml

# Wait for OLM to redeploy the original operator
oc wait csv -n $OPERATOR_NS -l "operators.coreos.com/$PACKAGE_NAME.$OPERATOR_NS=" \
  --for=jsonpath='{.status.phase}'=Succeeded --timeout=180s
```

**Non-OLM — reapply original install.yaml:**

```bash
oc apply -f /tmp/rollback-install.yaml
```

---

## Phase 5: Generate Review Checklist

Analyze the diff from Phase 1 and categorize changed files:

| File pattern | Category | Review focus |
|-------------|----------|--------------|
| `api/`, `*_types.go` | CRD/API | New fields, deprecations, backward compatibility |
| `internal/controller/`, `pkg/model/` | Controller/Reconciler | Reconciliation behavior, status updates, edge cases |
| `config/profile/`, `default-config/` | Default config | Verify defaults applied, check for regressions |
| `*_test.go`, `integration_tests/` | Tests | Run the new/modified tests |
| `.github/`, `Makefile`, `Dockerfile` | Build/CI | Verify builds still work |
| `docs/`, `*.md` | Documentation | Review for accuracy |
| `go.mod`, `go.sum` | Dependencies | Check for major version bumps |

### Generate the checklist

For each category with changes, generate specific verification items.

**Always include these baseline checks:**

```markdown
### Baseline Checks
- [ ] Operator pod started successfully with PR image (no crash loops)
- [ ] Operator logs show no errors (`oc logs deployment/$OPERATOR_DEPLOY -n $OPERATOR_NS --tail=50`)
- [ ] Existing Backstage CR reconciled without errors
- [ ] RHDH pods are running and healthy
```

**CRD/API changes — add:**

```markdown
### CRD/API Verification
- [ ] Apply a Backstage CR with the new/changed field(s) set
- [ ] Apply a Backstage CR without the new field(s) — verify backward compatibility
- [ ] Verify existing CRs still reconcile correctly after CRD update
- [ ] Check `oc explain backstage.spec.<new-field>` shows correct schema
```

**Controller/Reconciler changes — add:**

```markdown
### Controller Verification
- [ ] Check operator logs during reconciliation for the changed code paths
- [ ] Verify status conditions update correctly on the Backstage CR
- [ ] Test with multiple Backstage CRs (if applicable)
- [ ] Delete and recreate a Backstage CR — verify clean reconciliation
```

**Default config changes — add:**

```markdown
### Default Config Verification
- [ ] Deploy a fresh Backstage CR with defaults only
- [ ] Verify changed defaults are applied to the RHDH deployment
- [ ] Compare pod spec / configmaps before and after the change
```

**Test changes — add:**

```markdown
### Tests
- [ ] `make test` — unit tests pass
- [ ] `make integration-test USE_EXISTING_CLUSTER=true USE_EXISTING_CONTROLLER=true` — integration tests pass against live cluster
```

**Dependency changes — add:**

```markdown
### Dependency Review
- [ ] Review `go.mod` diff for major version bumps
- [ ] Check if new dependencies have acceptable licenses
```

**End the checklist with:**

```markdown
### Rollback
When done testing, rollback the operator image:
[rollback commands from Phase 4.7]
```

---

## Phase 6: Active Verification

**This phase verifies the PR's specific code changes on the cluster — not generic health checks.** The goal is to exercise the exact code paths the PR modified and capture evidence that the behavioral change works as intended.

### 6.1 Analyze the diff

Read the diff hunks from Phase 1. For each changed file, understand:

- What the code did **before** the change
- What it does **after**
- What behavioral difference this introduces on a running cluster

Map each changed code path to a concrete cluster-observable effect — something you can trigger and measure on the running cluster. If a code change has no cluster-observable effect (e.g., pure refactor with identical behavior), state that explicitly and explain why.

### 6.2 Propose a verification mutation plan

For each test, specify:

- **What to do**: the exact cluster action (create resource, edit CR, delete pod, etc.)
- **What to observe**: where to look (logs, pod spec, CR status, events, API response)
- **Pass criteria**: what output means the fix works
- **Fail criteria**: what output means the fix is broken

State every cluster-changing action as an operation under the write gate in
`SKILL.md`; read-only observations stay checks. Give each one its exact resource,
payload preview, preconditions, pass and fail criteria, and recovery. **STOP. Do
not run a changing verification command until the user approves that stated
set.**

### 6.3 Execute

Only after the user approves the stated operations:

Run each verification step on the cluster. For every step, capture the actual command output as evidence. Do not summarize — show the raw output so the user can see exactly what happened.

---

## Phase 7: Findings & Recommendations

Synthesize the verification results and provide a complete review assessment.

### 7.1 Verification summary

Summarize what was tested and the results:

| Category | Test performed | Result | Evidence |
|---|---|---|---|
| *[category]* | *[what was tested]* | Pass/Fail | *[key observation]* |

### 7.2 Best practice assessment

Review the PR's approach against the checked-out operator repository's current
controllers, CRDs, tests, and contributor guidance:

- Does the change follow the existing reconciliation flow pattern (preprocess → init model → apply → cleanup → status)?
- Are status conditions updated appropriately for new features or error cases?
- Are new ConfigMap/Secret references watched via `rhdh.redhat.com/ext-config-sync` label?
- Is error handling consistent with existing controller patterns (wrapped errors, retryable vs terminal)?
- Are new CRD fields documented with appropriate kubebuilder markers?
- Does the code avoid non-deterministic iteration patterns (sorted keys, stable ordering)?

### 7.3 Security review

Evaluate the changes from a security perspective:

- Are new environment variables or secrets handled safely (no plaintext logging, proper RBAC)?
- Do RBAC changes follow least-privilege principle?
- Are container image references pinned by digest where appropriate?
- Are new network exposures (ports, routes, service accounts) intentional and documented?
- Do dependency updates (`go.mod`) introduce known CVEs?
- Are user-supplied inputs validated before use in resource names or labels?

### 7.4 Improvement suggestions

Based on the findings, suggest concrete improvements if any:

- Code changes needed (reference specific files and lines from the diff)
- Missing test coverage for the changed code paths
- Documentation gaps
- Configuration or operational concerns

### 7.5 Rollback instructions

Present the rollback commands recorded in Phase 4.7:

**OLM-managed — restore original Subscription:**

```bash
# Delete PR-specific OLM resources
oc delete subscription rhdh-operator-pr-subscription -n $OPERATOR_NS
CSV_NAME=$(oc get csv -n $OPERATOR_NS --no-headers \
  -o custom-columns=NAME:.metadata.name | grep rhdh)
oc delete csv $CSV_NAME -n $OPERATOR_NS 2>/dev/null
oc delete catalogsource rhdh-operator-pr-catalog -n $OPERATOR_NS

# Restore original Subscription (points back to the shared CatalogSource)
oc apply -f /tmp/rollback-subscription.yaml

# Wait for OLM to redeploy the original operator
oc wait csv -n $OPERATOR_NS -l "operators.coreos.com/$PACKAGE_NAME.$OPERATOR_NS=" \
  --for=jsonpath='{.status.phase}'=Succeeded --timeout=180s
```

**Non-OLM — reapply original install.yaml:**

```bash
oc apply -f /tmp/rollback-install.yaml
```

</process>

<action_triggers>

| Trigger | Type | What | Resume When |
|---------|------|------|-------------|
| No CI images found | Wait | CI workflow may still be running | Workflow completes and posts comment |
| Images expired | Stop | PR images past 14-day TTL | Author pushes new commit to retrigger CI |
| No cluster access | Stop | User needs to `oc login` | User logs in and re-runs skill |
| No RHDH instance | State, then deploy | State the exact rhdh-test-instance deployment and cleanup operations; run them only after approval | Reported outcomes show the operator and Backstage CR running |

</action_triggers>

## What this workflow reports

Report the subject tested, one result per check, and the overall verdict. Add the
deployed bundle or manifests, the original and final cluster state, the findings,
the rollback commands, and the cleanup status. Report the outcome of every
deployment, verification, and cleanup operation the user approved. Do not cache
cluster state inside the skill directory.

<success_criteria>

Review is complete when:

- [ ] PR images identified from CI comment
- [ ] Images validated as existing in Quay registry
- [ ] Cluster has RHDH operator deployed from PR bundle/manifests (not just image swap)
- [ ] Operator pod is healthy (no crash loops)
- [ ] Backstage CR reconciles successfully
- [ ] Review checklist generated from diff analysis
- [ ] Active-verification operations stated and approved by user
- [ ] Verification executed with evidence captured
- [ ] Findings summary with pass/fail
- [ ] Best practice and security assessment completed
- [ ] Rollback instructions documented and shared with user
- [ ] Check results and cleanup status reported
- [ ] Every external write has a reported outcome naming its target

</success_criteria>
