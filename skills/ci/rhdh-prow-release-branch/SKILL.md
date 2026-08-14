---
name: rhdh-prow-release-branch
description: >-
  Commissions or decommissions the openshift/release Prow configuration for a
  single RHDH release branch: the ci-operator config
  `redhat-developer-rhdh-release-{version}.yaml`, the jobs `make update`
  generates from it, the `release-{version}` branch-protection block in
  `_prowconfig.yaml`, and the `#rhdh-e2e-alerts-X-Y` Slack channel and
  `rhdh-send-alert` Vault webhook. Use for "set up CI for release 1.11",
  "commission the 1.12 branch jobs", or "decommission 1.8". Prow configuration
  for a release branch only — the release itself is rhdh-release-status,
  rhdh-release-schedule, and rhdh-release-announce.
compatibility: "A local openshift/release checkout with make and git; Slack app admin and Vault access for the per-branch alert webhook."
---

# RHDH release-branch Prow configuration

Turn the CI configuration for one `release-{version}` branch of
`redhat-developer/rhdh` on or off in `openshift/release`. Both directions need a
local checkout because both end in `make update`.

This skill is about Prow configuration, not about the product release. What is
open against a release is `/rhdh-release-status`, its milestone dates are
`/rhdh-release-schedule`, and its freeze announcement is `/rhdh-release-announce`.
Individual test entries and cluster pools on a branch that already has jobs
belong to `/rhdh-prow-jobs`.

## Route

| Intent | Load |
|---|---|
| Create CI configuration for a new release branch | `workflows/commission-release.md` |
| Remove CI configuration for an end-of-life release branch | `workflows/decommission-release.md` |

`references/release-branch-config.md` holds the file paths, the release-vs-main
differences, and the Slack alert setup that both workflows use. Read it with
whichever workflow you loaded.

## Writing rules

Copying the config, editing `_prowconfig.yaml`, deleting files, running
`make update`, committing, pushing, and opening a pull request are writes. Follow
`/mutation-gate`, naming each file path as the target of its operation.

- Never hardcode the branch-protection block or the release-branch adjustments.
  Read the latest existing release branch and copy its current shape; required
  status-check contexts and presubmit settings change over time.
- Confirm the version-specific values with the user before finalizing: which OCP
  test entries to include, `MAPT_KUBERNETES_VERSION`, the OSD version,
  `releases.latest.release`, and the `build_root` tag.
- Decommissioning is destructive. Name every file and block to be removed, and
  the rollback, before removing anything.
- The Slack channel, its incoming webhook, and the Vault key
  `SLACK_ALERTS_WEBHOOK_URL_{X}_{Y}` are human steps outside the repository. Ask
  the user to perform them; do not treat the config change as finished while
  `reporter_config.channel` points at a channel that does not exist.

## Completion

Commissioning is complete when
`ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}.yaml`
exists with `zz_generated_metadata.branch` set to `release-{version}`, the
release-branch adjustments from the reference have been applied, the
`release-{version}` branch-protection entry sits in version order in
`_prowconfig.yaml`, `make update` has run, and the generated
`ci-operator/jobs/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}-*.yaml`
files are listed by name. State the Slack channel and Vault key status, and note
that the jobs will not fire until the `release-{version}` branch itself exists in
`redhat-developer/rhdh`.

Decommissioning is complete when the config file is deleted, the
`release-{version}` block is gone from `_prowconfig.yaml` with surrounding
indentation intact, `make update` has removed the generated job files, and every
removed file and block is named alongside its rollback. In both directions, state
the push and pull-request state explicitly — including "not pushed".
