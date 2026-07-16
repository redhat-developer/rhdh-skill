# Backport Auto Skill

Fully automated RHDH plugin backport workflow from PR cherry-pick to changelog.

## Quick Start

```bash
/backport-auto 1.10 3456
```

That's it! The skill handles everything:
- ✅ Auto-detects plugin from PR files
- ✅ Checks if already backported
- ✅ Resets workspace to baseline
- ✅ Cherry-picks with AI conflict resolution
- ✅ Creates and merges PRs automatically
- ✅ Monitors CI and auto-merges
- ✅ Handles Version Packages
- ✅ Updates overlays
- ✅ Creates changelog PR

## What It Does

### Full Workflow

```
Input: /backport-auto 1.10 3456

Step 1:  Parse PR #3456
Step 2:  Detect plugin: orchestrator
Step 3:  Check if already backported (git contains)
Step 4:  Reset workspace/orchestrator to baseline (from overlays/release-1.10/source.json)
Step 5:  Cherry-pick with AI conflict resolution
Step 6:  Push to fork
Step 7:  Create & merge PR #1: fork → orchestrator/release-1.10
Step 8:  Create & merge PR #2: release-1.10 → workspace/orchestrator
Step 9:  Detect & merge Version Packages PR
Step 10: Sync release-1.10 ← workspace (get version updates!)
Step 11: Update overlays source.json and metadata files
Step 12: Create changelog PR to main
Step 13: Done! 🎉
```

### Timeline

```
t=0:   Start
t=2:   Plugin detected, baseline found
t=5:   Cherry-pick complete (or AI resolved conflicts)
t=10:  PR #1 created, CI running
t=15:  PR #1 merged
t=16:  PR #2 created (AFTER PR #1 merges!)
t=20:  PR #2 merged
t=21:  Version Packages PR detected
t=25:  Version Packages merged
t=26:  Release branch synced
t=27:  Overlays updated
t=28:  Changelog PR created
t=30:  Complete
```

## Usage

### Basic

```bash
# PR number
/backport-auto 1.10 3456

# PR URL
/backport-auto 1.9 https://github.com/redhat-developer/rhdh-plugins/pull/2345

# Commit SHA
/backport-auto 1.11 abc123def
```

### Arguments

- `<release-version>`: Target release (e.g., `1.10`, `1.9`)
- `<pr-source>`: PR number, URL, or commit SHA

### Auto-Detection

- **Plugin**: Detected from PR files (`workspaces/{plugin}/...`)
- **Release branch**: `{plugin}/release-{version}`
- **Workspace branch**: `workspace/{plugin}`

## Features

### AI Conflict Resolution

When cherry-pick conflicts:

```
❌ MERGE CONFLICT DETECTED

Conflicting files:
  workspaces/orchestrator/plugins/orchestrator/src/api.ts
  workspaces/orchestrator/plugins/orchestrator/package.json

What would you like to do?

  1. Let the skill resolve it (AI auto-resolution)
  2. I will resolve it manually (abort process)

Enter choice [1/2]:
```

**Option 1:** AI reads both sides, understands intent, resolves intelligently  
**Option 2:** Abort with instructions for manual resolution

### Sequential PRs (Critical!)

**Correct flow:**
```
PR #1 → Merge → WAIT → PR #2
```

**Why:**
- PR #2 needs actual code changes
- Code only in release branch AFTER PR #1 merges
- PR #2 from upstream (not fork) triggers Version Packages

### Smart Detection

Checks if already backported:

```bash
git branch -r --contains $COMMIT_SHA | grep "$PLUGIN/release-$RELEASE"
```

Most reliable method - uses git history.

### Sync Direction

```
orchestrator/release-1.10 ← workspace/orchestrator
```

Pulls Version Packages changes (version updates, CHANGELOG) back to release branch.

## Files Created

### Main Skill

- `SKILL.md` - Complete 13-step workflow

### References

- `ai-conflict-resolution.md` - AI resolution logic
- `ci-monitoring.md` - Auto-merge when CI green
- `overlays-lookup.md` - Read baseline from overlays
- `overlays-update.md` - Update overlays source.json
- `plugin-detection.md` - Extract plugin from files
- `pr-creation.md` - PR templates and patterns
- `pr-detection.md` - Parse PR URLs/numbers
- `version-packages-detection.md` - Detect VP PR

## Prerequisites

- `gh` CLI installed and authenticated
- Write access to `rhdh-plugins` and `rhdh-plugin-export-overlays`
- Fork of both repos with `origin` remote
- `upstream` remote → `redhat-developer/rhdh-plugins`

## Common Scenarios

### Already Backported

```
🔍 Checking if already backported...
✅ Commit abc123 already in orchestrator/release-1.10
✅ Backport completed previously

Nothing to do.
```

### Conflict - AI Resolves

```
❌ Merge conflict in package.json
🤖 AI resolving...
✅ Resolved: package.json (kept version, added dependency)
✅ Continuing...
```

### Conflict - Manual Resolution

```
❌ Merge conflict in complex-logic.ts
User chooses: 2 (manual)

🛑 Aborting with instructions...
📝 State saved to: /tmp/backport-state-3456.json
```

### Multi-Plugin PR

```
❌ Error: PR touches multiple plugins
  - orchestrator
  - lightspeed

Please backport separately
```

## Next Steps

1. **Test** with a real backport PR
2. **Add** to rhdh-skill repository
3. **Document** for team
4. **Iterate** based on feedback

## Feedback from Testing

*(Add feedback from first use here)*

## Design Decisions

See full design discussion in conversation history for:
- Why sequential PRs not parallel
- Why sync pulls from workspace to release
- Why AI conflict resolution with user choice
- Why git-contains check is most reliable
- Why PR #2 must be from upstream

## License

Part of rhdh-skill repository.
