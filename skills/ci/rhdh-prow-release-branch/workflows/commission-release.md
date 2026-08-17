# Commission New RHDH Release Branch Jobs

Set up CI configuration for a new RHDH release branch. Requires a local `openshift/release` checkout.

Read `../references/release-branch-config.md` for file paths, templates, and release-vs-main differences.

## Steps

1. **Get the release version**:
   - If not provided, ask the user for the version (e.g. `1.11`)
   - Verify the config does NOT already exist: `ls ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}.yaml`

2. **Choose the source config**:
   - List existing configs: `ls ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-*.yaml`
   - Default to the latest existing release branch (highest version number)
   - Alternatively, use `main` as the source if the user prefers

3. **Copy and adjust the CI config**:
   - Copy the source file to `redhat-developer-rhdh-release-{version}.yaml`
   - Read both the `main` config and the latest existing release branch config to understand the current patterns
   - Apply all structural adjustments described in `../references/release-branch-config.md` — compare main vs release branch to determine what to change (Slack channel, cron schedule, cleanup jobs, presubmit settings)
   - Set `zz_generated_metadata.branch` to `release-{version}`

4. **Confirm version-specific settings** with the user:
   - OCP versions: which `e2e-ocp-v4-{VER}-helm-nightly` entries to include
   - K8s version (`MAPT_KUBERNETES_VERSION`)
   - OSD version
   - `build_root` tag
   - If copying from the latest release branch, these are often unchanged

5. **Set up Slack alerts** (see `../references/release-branch-config.md` > Slack Alert Setup):
   - Create Slack channel `#rhdh-e2e-alerts-{X}-{Y}` and incoming webhook
   - Add webhook URL to Vault secret `rhdh-send-alert` as key `SLACK_ALERTS_WEBHOOK_URL_{X}_{Y}`
   - Set `reporter_config.channel` to `#rhdh-e2e-alerts-{X}-{Y}` on every nightly test entry in the CI config

6. **Add branch protection** to `_prowconfig.yaml`:
   - Read the latest existing release branch entry from `_prowconfig.yaml` to get the current structure and contexts
   - Add a `release-{version}:` entry under `branch-protection.orgs.redhat-developer.repos.rhdh.branches`, copying the structure from the latest release branch
   - Place the new entry in version order among existing entries

7. **Run `make update`** to regenerate Prow job configs

8. **Verify and summarize**:
   - Confirm generated job files exist: `ls ci-operator/jobs/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}-*.yaml`
   - Show a summary of what was created

## Important Notes

- Always confirm OCP/K8s/OSD versions with the user before finalizing
- The source config determines the initial set of tests — the user may want to add or remove specific test entries after commissioning
- After the PR is merged, the actual `release-{version}` branch must exist in `redhat-developer/rhdh` for the jobs to trigger
