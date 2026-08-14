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

Before `git push`, freeze the branch and refspec and follow the write gate in
`SKILL.md`. Prepare the local commit first, then state the push as an operation
with its exact branch and refspec, get approval, and report its outcome.

```bash
git add .
git commit -m "Add <plugin-name> workspace"
git push -u origin add-<plugin-name>-workspace
```

### 3.2 Open Pull Request

Once the pushed head SHA and full body are known, state PR creation as a new
operation and get approval for it before running `gh pr create`.

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

1. Follow the guarded publish in `SKILL.md`; get approval for the stated
   operation before commenting `/publish` on the PR.
2. **Watch PR comments** — automation reports:
   - Compatibility issues with suggested fixes
   - Published OCI images on success
   - Failures with actionable guidance
3. If issues arise, see `references/ci-feedback.md`
4. Re-trigger with `/publish` after fixes

---

## Phase 4: Plugin Metadata

**Goal:** Create metadata files for integration tests and catalog registration.

### 4.1 Create Package Metadata Files

Create one YAML file per exported plugin in `workspaces/<name>/metadata/`.

**Kind:** `Package` — represents a single npm package (frontend or backend)

**Documentation:** [catalog-entities/marketplace/README.md](https://github.com/redhat-developer/rhdh-plugin-export-overlays/blob/main/catalog-entities/marketplace/README.md)

### 4.2 Create Plugin Entity

Create a Plugin entity that groups your packages together.

**Kind:** `Plugin` — user-facing catalog entry

**Location:** `catalog-entities/marketplace/plugins/<plugin-name>.yaml`

**Key fields:**

- `metadata.name` — short identifier
- `metadata.description` — brief summary
- `spec.description` — full markdown documentation
- `spec.packages` — list of Package names
- `spec.categories` — for filtering (e.g., `CI/CD`, `Cloud`)

### 4.3 Trigger Build & Tests

State the exact push as an operation, get approval, and report its outcome. Then
run the guarded publish separately, once the new head SHA is visible.

```bash
git add workspaces/<name>/metadata/ catalog-entities/marketplace/plugins/<name>.yaml
git commit -m "Add plugin metadata"
git push
```

Once approved, comment `/publish` to rebuild. Watch for test workflow results and
report the check URL as the operation's outcome.

> ⚠️ **Smoke test only:** The CI test verifies plugins install and RHDH starts without errors. It does **not** test plugin functionality (no API calls, no browser tests). Functional verification happens in Phase 5.

### 4.4 Add to Packages List (if applicable)

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

1. Read `references/rhdh-local.md` for PR tag, plugin configuration, entity,
   and verification patterns.
2. Extract exact `spec.dynamicArtifact` and `appConfigExamples` values from the
   generated metadata or `/publish` output. Do not construct an OCI reference.
3. Invoke `/rhdh-local` by name and give it, for each package, the exact dynamic
   artifact reference and its plugin config or `none`; the environment variables
   it needs by name; the catalog test entities; the checks from
   `references/rhdh-local.md`; and that it should clean up afterwards. If
   `rhdh-local` is not installed, say that local verification is unavailable,
   name `/setup-rhdh-skills install` as the human's next step, and stop this
   phase.
4. Take back its per-check results and preserve skipped checks with their
   reasons.
5. To add those results to the overlay PR, state the comment as an operation with
   its exact body and target, get approval, and report the resulting comment URL.
   Authentication failures inside the plugin card are acceptable only when
   installation, boot, and UI wiring are otherwise proven.

---

## Phase 6: PR Approval & Merge

**Goal:** Get PR reviewed and merged.

### 6.1 Request Review

Requesting reviewers is an external write. State one operation naming every
reviewer and the target PR, get approval, then report the outcome.

- [ ] Request review from CODEOWNERS
- [ ] For first workspace PR, request from cope team

### 6.2 Address Feedback & Merge

Each comment, re-trigger, and merge is its own operation unless every payload and
target is exact enough to state as one set. Follow the write gate in `SKILL.md`.
The onboarding request approves no merge.

- [ ] Respond to review comments
- [ ] Re-trigger `/publish` after significant changes
- [ ] Merge when all checks pass

### 6.3 JIRA Tracking (Optional)

If tracking this work in JIRA, update the ticket after merge.

**Reference:** See [RHIDP-11137](https://issues.redhat.com/browse/RHIDP-11137) for an example of how plugin onboarding was tracked.

**Details:** Invoke `/rhdh-jira-update` by name with the update you want. That
skill owns the Jira write, states the operation, and reports its outcome. Do not
copy Jira commands or credential handling into this workflow.

</process>

<action_triggers>

| Trigger | Type | What to Do | Resume When |
|---------|------|------------|-------------|
| License policy unclear | 👥 Sync | Check with team on acceptable licenses | Policy confirmed |
| Support tier assignment | 👥 Sync | Ask team: which `rhdh-*-packages.txt` file? | Tier confirmed |
| CI failure unclear | 📖 Reference | Check `references/ci-feedback.md` | Issue understood |
</action_triggers>

## Follow-up record

Report the workspace, source ref, exact dynamic artifacts and config, metadata
files, PR URL, publish status, and the local verification results. Name every
unresolved license, support-tier, upstream, and post-release verification
decision. Do not cache discoverable state locally.

<success_criteria>
This workflow is complete when:

- [ ] Workspace created with source.json + plugins-list.yaml
- [ ] `/publish` succeeds with OCI images
- [ ] Metadata files created (Package + Plugin entities)
- [ ] Plugin tested through `/rhdh-local`, with a result for every check requested
- [ ] PR reviewed and merged
- [ ] JIRA updated (if applicable)
</success_criteria>
