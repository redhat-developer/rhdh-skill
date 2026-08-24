---
name: rhdh-operator-pr-test
description: >-
  Tests an rhdh-operator pull request's CI-built operator, operator-bundle,
  and operator-catalog images on a live OpenShift cluster with oc, and reports
  evidence plus rollback. Use for "test this operator PR on a cluster",
  redhat-developer/rhdh-operator PR images or bundles, OLM CatalogSource and
  Subscription from a PR catalog, quay.io/rhdh-community/operator, or deploying
  a PR's CI bundle with oc.
compatibility: "oc, skopeo, and an accessible OpenShift cluster. GitHub reads go through /rhdh-forge. Cluster login is oc login."
---

# RHDH Operator PR Test

Deploy the PR's CI-built bundle onto a live cluster and verify the change there.
GitHub code review belongs to `/rhdh-pr-review`.

## Start here

Follow `workflows/test-operator-pr.md` from the top. Load
`references/operator-pr-images.md` when extracting or validating CI image URLs.

## Gates

| Gate | Required check | If fail |
|---|---|---|
| Forge | `/rhdh-forge` is installed and returns the PR | Stop; name `/setup-rhdh-skills install` |
| `oc` | `oc` is on `PATH` | Stop; name `/setup-rhdh-skills` |
| Cluster | `oc whoami` succeeds | Stop; the human runs `oc login`, or follows the rhdh-test-instance provision path in the workflow |
| Repository | The PR is `redhat-developer/rhdh-operator` | Stop; this skill tests that repository only |

## Boundaries

- `/rhdh-forge` owns GitHub reads. Invoke it by name with the PR URL or number
  and consume repository, number, state, files, diff, head and base refs, and
  comments. Do not parse the URL here or copy a fetch workflow.
- `/rhdh-pr-review` owns analyzing the diff for merge comments and posting a
  GitHub review.
- `/rhdh-local` owns a local compose runtime, not a live OpenShift cluster.
- `/rhdh-overlay` owns overlay PR artifact checks, not operator bundles.
- `/rhdh-context` locates an RHDH checkout when a local `rhdh-test-instance`
  tree is needed. Do not add it as a catalog dependency.

## Writes

Posting a `/test` comment, applying or deleting cluster resources, and deploying
or rolling back an RHDH instance are external writes: invoke `/mutation-gate`
and follow it. A cluster operation's target names the namespace; a comment's
target names the repository and PR number. A request to test approves no write.

Deploy the full PR bundle or manifests, not only the operator binary image.
Preserve the original cluster state and report it with cleanup.

## Completion

Complete when the report names the PR and images used, one result per live
check, the overall verdict, the deployed bundle or manifests, original and
final cluster state, rollback commands, cleanup status, and the outcome of
every approved write including skipped ones. Do not cache cluster state inside
the skill directory.
