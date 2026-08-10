---
name: overlay
description: >-
  Manages the rhdh-plugin-export-overlays repository — onboards plugins to the
  Extensions Catalog, updates plugin versions, fixes overlay build failures,
  triages and analyzes PRs, triggers publishes, manages plugin workspaces, and
  looks up plugin metadata.
  Use when working with overlays, importing plugins, debugging CI, checking PRs,
  bumping versions, looking up plugin metadata, or mentions "Extensions
  Catalog", "overlay build failed", "plugin registry", "overlay PR", "overlay
  doctor", "plugin import", "add plugin to catalog", "onboard plugin", "plugin
  workspace", "plugin installation reference".
---

<cli_setup>
This skill uses the orchestrator CLI. **Set up first:**

```bash
RHDH=../rhdh/scripts/rhdh
```

**Verify environment:**

```bash
$RHDH
```

If `needs_setup: true`, run `$RHDH doctor` before proceeding.
</cli_setup>

<essential_principles>

<principle name="overlay_repo_pattern">
All plugin exports go through [rhdh-plugin-export-overlays](https://github.com/redhat-developer/rhdh-plugin-export-overlays).
Each plugin lives in a workspace folder with `source.json` + `plugins-list.yaml`.
CI handles the actual export - we define the configuration.
</principle>

<principle name="version_fields">
Two Backstage version fields serve different purposes:
- `source.json` → `repo-backstage-version` = upstream's **actual** version
- `backstage.json` → `version` = our **override** for RHDH compatibility

Never confuse these. CI validates the source.json value matches upstream.
</principle>

<principle name="test_with_pr_artifacts">
Always test with PR artifacts before merge using rhdh-local.
OCI format: `oci://<registry>/<image>:pr_<number>__<version>!<package-name>`
Success = plugin loads and attempts API calls (auth errors are expected without real credentials).
</principle>

<principle name="copy_similar_workspaces">
When stuck, find a similar workspace and copy its patterns.
AWS plugins → copy from `aws-ecs/` or `aws-codebuild/`
Community plugins → copy from `backstage/`
Check existing PRs for structure examples.
</principle>

</essential_principles>

<intake>
## Identify Task

What overlay task would you like to do?

### Plugin Owner Tasks

*For contributors managing their own plugin(s)*

1. **Onboard a new plugin** — Add upstream plugin to Extensions Catalog
2. **Update plugin version** — Bump to newer upstream commit/tag
3. **Check plugin status** — Verify health and compatibility
4. **Fix build failure** — Debug CI/publish issues
5. **Lookup plugin metadata** — Get plugin version and artifact reference by branch

### Core Team Tasks

*For COPE/Plugins team managing the overlay repository*

6. **Triage overlay PRs** — Prioritize open PRs by criticality
7. **Analyze specific PR** — Check assignment, compatibility, merge readiness
8. **Trigger publish** — Add /publish comment to PR(s)

**Wait for response before proceeding.**
</intake>

<routing>
### Plugin Owner Routes

| Response | Workflow |
|----------|----------|
| 1, "onboard", "add", "new plugin", "import" | `workflows/onboard-plugin.md` |
| 2, "update", "bump", "upgrade", "version" | `workflows/update-plugin.md` |
| 3, "status", "check", "health" | Run inline status checks |
| 4, "fix", "debug", "failure", "error" | `workflows/fix-build.md` |
| 5, "metadata", "artifact", "dynamicArtifact", "plugin version", "installation tag" | Run inline metadata lookup |

### Core Team Routes

| Response | Workflow |
|----------|----------|
| 6, "triage", "prioritize", "backlog" | `workflows/triage-prs.md` |
| 7, "analyze", "check PR", "PR #" | `workflows/analyze-pr.md` |
| 8, "publish", "trigger" | Run inline publish trigger |

**After reading the workflow, follow it exactly.**
</routing>

<inline_status_check>
For status checks, use the CLI:

```bash
$RHDH workspace list              # List all workspaces
$RHDH workspace status <name>     # Check specific workspace
```

Or run direct commands:

```bash
# Recent CI runs
gh run list --repo redhat-developer/rhdh-plugin-export-overlays --limit 5

# Open PRs for workspace
gh pr list --repo redhat-developer/rhdh-plugin-export-overlays --search "<name>"
```

</inline_status_check>

<inline_metadata_lookup>
For plugin metadata lookup (e.g. version, package name) or for installation tag/reference lookup (`spec.dynamicArtifact` metadata), use:

```bash
# Preferred (if rhdh-local skill is installed)
python skills/rhdh-local/scripts/fetch-plugin-metadata.py <plugin-name> --branch <branch-or-tag>
```

Fallback (overlay-only install): resolve `spec.packages` from
`catalog-entities/extensions/plugins/<plugin-name>.yaml` first, then locate each
package metadata file under `workspaces/<plugin-workspace>/metadata/<file>.yaml`, and
read metadata there.

</inline_metadata_lookup>

<inline_publish_trigger>
For triggering publish on one or more PRs:

```bash
REPO="redhat-developer/rhdh-plugin-export-overlays"

# Single PR
gh pr comment <number> --repo $REPO --body "/publish"

# Check if publish already ran
gh pr view <number> --repo $REPO --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.name | contains("publish"))'
```

**Guards before triggering:**

1. PR is open (not closed/merged)
2. No `do-not-merge` label
3. Publish check not already successful

See `../rhdh/references/github-reference.md` for full patterns. If unavailable, use standard `gh` CLI patterns.
</inline_publish_trigger>

<reference_index>
**Overlay repo patterns:** references/overlay-repo.md
**CI feedback interpretation:** references/ci-feedback.md
**Metadata format:** references/metadata-format.md
**PR label priorities:** references/label-priority.md
**RHDH Local testing:** references/rhdh-local.md

**For GitHub/JIRA patterns:** See `../rhdh/references/` (if unavailable, use standard `gh` / `acli` patterns)
</reference_index>

<workflows_index>

### Plugin Owner Workflows

| Workflow | Purpose |
|----------|---------|
| onboard-plugin.md | Full 6-phase process to add new plugin |
| update-plugin.md | Bump to newer upstream version |
| fix-build.md | Debug and resolve CI failures |

### Core Team Workflows

| Workflow | Purpose |
|----------|---------|
| triage-prs.md | Prioritize open PRs by criticality |
| analyze-pr.md | Deep-dive on single PR (assignment, compat, readiness) |
| doctor.md | Environment setup guidance |
</workflows_index>

<templates_index>

| Template | Purpose |
|----------|---------|
| workspace-files.md | source.json, plugins-list.yaml, backstage.json |
</templates_index>

<success_criteria>

### Plugin Owner Success

- Plugin workspace created with correct structure
- CODEOWNERS entry added for the workspace
- CI passes (`/publish` succeeds)
- Plugin tested locally with rhdh-local
- PR merged to overlay repo
- *(Recommended)* Activity logged via `$RHDH log add`

### Core Team Success

- PR backlog prioritized with actionable next steps
- Stale PRs identified with suggested owners
- Publish triggered on PRs needing it
- Compatibility issues flagged before merge
- *(Recommended)* Triage session logged, follow-ups tracked via `$RHDH todo`
</success_criteria>
