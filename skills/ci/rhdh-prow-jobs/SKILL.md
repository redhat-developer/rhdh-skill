---
name: rhdh-prow-jobs
description: >-
  Lists, generates, and removes RHDH test entries and Hive ClusterPools in the
  openshift/release Prow ci-operator configuration. Covers OCP
  `e2e-ocp-vX-Y-helm-nightly` entries, `cluster_claim.version`, the
  `rhdh-cluster-pool` Hive pools, and AKS/EKS/GKE entries with
  `MAPT_KUBERNETES_VERSION`. Use for "add an OCP test entry", "which OCP versions
  are we testing", "list the cluster pools", "what AKS/EKS/GKE version is
  configured", or an OCP coverage-gap analysis.
compatibility: "Python 3.9+ and uv; gh for remote openshift/release reads; a local openshift/release checkout plus make for generation and removal."
---

# RHDH Prow test entries and cluster pools

Read and change which platform versions RHDH is tested on in `openshift/release`.
Listing and coverage analysis work against the remote repository through `gh`;
generation and removal need a local checkout because they end in `make update`.

Run the bundled scripts instead of reconstructing their YAML logic. Every script
accepts `--repo-dir` to point at a local `openshift/release` checkout and falls
back to the GitHub API when it is absent.

## Route

| Intent | Load |
|---|---|
| List OCP test entries, or add/remove one | `workflows/ocp-jobs.md` |
| List, generate, or delete a Hive ClusterPool | `workflows/ocp-pools.md` |
| Find OCP coverage gaps and stale configuration | `workflows/ocp-coverage.md` |
| List AKS, EKS, or GKE entries, or bump their K8s version | `workflows/k8s-jobs.md` |

Load only the selected workflow.

## Scope

This skill owns individual test entries and cluster pools on branches that
already exist. Creating or retiring the whole set of jobs for a release branch —
the branch config file, its generated jobs, and its branch-protection block — is
`/rhdh-prow-release-branch`. Running a configured job on demand is
`/rhdh-prow-trigger`.

## Composition

For whether a platform version is still supported, invoke `/rhdh-platform-lifecycle`
by name and use what it returns. Do not import its Python package or read its
files. `scripts/analyze_coverage.py` queries the lifecycle APIs directly so the
scripts stay standalone.

## Reading rules

- Report only versions that came from the read, never from recall. Say which
  config source was read and when.
- Extract OCP versions from `cluster_claim.version`, not from test names — some
  OCP-targeted tests do not encode the version in their name.
- A version that is configured is not the same as a version that is supported.
  Without lifecycle facts, name the platforms that remain unclassified rather
  than presenting configured versions as supported.

## Writing rules

Generating a file, editing a config, running `make update`, committing, pushing,
or opening a pull request is a write. Follow `/mutation-gate`, naming the
config file or job file as the target of each operation.

- Use `--dry-run` on `generate_cluster_pool.py` to preview before writing.
- `generate_test_entry.py` prints a block for review; inserting it is a separate
  approved edit.
- Run `make update` after any config change, and commit the config and the
  generated job files together.
- Removing an OCP version means both its test entries on every product branch
  and its cluster pool. Check for the other half before declaring the removal
  finished.

## Completion

A read is complete when the answer names the config source it was read from,
every entry, pool, or gap in it came from that read, and anything the scan could
not reach is named as unread instead of reported as absent.

A write is complete when every approved file edit has been applied and reported,
`make update` has run, the regenerated job files under
`ci-operator/jobs/redhat-developer/rhdh/` are named alongside the config change,
and the push and pull-request state is stated explicitly — including "not
pushed" when nothing was pushed. A removal is complete only once both the test
entries and the cluster pool for that version are accounted for.
