---
name: bug-fix
description: >
  Reproduce, diagnose, fix, and PR plugin bugs from Jira tickets or GitHub
  issues. Works with both rhdh-plugins and community-plugins. Supports UI bugs
  (Playwright e2e with before/after recordings) and backend bugs
  (unit/integration test verification). Triages issues for agent-readiness
  before attempting a fix. Accepts a Jira key (RHDHBUGS-1934), Jira URL
  (redhat.atlassian.net/browse/...), GitHub issue URL
  (github.com/.../issues/N), or a request to "fix this bug", "reproduce and
  fix", "/bug-fix". By default, stops after the fix for user verification
  before PR creation. Supports --no-verify mode to skip the verification gate
  and auto-create the PR. Chains into raise-pr for the full PR lifecycle.
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Bug Fix Skill ==========="
```
This must happen before any other work (reading references, MCP calls, etc.).
</principle>

<principle name="repro_test_is_temporary">
The reproduction test (`_repro-<KEY>.test.ts`) is a diagnostic tool, not a deliverable. It is deleted before staging. It must never appear in the PR.
</principle>

<principle name="runtime_discovery">
Do not hardcode workspace internals. Discover each workspace's e2e infrastructure at runtime by reading its `playwright.config.ts`, `e2e-tests/utils/`, and `plugins/*/src/translations/ref.ts`. The `references/workspace-map.md` maps issue metadata (Jira components, GitHub labels) to workspace directories, but everything else is discovered dynamically.
</principle>

<principle name="video_evidence">
**Applies to full-e2e mode only.** In no-e2e mode (backend bugs or workspaces without Playwright), video recordings are not captured and this principle is skipped.

In full-e2e mode, every bug fix PR with a UI change MUST include before/after screen recordings. This is NON-NEGOTIABLE and cannot be skipped, deferred, or worked around. The recordings prove the bug existed and the fix resolves it.

Enforcement rules:
- The reproduction test MUST be written and run BEFORE any fix is applied (Steps 3-4 happen before Step 5). Violating this order means there is no "before" state to record.
- The repro test MUST create its own browser context with `recordVideo` — NEVER use workspace bootstrap helpers (e.g., `bootstrapLightspeedE2ePage`) as they do not enable video recording.
- If video files are not present in `e2e-tests/_repro-artifacts/` at Step 8, STOP and go back to capture them. Do NOT proceed to PR creation without recordings.
- If the Playwright `context.close()` call is missing, the video file will be incomplete — always close the context.
</principle>

<principle name="fix_after_repro">
**Applies to full-e2e mode only.** In no-e2e mode, diagnosis and fix use unit tests instead of Playwright — see Step 2.5.

In full-e2e mode, NEVER apply the code fix before Steps 3 and 4 are complete. The correct order is:
1. Write repro test (Step 3)
2. Run repro test — it must FAIL (bug confirmed)
3. Capture "before" video (Step 4)
4. ONLY THEN apply the fix (Step 5)

If you find yourself wanting to fix first and test after, STOP — you are violating the step order. The "before" recording cannot be captured retroactively.
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner to the terminal so the user can track progress — even if the step's actual work is done via MCP tools or file reads rather than shell commands:
```
echo "================ Step N — <Step title> ==========="
```
This applies to ALL steps including Step 1. Run the echo command in the terminal before doing anything else for that step.
</principle>

<principle name="preflight_port_cleanup">
Before running any Playwright test, check whether the dev-server port (from `playwright.config.ts`) is already in use. If it is, kill the process occupying it:
```
lsof -ti:<PORT> | xargs kill -9 2>/dev/null || true
```
A stale dev server from a prior session will cause the test to connect to the wrong app and time out.
</principle>

<principle name="preflight_system_limits">
Before running any Playwright test, ensure the system file descriptor limit is raised and the shell command runs without sandbox restrictions to avoid restrictions on browser launch:
```
ulimit -n 65536 2>/dev/null || true
```
Without this, webpack's file watcher (Watchpack) may hit `EMFILE: too many open files` and crash Chrome/Chromium. This is primarily needed on macOS where the default file descriptor limit is 256. Linux typically defaults to 1024+ and may not require this adjustment.
</principle>

</essential_principles>

## Prerequisites

Tools are verified automatically in Step 0.5 (Readiness Check). The lists below document what is needed:

- **`gh` CLI** — GitHub CLI must be installed and authenticated (`gh auth status`). Required for ALL paths (PR creation + GitHub issue fetching). Install: https://cli.github.com/
- **Jira access (if Jira issue)** — At least ONE of:
  - `acli` on PATH + `.jira-token` configured. [ACLI docs](https://developer.atlassian.com/cloud/acli/guides/how-to-get-started/)
  - Jira MCP (Atlassian Rovo MCP server). [Setup guide](https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/)
- Working checkout of `rhdh-plugins` or `community-plugins`
- `yarn` available on PATH
- `ffmpeg` available on PATH (good-to-have; for video conversion; fall back to raw `.webm` if absent)

---

## Mode: check for `--no-verify` flag

Check if the user invoked this skill with `--no-verify`.

- **`--no-verify` present:** After the fix is verified (Step 6), skip the verification gate — chain directly into `raise-pr --a` (all approval gates auto-approved).
- **`--no-verify` absent (default):** After the fix is verified, STOP and present a summary for the user to verify locally. The user then invokes `raise-pr` or `raise-pr --a` when ready.

---

## Step 0 — Detect issue source (string parsing only)

Determine whether the user provided a Jira issue or a GitHub issue. This step is pure string parsing — it does NOT fetch or call any external tool.

1. Check the user's input against these patterns:

   **Jira patterns** (follow parsing rules in `raise-pr/references/jira-input.md`):
   - Bare key: `RHDHBUGS-1934`
   - Browse URL: `https://redhat.atlassian.net/browse/RHDHBUGS-1934`
   - URL without scheme: `redhat.atlassian.net/browse/RHIDP-15252`

   **GitHub patterns** (follow parsing rules in `references/github-input.md`):
   - Full URL: `https://github.com/redhat-developer/rhdh-plugins/issues/607`
   - Short URL: `github.com/backstage/community-plugins/issues/3574`
   - Bare number in checkout context: `#123` (resolve repo from `git remote -v`)

2. Store `issue_source` = `jira` or `github`.
   - For GitHub: also extract `github_issue_repo` and `github_issue_number` from the URL. The target repo is known from the URL.
   - For Jira: extract `jira_key`. The target repo is NOT known yet — it is resolved later in Step 2 from the workspace/component mapping.

**Do NOT fetch issue details yet** — that happens after the readiness check confirms the required tools are available.

---

## Step 0.5 — Readiness check

Verify that all required tools are available before attempting to fetch the issue or fix the bug. The checks are source-aware based on `issue_source` from Step 0.

Echo a readiness table to the terminal:

```
echo "================ Readiness Check ==========="
```

### Must-have (all contexts)

| Tool | Check command | Install link |
|------|--------------|-------------|
| `gh` CLI | `gh auth status` | https://cli.github.com/ |
| `yarn` | `yarn --version` | — |
| `node` | `node --version` | — |
| Working checkout | `git remote -v` matches `rhdh-plugins` or `community-plugins` | — |

### Must-have (source-conditional)

| Condition | Tool | Check |
|-----------|------|-------|
| Jira issue | At least ONE of: `acli` + `.jira-token`, OR Jira MCP | `which acli` + token file exists, OR MCP tool discovery |

### Good-to-have (warn only, do not block)

| Tool | Condition | What it enables | Link |
|------|-----------|----------------|------|
| `ffmpeg` | Always | Video conversion (.webm → .gif) | https://ffmpeg.org/download.html |
| `acli` | GitHub issue path | Jira cross-linking if needed later | https://developer.atlassian.com/cloud/acli/guides/how-to-get-started/ |
| Second Jira tool | Jira path, only one of ACLI/MCP present | ACLI: transitions + labels. MCP: rich reads + comments | — |

### Output format

```
 [PASS]  gh CLI — authenticated as <user>
 [PASS]  yarn — v<version>
 [PASS]  node — v<version>
 [PASS]  Working checkout — rhdh-plugins (detected from git remote)
 [PASS]  acli — v<version>
 [PASS]  .jira-token — configured
 [WARN]  ffmpeg — not found (video will remain as .webm) — https://ffmpeg.org/download.html
 [WARN]  Jira MCP — not configured (Jira comment updates will be skipped)
```

**If ANY must-have check fails:** STOP with clear instructions on how to install/configure the missing tool.

**If only good-to-have items are missing:** proceed with warnings.

---

## Step 1 — Fetch issue details

Now that the readiness check has confirmed the required tools are available, fetch the issue.

### If `issue_source` = `jira`

Read `references/workspace-map.md` for the Jira component-to-workspace mapping.

1. Fetch the full issue details using Jira MCP (`read_jira_issue`) or REST API (per `raise-pr/references/jira-input.md`):
   - Summary, description, steps to reproduce
   - Component field (maps to workspace)
   - Status (for post-PR transition)
   - Attachments/screenshots (visual reference for reproduction)
2. Store: `jira_key`, `jira_url`, `jira_summary`, `jira_description`, `jira_component`, `jira_status`

### If `issue_source` = `github`

Read `references/github-input.md` for `gh` CLI patterns.

1. Fetch the issue:
   ```
   gh issue view <NUMBER> --repo <owner/repo> --json title,body,labels,state,comments
   ```
2. Store: `github_issue_number`, `github_issue_url`, `github_issue_repo`, `github_issue_title`, `github_issue_body`, `github_issue_labels`

---

## Step 1.5 — Issue triage

Validate that the issue has enough detail for an automated fix. This gate prevents wasted effort on underspecified bugs.

### Required fields

Regardless of source, the issue must contain:

- **Steps to reproduce** — clear numbered steps
- **Expected behavior** — what should happen after the fix
- **Component / workspace** — identifiable from Jira Component field, GitHub `workspace/*` label, issue title prefix, or issue body
- **Target repository** — derivable from GitHub issue URL directly, or from Jira Component-to-workspace mapping

For **Jira issues**, map to the standard bug template fields:
- `Description of problem` — present
- `Steps to Reproduce` — present
- `Expected results` — present

For **GitHub issues**, scan the issue body for headings or sections containing reproduction steps and expected behavior (common patterns: `## Steps to reproduce`, `## Expected behavior`, `### How to reproduce`, `### Reproduction steps`).

### If triage fails (not agent-ready)

Automatically:

1. **Add label** `not-ready-for-agent` on the issue:
   - Jira: `acli jira workitem edit --key "$KEY" --label "not-ready-for-agent" --yes`
   - GitHub: `gh issue edit <N> --repo <repo> --add-label "not-ready-for-agent"`

2. **Add comment** with a missing-info checklist (only unchecked items are those actually missing; present items show as checked):

   ```
   This bug is not ready for automated fixing. The following information is missing:

   - [ ] Steps to reproduce
   - [ ] Component / workspace
   - [ ] Expected behavior
   - [ ] Target repository (rhdh-plugins or community-plugins)

   Please update this ticket with the missing details and remove the "not-ready-for-agent" label when ready.
   ```

3. **Echo the same to the user** in the terminal.

4. **STOP** — do not proceed with the fix.

### If triage passes

Echo a summary of extracted fields (issue key/URL, summary, workspace, repo) and proceed to Step 2.

---

## Step 2 — Identify workspace, repo, and discover infrastructure

Read `references/workspace-map.md` for workspace detection strategies.

### Workspace and repo detection

**If `issue_source` = `github`:**
The target repo is already known from the issue URL. Identify the workspace within that repo using the strategies in `references/workspace-map.md` (labels, body fields, title prefix, package names). See also `references/github-input.md` for workspace extraction from GitHub issues.

**If `issue_source` = `jira`:**
The target repo is NOT yet known. Map the Jira **Component** field to a workspace directory using `references/workspace-map.md`. The workspace mapping determines which repo to target (rhdh-plugins vs community-plugins).
- If no component is set or the component is unknown: ask the user which workspace and repo to target.

### Navigate and discover

1. Navigate to the workspace: `cd workspaces/<workspace-dir>`
2. **Discover infrastructure dynamically**:
   - Read `playwright.config.ts` (if present) for port configuration, locale list, start commands, and `APP_MODE` support.
   - Scan `e2e-tests/utils/` to discover available helper functions (translations, navigation, API mocking, accessibility).
   - Read `plugins/*/src/translations/ref.ts` for translation key structure (used for i18n-safe selectors).
   - Read `plugins/*/src/components/` to build a component-to-source-file map.
3. Run `yarn install` if `node_modules` is missing or stale.

Read `references/e2e-patterns.md` for shared Playwright patterns.

### Step 2.5 — Determine e2e mode

After discovering the workspace infrastructure, determine the execution mode:

- **full-e2e mode** — when the workspace has `playwright.config.ts` AND the bug involves a UI component.
- **no-e2e mode** — when the workspace has NO `playwright.config.ts`, OR the bug is backend-only (API, config, logic, data processing).

**In full-e2e mode:** Proceed with Steps 3–7 as defined (write repro test, capture before video, fix, capture after video, convert videos).

**In no-e2e mode:** Skip Steps 3, 4, 6, 7 entirely. The workflow becomes:

1. **Check existing test coverage**: Run `yarn test --watchAll=false` and check if any existing test already fails on the bug. If yes, use that test as the repro confirmation — no need to write a new one.
2. **If no existing test covers the bug**: Write a temporary repro unit test (`_repro-<KEY>.test.ts`) that reproduces the bug. Run it — it should FAIL (bug confirmed).
3. **Diagnose root cause**: No browser-based diagnostics (screenshots, DOM snapshots, computed styles) are available. Diagnosis relies on source code analysis, error logs/stack traces from the issue description, and test output.
4. **Apply the fix** in source code.
5. **Verify**: `yarn tsc:full` + `yarn test --watchAll=false` — all tests must pass (including the repro test or the previously-failing existing test).
6. **Delete repro test** if one was written (same principle as full-e2e: the repro test is a diagnostic tool, not a deliverable).
7. Proceed to Step 8 — but with NO recordings in caller context.

---

## Step 3 — Write reproduction test with video recording [full-e2e only]

Read `references/e2e-patterns.md` for test patterns and `references/video-recording.md` for video configuration.

1. Create a temporary test file: `e2e-tests/_repro-<KEY>.test.ts` (where `<KEY>` is the Jira key or GitHub issue number, e.g., `_repro-RHDHBUGS-1934.test.ts` or `_repro-607.test.ts`).
   - The `_` prefix signals this file is temporary and should not be committed.
2. The test must:
   - Import workspace-specific helpers discovered in Step 2 **only for navigation/setup** (e.g., API mocking, translations).
   - Use i18n-safe selectors (via translation keys) where available.
   - **Always create its own browser context with video recording** — do NOT rely on workspace bootstrap helpers for the context, as they may not enable video. Use the `browser` fixture directly:
     ```typescript
     test('repro', async ({ browser }) => {
       const context = await browser.newContext({
         recordVideo: { dir: 'test-results/', size: { width: 1280, height: 720 } },
       });
       const page = await context.newPage();
       
       // ... test steps using page ...
       
       await context.close(); // finalizes the video file
     });
     ```
     This guarantees video recording regardless of how the workspace's own e2e infrastructure manages contexts.
   - **CRITICAL**: Do NOT use workspace-provided bootstrap/setup functions (like `bootstrapLightspeedE2ePage`, `setupE2eTest`, etc.) as the browser context source. These helpers create contexts WITHOUT video recording. You MUST call `browser.newContext({ recordVideo: ... })` yourself and then replicate only the mock setup from those helpers (API mocking, route handlers) on your custom page. Copy the mock calls — not the context creation.
   - Encode the "steps to reproduce" from the issue description as Playwright actions.
   - Assert the **expected** behavior (the assertion should fail when the bug is present).
3. **Pre-flight: kill stale dev server** — before running the test, ensure the dev-server port (read from `playwright.config.ts` `webServer.url`) is free:
   ```
   lsof -ti:<PORT> | xargs kill -9 2>/dev/null || true
   ```
4. Run the test against the `en` locale in legacy mode. **Always** prefix with `ulimit -n 65536` and ensure the command runs without sandbox restrictions:
   ```
   ulimit -n 65536 && APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
   ```
5. The test should **fail** — confirming the bug is reproduced.

**If the test passes** (bug not reproduced): re-read the issue description, adjust the test, and retry. If still not reproducible after 2 attempts, report findings and ask the user for guidance.

---

## Step 4 — Capture "before" recording [full-e2e only]

1. After the failed test run (Step 3), locate the video file in `test-results/`.
   - Playwright saves videos at `test-results/<test-title>/video.webm`.
2. Copy the video to a stable path:
   ```
   mkdir -p e2e-tests/_repro-artifacts
   cp test-results/*/video.webm e2e-tests/_repro-artifacts/before-fix.webm
   ```
3. Store the path for later conversion (Step 7).

**If no video file is found in `test-results/`**: the test likely used a bootstrap helper instead of a custom `recordVideo` context. Rewrite the test to use `browser.newContext({ recordVideo: ... })` directly, then re-run.

---

## Step 5 — Diagnose and fix

**In no-e2e mode:** Skip sub-step 1 (browser diagnostics are not available). Start directly from sub-step 2 using source code analysis, error logs/stack traces from the issue description, and unit test output.

1. **Capture diagnostic context** [full-e2e only] from the failing state (before applying any fix). Re-use the reproduction test or run a lightweight Playwright script to gather:

   a. **Screenshot** of the buggy UI state:
      ```typescript
      await page.screenshot({ path: 'e2e-tests/_repro-artifacts/bug-state.png', fullPage: true });
      ```
   b. **DOM snapshot** of the target element:
      ```typescript
      const targetEl = page.locator('<selector-under-test>');
      const domSnapshot = await targetEl.evaluate(el => el.outerHTML);
      ```
   c. **Computed styles** of the target element (capture properties relevant to the bug):
      ```typescript
      const styles = await targetEl.evaluate(el => {
        const cs = window.getComputedStyle(el);
        return { display: cs.display, overflow: cs.overflow, scrollbarWidth: cs.scrollbarWidth };
      });
      ```

   Use the screenshot (read it as an image), DOM structure, and computed styles to identify the exact root cause before modifying any source files. This provides concrete runtime evidence rather than guessing from source alone.

2. **Diagnose**: trace from the failing Playwright selector back to the source:
   - Identify which React component renders the UI element under test.
   - Read the component source code (`plugins/*/src/components/`).
   - Cross-reference the captured DOM/styles with the component's render logic to pinpoint the root cause (e.g., MUI prop misconfiguration, missing state update, CSS issue, accessibility gap, i18n key mismatch).
3. **Apply the fix** in the source code.
4. **Validate**:
   - `yarn tsc:full` — type check passes.
   - `yarn test --watchAll=false` — unit tests pass.

**Confidence gates** — ask the user before proceeding if:
- Multiple possible root causes exist — present options and let the user choose.
- The fix touches more than 3 files — show the plan and get approval.
- The fix changes API surface or public types — this may need a minor version bump.

---

## Step 6 — Capture "after" recording [full-e2e only]

1. Re-run the reproduction test (with `ulimit` and without sandbox restrictions):
   ```
   ulimit -n 65536 && APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
   ```
2. The test should **pass** — confirming the fix works.
3. Copy the video:
   ```
   cp test-results/*/video.webm e2e-tests/_repro-artifacts/after-fix.webm
   ```
4. Optionally run in NFS mode as well to check for mode-specific regressions:
   ```
   APP_MODE=nfs npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
   ```

**If the test still fails after the fix**: re-examine the diagnosis and iterate.

---

## Step 7 — Convert videos for PR embedding [full-e2e only]

Read `references/video-recording.md` for conversion details.

1. Check if `ffmpeg` is available on PATH.
2. **If available**: convert `.webm` to `.gif`:
   ```
   ffmpeg -i e2e-tests/_repro-artifacts/before-fix.webm -vf "fps=10,scale=800:-1" -loop 0 e2e-tests/_repro-artifacts/before-fix.gif
   ffmpeg -i e2e-tests/_repro-artifacts/after-fix.webm -vf "fps=10,scale=800:-1" -loop 0 e2e-tests/_repro-artifacts/after-fix.gif
   ```
3. **If `ffmpeg` is not available**: keep the `.webm` files and note that they will be uploaded as PR comment attachments instead of inline GIFs.

---

## Step 8 — Clean up and create PR

### 8.0 — Validate recordings exist [HARD GATE — full-e2e only]

**In no-e2e mode:** Skip this sub-step entirely — there are no recordings to validate.

**In full-e2e mode:** Before proceeding with cleanup or PR creation, verify both recording files exist:

```
test -f e2e-tests/_repro-artifacts/before-fix.webm || { echo "ERROR: before-fix.webm missing — go back to Step 4"; exit 1; }
test -f e2e-tests/_repro-artifacts/after-fix.webm || { echo "ERROR: after-fix.webm missing — go back to Step 6"; exit 1; }
```

If either file is missing, DO NOT proceed. Return to the relevant step (4 or 6) and capture the recording. This gate ensures the PR will always have visual evidence.

### 8.1 — Delete temporary files

Remove the reproduction test and artifacts — these must not appear in the PR:

**In full-e2e mode:**
```
rm e2e-tests/_repro-<KEY>.test.ts
rm -rf test-results/
```
Keep `e2e-tests/_repro-artifacts/` temporarily (needed for PR image upload).

**In no-e2e mode:**
```
rm _repro-<KEY>.test.ts    # if a temporary repro unit test was written
rm -rf test-results/
```

### 8.2 — Stage fix files

Stage only the code fix (not the repro test or artifacts):

```
git add <fixed-source-files>
```

### 8.3 — Prepare caller context

Assemble the caller context that will be passed to `raise-pr`. This is prepared regardless of verify mode. Include only the fields relevant to the `issue_source`.

| Field | Value | Condition |
|-------|-------|-----------|
| `issue_source` | `jira` or `github` | Always |
| `jira_key` | The resolved Jira key from Step 1 | Jira only |
| `jira_url` | `https://redhat.atlassian.net/browse/<jira_key>` | Jira only |
| `jira_summary` | Issue summary from Step 1 | Jira only |
| `github_issue_number` | Issue number from Step 0 | GitHub only |
| `github_issue_url` | Full GitHub issue URL | GitHub only |
| `github_issue_repo` | `owner/repo` (e.g., `redhat-developer/rhdh-plugins`) | GitHub only |
| `github_issue_title` | Issue title from Step 1 | GitHub only |
| `recordings` | `{ before: "e2e-tests/_repro-artifacts/before-fix.gif", after: "e2e-tests/_repro-artifacts/after-fix.gif" }` | full-e2e only; `null` in no-e2e mode |
| `pr_description_extra` | `### Root cause\n<diagnosis from Step 5>` | Always |
| `test_plan` | Auto-generated markdown checklist (see below) | Always |

**Generating the `test_plan`:**

Build a markdown checklist of verification steps for the reviewer. Derive them from:
1. **Steps-to-reproduce** — convert each step into a positive verification action (e.g., "Click Help menu" becomes "- [ ] Open the Help menu").
2. **Expected behavior after fix** — add steps verifying the fix works (e.g., "- [ ] Verify scrollbar appears on hover").
3. **Regression check** — add at least one step confirming nothing else broke (e.g., "- [ ] Verify other menus/display modes are unchanged").

Example output:
```
- [ ] Open the dropdown menu with many items
- [ ] Verify scrollbar is hidden by default
- [ ] Hover over the menu content area
- [ ] Verify scrollbar becomes visible on hover
- [ ] Verify other dropdown menus are unaffected
```

### 8.4 — Verification gate [MODE-DEPENDENT]

**If `--no-verify`:** Chain into `raise-pr --a` immediately with the caller context from Step 8.3. Skip to Step 8.5 after PR creation.

`raise-pr` handles: repo detection, build, changeset, commit (with `Fixes:` trailer), push, PR creation (with `## UI before/after changes` and `## Test Plan`), and post-PR updates (Jira comment/transition or GitHub issue comment/label depending on `issue_source`).

> `raise-pr` uploads the GIF files to the branch via GitHub Contents API and embeds the resulting `raw.githubusercontent.com` URLs directly in the PR description. No manual image upload or separate PR comment is needed.

**If default (no flag):** STOP and present a verification summary to the user:

1. **Modified files** — list all source files changed by the fix.
2. **Root cause** — the diagnosis from Step 5.
3. **Recordings** — paths to before/after GIF files.
4. **Caller context** — print the assembled caller context table (from Step 8.3) so the user can confirm everything is ready.
5. **Next steps** — instruct the user:

```
Fix complete. Verify the changes locally, then create the PR:
  raise-pr              — interactive mode (approval gates at branch, staging, commit)
  raise-pr --a          — auto-approve mode (skip all gates)
```

The agent retains the caller context in the conversation. When the user invokes `raise-pr` or `raise-pr --a`, pass the full caller context from Step 8.3 so that `raise-pr` includes the Jira link, recordings, root cause, and test plan in the PR.

### 8.5 — Final cleanup

After the PR is created, delete the artifacts directory:

```
rm -rf e2e-tests/_repro-artifacts/
```

---

## When NOT to Use

- **Bugs requiring live backend data** — if reproduction depends on real API responses that cannot be mocked via the workspace's e2e test infrastructure.
- **Cross-workspace bugs** — if the fix requires changes across multiple workspaces, handle each workspace separately or use `raise-pr` directly.
- **Unsupported issue trackers** — this skill supports Jira (RHIDP, RHDHBUGS, RHDHPLAN, RHDHSUPP projects) and GitHub issues (rhdh-plugins, community-plugins). Other trackers or repos are not supported.

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/workspace-map.md` | Always — at the start of every invocation (Steps 0-2) |
| `references/github-input.md` | When `issue_source` = `github` (Steps 0, 1) |
| `references/e2e-patterns.md` | When writing the reproduction test — full-e2e mode only (Step 3) |
| `references/video-recording.md` | When configuring video capture — full-e2e mode only (Steps 3, 7) |
| `raise-pr/references/jira-input.md` | When `issue_source` = `jira` (Step 0) — shared with raise-pr |
| `raise-pr/references/repo-profiles.md` | Loaded by raise-pr during Step 8 chain |

</reference_index>
