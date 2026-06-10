# Release Branch CI Configuration

Shared definitions for commissioning and decommissioning RHDH release branch CI in `openshift/release`. Both `workflows/commission-release.md` and `workflows/decommission-release.md` reference this file.

## File Paths

For a given release version `{version}` (e.g. `1.10`):

| File | Path |
|------|------|
| **CI config** | `ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}.yaml` |
| **Generated jobs** | `ci-operator/jobs/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}-*.yaml` |
| **Branch protection** | `core-services/prow/02_config/redhat-developer/rhdh/_prowconfig.yaml` |

## Branch Protection

Each release branch has an entry under `branch-protection.orgs.redhat-developer.repos.rhdh.branches` in `_prowconfig.yaml`.

When commissioning, **read the latest existing release branch entry** from `_prowconfig.yaml` and copy its structure (keys, contexts, settings). Do not hardcode the block — the required status check contexts and protection settings change over time.

When decommissioning, remove the entire `release-{version}:` block, preserving indentation and formatting of surrounding entries.

## Release Branch vs Main Differences

When creating a release branch config from `main` or another release branch, **read both the `main` config and the latest existing release branch config** to understand the current patterns, then apply these structural adjustments:

| Adjustment | How to determine the correct value |
|------------|-----------------------------------|
| **Slack channel** | Read the latest release branch config. Pattern: `#rhdh-e2e-alerts-{X}-{Y}` (dots replaced with hyphens) |
| **Cron schedule** | Read the latest release branch config to see the current schedule pattern. Release branches use a different schedule than `main` to spread load |
| **Cleanup jobs** | Compare `main` with the latest release branch. Jobs present in `main` but absent from all release branches are main-only — remove them |
| **Presubmit tests** | Compare `main` with the latest release branch. Note differences in `always_run`, `max_concurrency`, and other settings — apply the release branch pattern |
| **`zz_generated_metadata.branch`** | Set to `release-{version}` |

Version-specific settings to verify with the user:

| Setting | How to determine |
|---------|-----------------|
| **OCP versions** | Read the source config's `e2e-ocp-v4-*-helm-nightly` entries. Ask the user which OCP versions to include for the new branch |
| **K8s version** (`MAPT_KUBERNETES_VERSION`) | Read from the source config. Ask the user if it should change |
| **OSD version** | Read from the source config. Ask the user if it should change |
| **`releases.latest.release`** | OCP release payload used by ci-operator (`channel` + `version`). Compare main and release branches — typically the same, but may differ if the release branch targets an older OCP |
| **`build_root` tag** | Read from the source config. Ask the user if it should change |

## Slack Alert Setup

Each release branch needs its own Slack channel and webhook for E2E alert notifications. There are two alert mechanisms:

1. **Prow `reporter_config`** — configured per-test in the CI config YAML (`reporter_config.channel`). Set to `#rhdh-e2e-alerts-{X}-{Y}` (dots replaced with hyphens). This fires on infrastructure-level errors.

2. **`rhdh-send-alert` step** — uses a Slack incoming webhook URL from the Vault secret `rhdh-send-alert` (namespace `test-credentials`). The script auto-detects the release version from `JOB_NAME` and looks for a versioned key `SLACK_ALERTS_WEBHOOK_URL_{X}_{Y}` (dots replaced with underscores), falling back to the default `SLACK_ALERTS_WEBHOOK_URL`.

### Setup steps

1. **Create Slack channel** `#rhdh-e2e-alerts-{X}-{Y}` in the [Nightly Test Alerts Slack app](https://api.slack.com/apps/A08U4AP1YTY/incoming-webhooks)
2. **Create incoming webhook** for the new channel in the same Slack app
3. **Add webhook URL to Vault** secret `rhdh-send-alert` as key `SLACK_ALERTS_WEBHOOK_URL_{X}_{Y}`
4. **Set `reporter_config.channel`** to `#rhdh-e2e-alerts-{X}-{Y}` on every nightly test entry in the CI config

## Post-Change Step

After modifying any CI config files, always run:

```bash
make update
```

This regenerates Prow job configs in `ci-operator/jobs/` and `zz_generated_metadata` sections. It also cleans up generated jobs for deleted configs.
