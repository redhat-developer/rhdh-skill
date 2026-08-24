# Commission New RHDH Release Branch Jobs

Set up CI configuration for a new RHDH release branch. Requires a local `openshift/release` checkout.

Read `../references/release-branch-config.md` for file paths, templates, and release-vs-main differences.

## Steps

1. **Get the release version**:
   - If not provided, ask the user for the version (e.g. `1.11`)
   - Verify the config does NOT already exist: `ls ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}.yaml`

2. **Prepare a clean local branch**:
   - Run `git status --porcelain --untracked-files=all` in the checkout. Stop if
     it prints any tracked or untracked path; do not mix this work with an
     existing change.
   - From the user-selected base branch, run
     `git switch -c "ci/rhdh-{version}-release-branch" "<base-branch>"`.
   - The branch and file edits below are local preparation, not external
     operations. Approval for publishing them happens only in the final step.

3. **Choose the source config**:
   - List existing configs: `ls ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-*.yaml`
   - Default to the latest existing release branch (highest version number)
   - Alternatively, use `main` as the source if the user prefers

4. **Copy and adjust the CI config**:
   - Copy the source file to `redhat-developer-rhdh-release-{version}.yaml`
   - Read both the `main` config and the latest existing release branch config to understand the current patterns
   - Apply all structural adjustments described in `../references/release-branch-config.md` — compare main vs release branch to determine what to change (Slack channel, cron schedule, cleanup jobs, presubmit settings)
   - Set `zz_generated_metadata.branch` to `release-{version}`

5. **Confirm version-specific settings** with the user:
   - OCP versions: which `e2e-ocp-v4-{VER}-helm-nightly` entries to include
   - K8s version (`MAPT_KUBERNETES_VERSION`)
   - OSD version
   - `build_root` tag
   - If copying from the latest release branch, these are often unchanged

6. **Set up Slack alerts** (see `../references/release-branch-config.md` > Slack Alert Setup):
   - Create Slack channel `#rhdh-e2e-alerts-{X}-{Y}` and incoming webhook
   - Add webhook URL to Vault secret `rhdh-send-alert` as key `SLACK_ALERTS_WEBHOOK_URL_{X}_{Y}`
   - Set `reporter_config.channel` to `#rhdh-e2e-alerts-{X}-{Y}` on every nightly test entry in the CI config

7. **Add branch protection** to `_prowconfig.yaml`:
   - Read the latest existing release branch entry from `_prowconfig.yaml` to get the current structure and contexts
   - Add a `release-{version}:` entry under `branch-protection.orgs.redhat-developer.repos.rhdh.branches`, copying the structure from the latest release branch
   - Place the new entry in version order among existing entries

8. **Run `make update`** to regenerate Prow job configs

9. **Validate and summarize**:
   - Run `git diff --check` and stop on any whitespace error.
   - Confirm generated job files exist: `ls ci-operator/jobs/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}-*.yaml`
   - Inspect `git status --short` and the complete diff. Confirm every changed
     path belongs to the release config, its generated jobs, or branch
     protection; stop on an unrelated path.
   - Show a summary of what was created

10. **Author and publish the pull request**:

- Use a direct title such as `ci: add RHDH {version} release branch jobs`.
- In the body, summarize the config, generated jobs, branch protection, and
     Slack/Vault readiness. Include `make update` in the test plan and name every
     generated job file.
- Invoke `/prose-editing` once on the completed title and body in the
     **flavored** register. Preserve paths, job names, contexts, versions,
     commands, and checklist state.
- Give the repository, base and head branches, edited title, and edited body
     to `/rhdh-forge`. It returns the exact `gh pr create` command and payload;
     it does not execute them. Keep that result as `<forge-pr-command>`.
- Invoke `/mutation-gate` once with this ordered plan and the complete
     previews. Each operation depends on the previous one succeeding:
     1. Commit the reviewed paths with
        `git add -- <reviewed-paths> && git commit -m "ci: add RHDH {version} release branch jobs"`.
     2. Push the commit with
        `git push --set-upstream origin ci/rhdh-{version}-release-branch`.
     3. Verify the head exists with
        `git ls-remote --exit-code origin refs/heads/ci/rhdh-{version}-release-branch`,
        then open the pull request with `<forge-pr-command>`.
- After approval, execute the three operations in order. Stop after a
     failure, mark later operations skipped, and report each outcome. For the
     pull request, report the returned URL or the exact failure.

## Important Notes

- Always confirm OCP/K8s/OSD versions with the user before finalizing
- The source config determines the initial set of tests — the user may want to add or remove specific test entries after commissioning
- After the PR is merged, the actual `release-{version}` branch must exist in `redhat-developer/rhdh` for the jobs to trigger
