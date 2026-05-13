# Workflow: Onboard a Plugin to RHDH Extensions Catalog

Add a new Backstage plugin to the RHDH Extensions Catalog via the overlay repository.

<required_reading>
**Read these reference files NOW:**

1. `references/overlay-repo.md` — Workspace patterns and examples
2. `references/ci-feedback.md` — Interpreting publish workflow output
</required_reading>

<prerequisites>
| Requirement | Details |
|-------------|---------|
| **Access** | Write access to [rhdh-plugin-export-overlays](https://github.com/redhat-developer/rhdh-plugin-export-overlays) |
| **Tools** | `git`, `gh` CLI |
| **Knowledge** | Basic understanding of Backstage plugins and dynamic plugin format |
</prerequisites>

<jira_kickstart>
**Do you have a JIRA issue for this plugin?**

If yes, provide the issue ID (e.g., `RHIDP-12345`). JIRA tickets often contain:

- Upstream repository URL
- Plugin name and package details
- License information
- Target RHDH version

This can skip much of Phase 1 discovery.

**Reference:** [RHIDP-11137](https://issues.redhat.com/browse/RHIDP-11137) — example plugin onboarding ticket
</jira_kickstart>

<process>

## Phase 1: Discovery & Evaluation

**Goal:** Verify the plugin is suitable for RHDH integration.

### 1.1 Identify Upstream Source

- [ ] Locate upstream repository URL
- [ ] Identify specific plugin path within repo (monorepo structure common)
- [ ] Note the package name(s) to export

**What to look for:**

- Most plugins live in monorepos under `plugins/<name>/` with `frontend`, `backend`, `common` subdirs
- Package names often follow `@<org>/<plugin-name>` and `@<org>/<plugin-name>-backend` pattern

### 1.2 License Check

- [ ] Verify license is Apache 2.0 or compatible
- [ ] Document license in evaluation notes

**Compatible licenses:**

- ✅ Apache 2.0 (preferred)
- ✅ MIT, BSD-2-Clause, BSD-3-Clause, ISC
- ⚠️ MPL-2.0 (review needed - weak copyleft)
- ❌ GPL, LGPL, AGPL (copyleft - not compatible)
- ❌ Proprietary, no license specified

### 1.3 Upstream Health

- [ ] Check last commit date (activity within 6 months preferred)
- [ ] Review open issues/PRs for red flags
- [ ] Identify maintainer responsiveness

**Red flags to watch for:**

- 🚩 No commits in 12+ months (abandoned)
- 🚩 Many open issues with no maintainer response
- 🚩 "Looking for maintainers" or archive notices
- 🚩 Breaking changes in recent commits without release
- 🚩 CI/build badges showing failures

**Quick health check commands:**

```bash
# Last commit date
gh api repos/<owner>/<repo>/commits?per_page=1 --jq '.[0].commit.committer.date'

# Open issues count
gh api repos/<owner>/<repo> --jq '.open_issues_count'

# Recent releases
gh release list -R <owner>/<repo> --limit 5
```

### 1.4 Backstage Version Compatibility

- [ ] Check upstream's `backstage.json` or `package.json` for Backstage version
- [ ] Compare against RHDH target version in [versions.json](https://github.com/redhat-developer/rhdh-plugin-export-overlays/blob/main/versions.json)
- [ ] Document any version gaps

**Version gap guidance:**

- Minor version gaps (e.g., 1.43 → 1.45) are typically safe
- Major version gaps require careful review of breaking changes

### 1.5 Decision Gate

| Criteria | Status |
|----------|--------|
| License compatible | |
| Upstream active | |
| Backstage version aligned | |

**Proceed?** Yes / No (document reason if No)

**When to say No:**

- License is incompatible (GPL/LGPL/proprietary)
- Repo appears abandoned with no alternative
- Major Backstage version gap (e.g., 1.x vs 2.x) with no upgrade path
- Plugin has known critical security issues

**When to escalate:**

- MPL-2.0 or other "gray area" licenses → Legal/compliance review
- Plugin is popular but unhealthy → Consider forking or community adoption
- Backstage version 2+ minor behind → Check with RHDH team on timeline
- Unsure about any criteria → Ask in #forum-rhdh-plugins Slack

---

## Phase 2: Workspace Creation

**Goal:** Create the workspace folder structure in the overlay repo.

### 2.1 Clone and Branch

```bash
cd repo/rhdh-plugin-export-overlays  # or clone fresh
git fetch upstream
git checkout main && git pull upstream main
git checkout -b add-<plugin-name>-workspace
```

### 2.2 Create Workspace Folder

```bash
mkdir -p workspaces/<workspace-name>
```

**Naming convention:** Use upstream scope/name, e.g., `aws-codebuild`, `backstage-community-techdocs`

### 2.3 Create `source.json`

See `templates/workspace-files.md` for the template.

**Key fields:**

- `repo` - Upstream GitHub URL (only `https://github.com/xxx` supported)
- `repo-ref` - Target commit SHA or tag
- `repo-flat` - `true` if plugins at repo root, `false` if inside workspace folder
- `repo-backstage-version` - Backstage version from upstream

**Validate upstream version:**

```bash
curl -s https://raw.githubusercontent.com/<owner>/<repo>/<commit>/backstage.json | jq .version
```

### 2.4 Create `plugins-list.yaml`

See `templates/workspace-files.md` for the template.

**Key patterns:**

- Path format: `plugins/<name>/frontend:` or `plugins/<name>/backend:`
- Use `--embed-package` for shared dependencies not published separately

### 2.5 (Optional) Create `backstage.json`

Usually not needed on first attempt. The CI will tell you if a version override is required.

**When CI says "incompatible workspaces":**

1. Add `backstage.json` with RHDH's target version
2. Keep `source.json`'s `repo-backstage-version` as the upstream's actual version

### 2.6 Add CODEOWNERS Entry

```bash
echo "/workspaces/<workspace-name>/ @<your-github-username>" >> CODEOWNERS
```

---

## Phase 3: PR & Build

**Goal:** Open PR, trigger build, pass smoke tests.

### 3.1 Commit and Push

```bash
git add .
git commit -m "Add <plugin-name> workspace"
git push -u origin add-<plugin-name>-workspace
```

### 3.2 Open Pull Request

```bash
gh pr create \
  --title "Add <plugin-name> workspace" \
  --body "## Summary
- Adds <plugin-name> plugin to RHDH Extensions Catalog
- Upstream: <upstream-url>
- License: Apache 2.0

## Checklist
- [ ] source.json created
- [ ] plugins-list.yaml created
- [ ] CODEOWNERS updated"
```

### 3.3 Trigger Build

1. Comment `/publish` on the PR
2. **Watch PR comments** — automation reports:
   - Compatibility issues with suggested fixes
   - Published OCI images on success
   - Failures with actionable guidance
3. If issues arise, see `references/ci-feedback.md`
4. Re-trigger with `/publish` after fixes

---

## Phase 4: Plugin Metadata

**Goal:** Create metadata files for integration tests and catalog registration.

### 4.1 Generate Package and Plugin Metadata

Follow `workflows/generate-metadata.md` to generate Package metadata (and Plugin entity if needed) for all plugins in the workspace.

Review the generated files before proceeding.

### 4.2 Add to Packages List (if applicable)

Plugins in these lists become "required" — release gates fail if they're incompatible.

| File | Tier | Meaning |
|------|------|---------|
| `rhdh-supported-packages.txt` | Supported | Full Red Hat support |
| `rhdh-techpreview-packages.txt` | Tech Preview | Limited support |
| `rhdh-community-packages.txt` | Community | Community-maintained |

**Format:** `<workspace>/plugins/<plugin-folder>` (e.g., `aws-codebuild/plugins/codebuild/frontend`)

> ⚠️ **Note:** Tier assignment is typically decided by RHDH team during release planning, not at onboarding time. If unclear, check with team before adding.

---

## Phase 5: Verification

**Goal:** Confirm plugin works using PR artifacts (before merge).

> 📖 **Full reference:** See `references/rhdh-local.md` for complete setup, commands, and troubleshooting.

### 5.1 Set Up Local Test Environment

```bash
cd repo/rhdh-local
podman compose up -d
# Access at http://localhost:7007, login as Guest
```

### 5.2 Configure PR Artifacts

Create `configs/dynamic-plugins/dynamic-plugins.override.yaml` with OCI URLs from PR `/publish` comment:

```yaml
includes:
  - dynamic-plugins.default.yaml

plugins:
  - package: oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/<package>:pr_<number>__<version>!<package>
    disabled: false
    pluginConfig:
      # Copy from workspaces/<plugin>/metadata/*.yaml appConfigExamples
```

### 5.3 Create Test Entity

Create `configs/catalog-entities/components.override.yaml` with required annotations:

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: <plugin>-test-service
  annotations:
    <annotation-key>: <test-value>  # Check plugin README for required annotations
spec:
  type: service
  lifecycle: experimental
  owner: user:default/guest
```

Restart to load: `podman compose down && podman compose up -d`

### 5.4 Verify Plugin Works

- [ ] Backend health: `curl http://localhost:7007/api/<plugin>/health` returns `{"status":"ok"}`
- [ ] Logs clean: `podman compose logs rhdh 2>&1 | grep -i <plugin>` shows no errors
- [ ] Card renders on test entity Overview tab
- [ ] Auth errors expected without real credentials — confirms wiring works

### 5.5 (Optional) Test Extensions Catalog Visibility

To verify the Plugin entity appears in `/extensions/catalog`:

1. Create `compose.override.yaml` mounting catalog entities
2. Create `configs/app-config/app-config.local.yaml` with `Plugin` kind allowed

See `references/rhdh-local.md` → `<extensions_catalog_visibility>` for complete config.

**Verification:**

- [ ] Plugin card appears in Extensions Catalog
- [ ] Name, description, categories display correctly

### 5.6 Update PR Description

Add verification results to PR. See `templates/workspace-files.md` for template.

### 5.7 Local Cleanup

```bash
rm configs/dynamic-plugins/dynamic-plugins.override.yaml
rm configs/catalog-entities/components.override.yaml
rm -f compose.override.yaml configs/app-config/app-config.local.yaml
podman compose down
```

---

## Phase 6: PR Approval & Merge

**Goal:** Get PR reviewed and merged.

### 6.1 Request Review

- [ ] Request review from CODEOWNERS
- [ ] For first workspace PR, request from cope team

### 6.2 Address Feedback & Merge

- [ ] Respond to review comments
- [ ] Re-trigger `/publish` after significant changes
- [ ] Merge when all checks pass

### 6.3 JIRA Tracking (Optional)

If tracking this work in JIRA, update the ticket after merge.

**Reference:** See [RHIDP-11137](https://issues.redhat.com/browse/RHIDP-11137) for an example of how plugin onboarding was tracked.

**Details:** Use the `rhdh-jira` skill for CLI patterns if needed.

</process>

<action_triggers>

| Trigger | Type | What to Do | Resume When |
|---------|------|------------|-------------|
| License policy unclear | 👥 Sync | Check with team on acceptable licenses | Policy confirmed |
| Support tier assignment | 👥 Sync | Ask team: which `rhdh-*-packages.txt` file? | Tier confirmed |
| CI failure unclear | 📖 Reference | Check `references/ci-feedback.md` | Issue understood |
</action_triggers>

<tracking>

## Activity Logging

Log key milestones to maintain context across sessions:

```bash
# Starting onboard
$RHDH log add "Started onboard: <plugin-name> from <upstream-url>" --tag onboard --tag <plugin-name>

# Phase completions
$RHDH log add "Phase 1 complete: <plugin-name> approved for onboard" --tag onboard --tag <plugin-name>
$RHDH log add "Phase 2 complete: workspace created for <plugin-name>" --tag onboard --tag <plugin-name>
$RHDH log add "Phase 3 complete: PR opened #<number>" --tag onboard --tag <plugin-name>
$RHDH log add "Phase 4 complete: metadata added for <plugin-name>" --tag onboard --tag <plugin-name>
$RHDH log add "Phase 5 complete: <plugin-name> verified locally" --tag onboard --tag <plugin-name>
$RHDH log add "Onboard complete: <plugin-name> merged" --tag onboard --tag <plugin-name>
```

## Follow-up Todos

Create todos when blocked or when follow-up is needed:

```bash
# License unclear
$RHDH todo add "Check license with legal for <plugin-name>" --context "<plugin-name>"

# Waiting on external response
$RHDH todo add "Follow up with upstream maintainer on <issue>" --context "<plugin-name>"

# Post-merge follow-up
$RHDH todo add "Verify <plugin-name> in next RHDH release" --context "<plugin-name>"

# Add notes to existing todo
$RHDH todo note <slug> "Sent email to legal@redhat.com"
$RHDH todo note <slug> "Response: approved with attribution"
$RHDH todo done <slug>
```

## Viewing History

```bash
# Find all onboard activity
$RHDH log search "onboard"
$RHDH log search "<plugin-name>"

# Check pending todos
$RHDH todo list --pending
```

</tracking>

<success_criteria>
This workflow is complete when:

- [ ] Workspace created with source.json + plugins-list.yaml
- [ ] `/publish` succeeds with OCI images
- [ ] Metadata files created (Package + Plugin entities)
- [ ] Plugin tested locally with rhdh-local
- [ ] PR reviewed and merged
- [ ] JIRA updated (if applicable)
</success_criteria>
