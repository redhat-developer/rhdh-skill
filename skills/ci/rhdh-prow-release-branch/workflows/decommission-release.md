# Decommission RHDH Release Branch Jobs

Remove all CI configuration for a given RHDH release branch when it reaches end-of-life. Requires a local `openshift/release` checkout.

Read `../references/release-branch-config.md` for file paths and templates.

## Steps

1. **Get the release version**:
   - If not provided, list existing configs: `ls ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-*.yaml`

2. **Verify files to be removed** (show the user and ask for confirmation):
   - **CI config**: `ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}.yaml`
   - **Generated jobs** (removed by `make update`): `ci-operator/jobs/redhat-developer/rhdh/redhat-developer-rhdh-release-{version}-*.yaml`
   - **Branch protection**: `release-{version}:` block in `core-services/prow/02_config/redhat-developer/rhdh/_prowconfig.yaml`

3. **Prepare a clean local branch**:
   - Run `git status --porcelain --untracked-files=all` in the checkout. Stop if
     it prints any tracked or untracked path; do not mix this work with an
     existing change.
   - From the user-selected base branch, run
     `git switch -c "ci/rhdh-{version}-release-branch-removal" "<base-branch>"`.
   - The branch and file edits below are local preparation, not external
     operations. Approval for publishing them happens only in the final step.

4. **Delete the CI config file**

5. **Remove branch protection configuration**:
   Edit `_prowconfig.yaml` to remove the entire `release-{version}:` block under `branch-protection.orgs.redhat-developer.repos.rhdh.branches`. Be careful to:
   - Only remove the block for the specified version
   - Preserve indentation and formatting of surrounding blocks
   - Not leave blank lines where the block was removed

6. **Run `make update`** to regenerate Prow job configs (this also removes the generated job files for the deleted config)

7. **Validate and summarize**:
   - Run `git diff --check` and stop on any whitespace error.
   - Inspect `git status --short` and the complete diff. Confirm every changed
     path belongs to the removed release config, its generated jobs, or branch
     protection; stop on an unrelated path.
   - Summarize what was removed.

8. **Author and publish the pull request**:
   - Use a direct title such as `ci: remove RHDH {version} release branch jobs`.
   - In the body, name the removed config, generated jobs, and branch-protection
     block. Include `make update` in the test plan and state the recovery path.
   - Invoke `/prose-editing` once on the completed title and body in the
     **flavored** register. Preserve paths, job names, contexts, versions,
     commands, and checklist state.
   - Give the repository, base and head branches, edited title, and edited body
     to `/rhdh-forge`. It returns the exact `gh pr create` command and payload;
     it does not execute them. Keep that result as `<forge-pr-command>`.
   - Invoke `/mutation-gate` once with this ordered plan and the complete
     previews. Each operation depends on the previous one succeeding:
     1. Commit the reviewed paths with
        `git add -- <reviewed-paths> && git commit -m "ci: remove RHDH {version} release branch jobs"`.
     2. Push the commit with
        `git push --set-upstream origin ci/rhdh-{version}-release-branch-removal`.
     3. Verify the head exists with
        `git ls-remote --exit-code origin refs/heads/ci/rhdh-{version}-release-branch-removal`,
        then open the pull request with `<forge-pr-command>`.
   - After approval, execute the three operations in order. Stop after a
     failure, mark later operations skipped, and report each outcome. For the
     pull request, report the returned URL or the exact failure.

## Important Notes

- This operation is destructive -- always confirm with the user before proceeding
- Always verify files exist before attempting deletion
