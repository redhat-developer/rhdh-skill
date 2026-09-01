---
name: rhdh-smoke-tests
description: >-
  Walks RHDH Helm and Operator smoke tests in one namespace each:
  install the previous GA, upgrade to this RC, then if this stream is not the
  newest, upgrade to the latest GA of the next minor. Enables Guest via Helm
  upstream.backstage.appConfig or an Operator ConfigMap, then verifies pods,
  Guest sign-in, and the extensions packages API. Use for "run the helm smoke
  tests", "operator RC smoke", "upgrade 1.10.3 to 1.10.4 RC", "1.9.8 to 1.9.9
  then 1.10", "GA smoke test", or "SMOKE_TESTS helm and operator".
compatibility: "oc, helm, curl, and python3; a dedicated smoke kubeconfig (not Konflux or OpenShift CI)."
---

# RHDH Helm and Operator smoke tests

Smoke test after an RC (Quay CI chart / IIB). Helm **and** Operator are both
mandatory. One Helm namespace and one Operator namespace — the three checks are
a chain in that namespace, not three installs.

This is not full QE, Prow e2e, local compose, or an operator-PR catalog test.

## Route

1. Collect tags and `KUBECONFIG`. Stop if either is missing — do not invent CI tags.
2. Default is an **RC** run. A **GA** run (published chart / OperatorHub `fast`,
   including `fast` ↔ `fast-1.y`) only when the user asked for GA.
3. Load `workflows/helm.md` for the Helm chain, `workflows/operator.md` for the
   Operator chain.
4. After every install or upgrade: Guest (below), then verify (below).

| Load when | File |
|---|---|
| Helm chain | `workflows/helm.md` |
| Operator chain | `workflows/operator.md` |
| Guest fragment | `assets/app-config-guest.yaml` |
| Helm Guest overlay | `assets/helm-values-guest.yaml` |

`SKILL_DIR` is the directory that contains this `SKILL.md`.

Always **print** the next statement and snippet. Run `oc`/`helm` only when the
user says to run it. Then follow `/mutation-gate` for **one step** (one install
or one upgrade), not the whole chain.

## The chain (same namespace)

Three checks, one Helm release / one Backstage CR:

1. **Install previous GA** — published chart or OperatorHub `fast`. Verify.
2. **Upgrade to this RC** — Quay `*-CI` chart or IIB. Verify.
3. **Higher-stream** — only when this RC is **not** already the newest stream:
   upgrade to the **latest published GA of the next minor** (for example `1.10.z`,
   not a skip to 2.0). Verify.

Examples:

- Testing **1.10.4 RC** (newest stream): install `1.10.3` GA, upgrade to `1.10.4`
  RC. Skip step 3.
- Testing **1.9.9 RC** (older stream): install `1.9.8` GA, upgrade to `1.9.9` RC,
  then upgrade to latest `1.10.z` GA.

Leave the namespace in place after the chain so it can be inspected.

Operator OLM Subscription is cluster-wide (`rhdh-operator`). Helm and Operator
chains can share a cluster; do not run two Operator CSV targets at once.

## Shared setup

```bash
export KUBECONFIG=/path/to/smoke.kubeconfig
oc whoami

# tags from Slack / Quay / charts.openshift.io — do not guess
PREV_GA=1.10.3
RC_CHART=1.10-NNN-CI
RC_VER=1.10.4
STREAM=1.10
NEXT_GA=            # e.g. 1.10.3 when testing 1.9.9; omit if this stream is newest
NEXT_STREAM=        # e.g. 1.10 when testing 1.9
NS_HELM=rhdh-${STREAM}-helm
NS_OP=rhdh-${STREAM}-op
```

## Guest enablement

Guest is off by default. Apply after every install or upgrade, before verify.

**Helm — `upstream.backstage.appConfig`.** Pass
`"${SKILL_DIR}/assets/helm-values-guest.yaml"` on the install and on every
`helm upgrade --reuse-values`. Do not `oc create configmap` and do not use
`extraAppConfig`.

**Operator — ConfigMap + Backstage CR.** Apply once; it survives CSV upgrades.

```bash
oc -n "${NS_OP}" create configmap app-config-guest \
  --from-file=app-config-guest.yaml="${SKILL_DIR}/assets/app-config-guest.yaml" \
  --dry-run=client -o yaml | oc apply -f -
CR_NAME=$(oc -n "${NS_OP}" get backstage -o jsonpath='{.items[0].metadata.name}')
oc -n "${NS_OP}" patch backstage "${CR_NAME}" --type merge -p \
  '{"spec":{"application":{"appConfig":{"configMaps":[{"name":"app-config-guest"}]}}}}'
```

## Verify

`scripts/verify_ns.sh --namespace "${NS}"` after Guest. Fail on
`ImagePullBackOff`, `CrashLoopBackOff`, `OOMKilled`, or 401/403 in
`install-dynamic-plugins`. 504 right after install = still starting.

Packages API must list **~100+** packages (`disabled: true` entries are OK).
UI: Administration → Extensions → Catalog must not be empty.

## Gotchas

- Empty Operator CatalogSource: wait for a new IIB; do not proceed.
- GA images must be `registry.redhat.io/rhdh/…`. Quay `*-CI` after a "GA" step
  means the install is still on RC tags.
- Helm Guest via `extraAppConfig` fights the chart-generated `appConfig`.

## Completion

Report Helm and Operator separately. For each, list steps 1–3 as pass, fail, or
skipped (step 3 N/A on the newest stream), with the **one** namespace used.
Name the Guest method (Helm `appConfig` vs Operator ConfigMap). A step that
never ran because an earlier write was refused is skipped, not omitted.
