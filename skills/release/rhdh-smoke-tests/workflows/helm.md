# Helm smoke chain

One namespace, one release `redhat-developer-hub`. After every snippet: Guest
values file on the same `helm` command (or a follow-up `--reuse-values -f`),
then verify.

```bash
helm repo add openshift-helm-charts https://charts.openshift.io/
helm repo update
NS="${NS_HELM}"
```

Fail the chain if an upgrade rolls back, CrashLoops, or Guest/catalog breaks.

## RC (default)

### 1. Install previous GA

```bash
helm install redhat-developer-hub openshift-helm-charts/redhat-developer-hub \
  --version "${PREV_GA}" --namespace "${NS}" --create-namespace \
  -f "${SKILL_DIR}/assets/helm-values-guest.yaml"
```

Then verify.

### 2. Upgrade to this RC

```bash
helm upgrade redhat-developer-hub oci://quay.io/rhdh/chart --version "${RC_CHART}" \
  -n "${NS}" --reuse-values -f "${SKILL_DIR}/assets/helm-values-guest.yaml"
oc -n "${NS}" rollout status deploy/redhat-developer-hub
```

Then verify. Images may be Quay `*-CI` on this step.

### 3. Higher-stream (older branch only)

Skip when this RC is already the newest stream. Target the latest **published**
next-minor GA (`${NEXT_GA}`), not a next-minor CI tag.

```bash
helm upgrade redhat-developer-hub openshift-helm-charts/redhat-developer-hub \
  --version "${NEXT_GA}" -n "${NS}" --reuse-values \
  -f "${SKILL_DIR}/assets/helm-values-guest.yaml"
oc -n "${NS}" rollout status deploy/redhat-developer-hub
```

Then verify. Images must be `registry.redhat.io/rhdh/…`.

## GA run (only if asked)

Same three steps in `${NS_HELM}`. Step 2 uses `--version "${RC_VER}"` from
`openshift-helm-charts/redhat-developer-hub` instead of `oci://quay.io/rhdh/chart`.
Every step must pull `registry.redhat.io/rhdh/…`.
