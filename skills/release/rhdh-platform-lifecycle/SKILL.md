---
name: rhdh-platform-lifecycle
description: >-
  Reports vendor support phases and end-of-life dates for RHDH and the platforms
  it runs on: OpenShift, ARO, OSD, ROSA, AKS, EKS, GKE, PostgreSQL, Red Hat build
  of Keycloak, and Quay. Use for "is OCP 4.16 still supported", "when does
  PostgreSQL 15 go EOL", "which Kubernetes version should AKS be on", "which OCP
  versions does RHDH 1.10 support", or an RHBK or Quay lifecycle lookup. Product
  lifecycle only — RHDH milestone dates such as Code Freeze belong to
  rhdh-release-schedule.
compatibility: "Python 3.9+; uv for PEP 723 YAML-backed scripts; gh for remote openshift/release access."
---

# RHDH platform support

Produce lifecycle facts without changing repositories or external systems.

## Route

| Question | Load | Run |
|---|---|---|
| RHDH support and compatible OCP versions | `workflows/check-rhdh.md` | `scripts/check_rhdh_lifecycle.py` |
| OpenShift support phases | `workflows/check-ocp.md` | `scripts/check_ocp_lifecycle.py` |
| Azure AKS support and configured versions | `workflows/check-aks.md` | `scripts/check_aks_lifecycle.py` |
| AWS EKS support and configured versions | `workflows/check-eks.md` | `scripts/check_eks_lifecycle.py` |
| Google GKE support | `workflows/check-gke.md` | `scripts/check_gke_lifecycle.py` |
| PostgreSQL support | `workflows/check-pg.md` | `scripts/check_pg_lifecycle.py` |
| RHBK, Quay, or another Red Hat product | `workflows/check-redhat.md` | `scripts/check_lifecycle.py` |

Load one workflow. Use the bundled script for deterministic retrieval and
classification; add judgment only after its output is available.

## What to report

Report, for the product asked about and the date the answer was produced:

- each version with the support phase and the source date the script returned;
- versions found only in `openshift/release`, labelled configured, never supported;
- the RHDH-to-platform compatibility pairs, where the script emits them;
- every endpoint the answer rests on;
- every version the script could not classify, as a warning.

Preserve the script's source dates and uncertainty. Distinguish vendor lifecycle
from versions merely configured in `openshift/release`. Do not infer that a
configured version is supported.

## Composition

Other skills invoke `/rhdh-platform-lifecycle` by name and use what it reports.
`rhdh_lifecycle` is a private, local adapter: no other skill imports it or
locates this skill on disk, and all repository and YAML access stays behind it.

## Completion

Complete when every product and version named in the request carries the support
phase and the source date the script returned, the answer names each endpoint it
rests on, and every version the script could not classify is reported as a
warning rather than dropped or estimated. A version found only in
`openshift/release` is reported as configured and never as supported. If a
lifecycle source was unreachable, name the product that remains unassessed
instead of returning the partial list as the answer.
