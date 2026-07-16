---
name: backport-auto
description: >
  Fully automate the RHDH plugin backport process from PR cherry-pick to changelog.
  Handles: workspace reset, cherry-pick with AI conflict resolution, sequential PR creation,
  CI monitoring, auto-merge, Version Packages detection, overlays update, and release sync.
  Accepts a release version and PR number/URL. Auto-detects plugin from PR files.
  Use when you need to backport changes to a release branch (e.g., "backport PR #3456 to 1.10").
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Backport Auto Skill ==========="
```
This must happen before any other work.
</principle>

<principle name="sequential_prs_not_parallel">
CRITICAL: PR creation is SEQUENTIAL, not parallel.

Correct order:
1. Create PR #1: fork:backport-branch → upstream:plugin/release-x.y
2. Wait for PR #1 to FULLY MERGE
3. Fetch upstream (get updated release branch)
4. Create PR #2: upstream:plugin/release-x.y → upstream:workspace/plugin

PR #2 MUST be created AFTER PR #1 merges because:
- PR #2 needs the actual code changes
- Code only exists in release-x.y branch AFTER PR #1 merges
- PR #2 from upstream (not fork) triggers Version Packages workflow

NEVER create both PRs at the same time.
</principle>

<principle name="upstream_pr2_requirement">
PR #2 MUST be from upstream, NOT from fork.

Wrong: fork:plugin/release-x.y → workspace/plugin (won't trigger Version Packages)
Right: upstream:plugin/release-x.y → workspace/plugin (triggers Version Packages)

The head branch must show as "redhat-developer:plugin/release-x.y" not "username:plugin/release-x.y"
</principle>

<principle name="git_contains_check">
Before starting any work, check if the commit already exists in the target release branch:

```bash
git fetch upstream
if git branch -r --contains $COMMIT_SHA | grep -q "$PLUGIN/release-$RELEASE"; then
  echo "✅ Commit already in $PLUGIN/release-$RELEASE"
  echo "Backport completed previously. Nothing to do."
  exit 0
fi
```

This is the most reliable detection method. Skip all other checks.
</principle>

<principle name="ai_conflict_resolution_with_choice">
When cherry-pick conflicts occur, present user with TWO options:

1. Let the skill resolve it (AI auto-resolution)
2. I will resolve it manually (abort process)

If user chooses option 1:
- Use Read tool to analyze conflicting files
- Understand both sides of the conflict
- Generate intelligent resolution
- Use Edit/Write tool to apply resolution
- Validate syntax if TypeScript/JavaScript
- Continue cherry-pick

If user chooses option 2:
- Save state to /tmp/backport-state-{PR_NUM}.json
- Print clear instructions for manual resolution
- Exit with status 1
</principle>

<principle name="sync_direction_matters">
The sync step pulls Version Packages changes BACK to the release branch:

orchestrator/release-1.10 ← workspace/orchestrator

This is necessary because:
- Version Packages PR merges INTO workspace/orchestrator
- Release branch does NOT automatically get the version updates
- Without sync, future cherry-picks will conflict on version numbers

Use git reset --hard to sync, NOT merge.
</principle>

<principle name="step_echo_banners">
Before executing each numbered Step, echo a clearly visible banner:
```
echo "================ Step N — <Step title> ==========="
```
</principle>

<principle name="generic_plugin_and_release">
All branch names, paths, and references are dynamic based on detected plugin and provided release version.

Do NOT hardcode "orchestrator" or "1.10" anywhere.

Variables:
- PLUGIN (detected from PR files)
- RELEASE (provided by user)
- RELEASE_BRANCH="${PLUGIN}/release-${RELEASE}"
- WORKSPACE_BRANCH="workspace/${PLUGIN}"
- OVERLAYS_BRANCH="release-${RELEASE}"
</principle>

</essential_principles>

## Prerequisites

- **`gh` CLI** — GitHub CLI must be installed and authenticated
- **Git access** — Write access to `rhdh-plugins` and `rhdh-plugin-export-overlays` repos
- **Fork** — User must have a fork of `rhdh-plugins` with `origin` remote configured
- **Upstream** — `upstream` remote pointing to `redhat-developer/rhdh-plugins`
- Working checkout of `rhdh-plugins` repo

---

## Arguments

**Usage:** `/backport-auto <release-version> <pr-source>`

- **release-version** (required): Target release version (e.g., `1.10`, `1.9`, `1.11`)
- **pr-source** (required): One of:
  - PR number: `3456`
  - PR URL: `https://github.com/redhat-developer/rhdh-plugins/pull/3456`
  - Commit SHA(s): `abc123,def456` (comma-separated, requires manual plugin detection)

**Examples:**
```bash
/backport-auto 1.10 3456
/backport-auto 1.9 https://github.com/redhat-developer/rhdh-plugins/pull/2345
```

---

## Step 1 — Parse arguments and fetch PR details

Read `references/pr-detection.md` for parsing rules.

1. Extract release version from first argument: `RELEASE="1.10"`

2. Parse PR source:
   - If URL: extract PR number from URL path
   - If number: use directly
   - If commit SHA: store for later (manual plugin detection needed)

3. Fetch PR details via `gh`:
   ```bash
   gh pr view $PR_NUM \
     --repo redhat-developer/rhdh-plugins \
     --json files,mergeCommit,title,url
   ```

4. Extract data:
   - `files`: List of changed files
   - `mergeCommit.oid`: Commit SHA to cherry-pick
   - `title`: PR title (for backport PR description)
   - `url`: Original PR URL (for references)

5. Store: `PR_NUM`, `COMMIT_SHA`, `PR_TITLE`, `PR_URL`

---

## Step 2 — Auto-detect plugin from PR files

Read `references/plugin-detection.md` for detection logic.

1. Get list of changed files from PR:
   ```bash
   FILES=$(gh pr view $PR_NUM --json files --jq '.files[].path')
   ```

2. Extract plugin from file paths:
   ```bash
   # Example file: workspaces/orchestrator/plugins/orchestrator/src/api.ts
   # Extract: orchestrator (second path segment)
   
   PLUGIN=$(echo "$FILES" | head -1 | cut -d'/' -f2)
   ```

3. Validate all files belong to same plugin:
   ```bash
   for FILE in $FILES; do
     FILE_PLUGIN=$(echo "$FILE" | cut -d'/' -f2)
     if [ "$FILE_PLUGIN" != "$PLUGIN" ] && [ "$FILE_PLUGIN" != ".github" ]; then
       echo "❌ Error: PR touches multiple plugins: $PLUGIN, $FILE_PLUGIN"
       echo "Please backport each plugin separately"
       exit 1
     fi
   done
   ```

4. If no plugin detected (non-workspace files only):
   ```bash
   echo "❌ Error: Cannot detect plugin from PR files"
   echo "Files changed:"
   echo "$FILES"
   echo ""
   echo "This PR doesn't touch any workspace."
   exit 1
   ```

5. Construct branch names:
   ```bash
   RELEASE_BRANCH="${PLUGIN}/release-${RELEASE}"
   WORKSPACE_BRANCH="workspace/${PLUGIN}"
   BACKPORT_BRANCH="backport/${PR_NUM}-to-release-${RELEASE}"
   ```

6. Store: `PLUGIN`, `RELEASE_BRANCH`, `WORKSPACE_BRANCH`, `BACKPORT_BRANCH`

---

## Step 3 — Check if already backported

1. Fetch latest from upstream:
   ```bash
   git fetch upstream
   ```

2. Check if commit exists in target release branch:
   ```bash
   if git branch -r --contains $COMMIT_SHA | grep -q "upstream/$RELEASE_BRANCH"; then
     echo "✅ Commit $COMMIT_SHA already exists in $RELEASE_BRANCH"
     echo "✅ Backport completed previously"
     echo ""
     echo "Nothing to do."
     exit 0
   fi
   ```

3. Optional: Check workspace branch (fully completed backport):
   ```bash
   if git branch -r --contains $COMMIT_SHA | grep -q "upstream/$WORKSPACE_BRANCH"; then
     echo "✅ Commit $COMMIT_SHA already in $WORKSPACE_BRANCH"
     echo "✅ Full backport workflow completed previously"
     echo ""
     echo "Nothing to do."
     exit 0
   fi
   ```

4. If checks pass:
   ```bash
   echo "✅ No existing backport found"
   echo "✅ Safe to proceed"
   ```

---

## Step 4 — Reset workspace branch to overlays baseline

Read `references/overlays-lookup.md` for overlays repository structure.

1. Clone overlays repository:
   ```bash
   OVERLAYS_REPO="rhdh-plugin-export-overlays"
   OVERLAYS_BRANCH="release-${RELEASE}"
   
   rm -rf /tmp/overlays-${RELEASE}
   gh repo clone redhat-developer/$OVERLAYS_REPO /tmp/overlays-${RELEASE}
   cd /tmp/overlays-${RELEASE}
   git checkout $OVERLAYS_BRANCH
   ```

2. Read baseline commit from source.json:
   ```bash
   SOURCE_FILE="workspaces/${PLUGIN}/source.json"
   
   if [ ! -f "$SOURCE_FILE" ]; then
     echo "❌ Error: $SOURCE_FILE not found in overlays repo"
     echo "Plugin may not be published in release-${RELEASE}"
     exit 1
   fi
   
   RESET_COMMIT=$(jq -r '.["repo-ref"]' "$SOURCE_FILE")
   
   echo "📍 Baseline commit for reset: $RESET_COMMIT"
   echo "   From: overlays/$OVERLAYS_BRANCH/$SOURCE_FILE"
   ```

3. Validate commit exists:
   ```bash
   cd ~/rhdh-plugins  # or actual repo path
   git fetch upstream
   
   if ! git cat-file -t $RESET_COMMIT &>/dev/null; then
     echo "❌ Error: Commit $RESET_COMMIT not found"
     echo "Overlays source.json may be outdated"
     exit 1
   fi
   ```

4. Reset workspace branch:
   ```bash
   git checkout $WORKSPACE_BRANCH || git checkout -b $WORKSPACE_BRANCH upstream/$WORKSPACE_BRANCH
   git reset --hard $RESET_COMMIT
   git push upstream $WORKSPACE_BRANCH --force
   
   echo "✅ Reset $WORKSPACE_BRANCH to $RESET_COMMIT"
   ```

---

## Step 5 — Create local branch and cherry-pick

1. Create backport branch from release branch:
   ```bash
   git fetch upstream
   git checkout -b $BACKPORT_BRANCH upstream/$RELEASE_BRANCH
   
   echo "✅ Created branch: $BACKPORT_BRANCH"
   echo "   From: $RELEASE_BRANCH"
   ```

2. Cherry-pick commit(s):
   ```bash
   COMMITS_TO_PICK=($COMMIT_SHA)  # Can be array if multiple commits
   
   for COMMIT in "${COMMITS_TO_PICK[@]}"; do
     echo "🍒 Cherry-picking $COMMIT..."
     git cherry-pick $COMMIT
     
     if [ $? -ne 0 ]; then
       # Conflict detected - see Step 5.1
       handle_cherry_pick_conflict "$COMMIT"
     else
       echo "✅ Cherry-pick successful"
     fi
   done
   ```

3. If all cherry-picks succeed:
   ```bash
   echo "✅ All commits cherry-picked successfully"
   ```

---

## Step 5.1 — Handle cherry-pick conflicts

When cherry-pick conflict occurs:

1. Show conflict information:
   ```bash
   echo ""
   echo "❌ =========================================="
   echo "❌ MERGE CONFLICT DETECTED"
   echo "❌ =========================================="
   echo ""
   echo "Commit: $COMMIT"
   echo "Branch: $BACKPORT_BRANCH"
   echo ""
   echo "Conflicting files:"
   git diff --name-only --diff-filter=U
   echo ""
   ```

2. Ask user for resolution method:
   ```bash
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   echo ""
   echo "What would you like to do?"
   echo ""
   echo "  1. Let the skill resolve it (AI auto-resolution)"
   echo "  2. I will resolve it manually (abort process)"
   echo ""
   read -p "Enter choice [1/2]: " CHOICE
   ```

3. If choice is 1 (AI resolution):
   ```bash
   ai_resolve_conflicts
   ```
   - See `references/ai-conflict-resolution.md` for detailed AI resolution logic
   - For each conflicting file:
     - Use Read tool to get file with conflict markers
     - Analyze both sides (HEAD vs incoming)
     - Understand commit intent from git log
     - Generate intelligent resolution
     - Use Edit tool to write resolved file
     - Validate syntax if TypeScript/JavaScript
   - Stage resolved files: `git add .`
   - Continue cherry-pick: `git cherry-pick --continue`

4. If choice is 2 (manual resolution):
   ```bash
   abort_and_save_state
   ```
   - See Step 5.2

---

## Step 5.2 — Abort and save state (manual resolution chosen)

1. Save state for potential resume:
   ```bash
   cat > /tmp/backport-state-${PR_NUM}.json <<EOF
   {
     "pr_num": "$PR_NUM",
     "plugin": "$PLUGIN",
     "release": "$RELEASE",
     "branch": "$BACKPORT_BRANCH",
     "failed_commit": "$COMMIT",
     "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
   }
   EOF
   ```

2. Print manual resolution instructions:
   ```bash
   echo ""
   echo "🛑 Aborting backport process..."
   echo ""
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   echo "📋 Manual Resolution Instructions:"
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   echo ""
   echo "Branch: $BACKPORT_BRANCH"
   echo "Commit: $COMMIT"
   echo ""
   echo "To continue manually:"
   echo ""
   echo "1. In another terminal:"
   echo "   cd $(pwd)"
   echo "   git status  # See conflicting files"
   echo ""
   echo "2. Edit and resolve conflicts in:"
   git diff --name-only --diff-filter=U | sed 's/^/   /'
   echo ""
   echo "3. Stage resolved files:"
   echo "   git add <files>"
   echo ""
   echo "4. Continue cherry-pick:"
   echo "   git cherry-pick --continue"
   echo ""
   echo "5. Push to fork:"
   echo "   git push origin $BACKPORT_BRANCH"
   echo ""
   echo "6. Then continue automation:"
   echo "   /backport-continue $RELEASE $PR_NUM"
   echo ""
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   echo ""
   echo "📝 State saved to: /tmp/backport-state-${PR_NUM}.json"
   echo ""
   echo "❌ Process aborted"
   ```

3. Exit:
   ```bash
   exit 1
   ```

---

## Step 6 — Push backport branch to fork

1. Push branch:
   ```bash
   git push origin $BACKPORT_BRANCH
   
   echo "✅ Pushed branch to fork: origin/$BACKPORT_BRANCH"
   ```

---

## Step 7 — Create and merge PR #1 (fork → release branch)

Read `references/pr-creation.md` for PR creation patterns.

1. Create PR #1:
   ```bash
   gh pr create \
     --repo redhat-developer/rhdh-plugins \
     --base $RELEASE_BRANCH \
     --head $(gh api user --jq .login):$BACKPORT_BRANCH \
     --title "backport: PR #${PR_NUM} to release-${RELEASE}" \
     --body "Cherry-picked from #${PR_NUM} for ${RELEASE} release

   Original PR: ${PR_URL}
   Plugin: ${PLUGIN}
   Release: ${RELEASE}

   This is part 1/2 of the backport workflow.
   After merge, PR #2 will sync to workspace branch."
   
   PR1_NUM=$(gh pr view --json number --jq '.number')
   
   echo "✅ PR #1 created: #$PR1_NUM"
   echo "   $BACKPORT_BRANCH → $RELEASE_BRANCH"
   ```

2. Monitor CI on PR #1:
   ```bash
   monitor_ci_and_merge $PR1_NUM
   ```
   - See `references/ci-monitoring.md` for CI monitoring logic
   - Poll every 30 seconds
   - Check `statusCheckRollup` via gh API
   - If all green: auto-merge
   - If any red: exit with error

3. Wait for merge to fully complete:
   ```bash
   wait_for_pr_merged $PR1_NUM
   
   echo "✅ PR #1 merged"
   echo "✅ Changes now in $RELEASE_BRANCH"
   ```

---

## Step 8 — Create and merge PR #2 (release → workspace)

CRITICAL: This step happens AFTER PR #1 fully merges.

1. Fetch latest upstream (includes merged PR #1):
   ```bash
   git fetch upstream
   
   echo "✅ Fetched latest upstream"
   echo "   $RELEASE_BRANCH now contains merged changes"
   ```

2. Create PR #2 from upstream branch:
   ```bash
   gh pr create \
     --repo redhat-developer/rhdh-plugins \
     --base $WORKSPACE_BRANCH \
     --head $RELEASE_BRANCH \
     --title "chore: sync ${PLUGIN} release-${RELEASE} to workspace" \
     --body "Backport of #${PR_NUM} to release ${RELEASE}

   Original PR: ${PR_URL}
   Backport PR #1: #${PR1_NUM}

   This PR triggers the Version Packages workflow.

   **Do not edit manually** - auto-generated by backport-auto skill."
   
   PR2_NUM=$(gh pr view --json number --jq '.number')
   
   echo "✅ PR #2 created: #$PR2_NUM"
   echo "   $RELEASE_BRANCH → $WORKSPACE_BRANCH"
   echo "   ⚠️  This PR triggers Version Packages workflow"
   ```

3. Monitor CI on PR #2:
   ```bash
   monitor_ci_and_merge $PR2_NUM
   
   echo "✅ PR #2 merged"
   ```

---

## Step 9 — Detect and merge Version Packages PR

Read `references/version-packages-detection.md` for detection logic.

**Two scenarios exist after PR #2 merges:**
- **Scenario A:** No existing Version Packages PR → bot creates a new one. Wait for it to appear.
- **Scenario B:** Version Packages PR already open for this plugin → bot updates the existing PR with new changeset. Wait for the update (new commit pushed to PR branch).

1. Check if a Version Packages PR already exists:
   ```bash
   echo "🔍 Checking for existing Version Packages PR..."
   
   VP_PR_NUM=$(gh pr list \
     --repo redhat-developer/rhdh-plugins \
     --base $WORKSPACE_BRANCH \
     --search "Version Packages (${PLUGIN}) in:title" \
     --state open \
     --json number \
     --jq '.[0].number')
   ```

2. **If VP PR already exists (Scenario B)** — wait for bot to update it:
   ```bash
   if [ -n "$VP_PR_NUM" ]; then
     echo "📋 Existing Version Packages PR found: #$VP_PR_NUM"
     echo "⏳ Waiting for bot to update it with new changeset..."
     
     BEFORE_SHA=$(gh pr view $VP_PR_NUM \
       --repo redhat-developer/rhdh-plugins \
       --json headRefOid --jq '.headRefOid')
     
     MAX_WAIT=300
     ELAPSED=0
     while [ $ELAPSED -lt $MAX_WAIT ]; do
       CURRENT_SHA=$(gh pr view $VP_PR_NUM \
         --repo redhat-developer/rhdh-plugins \
         --json headRefOid --jq '.headRefOid')
       
       if [ "$CURRENT_SHA" != "$BEFORE_SHA" ]; then
         echo "✅ Version Packages PR #$VP_PR_NUM updated with new changeset"
         break
       fi
       
       echo "⏳ Waiting for update... (${ELAPSED}s)"
       sleep 10
       ELAPSED=$((ELAPSED + 10))
     done
   fi
   ```

3. **If no VP PR exists (Scenario A)** — wait for bot to create one:
   ```bash
   if [ -z "$VP_PR_NUM" ]; then
     echo "⏳ No existing Version Packages PR. Waiting for bot to create one..."
     sleep 10
     
     MAX_WAIT=300
     ELAPSED=0
     while [ -z "$VP_PR_NUM" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
       VP_PR_NUM=$(gh pr list \
         --repo redhat-developer/rhdh-plugins \
         --base $WORKSPACE_BRANCH \
         --search "Version Packages (${PLUGIN}) in:title" \
         --state open \
         --json number \
         --jq '.[0].number')
       
       if [ -z "$VP_PR_NUM" ]; then
         echo "⏳ Waiting for Version Packages PR... (${ELAPSED}s)"
         sleep 10
         ELAPSED=$((ELAPSED + 10))
       fi
     done
     
     if [ -z "$VP_PR_NUM" ]; then
       echo "❌ Error: Version Packages PR not created after ${MAX_WAIT}s"
       echo "Check if workflow triggered correctly"
       exit 1
     fi
     
     echo "✅ Version Packages PR detected: #$VP_PR_NUM"
   fi
   ```

3. Validate it's the correct PR:
   ```bash
   VP_TITLE=$(gh pr view $VP_PR_NUM --json title --jq '.title')
   VP_BASE=$(gh pr view $VP_PR_NUM --json baseRefName --jq '.baseRefName')
   
   if [[ ! "$VP_TITLE" =~ "Version Packages ($PLUGIN)" ]]; then
     echo "⚠️ Warning: PR title doesn't match expected pattern"
     echo "Expected: Version Packages ($PLUGIN)"
     echo "Got: $VP_TITLE"
   fi
   
   if [ "$VP_BASE" != "$WORKSPACE_BRANCH" ]; then
     echo "❌ Error: Version Packages PR has wrong base"
     echo "Expected: $WORKSPACE_BRANCH"
     echo "Got: $VP_BASE"
     exit 1
   fi
   
   echo "✅ Validation passed"
   ```

4. Monitor CI and merge:
   ```bash
   monitor_ci_and_merge $VP_PR_NUM
   
   echo "✅ Version Packages PR merged"
   ```

5. Capture merge commit SHA:
   ```bash
   VP_COMMIT=$(gh pr view $VP_PR_NUM --json mergeCommit --jq '.mergeCommit.oid')
   
   echo "📝 Version Packages commit: $VP_COMMIT"
   ```

---

## Step 10 — Sync release branch from workspace

CRITICAL: This pulls version updates back to the release branch.

1. Fetch latest:
   ```bash
   git fetch upstream
   ```

2. Checkout release branch:
   ```bash
   git checkout $RELEASE_BRANCH
   ```

3. Reset to workspace branch:
   ```bash
   git reset --hard upstream/$WORKSPACE_BRANCH
   
   echo "✅ Reset $RELEASE_BRANCH to match $WORKSPACE_BRANCH"
   ```

4. Force push with safety check:
   ```bash
   git push upstream $RELEASE_BRANCH --force-with-lease
   
   if [ $? -eq 0 ]; then
     echo "✅ Synced $RELEASE_BRANCH ← $WORKSPACE_BRANCH"
     echo "   Release branch now has version updates"
   else
     echo "❌ Error: Force push rejected"
     echo "Someone may have pushed to $RELEASE_BRANCH concurrently"
     exit 1
   fi
   ```

---

## Step 11 — Update overlays repository

Read `references/overlays-update.md` for update workflow.

**Two scenarios exist:**
- **Scenario A:** No existing overlays PR for this plugin/branch → create a new PR
- **Scenario B:** An overlays PR already open for this plugin on this release branch → update that PR with the new commit hash

1. Navigate to overlays repo:
   ```bash
   cd /tmp/overlays-${RELEASE}
   git fetch origin
   git checkout $OVERLAYS_BRANCH
   git pull origin $OVERLAYS_BRANCH
   ```

2. Check if an overlays PR already exists for this plugin:
   ```bash
   EXISTING_OVERLAYS_PR=$(gh pr list \
     --repo redhat-developer/rhdh-plugin-export-overlays \
     --base "release-${RELEASE}" \
     --search "${PLUGIN} in:title" \
     --state open \
     --json number,headRefName \
     --jq '.[0]')
   
   EXISTING_OVERLAYS_PR_NUM=$(echo "$EXISTING_OVERLAYS_PR" | jq -r '.number // empty')
   EXISTING_OVERLAYS_BRANCH=$(echo "$EXISTING_OVERLAYS_PR" | jq -r '.headRefName // empty')
   ```

3. **If overlays PR already exists (Scenario B)** — update the existing PR:
   ```bash
   if [ -n "$EXISTING_OVERLAYS_PR_NUM" ]; then
     echo "📋 Existing overlays PR found: #$EXISTING_OVERLAYS_PR_NUM"
     echo "   Updating with new commit hash..."
     
     # Checkout the existing PR branch
     git checkout "$EXISTING_OVERLAYS_BRANCH"
     git pull origin "$EXISTING_OVERLAYS_BRANCH"
     
     # Update source.json with new VP commit
     SOURCE_FILE="workspaces/${PLUGIN}/source.json"
     jq --arg commit "$VP_COMMIT" '.["repo-ref"] = $commit' \
       "$SOURCE_FILE" > /tmp/source.json.tmp
     mv /tmp/source.json.tmp "$SOURCE_FILE"
     
     # Update metadata files with new version
     update_metadata_files "$PLUGIN" "$VP_VERSION"
     
     # Commit and push to the existing PR branch
     git add "workspaces/${PLUGIN}/"
     git commit -m "chore: update ${PLUGIN} repo-ref to ${VP_COMMIT}

   Backport of redhat-developer/rhdh-plugins#${PR_NUM} to ${RELEASE}
   Version Packages commit: ${VP_COMMIT}"
     
     git push origin "$EXISTING_OVERLAYS_BRANCH"
     
     OVERLAYS_PR=$EXISTING_OVERLAYS_PR_NUM
     echo "✅ Updated existing overlays PR: #$OVERLAYS_PR"
   fi
   ```

4. **If no overlays PR exists (Scenario A)** — create a new PR:
   ```bash
   if [ -z "$EXISTING_OVERLAYS_PR_NUM" ]; then
     SOURCE_FILE="workspaces/${PLUGIN}/source.json"
     
     # Update repo-ref to Version Packages commit
     jq --arg commit "$VP_COMMIT" '.["repo-ref"] = $commit' \
       "$SOURCE_FILE" > /tmp/source.json.tmp
     mv /tmp/source.json.tmp "$SOURCE_FILE"
     
     # Update metadata files with new version
     update_metadata_files "$PLUGIN" "$VP_VERSION"
     
     echo "✅ Updated $SOURCE_FILE"
     echo "   repo-ref: $VP_COMMIT"
     
     # Create branch, commit, push, and create PR
     BRANCH_NAME="update-${PLUGIN}-${RELEASE}-pr${PR_NUM}"
     git checkout -b "$BRANCH_NAME"
     git add "workspaces/${PLUGIN}/"
     git commit -m "chore: update ${PLUGIN} to ${VP_COMMIT}

   Backport of redhat-developer/rhdh-plugins#${PR_NUM} to ${RELEASE}
   Version Packages commit: ${VP_COMMIT}"
     
     git push origin "$BRANCH_NAME"
     
     gh pr create \
       --repo redhat-developer/rhdh-plugin-export-overlays \
       --base "release-${RELEASE}" \
       --head "$BRANCH_NAME" \
       --title "chore: update ${PLUGIN} for ${RELEASE} release" \
       --body "Updates ${PLUGIN} source to Version Packages commit

   **Backport details:**
   - Original PR: redhat-developer/rhdh-plugins#${PR_NUM}
   - Release: ${RELEASE}
   - Version Packages commit: ${VP_COMMIT}

   **Changes:**
   - Updated \`workspaces/${PLUGIN}/source.json\`
   - Updated \`workspaces/${PLUGIN}/metadata/*.yaml\`"
     
     OVERLAYS_PR=$(gh pr view --json number --jq '.number')
     
     echo "✅ Overlays PR created: #$OVERLAYS_PR"
     echo "   Repository: rhdh-plugin-export-overlays"
   fi
   ```

5. Issue `/publish` command on the overlays PR:
   ```bash
   echo "📦 Issuing /publish command on overlays PR #$OVERLAYS_PR..."
   
   gh pr comment $OVERLAYS_PR \
     --repo redhat-developer/rhdh-plugin-export-overlays \
     --body "/publish"
   
   echo "⏳ Waiting for /publish validation..."
   ```

6. Monitor `/publish` result — check PR comments for success or validation errors:
   ```bash
   MAX_WAIT=300
   ELAPSED=0
   PUBLISH_OK=false
   
   while [ $ELAPSED -lt $MAX_WAIT ]; do
     sleep 15
     ELAPSED=$((ELAPSED + 15))
     
     # Get latest bot comment after our /publish
     LATEST_COMMENT=$(gh pr view $OVERLAYS_PR \
       --repo redhat-developer/rhdh-plugin-export-overlays \
       --json comments --jq '.comments[-1].body')
     
     if echo "$LATEST_COMMENT" | grep -q "validation error"; then
       echo "❌ /publish validation failed — version mismatches detected"
       PUBLISH_OK=false
       break
     elif echo "$LATEST_COMMENT" | grep -qi "success\|published\|completed"; then
       echo "✅ /publish succeeded"
       PUBLISH_OK=true
       break
     fi
     
     echo "⏳ Waiting for /publish result... (${ELAPSED}s)"
   done
   ```

7. If `/publish` failed with version mismatches — parse errors, fix metadata, and retry:
   ```bash
   if [ "$PUBLISH_OK" = false ]; then
     echo "🔧 Fixing version mismatches in metadata files..."
     
     # Parse mismatch errors from the comment
     # Format: "rhdh-bsp-orchestrator.yaml  mismatch  Version mismatch: expected "5.7.13" but got "5.7.12""
     # Extract filename and expected version pairs
     
     echo "$LATEST_COMMENT" | grep "mismatch" | while read -r line; do
       YAML_FILE=$(echo "$line" | awk '{print $1}')
       EXPECTED_VER=$(echo "$line" | grep -oP 'expected "\K[^"]+')
       
       METADATA_PATH="workspaces/${PLUGIN}/metadata/${YAML_FILE}"
       
       if [ -f "$METADATA_PATH" ]; then
         echo "   Fixing $YAML_FILE: version → $EXPECTED_VER"
         sed -i.bak "s/^version: .*/version: \"$EXPECTED_VER\"/" "$METADATA_PATH"
         rm -f "${METADATA_PATH}.bak"
         git add "$METADATA_PATH"
       fi
     done
     
     # Commit and push the fixes
     git commit -m "fix: update metadata versions for ${PLUGIN}

   Fixed version mismatches reported by /publish validation"
     
     git push origin HEAD
     
     echo "✅ Metadata versions fixed, retrying /publish..."
     
     # Retry /publish
     gh pr comment $OVERLAYS_PR \
       --repo redhat-developer/rhdh-plugin-export-overlays \
       --body "/publish"
     
     # Wait for retry result
     ELAPSED=0
     while [ $ELAPSED -lt $MAX_WAIT ]; do
       sleep 15
       ELAPSED=$((ELAPSED + 15))
       
       LATEST_COMMENT=$(gh pr view $OVERLAYS_PR \
         --repo redhat-developer/rhdh-plugin-export-overlays \
         --json comments --jq '.comments[-1].body')
       
       if echo "$LATEST_COMMENT" | grep -q "validation error"; then
         echo "❌ /publish still failing after metadata fix"
         echo "   Manual intervention required"
         echo "   PR: https://github.com/redhat-developer/rhdh-plugin-export-overlays/pull/$OVERLAYS_PR"
         break
       elif echo "$LATEST_COMMENT" | grep -qi "success\|published\|completed"; then
         echo "✅ /publish succeeded after metadata fix"
         PUBLISH_OK=true
         break
       fi
       
       echo "⏳ Waiting for /publish retry result... (${ELAPSED}s)"
     done
   fi
   ```

8. If `/publish` succeeded — wait for ALL CI checks (including slow ones like `ci/prow/e2e-ocp-helm`) to pass, then merge:
   ```bash
   if [ "$PUBLISH_OK" = true ]; then
     echo "⏳ Waiting for all CI checks to pass (this can take a while, e.g. e2e-ocp-helm)..."
     
     # monitor_ci_and_merge waits for ALL checks to go green, not just /publish
     # Some checks like ci/prow/e2e-ocp-helm can take 30+ minutes
     monitor_ci_and_merge $OVERLAYS_PR redhat-developer/rhdh-plugin-export-overlays
     echo "✅ Overlays PR #$OVERLAYS_PR merged (all CI passed)"
   else
     echo "⚠️ Overlays PR #$OVERLAYS_PR left open — /publish did not succeed"
     echo "   Manual intervention required"
   fi
   ```

---

## Step 12 — Create changelog PR to main

1. Navigate back to rhdh-plugins:
   ```bash
   cd ~/rhdh-plugins  # or actual repo path
   git fetch upstream
   ```

2. Create changelog branch:
   ```bash
   CHANGELOG_BRANCH="changelog/${PLUGIN}-${RELEASE}-pr${PR_NUM}"
   
   git checkout -b $CHANGELOG_BRANCH upstream/main
   ```

3. Determine changelog file location:
   ```bash
   # Standard location
   CHANGELOG_FILE="workspaces/${PLUGIN}/CHANGELOG.md"
   
   if [ ! -f "$CHANGELOG_FILE" ]; then
     # Try plugin-specific location
     CHANGELOG_FILE="workspaces/${PLUGIN}/plugins/${PLUGIN}/CHANGELOG.md"
   fi
   
   if [ ! -f "$CHANGELOG_FILE" ]; then
     echo "⚠️ Warning: CHANGELOG.md not found for ${PLUGIN}"
     echo "Skipping changelog PR"
     # Continue anyway - some plugins may not have changelogs
   else
     update_changelog
   fi
   ```

4. Update changelog:
   ```bash
   # Read Version Packages PR to get version number
   VP_VERSION=$(gh pr view $VP_PR_NUM --json body --jq '.body' | grep -oP '@redhat-developer/\S+@\K[\d.]+' | head -1)
   
   # Add entry to changelog
   CHANGELOG_ENTRY="## ${VP_VERSION}

   ### Backports
   
   - Backported #${PR_NUM}: ${PR_TITLE} ([#${VP_PR_NUM}](https://github.com/redhat-developer/rhdh-plugins/pull/${VP_PR_NUM}))
   "
   
   # Insert after first heading (## or #)
   # Use sed or manually edit with Edit tool
   ```

5. Commit and push:
   ```bash
   git add "$CHANGELOG_FILE"
   git commit -m "docs: add ${PLUGIN} ${RELEASE} changelog for PR #${PR_NUM}"
   git push origin $CHANGELOG_BRANCH
   ```

6. Create changelog PR:
   ```bash
   gh pr create \
     --repo redhat-developer/rhdh-plugins \
     --base main \
     --head $(gh api user --jq .login):$CHANGELOG_BRANCH \
     --title "docs: add ${PLUGIN} ${RELEASE} changelog for backport #${PR_NUM}" \
     --body "Adds changelog entry for backported PR #${PR_NUM}

   **Backport details:**
   - Original PR: #${PR_NUM}
   - Release: ${RELEASE}
   - Version: ${VP_VERSION}
   - Plugin: ${PLUGIN}

   This tracks what was backported to the ${RELEASE} release."
   
   CHANGELOG_PR=$(gh pr view --json number --jq '.number')
   
   echo "✅ Changelog PR created: #$CHANGELOG_PR"
   ```

7. Monitor CI and merge changelog PR:
   ```bash
   echo "⏳ Waiting for CI on changelog PR #$CHANGELOG_PR..."
   monitor_ci_and_merge $CHANGELOG_PR
   echo "✅ Changelog PR #$CHANGELOG_PR merged"
   ```

---

## Step 13 — Summary and completion

1. Print summary:
   ```bash
   echo ""
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   echo "✅ BACKPORT COMPLETED SUCCESSFULLY"
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   echo ""
   echo "Plugin: $PLUGIN"
   echo "Release: $RELEASE"
   echo "Original PR: #$PR_NUM"
   echo ""
   echo "All PRs merged:"
   echo "  1️⃣  Backport PR #1: #$PR1_NUM (merged)"
   echo "  2️⃣  Backport PR #2: #$PR2_NUM (merged)"
   echo "  3️⃣  Version Packages: #$VP_PR_NUM (merged)"
   echo "  4️⃣  Overlays update: #$OVERLAYS_PR (/publish + merged)"
   echo "  5️⃣  Changelog PR: #$CHANGELOG_PR (merged)"
   echo ""
   echo "Version Packages commit: $VP_COMMIT"
   echo ""
   echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
   ```

---

## When NOT to Use

- **Multi-plugin PRs** — If PR touches multiple plugins, split into separate backports
- **Non-workspace changes** — If PR only changes CI, docs, or root-level files
- **Already backported** — Skill will detect and exit early
- **Breaking changes** — Requires manual review and potential code adjustments
- **Emergency hotfixes** — Manual process may be faster for critical fixes

---

<reference_index>

## Reference Index

| Reference | Load when... |
|-----------|-------------|
| `references/pr-detection.md` | Step 1 — parsing PR URLs and numbers |
| `references/plugin-detection.md` | Step 2 — extracting plugin from file paths |
| `references/overlays-lookup.md` | Step 4 — reading overlays source.json |
| `references/ai-conflict-resolution.md` | Step 5.1 — AI conflict resolution logic |
| `references/ci-monitoring.md` | Steps 7, 8, 9 — monitoring CI and auto-merge |
| `references/version-packages-detection.md` | Step 9 — detecting Version Packages PR |
| `references/overlays-update.md` | Step 11 — updating overlays repository |
| `references/pr-creation.md` | Steps 7, 8, 12 — PR creation patterns |

</reference_index>
