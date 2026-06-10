---
name: prow
description: >-
  Manage Prow CI job configurations for RHDH in the openshift/release
  repository. List, generate, add, and remove OCP test entries and cluster
  pools. List K8s platform test entries (AKS, EKS, GKE). Analyze OCP
  version coverage gaps. Commission new release branches and decommission
  end-of-life ones. Use when working with RHDH CI config, Prow jobs,
  cluster pools, or openshift/release CI management.
---
# RHDH Prow CI Management

Manage Prow CI job configurations for RHDH in the `openshift/release` repository.

## Prerequisites

- Python 3.9+
- For listing: works from any directory (auto-detects local checkout or uses GitHub API)
- For generating/modifying: requires a local `openshift/release` checkout

## Important: Branch Terminology

**"Branch" refers to the RHDH product branch** encoded in the config filename (e.g., `main`, `release-1.8`), **NOT** a git branch in `openshift/release`. All CI config files live on the `main` git branch.

## Identify Task

What CI management task do you need?

| Query matches | Workflow |
|---|---|
| "OCP test", "OCP job", "e2e-ocp", "add OCP version", "new OCP test" | `workflows/ocp-jobs.md` |
| "cluster pool", "ClusterPool", "Hive pool" | `workflows/ocp-pools.md` |
| "coverage", "gap analysis", "what OCP versions are missing" | `workflows/ocp-coverage.md` |
| "AKS test", "EKS test", "GKE test", "K8s platform jobs" | `workflows/k8s-jobs.md` |
| "commission", "new release branch", "create release branch CI", "onboard release", "add release branch" | `workflows/commission-release.md` |
| "decommission", "EOL release", "remove release branch", "clean up old release" | `workflows/decommission-release.md` |

After reading the workflow, follow it exactly.

## Available Scripts

All listing scripts support `--repo-dir` to override the openshift/release location and work in both local and remote (GitHub API) modes.

| Script | Purpose |
|--------|---------|
| `scripts/list_ocp_test_configs.py` | List OCP test entries per branch |
| `scripts/generate_test_entry.py` | Generate a new OCP test entry YAML block |
| `scripts/list_cluster_pools.py` | List RHDH Hive ClusterPool configurations |
| `scripts/generate_cluster_pool.py` | Generate a new ClusterPool YAML file |
| `scripts/analyze_coverage.py` | Cross-reference coverage against lifecycle data |
| `scripts/list_aks_jobs.py` | List AKS test entries |
| `scripts/list_eks_jobs.py` | List EKS test entries |
| `scripts/list_gke_jobs.py` | List GKE test entries |

## After Any Change

Always run `make update` after modifying CI config files:

```bash
make update
```

This regenerates Prow job configs in `ci-operator/jobs/` and `zz_generated_metadata` sections.

## Related Skills

- **`lifecycle`**: Provides repo resolution, YAML I/O, and lifecycle data.
  The `rhdh_prow` package delegates to `rhdh_lifecycle` for shared utilities.
