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

<principle name="script_driven">
All mechanical work is done by `../backport-auto/scripts/backport.py` with `--mode finish`.
The agent's role is:
1. Validate prerequisites (PR #1 and PR #2 must be merged)
2. Run the script
3. Report results
</principle>

<principle name="assume_prs_merged">
This skill assumes PR #1 and PR #2 from backport-create are ALREADY MERGED.

The script validates this. If PRs are not merged, it exits with an error and instructions.
</principle>

</essential_principles>

## Prerequisites

- **`gh` CLI** — installed and authenticated
- **Git access** — to `rhdh-plugins` and `rhdh-plugin-export-overlays`
- **Fork** — of both repos with `origin` remote pointing to fork
- **`upstream` remote** — pointing to `redhat-developer/rhdh-plugins`
- **Python 3.9+** — for the backport script
- **PR #1 and PR #2** from `backport-create` must be **MERGED**

---

## Usage

```bash
/backport-finish <release-version> <original-pr-number>
```

**Examples:**
```bash
/backport-finish 1.10 3456
```

---

## Workflow

### Step 1 — Run the script

```bash
python ../backport-auto/scripts/backport.py <release> <pr_source> --mode finish
```

The script runs steps 9-13:
9. Detect and merge Version Packages PR (handles both new and existing VP PR)
10. Sync release branch from workspace
11. Update overlays (source.json + metadata), /publish, wait for CI, merge
12. Create and merge changelog PR to main
13. Print summary

### Step 2 — Report results

The script prints a summary with all PRs created/merged and the final state.

---

## Workflow Chain

The complete manual workflow:

```bash
# 1. Create PRs
/backport-create 1.10 3456

# 2. Manual review and merge
#    - Review PR #1, merge when ready
#    - Review PR #2, merge when ready

# 3. Finish the backport
/backport-finish 1.10 3456
```

---

## When to Use

**Use `backport-finish` when:**
- You already ran `backport-create`
- You manually merged PR #1 and PR #2
- You're ready to complete the backport workflow

**Do NOT use when:**
- You haven't run `backport-create` yet
- PR #1 or PR #2 are not merged yet
- You want full automation (use `backport-auto` instead)

---

## Reference Files

Shares all reference files with `backport-auto` skill:
- `../backport-auto/references/version-packages-detection.md`
- `../backport-auto/references/ci-monitoring.md`
- `../backport-auto/references/overlays-update.md`
- `../backport-auto/references/pr-creation.md`
