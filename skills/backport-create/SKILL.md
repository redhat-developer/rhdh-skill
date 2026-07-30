---
name: backport-create
description: >
  Semi-manual backport workflow - creates backport PRs and stops for user review.
  Handles: workspace reset, cherry-pick with AI conflict resolution, and PR creation.
  User reviews and merges PRs manually, then runs backport-finish to complete the workflow.
  Use when you want control over PR review and merging. Accepts release version and PR number/URL.
---

<essential_principles>

<principle name="script_driven">
All mechanical work is done by `../backport-auto/scripts/backport.py` with `--mode create`.
The agent's role is:
1. Validate prerequisites
2. Run the script
3. Handle cherry-pick conflicts if the script exits with code 2
4. Print next-step instructions
</principle>

<principle name="stop_after_pr_creation">
This skill creates PRs and STOPS. It does NOT auto-merge or continue to Version Packages.

After creating PR #1 and PR #2, the script prints clear instructions for the user to:
1. Review the PRs
2. Merge them manually when ready
3. Run /backport-finish to complete the workflow
</principle>

<principle name="ai_conflict_resolution">
When the script exits with code 2 (cherry-pick conflict), follow the same conflict
resolution flow as backport-auto/SKILL.md. See `../backport-auto/references/ai-conflict-resolution.md`.
</principle>

</essential_principles>

## Prerequisites

- **`gh` CLI** — installed and authenticated
- **Git access** — to `rhdh-plugins` and `rhdh-plugin-export-overlays`
- **Fork** — of `rhdh-plugins` with `origin` remote pointing to fork
- **`upstream` remote** — pointing to `redhat-developer/rhdh-plugins`
- **Python 3.9+** — for the backport script

---

## Usage

```bash
/backport-create <release-version> <pr-source>
```

**Examples:**
```bash
/backport-create 1.10 3456
/backport-create 1.9 https://github.com/redhat-developer/rhdh-plugins/pull/2345
/backport-create 1.10 abc123f
```

---

## Workflow

### Step 1 — Run the script

```bash
python ../backport-auto/scripts/backport.py <release> <pr_source> --mode create
```

The script runs steps 1-7:
1. Parse arguments and fetch PR details
2. Auto-detect plugin from PR files
3. Check if already backported
4. Reset workspace branch to overlays baseline
5. Cherry-pick commit(s)
6. Push backport branch to fork
7. Create PR #1 (fork → release branch)

Then STOPS and prints the PR URL + next-step instructions.
PR #2 is NOT created yet — it must wait until PR #1 is merged so the
release branch has the backported changes.

### Step 2 — Handle conflicts (if exit code 2)

Same as backport-auto — see `../backport-auto/SKILL.md` Step 2.

After conflict resolution:
```bash
git add .
git cherry-pick --continue
python ../backport-auto/scripts/backport.py <release> <pr_source> --mode create --continue-from <state_file>
```

### Step 3 — Report results

The script prints a summary with:
- PR #1 URL
- Next-step instructions (review, merge PR #1, then run `/backport-finish`)

---

## When to Use

**Use `backport-create` when:**
- You want to review PRs before merging
- You need to make manual adjustments
- You want control over timing of merges
- Testing/validation needed before merge

**Use `backport-auto` when:**
- You trust the automation completely
- You want hands-off backport

---

## Reference Files

Shares all reference files with `backport-auto` skill:
- `../backport-auto/references/ai-conflict-resolution.md`
- `../backport-auto/references/pr-detection.md`
- `../backport-auto/references/plugin-detection.md`
- `../backport-auto/references/pr-creation.md`
