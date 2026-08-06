---
name: raise-pr
description: >
  Automate the full PR workflow for rhdh-plugins and community-plugins monorepos:
  detect workspace, build, generate changeset, commit, push, and create the GitHub PR.
  Auto-detects which repo you're in. Supports --a auto-approve mode to skip all
  approval gates.   Accepts an optional Jira key/URL or GitHub issue URL to link the PR to
  a tracked issue (adds comments, transitions, and auto-close links). Use when asked to "raise a PR",
  "create a PR", "submit a PR", "open a PR", "push my changes", "make a PR for this
  plugin", or "PR workflow". Also use when user says "raise pr", "/pr", or mentions
  creating a pull request in rhdh-plugins or community-plugins.
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Raise PR Skill ==========="
```
This must happen before any other work (reading references, detecting repo profile, etc.).
</principle>

<principle name="scoped_dist_cleanup">
Pre-build cleanup uses `rm -rf plugins/*/dist packages/*/dist` scoped to the workspace directory. If permission errors occur (root-owned files from a prior Docker build), **skip only `yarn build:all`** and warn the user to run `sudo chown -R $(whoami) .` to fix ownership permanently. Never use `sudo` in the skill itself. Never use `find -name dist` or any broad recursive search — that deletes `dist/` inside `node_modules` and breaks everything.
</principle>

<principle name="changesets_skip_packages">
Only plugins under `plugins/*` with published-source changes need changesets. Always ignore `packages/*` — those are private app/backend packages that are never published. Within each plugin, only include it if changes touch `src/` or other published paths (root `index.ts`, `config.d.ts`, `package.json`). Changes only in `dev/`, `tests/`, `__fixtures__/`, or storybook stories do not require a changeset.
</principle>

<principle name="baseline_diffing">
Capture `git status --porcelain` before builds as the baseline. After builds, only stage files that are new relative to that baseline. Pre-existing dirty files (local config overrides, dev fixtures) must never be staged.
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner to the terminal so the user can track progress:
```
echo "================ Step N — <Step title> ==========="
```
</principle>

<principle name="no_manual_pr_creation">
NEVER bypass this skill by running `gh pr create` or `git push` directly. When another skill (e.g., `bug-fix`) chains into `raise-pr`, you MUST read and follow every step of this skill sequentially — especially Step 10 (push, upload recordings, create PR). Skipping steps or substituting manual commands causes broken PR descriptions, missing recordings, and missing changesets. If you find yourself about to run `gh pr create` without having completed Steps 1–9 first, STOP — you are violating the skill contract.
</principle>

<principle name="recordings_upload_hard_gate">
When `recordings` caller context is provided, the GIF upload in Step 10.2 is MANDATORY — not optional. You MUST upload both GIF files to the dedicated `screenrecordings` branch on the user's fork via the GitHub Contents API and extract real `raw.githubusercontent.com` URLs BEFORE constructing the PR body. NEVER upload to the feature branch (it pollutes the PR diff and lands on upstream main). NEVER use placeholder URLs, `github.com/user-attachments/assets/` URLs, or any fabricated URLs. If the upload fails, you MUST either retry or inform the user that manual upload is needed — do NOT silently proceed with broken image links.
</principle>

</essential_principles>

## Prerequisites

- **`gh` CLI** — GitHub CLI must be installed and authenticated (`gh auth status` should show logged in). Install: https://cli.github.com/
- **Jira MCP** — The Atlassian Rovo MCP server must be configured in your agent environment for Jira comment updates. Setup guide: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
  - If not configured, the skill will skip Jira updates and log a warning.
- Working checkout of `rhdh-plugins` (or `community-plugins`)
- `yarn` available on PATH

---

## Mode: check for `--a` flag

Check if the user invoked this skill with `--a` (auto-approve mode).

- **`--a` present:** All approval gates (Steps 4, 8, and 9) are skipped — proceed automatically.
- **`--a` absent (default):** Approval gates require user confirmation before proceeding.

---

## Step 1 — Detect repo profile

Read `references/repo-profiles.md` and follow the detection logic. Run `git remote -v`, match the remote URLs, and load the matching profile (upstream repo, npm scope, PR body template, changeset docs link).

If no profile matches, ask the user which repo they are targeting before proceeding.

Store the profile values for use in Steps 5, 6, and 10.

---

## Step 1.5 — Resolve issue context

Determine whether the PR is linked to a Jira issue, GitHub issue, or neither.

### Source 1: Caller context (highest priority)

If another skill (e.g., `bug-fix`) provides caller context with `issue_source`, use it directly:

- **`issue_source` = `jira`:** Use `jira_key`, `jira_url`, `jira_summary` from caller context. Skip detection.
- **`issue_source` = `github`:** Use `github_issue_number`, `github_issue_url`, `github_issue_repo`, `github_issue_title` from caller context. Skip detection.

### Source 2: User argument

If no caller context, parse the user's argument:

**Jira patterns** (read `references/jira-input.md`):
- If input matches `(RHIDP|RHDHBUGS|RHDHPLAN|RHDHSUPP)-\d+` anywhere in the string, extract that as the key.
- If input contains `atlassian.net/browse/`, extract everything after `/browse/` as the key.
- Construct: `jira_url = https://redhat.atlassian.net/browse/<jira_key>`
- Set `issue_source = jira`.

**GitHub patterns** (read `bug-fix/references/github-input.md`):
- If input contains `github.com/.../issues/<N>`, extract owner/repo and number.
- If input matches `#\d+`, resolve repo from `git remote -v`.
- Construct: `github_issue_url = https://github.com/<owner>/<repo>/issues/<N>`
- Set `issue_source = github`.

### Source 3: Branch name

If no argument matched, check the current branch name:
- Jira key pattern: `fix/RHDHBUGS-1934-keyboard-nav` → extract `RHDHBUGS-1934`, set `issue_source = jira`.
- GitHub issue pattern: `fix/607-report-portal-crash` → extract `#607` only if combined with repo context from `git remote -v`, set `issue_source = github`.

### Source 4: Prompt

Ask: "Issue key, URL, or #number? (enter to skip)".

### Fetch summary (if not provided by caller)

- **Jira:** Use the Jira REST API per `references/jira-input.md` to fetch the issue summary. If auth is not configured or the fetch fails, store `jira_summary = null` and continue.
- **GitHub:** `gh issue view <N> --repo <repo> --json title -q .title`. If fetch fails, store `github_issue_title = null` and continue.

### Store

Set `issue_source` = `jira`, `github`, or `null`. If `null`, all issue-specific behavior in later steps is skipped.

---

## Step 2 — Detect workspace(s) from staged changes

1. Run `git diff --cached --name-only` to list all staged files.
2. If no files are staged, stop: "No staged changes found. Stage your changes with `git add` before running this command."
3. Extract workspace names from staged file paths. The workspace is the second path segment (e.g., `workspaces/bulk-import/plugins/foo/src/index.ts` → workspace `bulk-import`, path `workspaces/bulk-import`).
4. If staged files span **multiple** workspaces, inform the user: "Changes detected in **N** workspace(s): `<list>`. Proceed? (Yes/No)". Wait for confirmation. If declined, stop.
5. Store the workspace names and paths for later steps.

---

## Step 3 — Capture baseline snapshot

Run `git status --porcelain` and save the full output as the **baseline snapshot**. This captures all files that were already dirty or untracked before any build commands run. Used in Step 7 to filter out pre-existing changes.

---

## Step 4 — Create branch (only if on `main`) [APPROVAL GATE]

1. Run `git branch --show-current`.
2. **If on `main`:**
   a. Analyze the staged diff (`git diff --cached`) to understand the changes.
   b. Generate a branch name:
      - **If `jira_key` is set:** `fix/<workspace>-<JIRA-KEY>-<short-slug>` (e.g., `fix/adoption-insights-RHDHBUGS-1934-keyboard-nav-dropdown`). This matches the existing repo convention and enables auto-linking in the Jira Development panel.
      - **If no Jira key:** `feat/<workspace>-<short-description>` (use `fix/` for bug fixes). For multiple workspaces, use a general description.
   c. **If NOT auto-approve:** present the proposed branch name and a one-line summary. Wait for approval. **If auto-approve:** proceed immediately.
   d. Run `git checkout -b <branch-name>`.
3. **If NOT on `main`:** skip branch creation. Inform the user: "Already on branch `<name>`, skipping branch creation."

---

## Step 5 — Build and validate each workspace

For **each** workspace from Step 2, run the following commands **sequentially** inside the workspace directory (e.g., `workspaces/bulk-import`). If any command fails, **stop immediately** and report the error with the failing command, workspace, and output.

### 5.0 — Pre-build cleanup

Remove stale `dist/` directories that may contain root-owned files from previous Docker or sudo builds:

```
rm -rf plugins/*/dist packages/*/dist
```

**If `EACCES` permission error occurs:** Set a flag `SKIP_BUILD_ALL=true`. Log a warning with the permanent fix:
```
echo "⚠️  Skipping yarn build:all — dist/ has root-owned files. Run 'sudo chown -R $(whoami) .' to fix ownership, then re-run."
```

Never use `sudo` in the skill itself — just tell the user how to fix it.

### 5.1–5.6 — Build pipeline

Run in order:

1. `yarn` — install dependencies
2. `yarn prettier:fix` — format code
3. `yarn tsc:full` — full TypeScript type check
4. `yarn build:all` — build all packages. **Skip this step if `SKIP_BUILD_ALL=true`** (from 5.0 fallback).
5. `yarn test --watchAll=false` — run tests (disable Jest watch mode)
6. `yarn build:api-reports:only` — generate/update API reports (depends on `tsc:full`, always runs)

---

## Step 6 — Generate changeset per workspace

For **each** workspace from Step 2, generate a changeset programmatically. Use the npm scope from the detected repo profile (Step 1).

1. From the staged diff (`git diff --cached`), determine:
   - Which **plugins** under this workspace are affected (look at `plugins/*` only — **ignore `packages/*`**).
   - Within each plugin, only include it if changes touch published paths (`src/`, root `index.ts`, `config.d.ts`, `package.json`). Skip plugins with changes only in `dev/`, `tests/`, `__fixtures__/`, or stories.
   - Read each affected plugin's `package.json` for its npm package name.
   - Infer the semver bump: `patch` for fixes, `minor` for features, `major` for breaking changes.
   - **If no plugins have published-source changes, skip changeset generation for this workspace.**
2. Generate a short summary (1-2 sentences).
3. Generate a random changeset ID: `<adjective>-<noun>-<verb>` pattern, lowercase, 5-8 chars per word. Each workspace gets a unique ID.
4. Write the changeset file to `<workspace>/.changeset/<random-id>.md`:

```
---
'<package-name>': <bump-type>
---

<summary>
```

If multiple packages are affected, list each on its own YAML line.

**Do NOT run `yarn changeset` interactively.** Create files programmatically.

---

## Step 7 — Identify build-generated files

1. Run `git status --porcelain` for the **current snapshot**.
2. Compare against the **baseline snapshot** from Step 3.
3. Files only in the current snapshot are build-generated (created by Step 5 builds or Step 6 changesets).
4. Files already in the baseline are pre-existing — exclude them from staging.

---

## Step 8 — Stage build-generated files [APPROVAL GATE]

1. Present the filtered list of build-generated files from Step 7.
2. **If NOT auto-approve:** ask the user for approval before staging. **If auto-approve:** stage all automatically.
3. Run `git add` for each approved file.

---

## Step 9 — Commit [APPROVAL GATE]

1. Run `git diff --cached --stat` to review all staged changes.
2. Generate a commit message in conventional commit format: `<type>(<workspace>): <short description>` (e.g., `feat(bulk-import): add batch repository import support`).
3. **If `issue_source` is set**, append a `Fixes:` trailer in the commit body — but **only if the issue type is allowed for this repo profile**:
   - **rhdh-plugins:** Both Jira and GitHub issue URLs are allowed.
   - **community-plugins:** Only GitHub issue URLs are allowed. If `issue_source = jira`, do NOT add a `Fixes:` trailer (Jira info must never appear in community-plugins git history).

   Examples:
   - rhdh-plugins + Jira: `Fixes: https://redhat.atlassian.net/browse/RHDHBUGS-1934`
   - rhdh-plugins + GitHub: `Fixes: https://github.com/redhat-developer/rhdh-plugins/issues/607`
   - community-plugins + GitHub: `Fixes: https://github.com/backstage/community-plugins/issues/3574`
   - community-plugins + Jira: **no trailer** (omit entirely)

```
fix(adoption-insights): enable keyboard navigation in header date-range dropdown

Fixes: <issue_url>
```

4. **If NOT auto-approve:** present the commit message and staged file summary. Wait for approval. **If auto-approve:** commit immediately.
5. Commit with the **`-s` flag** (Signed-off-by):

```
git commit -s -m "<subject>" -m "Fixes: <issue_url>"
```

Where `<issue_url>` is `jira_url` or `github_issue_url` depending on `issue_source`. If `issue_source` is null, or if the profile is community-plugins and `issue_source` is jira, omit the second `-m` flag.

---

## Step 10 — Push and create PR

1. Push the branch:

```
git push -u origin HEAD
```

2. **Upload recording GIFs to dedicated `screenrecordings` branch [HARD GATE when `recordings` is provided]**:

   Skip this sub-step ONLY if `recordings` caller context is NOT provided. When `recordings` IS provided, this sub-step is MANDATORY — do NOT skip, defer, or substitute with placeholder URLs.

   GIFs are uploaded to a dedicated `screenrecordings` branch on the user's fork — NOT the feature branch. This keeps the GIFs out of the PR diff and prevents them from landing on upstream `main` when the PR merges.

   a. Verify both local GIF files exist before proceeding:
   ```
   ls -la <recordings.before> <recordings.after>
   ```
   If either file is missing, STOP and inform the user.

   b. Determine the fork owner and repo name from the `origin` remote URL (e.g., `its-mitesh-kumar/rhdh-plugins`).
   c. Build the issue-specific upload path to avoid filename collisions across bug fixes:
   - If `issue_source = jira`: `ISSUE_ID = <jira_key>` (e.g., `RHDHBUGS-2911`)
   - If `issue_source = github`: `ISSUE_ID = <github_issue_number>` (e.g., `9834`)
   - If no issue context: `ISSUE_ID = $(date +%Y%m%d-%H%M%S)`

   Upload path: `screenrecordings/<workspace>-<ISSUE_ID>/before-fix.gif` and `.../after-fix.gif`.

   d. Ensure the `screenrecordings` branch exists on the fork. Check and create if needed:
   ```
   TOKEN=$(gh auth token)
   # Check if branch exists
   HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
     -H "Authorization: token $TOKEN" \
     "https://api.github.com/repos/<fork-owner>/<repo-name>/git/ref/heads/screenrecordings")
   if [ "$HTTP_STATUS" != "200" ]; then
     # Get the SHA of the default branch HEAD
     DEFAULT_SHA=$(curl -s -H "Authorization: token $TOKEN" \
       "https://api.github.com/repos/<fork-owner>/<repo-name>/git/ref/heads/main" | \
       python3 -c "import sys,json; print(json.load(sys.stdin)['object']['sha'])")
     # Create the branch
     curl -s -X POST \
       -H "Authorization: token $TOKEN" \
       -H "Accept: application/vnd.github+json" \
       -d '{"ref":"refs/heads/screenrecordings","sha":"'"$DEFAULT_SHA"'"}' \
       "https://api.github.com/repos/<fork-owner>/<repo-name>/git/refs"
   fi
   ```

   e. For each GIF file (`recordings.before` and `recordings.after`), upload to the `screenrecordings` branch via the GitHub Contents API:

   ```
   GIF_B64=$(base64 -i <local-gif-path>)
   RESPONSE=$(curl -s -X PUT \
     -H "Authorization: token $TOKEN" \
     -H "Accept: application/vnd.github+json" \
     -d '{"message":"docs: add <before|after>-fix recording for <workspace>-<ISSUE_ID>","content":"'"$GIF_B64"'","branch":"screenrecordings"}' \
     "https://api.github.com/repos/<fork-owner>/<repo-name>/contents/screenrecordings/<workspace>-<ISSUE_ID>/<before|after>-fix.gif")
   echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); url=d.get('content',{}).get('download_url',''); print('download_url:', url); exit(0 if url.startswith('https://raw.githubusercontent.com') else 1)"
   ```

   f. Extract the `download_url` from the JSON response — this is the `raw.githubusercontent.com` URL. **Verify** that the URL starts with `https://raw.githubusercontent.com/` — if it does not, the upload failed.
   g. Store both URLs: `before_gif_url`, `after_gif_url`.
   h. Echo a verification banner:
   ```
   echo "✅ GIF upload verified: before=$before_gif_url after=$after_gif_url"
   ```

   **If upload fails:** Retry once. If the retry also fails, log a warning and inform the user to manually drag GIFs into the PR description on GitHub. Use placeholder text `_(Recording upload failed — drag GIF manually)_` in the PR body instead of a broken image link. NEVER fabricate a URL that looks real but does not resolve.

3. Generate a PR title from the commit subject line.
4. Build the PR body from the detected repo profile template (Step 1). The body has conditional sections:
   - **`## Fixed`** — repo-dependent:
     - **rhdh-plugins:** include if `issue_source` is set. Jira: `- [<JIRA-KEY>](<jira_url>) — <jira_summary>`. GitHub: `- Fixes <github_issue_url>`.
     - **community-plugins:** include ONLY if `issue_source = github`. Use `- Fixes <github_issue_url>` (triggers auto-close). NEVER include Jira info — omit `## Fixed` entirely when `issue_source = jira`.
   - **`## UI before changes` / `## UI after changes`** — include only if `recordings` are provided in caller context. Use the `raw.githubusercontent.com` URLs from sub-step 2 in the markdown: `![Before fix](<before_gif_url>)` / `![After fix](<after_gif_url>)`. **CRITICAL**: Both URLs MUST have been obtained from the GitHub Contents API response in sub-step 2. NEVER construct, guess, or fabricate these URLs. If sub-step 2 failed and you have no valid URLs, use the placeholder text from the failure path instead of a broken image link.
   - **`pr_description_extra`** — if provided by caller context (e.g., root cause analysis from `bug-fix`), insert it after the generated description paragraph.
   - **`## Test Plan`** — include only if `test_plan` is provided in caller context. Insert the markdown checklist as-is.
   - **`## Checklist`** — always present.
   - **`## Note`** — include whenever `issue_source` is present in caller context (indicating `bug-fix` invoked `raise-pr`). Contains the skill attribution disclaimer. Omit for standalone `raise-pr` invocations.
5. Create the PR using `gh pr create` with the repo-appropriate template. Use the upstream repo value for `--repo` and `main` for `--base`. Pass the body via HEREDOC:

```
gh pr create --repo <upstream-repo> --base main --title "<title>" --body "$(cat <<'EOF'
<assembled PR body>
EOF
)"
```

6. Capture and store the PR URL for Step 11.
7. Display the PR URL.

---

## Step 11 — Post-PR issue updates

**Skip this step entirely if `issue_source` is null.**

### If `issue_source` = `jira`

1. **Comment** on the Jira issue documenting the PR submission:
   ```
   Use the Jira MCP `add_jira_comment` tool:
     issueKey: "<jira_key>"
     body: "PR submitted: <PR_URL>"
   ```

2. **Transition** the issue status to "Review" (if ACLI is available):
   ```
   acli jira workitem transition --key "<jira_key>" --status "Review" --yes
   ```
   Query available transitions first: `acli jira workitem getTransitions --key "<jira_key>"`. If "Review" is not available, skip the transition and log a warning.

3. **Add web link** — add the PR URL as a remote link on the Jira issue (if REST auth is available):
   ```
   POST /rest/api/3/issue/<jira_key>/remotelink
   { "object": { "url": "<PR_URL>", "title": "GitHub PR: <PR_title>" } }
   ```
   See `references/jira-input.md` for REST API patterns.

**If any Jira call fails:** Log a warning and continue — the PR has been created successfully:
```
echo "⚠️  Could not update <jira_key>. Add manually: <PR_URL>"
```

### If `issue_source` = `github`

1. **Comment** on the GitHub issue:
   ```
   gh issue comment <github_issue_number> --repo <github_issue_repo> --body "Fix submitted: <PR_URL>"
   ```

2. **Auto-close** — no explicit action needed. The `Fixes <github_issue_url>` in the PR body (Step 10) causes GitHub to automatically close the issue when the PR merges.

**If the comment fails:** Log a warning and continue:
```
echo "⚠️  Could not comment on #<github_issue_number>. Add manually: <PR_URL>"
```

---

## Gotchas

- **Fork workflows:** The user may have `origin` pointing to their fork and `upstream` to the canonical repo. Detection checks all remotes, not just `origin`. The `--repo` flag on `gh pr create` targets the canonical upstream regardless of which remote `origin` points to.
- **Multiple workspaces:** Each workspace gets its own build cycle (Step 5) and changeset (Step 6). The commit (Step 9) bundles everything into one commit. If the user prefers separate PRs per workspace, they should stage and run the skill once per workspace.
- **Changeset ID collisions:** Each workspace must get a unique random ID. If generating for multiple workspaces in one run, track used IDs and avoid duplicates.

## Caller Context (optional)

When another skill chains into `raise-pr`, it may provide a **caller context** with pre-resolved values. If present, these override the defaults — skip detection for any field that is already provided.

| Field | Type | Used in | Description |
|-------|------|---------|-------------|
| `issue_source` | string | Steps 1.5, 9, 10, 11 | `"jira"` or `"github"` — determines which issue-specific logic to follow |
| `jira_key` | string | Steps 1.5, 4, 9, 10, 11 | Pre-resolved Jira issue key (skip Step 1.5 detection). Jira only. |
| `jira_url` | string | Steps 9, 10, 11 | Full Jira browse URL. Jira only. |
| `jira_summary` | string | Step 10 | Issue summary for the PR body `## Fixed` section. Jira only. |
| `github_issue_number` | number | Steps 1.5, 10, 11 | GitHub issue number. GitHub only. |
| `github_issue_url` | string | Steps 9, 10, 11 | Full GitHub issue URL (e.g., `https://github.com/redhat-developer/rhdh-plugins/issues/607`). GitHub only. |
| `github_issue_repo` | string | Steps 10, 11 | `owner/repo` (e.g., `redhat-developer/rhdh-plugins`). GitHub only. |
| `github_issue_title` | string | Step 10 | Issue title for the PR body `## Fixed` section. GitHub only. |
| `recordings` | object | Step 10 | `{ before: "<local-gif-path>", after: "<local-gif-path>" }` — local GIF paths; `raise-pr` uploads them to the branch via GitHub Contents API and uses the resulting `raw.githubusercontent.com` URLs in the PR body. `null` in no-e2e mode. |
| `pr_description_extra` | string | Step 10 | Extra text inserted after the description (e.g., root cause analysis) |
| `test_plan` | string | Step 10 | Markdown checklist for the `## Test Plan` section (e.g., `"- [ ] Open menu\n- [ ] Verify scrollbar on hover"`) |

Skills that chain into `raise-pr`:

- **`bug-fix`** — provides `issue_source` plus the relevant issue fields, optionally `recordings` (full-e2e mode only), `pr_description_extra`, and `test_plan`.

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/repo-profiles.md` | Always — at the start of every invocation (Step 1) |
| `references/jira-input.md` | When resolving Jira context (Step 1.5, `issue_source` = `jira`) |
| `bug-fix/references/github-input.md` | When resolving GitHub issue context (Step 1.5, `issue_source` = `github`) |

</reference_index>
