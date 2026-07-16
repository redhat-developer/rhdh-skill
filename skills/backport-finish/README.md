# Backport Finish Skill

Complete the backport after manual PR review and merge.

## Quick Start

```bash
/backport-finish 1.10 3456
```

Assumes you already ran `/backport-create` and merged the PRs manually.

## What It Does

Completes the backport workflow (Stage 2):

1. ✅ Validates PRs were merged
2. ✅ Detects Version Packages PR
3. ✅ Merges Version Packages PR (auto)
4. ✅ Syncs release branch ← workspace
5. ✅ Updates overlays source.json and metadata
6. ✅ Creates changelog PR to main

## Prerequisites

**You must have:**
- ✅ Run `/backport-create 1.10 3456` first
- ✅ Manually merged PR #1 (backport → release)
- ✅ Manually merged PR #2 (release → workspace)
- ✅ Version Packages PR exists (auto-created after PR #2)

## When to Use

**Use `backport-finish` when:**
- ✅ You ran `backport-create` earlier
- ✅ You manually merged both PRs
- ✅ You're ready to complete the workflow

**Do NOT use when:**
- ❌ You haven't run `backport-create` yet
- ❌ PRs are not merged yet
- ❌ You want full automation (use `backport-auto`)

## Complete Manual Workflow

```bash
# 1. Create PRs
/backport-create 1.10 3456

# 2. Manually review and merge (you do this)
#    - Merge PR #1 in GitHub
#    - Merge PR #2 in GitHub
#    - Wait for Version Packages PR

# 3. Complete backport
/backport-finish 1.10 3456

# Output:
# ✅ BACKPORT COMPLETED
# ✅ Version Packages: #3502 (merged)
# 📝 Overlays update: #45
# 📝 Changelog PR: #3503
```

## See Also

- [backport-auto](../backport-auto/) - Full automation (no manual steps)
- [backport-create](../backport-create/) - Create PRs (first step)
