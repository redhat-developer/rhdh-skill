# Backport Create Skill

Semi-manual backport workflow - creates PRs and stops for user review.

## Quick Start

```bash
/backport-create 1.10 3456
```

Creates backport PRs and stops. You review and merge manually, then run `/backport-finish` to complete.

## What It Does

Creates PRs but **does NOT auto-merge**:

1. ✅ Auto-detects plugin from PR files
2. ✅ Checks if already backported
3. ✅ Resets workspace to baseline
4. ✅ Cherry-picks with AI conflict resolution
5. ✅ Creates PR #1: fork → release branch
6. ✅ Creates PR #2: release → workspace
7. 🛑 **STOPS** - Prints PR URLs for manual review

## Then You Manually

1. Review PR #1 and merge when ready
2. Review PR #2 and merge when ready
3. Wait for Version Packages PR to be created
4. Review and merge Version Packages PR
5. Run `/backport-finish 1.10 3456` to complete

## When to Use

**Use `backport-create` when:**
- ✅ You want to review PRs before merging
- ✅ You need to make manual adjustments
- ✅ You want control over timing
- ✅ Testing needed before merge

**Use `backport-auto` when:**
- ✅ You trust full automation
- ✅ Standard backport with no special requirements

## Complete Workflow

```bash
# 1. Create PRs
/backport-create 1.10 3456

# Output:
# ✅ BACKPORT PRS CREATED
# 1️⃣  Backport to release: #3500
# 2️⃣  Sync to workspace: #3501
# 
# 📋 NEXT STEPS:
# 1. Review and merge PR #3500
# 2. Review and merge PR #3501
# 3. Wait for Version Packages PR
# 4. Run: /backport-finish 1.10 3456

# 2. Manual review (you do this in GitHub)
#    - Check PR #3500, merge
#    - Check PR #3501, merge
#    - Version Packages PR auto-created

# 3. Complete backport
/backport-finish 1.10 3456
```

## See Also

- [backport-auto](../backport-auto/) - Full automation
- [backport-finish](../backport-finish/) - Complete manual workflow
