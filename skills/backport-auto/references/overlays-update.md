# Overlays Repository Update

How to update the overlays repository after Version Packages merges.

## What Gets Updated

After Version Packages PR merges to `workspace/{plugin}`, update:

```
rhdh-plugin-export-overlays/
└── workspaces/{plugin}/
    ├── source.json              ← Update repo-ref to Version Packages commit
    └── metadata/
        └── *.yaml               ← Update version in all metadata files
```

## Update Process

```bash
update_overlays_source() {
  local PLUGIN=$1
  local RELEASE=$2
  local VP_COMMIT=$3
  
  echo "📝 Updating overlays for $PLUGIN @ $RELEASE"
  echo "   New commit: $VP_COMMIT"
  
  # Navigate to overlays repo (cached from earlier)
  OVERLAYS_DIR="/tmp/overlays-${RELEASE}"
  cd "$OVERLAYS_DIR"
  
  # Fetch latest
  git fetch origin
  git checkout "release-${RELEASE}"
  git pull origin "release-${RELEASE}"
  
  # Update source.json
  SOURCE_FILE="workspaces/${PLUGIN}/source.json"
  
  if [ ! -f "$SOURCE_FILE" ]; then
    echo "❌ Error: $SOURCE_FILE not found"
    return 1
  fi
  
  # Read current content
  CURRENT_REF=$(jq -r '.["repo-ref"]' "$SOURCE_FILE")
  echo "   Previous: $CURRENT_REF"
  
  # Update repo-ref field
  jq --arg commit "$VP_COMMIT" \
    '.["repo-ref"] = $commit' \
    "$SOURCE_FILE" > /tmp/source.json.tmp
  
  mv /tmp/source.json.tmp "$SOURCE_FILE"
  
  # Verify update
  NEW_REF=$(jq -r '.["repo-ref"]' "$SOURCE_FILE")
  
  if [ "$NEW_REF" != "$VP_COMMIT" ]; then
    echo "❌ Error: Update failed"
    echo "   Expected: $VP_COMMIT"
    echo "   Got: $NEW_REF"
    return 1
  fi
  
  echo "✅ Updated source.json"
  echo "   New repo-ref: $VP_COMMIT"
  
  return 0
}
```

## Update Metadata Files

After updating source.json, update version in metadata YAML files:

```bash
update_metadata_files() {
  local PLUGIN=$1
  local VP_VERSION=$2
  
  METADATA_DIR="workspaces/${PLUGIN}/metadata"
  
  if [ ! -d "$METADATA_DIR" ]; then
    echo "⚠️ No metadata directory found: $METADATA_DIR"
    return 0
  fi
  
  echo "📝 Updating metadata files..."
  
  # Find all YAML files in metadata directory
  YAML_FILES=$(find "$METADATA_DIR" -name "*.yaml" -o -name "*.yml")
  
  if [ -z "$YAML_FILES" ]; then
    echo "⚠️ No YAML files found in $METADATA_DIR"
    return 0
  fi
  
  # Update version in each YAML file
  for YAML_FILE in $YAML_FILES; do
    echo "   Updating: $YAML_FILE"
    
    # Update version field (format: version: "1.2.3")
    sed -i.bak "s/^version: .*/version: \"$VP_VERSION\"/" "$YAML_FILE"
    rm -f "${YAML_FILE}.bak"
    
    # Stage the file
    git add "$YAML_FILE"
  done
  
  echo "✅ Updated metadata files"
  
  return 0
}
```

## Two Scenarios for Overlays PR

After Version Packages merges, the VP commit hash must be set in `source.json`. But an overlays PR
for this plugin/release may already be open (from a previous backport or another change). Handle both:

### Scenario A: No existing overlays PR → create new

### Scenario B: Overlays PR already open → update existing PR

Check first:

```bash
check_existing_overlays_pr() {
  local PLUGIN=$1
  local RELEASE=$2

  EXISTING_PR=$(gh pr list \
    --repo redhat-developer/rhdh-plugin-export-overlays \
    --base "release-${RELEASE}" \
    --search "${PLUGIN} in:title" \
    --state open \
    --json number,headRefName \
    --jq '.[0]')

  EXISTING_PR_NUM=$(echo "$EXISTING_PR" | jq -r '.number // empty')
  EXISTING_PR_BRANCH=$(echo "$EXISTING_PR" | jq -r '.headRefName // empty')

  if [ -n "$EXISTING_PR_NUM" ]; then
    echo "📋 Existing overlays PR found: #$EXISTING_PR_NUM (branch: $EXISTING_PR_BRANCH)"
  else
    echo "📋 No existing overlays PR — will create new one"
  fi
}
```

## Update Existing Overlays PR (Scenario B)

```bash
update_existing_overlays_pr() {
  local PLUGIN=$1
  local RELEASE=$2
  local VP_COMMIT=$3
  local PR_NUM=$4
  local EXISTING_PR_BRANCH=$5

  cd "$OVERLAYS_DIR"

  # Checkout the existing PR branch
  git checkout "$EXISTING_PR_BRANCH"
  git pull origin "$EXISTING_PR_BRANCH"

  # Update source.json
  SOURCE_FILE="workspaces/${PLUGIN}/source.json"
  jq --arg commit "$VP_COMMIT" '.["repo-ref"] = $commit' \
    "$SOURCE_FILE" > /tmp/source.json.tmp
  mv /tmp/source.json.tmp "$SOURCE_FILE"

  # Update metadata files
  update_metadata_files "$PLUGIN" "$VP_VERSION"

  # Commit and push to the existing PR branch
  git add "workspaces/${PLUGIN}/"
  git commit -m "chore: update ${PLUGIN} repo-ref to ${VP_COMMIT}

Backport of redhat-developer/rhdh-plugins#${PR_NUM} to ${RELEASE}
Version Packages commit: ${VP_COMMIT}"

  git push origin "$EXISTING_PR_BRANCH"

  echo "✅ Updated existing overlays PR with new commit hash"

  return 0
}
```

## Commit and Push New PR (Scenario A)

```bash
commit_and_push_overlays() {
  local PLUGIN=$1
  local RELEASE=$2
  local VP_COMMIT=$3
  local PR_NUM=$4
  
  cd "$OVERLAYS_DIR"
  
  # Stage changes
  git add "workspaces/${PLUGIN}/"
  
  # Create commit
  COMMIT_MSG="chore: update ${PLUGIN} to ${VP_VERSION}

Backport of redhat-developer/rhdh-plugins#${PR_NUM} to ${RELEASE}

Changes:
- Updated source.json repo-ref: ${VP_COMMIT}
- Updated metadata files version: ${VP_VERSION}

Version Packages commit: ${VP_COMMIT}
Release: ${RELEASE}
Plugin: ${PLUGIN}"
  
  git commit -m "$COMMIT_MSG"
  
  # Push to fork (assuming user has fork)
  FORK_REMOTE="origin"
  BRANCH_NAME="update-${PLUGIN}-${RELEASE}-pr${PR_NUM}"
  
  git checkout -b "$BRANCH_NAME"
  git push "$FORK_REMOTE" "$BRANCH_NAME"
  
  echo "✅ Committed and pushed to fork"
  echo "   Branch: $BRANCH_NAME"
  
  return 0
}
```

## Create Overlays PR (Scenario A only)

```bash
create_overlays_pr() {
  local PLUGIN=$1
  local RELEASE=$2
  local VP_COMMIT=$3
  local PR_NUM=$4
  local BRANCH_NAME=$5
  
  echo "📝 Creating overlays PR..."
  
  # Get fork owner
  FORK_OWNER=$(git config --get remote.origin.url | sed -E 's/.*github.com[:\/]([^\/]+)\/.*/\1/')
  
  # Create PR
  gh pr create \
    --repo redhat-developer/rhdh-plugin-export-overlays \
    --base "release-${RELEASE}" \
    --head "${FORK_OWNER}:${BRANCH_NAME}" \
    --title "chore: update ${PLUGIN} for ${RELEASE} release" \
    --body "Updates ${PLUGIN} source to Version Packages commit from backport

**Backport Details:**
- Original PR: redhat-developer/rhdh-plugins#${PR_NUM}
- Release: ${RELEASE}
- Plugin: ${PLUGIN}
- Version Packages commit: [\`${VP_COMMIT:0:7}\`](https://github.com/redhat-developer/rhdh-plugins/commit/${VP_COMMIT})

**Changes:**
- Updated \`workspaces/${PLUGIN}/source.json\`
- Updated \`workspaces/${PLUGIN}/metadata/*.yaml\`
- Set \`repo-ref\` to ${VP_COMMIT}

**Impact:**
This update ensures the ${RELEASE} overlays point to the latest backported version of ${PLUGIN}.

---
🤖 Auto-generated by backport-auto skill"
  
  OVERLAYS_PR=$(gh pr view --json number --jq '.number')
  
  echo "✅ Overlays PR created: #$OVERLAYS_PR"
  echo "   Repository: rhdh-plugin-export-overlays"
  echo "   URL: https://github.com/redhat-developer/rhdh-plugin-export-overlays/pull/$OVERLAYS_PR"
  
  export OVERLAYS_PR_NUM=$OVERLAYS_PR
  
  return 0
}
```

## Why This Update is Necessary

Without updating overlays:

❌ **Overlays repo is outdated:**
- Points to old commit (before backport)
- Next release build uses wrong version
- Published packages don't include backported fixes

✅ **After update:**
- Overlays points to Version Packages commit
- Next release build includes backported changes
- Published packages are correct

## Validation

Verify the update is correct:

```bash
validate_overlays_update() {
  local PLUGIN=$1
  local RELEASE=$2
  local VP_COMMIT=$3
  
  cd "$OVERLAYS_DIR"
  
  # Check source.json has correct commit
  ACTUAL_REF=$(jq -r '.["repo-ref"]' "workspaces/${PLUGIN}/source.json")
  
  if [ "$ACTUAL_REF" != "$VP_COMMIT" ]; then
    echo "❌ Validation failed"
    echo "   Expected: $VP_COMMIT"
    echo "   Got: $ACTUAL_REF"
    return 1
  fi
  
  # Check commit exists in rhdh-plugins
  cd ~/rhdh-plugins
  if ! git cat-file -t $VP_COMMIT &>/dev/null; then
    echo "❌ Validation failed: Commit doesn't exist"
    return 1
  fi
  
  # Check commit is on workspace branch
  if ! git branch -r --contains $VP_COMMIT | grep -q "workspace/${PLUGIN}"; then
    echo "⚠️ Warning: Commit not on workspace/${PLUGIN} branch"
  fi
  
  echo "✅ Overlays update validated"
  
  return 0
}
```

## Complete Update Workflow

```bash
# Full workflow — handles both scenarios (new PR vs update existing)
update_overlays_workflow() {
  local PLUGIN=$1
  local RELEASE=$2
  local VP_COMMIT=$3
  local PR_NUM=$4
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Updating Overlays Repository"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  # 1. Check if overlays PR already exists for this plugin/release
  check_existing_overlays_pr "$PLUGIN" "$RELEASE"
  
  if [ -n "$EXISTING_PR_NUM" ]; then
    # Scenario B: Update existing PR
    update_existing_overlays_pr "$PLUGIN" "$RELEASE" "$VP_COMMIT" "$PR_NUM" "$EXISTING_PR_BRANCH" || return 1
    OVERLAYS_PR_NUM=$EXISTING_PR_NUM
  else
    # Scenario A: Create new PR
    # 1. Update source.json
    update_overlays_source "$PLUGIN" "$RELEASE" "$VP_COMMIT" || return 1
    
    # 2. Update metadata YAML files
    update_metadata_files "$PLUGIN" "$VP_VERSION" || return 1
    
    # 3. Validate update
    validate_overlays_update "$PLUGIN" "$RELEASE" "$VP_COMMIT" || return 1
    
    # 4. Commit and push
    BRANCH_NAME="update-${PLUGIN}-${RELEASE}-pr${PR_NUM}"
    commit_and_push_overlays "$PLUGIN" "$RELEASE" "$VP_COMMIT" "$PR_NUM" || return 1
    
    # 5. Create PR
    create_overlays_pr "$PLUGIN" "$RELEASE" "$VP_COMMIT" "$PR_NUM" "$BRANCH_NAME" || return 1
  fi
  
  # 6. Issue /publish and handle validation
  publish_and_merge_overlays "$PLUGIN" "$RELEASE" "$OVERLAYS_PR_NUM" || return 1
  
  echo ""
  echo "✅ Overlays update complete"
  echo "   PR: #$OVERLAYS_PR_NUM"
  
  return 0
}
```

## /publish Command Flow

After the overlays PR is created or updated, `/publish` must be issued as a PR comment
to trigger image builds. The `/publish` command runs validation that checks metadata
versions match actual package versions.

**Flow:**
1. Comment `/publish` on the PR
2. Wait for bot response
3. If validation errors (version mismatches) → fix metadata, push, `/publish` again
4. If success → merge the PR

```bash
publish_and_merge_overlays() {
  local PLUGIN=$1
  local RELEASE=$2
  local PR_NUM=$3
  local MAX_WAIT=300

  echo "📦 Issuing /publish on overlays PR #$PR_NUM..."

  gh pr comment $PR_NUM \
    --repo redhat-developer/rhdh-plugin-export-overlays \
    --body "/publish"

  # Wait for /publish result
  ELAPSED=0
  PUBLISH_OK=false

  while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 15
    ELAPSED=$((ELAPSED + 15))

    LATEST_COMMENT=$(gh pr view $PR_NUM \
      --repo redhat-developer/rhdh-plugin-export-overlays \
      --json comments --jq '.comments[-1].body')

    if echo "$LATEST_COMMENT" | grep -q "validation error"; then
      echo "❌ /publish validation failed"
      PUBLISH_OK=false
      break
    elif echo "$LATEST_COMMENT" | grep -qi "success\|published\|completed"; then
      echo "✅ /publish succeeded"
      PUBLISH_OK=true
      break
    fi

    echo "⏳ Waiting for /publish result... (${ELAPSED}s)"
  done

  # If validation failed — fix metadata versions and retry
  if [ "$PUBLISH_OK" = false ]; then
    fix_metadata_from_publish_errors "$PLUGIN" "$LATEST_COMMENT"

    # Retry /publish
    gh pr comment $PR_NUM \
      --repo redhat-developer/rhdh-plugin-export-overlays \
      --body "/publish"

    ELAPSED=0
    while [ $ELAPSED -lt $MAX_WAIT ]; do
      sleep 15
      ELAPSED=$((ELAPSED + 15))

      LATEST_COMMENT=$(gh pr view $PR_NUM \
        --repo redhat-developer/rhdh-plugin-export-overlays \
        --json comments --jq '.comments[-1].body')

      if echo "$LATEST_COMMENT" | grep -qi "success\|published\|completed"; then
        PUBLISH_OK=true
        break
      elif echo "$LATEST_COMMENT" | grep -q "validation error"; then
        echo "❌ /publish still failing after fix — manual intervention required"
        break
      fi
    done
  fi

  # Merge if /publish succeeded — but wait for ALL CI checks first
  # Overlays repo has slow CI checks (e.g. ci/prow/e2e-ocp-helm) that can take 30+ minutes
  if [ "$PUBLISH_OK" = true ]; then
    echo "⏳ /publish passed. Waiting for all CI checks (e2e-ocp-helm can take 30+ min)..."
    monitor_ci_and_merge $PR_NUM redhat-developer/rhdh-plugin-export-overlays
    echo "✅ Overlays PR #$PR_NUM merged (all CI passed)"
  else
    echo "⚠️ Overlays PR #$PR_NUM left open — /publish did not succeed"
    echo "   Manual intervention required"
  fi

  return 0
}
```

## Fixing Metadata Version Mismatches

When `/publish` reports version mismatches like:
```
rhdh-bsp-orchestrator.yaml  mismatch  Version mismatch: expected "5.7.13" but got "5.7.12"
```

Parse the errors and update each metadata file:

```bash
fix_metadata_from_publish_errors() {
  local PLUGIN=$1
  local ERROR_OUTPUT=$2

  echo "🔧 Fixing version mismatches in metadata files..."

  echo "$ERROR_OUTPUT" | grep "mismatch" | while read -r line; do
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

  git commit -m "fix: update metadata versions for ${PLUGIN}

Fixed version mismatches reported by /publish validation"

  git push origin HEAD

  echo "✅ Metadata versions fixed, retrying /publish..."
}
```

## Error Handling

**No fork access:**
```
❌ Error: Could not push to fork
fatal: remote origin does not exist

You need a fork of rhdh-plugin-export-overlays
Create fork: gh repo fork redhat-developer/rhdh-plugin-export-overlays
```

**Merge conflict:**
```
❌ Error: PR cannot be created - base branch changed

Someone else updated source.json concurrently
Fetch latest and retry:
  cd /tmp/overlays-1.10
  git pull origin release-1.10
  # Then retry update
```

**Invalid commit:**
```
❌ Validation failed: Commit doesn't exist
Expected: abc123
Got: abc123

Version Packages commit may not be pushed yet
Wait a moment and retry
```

## IMPORTANT: Never merge without /publish

Overlays PRs MUST go through `/publish` before merging. The `/publish` command:
1. Validates metadata versions match actual package versions
2. Triggers image builds
3. Only after success should the PR be merged

```bash
# CORRECT flow:
# 1. Comment /publish
# 2. Wait for validation
# 3. Fix mismatches if any
# 4. Merge only after /publish succeeds

# WRONG — never do this:
gh pr merge $OVERLAYS_PR_NUM --auto --squash  # ❌ skips /publish
```

## Cleanup

After PR is merged:

```bash
# Clean up local branch
cd "$OVERLAYS_DIR"
git checkout "release-${RELEASE}"
git branch -D "$BRANCH_NAME" 2>/dev/null

# Cache is kept for potential future backports
```
