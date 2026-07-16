---
name: backport-create
description: >
  Semi-manual backport workflow - creates backport PRs and stops for user review.
  Handles: workspace reset, cherry-pick with AI conflict resolution, and PR creation.
  User reviews and merges PRs manually, then runs backport-finish to complete the workflow.
  Use when you want control over PR review and merging. Accepts release version and PR number/URL.
---

<essential_principles>

<principle name="skill_entry_banner">
As the very first action when the skill is invoked, echo a skill entry banner to the terminal:
```
echo "================ Using Backport Create Skill ==========="
```
This must happen before any other work.
</principle>

<principle name="stop_after_pr_creation">
This skill creates PRs and STOPS. It does NOT auto-merge or continue to Version Packages.

After creating PR #1 and PR #2, print clear instructions for user to:
1. Review the PRs
2. Merge them manually when ready
3. Run /backport-finish to complete the workflow

Do NOT monitor CI or auto-merge. That's the user's responsibility.
</principle>

<principle name="reuse_backport_auto_logic">
Steps 1-8 are IDENTICAL to backport-auto skill.
Read and follow backport-auto/SKILL.md Steps 1-8.

The only difference: Stop after Step 8 (PR #2 creation) instead of continuing.
</principle>

</essential_principles>

## Prerequisites

Same as backport-auto skill:
- `gh` CLI installed and authenticated
- Git access to `rhdh-plugins` and `rhdh-plugin-export-overlays`
- Fork of `rhdh-plugins` with `origin` remote
- `upstream` remote pointing to `redhat-developer/rhdh-plugins`

---

## Arguments

**Usage:** `/backport-create <release-version> <pr-source>`

- **release-version** (required): Target release version (e.g., `1.10`)
- **pr-source** (required): PR number, URL, or commit SHA

**Examples:**
```bash
/backport-create 1.10 3456
/backport-create 1.9 https://github.com/redhat-developer/rhdh-plugins/pull/2345
```

---

## Workflow

Execute Steps 1-8 from `backport-auto/SKILL.md`:

1. Parse arguments and fetch PR details
2. Auto-detect plugin from PR files
3. Check if already backported
4. Reset workspace branch to overlays baseline
5. Create local branch and cherry-pick (with AI conflict resolution if needed)
6. Push backport branch to fork
7. Create PR #1 (fork → release branch)
8. Create PR #2 (release → workspace)

**STOP HERE** - Do NOT continue to Step 9+

---

## After PR Creation

Print summary and instructions:

```bash
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ BACKPORT PRS CREATED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Plugin: $PLUGIN"
echo "Release: $RELEASE"
echo "Original PR: #$PR_NUM"
echo ""
echo "PRs created:"
echo "  1️⃣  Backport to release: #$PR1_NUM"
echo "      $BACKPORT_BRANCH → $RELEASE_BRANCH"
echo "      Review: https://github.com/redhat-developer/rhdh-plugins/pull/$PR1_NUM"
echo ""
echo "  2️⃣  Sync to workspace: #$PR2_NUM"
echo "      $RELEASE_BRANCH → $WORKSPACE_BRANCH"
echo "      Review: https://github.com/redhat-developer/rhdh-plugins/pull/$PR2_NUM"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NEXT STEPS (Manual):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Review PR #$PR1_NUM"
echo "   - Check cherry-pick correctness"
echo "   - Verify CI passes"
echo "   - Merge when ready"
echo ""
echo "2. Review PR #$PR2_NUM"
echo "   - Verify it contains changes from PR #1"
echo "   - Check CI passes"
echo "   - Merge when ready"
echo ""
echo "3. Wait for Version Packages PR to be created"
echo "   - Auto-generated after PR #2 merges"
echo "   - Title: Version Packages ($PLUGIN)"
echo "   - Review and merge it"
echo ""
echo "4. Complete the backport:"
echo "   /backport-finish $RELEASE $PR_NUM"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## When to Use

**Use `backport-create` when:**
- ✅ You want to review PRs before merging
- ✅ You need to make manual adjustments
- ✅ You want control over timing of merges
- ✅ Testing/validation needed before merge

**Use `backport-auto` when:**
- ✅ You trust the automation completely
- ✅ You want hands-off backport
- ✅ Standard backport with no special requirements

---

## Reference Files

Shares all reference files with `backport-auto` skill:
- `../backport-auto/references/pr-detection.md`
- `../backport-auto/references/plugin-detection.md`
- `../backport-auto/references/overlays-lookup.md`
- `../backport-auto/references/ai-conflict-resolution.md`
- `../backport-auto/references/pr-creation.md`
