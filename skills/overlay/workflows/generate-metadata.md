# Workflow: Generate and Audit Package Metadata

Generate missing `kind: Package` metadata YAML files for plugins in an overlay workspace, and audit existing metadata for consistency issues.

<required_reading>
**Read these reference files NOW:**

1. `references/metadata-format.md` — Package and Plugin entity structure
2. `references/overlay-repo.md` — Workspace patterns and file layout
</required_reading>

<prerequisites>
| Requirement | Details |
|-------------|---------|
| **Overlay repo** | Local checkout of [rhdh-plugin-export-overlays](https://github.com/redhat-developer/rhdh-plugin-export-overlays) |
| **Tools** | `gh` CLI (authenticated with GitHub) |
| **Script** | `scripts/derive-metadata.py` — handles deterministic field derivation, workspace scanning, and env var extraction |
</prerequisites>

<process>

## Phase 1: Workspace Identification

If the workspace name is already known from context (e.g., called from `onboard-plugin.md` Phase 4), use it.

Otherwise, ask the user which workspace to operate on.

Confirm the workspace exists:

```bash
ls workspaces/<workspace>/source.json workspaces/<workspace>/plugins-list.yaml
```

---

## Phase 2: Scan for Missing Metadata

Run the scan command from the overlay repo root (no network needed):

```bash
python3 scripts/derive-metadata.py scan --workspace <workspace>
```

This returns JSON with: `missing_metadata` (plugin paths without metadata files), `version_mismatches` (existing files with stale `supportedVersions`), `empty_config_issues` (files with `appConfigExamples: []` but no `appConfigNotRequired`), `existing_metadata` (copyable fields from existing files), and `source_paths` (upstream paths for GitHub API calls).

If `missing_count` is 0, report "All plugins already have metadata — no new files needed." Skip Phases 3–5 and proceed directly to Phase 6.3 (consistency checks using the scan output).

Otherwise, list the missing plugins and proceed.

---

## Phase 3: Fetch Upstream Source and Derive Fields

For each missing plugin, fetch its `package.json` and optionally `config.d.ts` from the upstream repo using direct `gh api` calls (these go through the user's command allowlist — no sandbox permission needed), then run the derive script to compute all metadata fields.

### 3.1 Fetch and derive per plugin

For each plugin path in `missing_metadata`, use the corresponding entry from `source_paths` and the `repo_ref` and `owner_repo` from the scan output:

**Fetch package.json:**

```bash
gh api "repos/<owner_repo>/contents/<source_path>/package.json?ref=<repo_ref>" --jq '.content' | base64 -d
```

**Derive metadata fields** (pass the fetched JSON to the script — no network needed):

```bash
python3 scripts/derive-metadata.py derive \
  --workspace <workspace> \
  --plugin-path <plugin-path> \
  --package-json '<package.json content>'
```

This returns JSON with all deterministic fields: `metadata_name`, `filename`, `title`, `packageName`, `version`, `role`, `dynamicArtifact`, `supportedVersions`, `sourceCodeUrl`, `bugsUrl`, plus `author`, `support`, `lifecycle`, `partOf` copied from existing metadata (if any).

The script handles:
- **Name derivation**: strips `@`, replaces `/` with `-`, shortens if >63 chars using [shorten-component-name.sh](https://github.com/redhat-developer/rhdh-plugin-export-utils/blob/main/common/scripts/shorten-component-name.sh) rules
- **OCI URL**: `oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/<name>:bs_<ver>__<ver>!<name>`
- **Links/annotations**: Source Code URL respects `repo-flat` and plugin path (handles `.` for root-level plugins)
- **supportedVersions**: from `backstage.json` override or `source.json`
- **Existing metadata fields**: copies `author`, `support`, `lifecycle`, `partOf` from existing files
- **Support level**: if the derived `support` is `generally-available` or `tech-preview` (copied from existing metadata), the script sets `support_needs_confirmation: true`. Ask the user: "Existing metadata uses `<support>`. Apply the same tier to the new package, or default to `community`?" If the context does not allow asking, default to `community`.

### 3.2 Fetch config.d.ts (if present)

```bash
gh api "repos/<owner_repo>/contents/<source_path>/config.d.ts?ref=<repo_ref>" --jq '.content' | base64 -d
```

If this returns a 404, the plugin has no config schema — that's fine.

### 3.3 Check for frontend source files

```bash
gh api "repos/<owner_repo>/contents/<source_path>/src?ref=<repo_ref>" --jq '.[].name'
```

Note whether `plugin.ts`, `plugin.tsx`, or `alpha.ts` are present — needed for Phase 4 frontend wiring.

**`supportedVersions` mismatches** were already detected in Phase 2 scan output (`version_mismatches`). Use the correct derived value for new metadata and carry the mismatch list to Phase 5

---

## Phase 4: Analyze Config and Wiring Per Plugin

For each plugin, analyze its configuration schema and frontend wiring using the data fetched in Phase 3.

### 4a. Analyze config schema

Use the `config.d.ts` content fetched in Phase 3.2 (if present).

**If `config.d.ts` content was fetched** for this plugin:

1. Parse the TypeScript `Config` interface to extract:
   - Config key paths (e.g., `argocd.baseUrl`, `argocd.appLocatorMethods[].instances[].url`)
   - Types (string, boolean, number, array, object)
   - `@visibility` annotations (`frontend`, `backend`, `secret`)
   - JSDoc descriptions

2. If more source context is needed to validate config usage, fetch individual files via `gh api` as needed (this may require one additional authorization).

3. Generate `appConfigExamples` content using placeholder values:
   - `@visibility secret` fields → `${UPPER_SNAKE_CASE}` env var placeholder (e.g., `${ARGOCD_PASSWORD}`)
   - String fields → realistic placeholder URL or name (e.g., `https://argocd.example.com`)
   - Boolean fields → `true` or `false`
   - Number fields → sensible default from JSDoc or `0`
   - Array fields → one example entry

**If NO `config.d.ts` content is present:**

- For **backend plugins**: set `appConfigNotRequired: true` and `appConfigExamples: []`
- For **frontend plugins**: `appConfigExamples` will contain only the wiring section from 4b

### 4b. Frontend wiring (frontend plugins only)

Use the `plugin.ts`/`alpha.ts` presence from Phase 3.3 to determine which source files to analyze. If needed, fetch them via `gh api`:

```bash
gh api repos/<owner>/<repo>/contents/<source-path>/src/plugin.ts?ref=<repo-ref> --jq '.content' | base64 -d
```

Alternatively, delegate to the **`generate-frontend-wiring` skill** to analyze:
- `src/plugin.ts` / `src/plugin.tsx` — `createRoutableExtension`, `createComponentExtension` calls
- `src/alpha.ts` — new frontend system extensions
- `src/index.ts` — public exports

Merge the resulting `dynamicPlugins.frontend.<scalprum-name>` section into `appConfigExamples`:

```yaml
appConfigExamples:
  - title: Default configuration
    content:
      dynamicPlugins:
        frontend:
          <scalprum-name>:
            mountPoints:
              - mountPoint: <mount-point>
                importName: <ImportName>
                config:
                  layout:
                    gridColumn: 1 / -1
```

If both wiring AND config schema exist for a frontend plugin, combine them into a single `appConfigExamples` entry — the `dynamicPlugins` wiring section plus the app-config keys from 4a.

---

## Phase 5: Plugin Entity Resolution

### 5a. Existing metadata exists in the workspace

Extract `partOf` values from existing Package YAML files. Use the same `partOf` for all new packages.

### 5b. No existing metadata — called from onboard-plugin

Create a Plugin entity at `catalog-entities/extensions/plugins/<workspace>.yaml`:

```yaml
apiVersion: extensions.backstage.io/v1alpha1
kind: Plugin
metadata:
  name: <workspace-name>
  namespace: rhdh
  title: <TODO: Display title>
  description: <TODO: Brief description for listing>
spec:
  description: |
    ## Overview
    <TODO: What the plugin does>

    ## Features
    - <TODO: Feature 1>

    ## Configuration
    <TODO: How to configure>
  packages:
    - <metadata-name-1>
    - <metadata-name-2>
  categories:
    - <TODO: Category>
  highlights:
    - <TODO: Highlight 1>
  developer: <author from Phase 2 output>
  supportLevel: community
```

Also add the file to `catalog-entities/extensions/plugins/all.yaml` in alphabetical order.

Set `partOf` for all Package entities to the Plugin entity's `metadata.name`.

### 5c. No existing metadata — called standalone

Ask the user: "No Plugin entity found for this workspace. Do you want to create one?"

- If yes: follow 5b
- If no: leave `partOf` empty

---

## Phase 6: Write Files and Report

### 6.1 Assemble and write Package YAML files

For each plugin, assemble the full Package YAML:

```yaml
apiVersion: extensions.backstage.io/v1alpha1
kind: Package
metadata:
  name: <metadata-name>
  namespace: rhdh
  title: "<title>"
  links:
    - url: https://red.ht/rhdh
      title: Homepage
    - url: <repo>/issues
      title: Bugs
    - title: Source Code
      url: <source-code-url>
  annotations:
    backstage.io/source-location: url:<source-code-url>
  tags: []
spec:
  packageName: "<npm-package-name>"
  dynamicArtifact: <oci-url>
  version: <version>
  backstage:
    role: <role>
    supportedVersions: <supported-versions>
  author: <author>
  support: <support>
  lifecycle: <lifecycle>
  partOf:
    - <plugin-entity-name>
  appConfigNotRequired: <true if backend with no config, omit otherwise>
  appConfigExamples:
    <generated examples or []>
```

Write to `workspaces/<workspace>/metadata/<metadata-name>.yaml`.

### 6.2 Update smoke test environment variables

For each generated metadata file, extract env var references:

```bash
python3 scripts/derive-metadata.py extract-env-vars workspaces/<workspace>/metadata/<filename>.yaml
```

If any `${VAR_NAME}` env var placeholders are found, ensure they have corresponding entries in `workspaces/<workspace>/smoke-tests/test.env`.

**If `smoke-tests/test.env` exists:** read it, identify any `${VAR_NAME}` references from the new metadata that are missing from the file, and append them with dummy placeholder values:
- Secret/token fields → `dummy-smoke-test-secret`
- URL fields → `https://smoke-test.example.com/<service>`
- Username fields → `dummyAdmin`
- Password fields → `dummyPassword`
- Other string fields → `dummy-value`

**If `smoke-tests/test.env` does not exist:** create it with the standard header and all required env vars:

```
# Smoke-test placeholders for dynamic plugin config substitution.
# Values are non-production dummies for CI/local smoke runs only.
# Existing entries win over generated defaults; re-run to add missing keys.

VAR_NAME=dummy-value
```

Preserve any existing entries — never overwrite values that are already set.

### 6.3 Audit existing metadata and present summary

This phase always runs — even when no new files were generated (audit-only mode).

**If new files were generated,** show a summary table:

| File | Package Name | Role | Config Found | Wiring |
|------|-------------|------|-------------|--------|
| `<filename>` | `<packageName>` | `<role>` | yes/no (N keys) | N mount points / N/A |

If a Plugin entity was created, note it separately.

**Then run the following consistency checks on ALL metadata files in the workspace (both new and pre-existing):**

#### Check: `supportedVersions` consistency

Derive the expected `supportedVersions` value:
1. If `workspaces/<workspace>/backstage.json` exists, use its `version` field
2. Otherwise, use `repo-backstage-version` from `source.json`

Compare against the `spec.backstage.supportedVersions` in every metadata file. If any files have a stale or incorrect value, list them and ask the user:

> "The following metadata files have `supportedVersions: <old>` but the expected value is `<new>`. Do you want to fix them?"

If the user answers yes, update the `supportedVersions` field in those files. If no, leave them unchanged.

#### Check: `appConfigExamples: []` without `appConfigNotRequired`

Scan all metadata files for files that have `appConfigExamples: []` but are missing `spec.appConfigNotRequired: true`. This combination fails publish validation — an empty `appConfigExamples` is only valid when `appConfigNotRequired: true` is explicitly set. If any files match, list them and ask:

> "The following metadata files have empty `appConfigExamples` but are missing `appConfigNotRequired: true`. Do you want to fix them?"

If the user answers yes, add `appConfigNotRequired: true` above `appConfigExamples: []` in those files. If no, leave them unchanged.

#### Summary

If all checks pass with no issues found, report: "All existing metadata files are consistent — no fixes needed."

### 6.4 Propose commit message and PR description

After all questions have been asked and answered, propose:

**Commit message** (concise, following repo conventions):

When new files were generated:

```
Add metadata for <plugin-name(s)> in <workspace> workspace
```

When new files were generated AND existing files were fixed:

```
Add metadata for <plugin-name(s)> in <workspace> workspace

Also fix <description of fixes> in existing metadata files.
```

When only existing files were fixed (audit-only mode):

```
Fix metadata inconsistencies in <workspace> workspace
```

**PR description** (concise and conformant):

```markdown
## Summary
- <If applicable: Adds Package metadata for N plugin(s) in the `<workspace>` workspace>
- <If applicable: Creates Plugin entity for `<workspace>`>
- <If applicable: Fixes `supportedVersions` in N existing metadata files>
- <If applicable: Adds missing `appConfigNotRequired` to N existing metadata files>
- <If applicable: Adds smoke test env vars to `test.env`>

## Generated files
<list of created/modified files>

## Checklist
- [ ] Package metadata reviewed
- [ ] `appConfigExamples` verified against upstream config schema
- [ ] Smoke test env vars present for all `${VAR}` references
- [ ] `/publish` triggered and successful
```

**Disclaimer:** Review the generated files before committing. Pay special attention to `appConfigExamples` — the config schema analysis may need manual refinement.

</process>

<success_criteria>
This workflow is complete when:

- [ ] All plugins in the workspace have corresponding Package metadata YAML files
- [ ] Each Package YAML has correct `packageName`, `version`, `backstage.role`
- [ ] `appConfigExamples` are populated from config schema analysis (or marked `appConfigNotRequired`)
- [ ] Frontend plugins have `dynamicPlugins` wiring in `appConfigExamples`
- [ ] `metadata.links` and `annotations` point to correct source locations
- [ ] `dynamicArtifact` OCI URL follows the naming convention
- [ ] `metadata.name` respects the 63-character Kubernetes limit (shortened if needed)
- [ ] `partOf` references a valid Plugin entity
- [ ] `smoke-tests/test.env` contains dummy values for all `${VAR}` references in `appConfigExamples`
- [ ] No files have `appConfigExamples: []` without `appConfigNotRequired: true`
- [ ] User has reviewed all generated files
</success_criteria>
