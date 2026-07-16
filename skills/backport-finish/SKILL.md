---
name: backport-finish
description: >
  Complete the backport workflow after manual PR review and merge.
  Assumes PR #1 and PR #2 are already merged. Handles: Version Packages detection and merge,
  release branch sync, overlays update, and changelog PR creation.
  Use after running backport-create and manually merging the PRs.
  Accepts release version and original PR number.
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Backport Finish Skill ==========="
```
This must happen before any other work.
</principle>

<principle name="assume_prs_merged">
This skill assumes PR #1 and PR #2 from backport-create are ALREADY MERGED.

Do NOT create or merge these PRs. Only handle the post-merge workflow:
- Detect and merge Version Packages PR
- Sync release branch
- Update overlays
- Create changelog PR

If PRs are not merged, detect and warn user.
</principle>

<principle name="reuse_backport_auto_logic">
Steps are IDENTICAL to backport-auto/SKILL.md Steps 9-13.
Read and follow backport-auto/SKILL.md for the workflow logic.

The only difference: We start at Step 9 instead of Step 1.
</principle>

</essential_principles>

## Prerequisites

Same as backport-auto skill:
- `gh` CLI installed and authenticated
- Git access to `rhdh-plugins` and `rhdh-plugin-export-overlays`
- Fork of both repos with `origin` remote
- `upstream` remote pointing to `redhat-developer/rhdh-plugins`

**Additional:**
- PR #1 and PR #2 from `backport-create` must be MERGED
- You should have run `backport-create` first

---

## Arguments

**Usage:** `/backport-finish <release-version> <original-pr-number>`

- **release-version** (required): Target release version (e.g., `1.10`)
- **original-pr-number** (required): Original PR number that was backported

**Examples:**
```bash
/backport-finish 1.10 3456
```

---

## Step 0 — Validate prerequisites

Before starting, validate that backport-create was run and PRs are merged:

```bash
# Get plugin from original PR
gh pr view $PR_NUM --repo redhat-developer/rhdh-plugins --json files

# Detect plugin (same logic as backport-auto Step 2)
PLUGIN=$(detect_plugin_from_pr)

# Construct branch names
RELEASE_BRANCH="${PLUGIN}/release-${RELEASE}"
WORKSPACE_BRANCH="workspace/${PLUGIN}"

# Check if changes exist in release branch
git fetch upstream

if ! git log upstream/$RELEASE_BRANCH --oneline | head -20 | grep -q "#$PR_NUM"; then
  echo "⚠️ Warning: Could not find PR #$PR_NUM in $RELEASE_BRANCH"
  echo ""
  echo "Expected workflow:"
  echo "  1. Run: /backport-create $RELEASE $PR_NUM"
  echo "  2. Merge PR #1 and PR #2 manually"
  echo "  3. Run: /backport-finish $RELEASE $PR_NUM"
  echo ""
  read -p "Continue anyway? [y/N]: " CONTINUE
  if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

echo "✅ Prerequisites validated"
```

---

## Step 9 — Detect and merge Version Packages PR

Execute Step 9 from `backport-auto/SKILL.md`:

Read `../backport-auto/references/version-packages-detection.md` for detection logic.

1. Wait for Version Packages PR to be created
2. Detect PR with title: `Version Packages ($PLUGIN)`
3. Validate it's the correct PR
4. Monitor CI
5. Auto-merge when green
6. Capture merge commit SHA

---

## Step 10 — Sync release branch from workspace

Execute Step 10 from `backport-auto/SKILL.md`:

Pull version updates back to release branch:

```bash
git fetch upstream
git checkout $RELEASE_BRANCH
git reset --hard upstream/$WORKSPACE_BRANCH
git push upstream $RELEASE_BRANCH --force-with-lease
```

---

## Step 11 — Update overlays repository

Execute Step 11 from `backport-auto/SKILL.md`:

Read `../backport-auto/references/overlays-update.md` for update workflow.

1. Clone/update overlays repo
2. Checkout `release-${RELEASE}` branch
3. Update `workspaces/${PLUGIN}/source.json` with Version Packages commit
4. Update `workspaces/${PLUGIN}/metadata/*.yaml` files with new version
5. Commit and push to fork
6. Create overlays PR

---

## Step 12 — Create changelog PR to main

Execute Step 12 from `backport-auto/SKILL.md`:

1. Create changelog branch
2. Update `CHANGELOG.md` with backport entry
3. Commit and push
4. Create changelog PR to main

---

## Step 13 — Summary and completion

Print summary:

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
echo "PRs created/merged:"
echo "  ✅ Version Packages: #$VP_PR_NUM (merged)"
echo "  📝 Overlays update: #$OVERLAYS_PR"
echo "  📝 Changelog PR: #$CHANGELOG_PR"
echo ""
echo "Version Packages commit: $VP_COMMIT"
echo ""
echo "Next steps:"
echo "  - Review and merge overlays PR: #$OVERLAYS_PR"
echo "  - Review and merge changelog PR: #$CHANGELOG_PR"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## When to Use

**Use `backport-finish` when:**
- ✅ You already ran `backport-create`
- ✅ You manually merged PR #1 and PR #2
- ✅ You're ready to complete the backport workflow
- ✅ Version Packages PR has been created

**Do NOT use when:**
- ❌ You haven't run `backport-create` yet
- ❌ PR #1 or PR #2 are not merged yet
- ❌ You want full automation (use `backport-auto` instead)

---

## Workflow Chain

The complete manual workflow:

```bash
# 1. Create PRs
/backport-create 1.10 3456

# 2. Manual review and merge
#    - Review PR #1, merge when ready
#    - Review PR #2, merge when ready
#    - Wait for Version Packages PR
#    - Review and optionally merge VP PR

# 3. Finish the backport
/backport-finish 1.10 3456
```

---

## Reference Files

Shares all reference files with `backport-auto` skill:
- `../backport-auto/references/version-packages-detection.md`
- `../backport-auto/references/ci-monitoring.md`
- `../backport-auto/references/overlays-update.md`
- `../backport-auto/references/pr-creation.md`
