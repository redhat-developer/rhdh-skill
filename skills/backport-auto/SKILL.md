---
name: backport-auto
description: >
  Fully automate the RHDH plugin backport process from PR cherry-pick to changelog.
  Handles: cherry-pick with AI conflict resolution, PR creation,
  CI monitoring, auto-merge, Version Packages detection, and overlays update.
  Uses release-x.y/{plugin} branches directly (no workspace/{plugin} intermediary).
  Accepts a release version and PR number/URL. Auto-detects plugin from PR files.
  Use when you need to backport changes to a release branch (e.g., "backport PR #3456 to 1.10").
---

<essential_principles>

<principle name="script_driven">
All mechanical work is done by `scripts/backport.py`. The agent's role is:
1. Validate prerequisites
2. Run the script
3. Handle cherry-pick conflicts if the script exits with code 2
4. Report results
</principle>

<principle name="ai_conflict_resolution">
When the script exits with code 2 (cherry-pick conflict), it saves state to a JSON file
and prints the path as `STATE_FILE=<path>` to stderr. The agent must:

1. Read the state file to get the list of conflicting files
2. Present the user with TWO options:
   - Option 1: Let the skill resolve conflicts (AI auto-resolution)
   - Option 2: User resolves manually (abort)

If user chooses Option 1:
- Read each conflicting file (with conflict markers)
- Understand both sides of the conflict using `git log` and `git show`
- Generate intelligent resolution
- Write resolved files using Edit tool
- Validate syntax (npx tsc --noEmit for TypeScript)
- Check no conflict markers remain
- Run: `git add . && git cherry-pick --continue`
- Re-run script with `--continue-from <state_file>`

If user chooses Option 2:
- Print manual resolution instructions and stop

See `references/ai-conflict-resolution.md` for detailed resolution strategies.
</principle>

</essential_principles>

## Prerequisites

- **`gh` CLI** — installed and authenticated
- **Git access** — to `rhdh-plugins`
- **Fork** — of `rhdh-plugins` with `origin` remote pointing to fork
- **`upstream` remote** — pointing to `redhat-developer/rhdh-plugins`
- **Python 3.9+** — for the backport script

---

## Usage

```bash
/backport-auto <release-version> <pr-source>
```

**Examples:**
```bash
/backport-auto 1.10 3456
/backport-auto 1.9 https://github.com/redhat-developer/rhdh-plugins/pull/2345
/backport-auto 1.10 abc123f
```

---

## Workflow

### Step 1 — Run the script

```bash
python scripts/backport.py <release> <pr_source> --mode auto
```

The script handles all 10 steps:
1. Parse arguments and fetch PR details
2. Auto-detect plugin from PR files (also detects yarn.lock-only changes)
3. Check if already backported
4. Cherry-pick commit(s)
5. Push backport branch to fork
6. Create PR #1 (fork → release branch), monitor CI, merge
7. Detect and merge Version Packages PR (skipped for yarn.lock-only; cleans up stale `maintenance-changesets-release` branch)
8. Trigger overlays update workflow, /publish, wait for CI, merge
9. Create and merge changelog PR to main (skipped for yarn.lock-only)
10. Print summary

### Step 2 — Handle conflicts (if exit code 2)

If the script exits with code 2, cherry-pick had conflicts:

1. Parse `STATE_FILE=<path>` from stderr output
2. Load state: read the JSON file for `conflict_files` list
3. Ask user: resolve with AI or manually?

**AI resolution:**
```bash
# Read each conflicting file
# Analyze conflict markers
# Write resolution using Edit tool
# Then:
git add .
git cherry-pick --continue
python scripts/backport.py <release> <pr_source> --continue-from <state_file>
```

**Manual resolution:**
```
Print instructions and stop.
```

### Step 3 — Report results

The script prints a summary to stderr. With `--json`, structured output goes to stdout.

---

## Script flags

| Flag | Description |
|------|-------------|
| `--mode auto` | Full workflow (default) |
| `--mode create` | Steps 1-6 only, creates PR #1 and stops |
| `--mode finish` | Steps 7-10, handles Version Packages, overlays, and changelog (after PR #1 merge) |
| `--continue-from FILE` | Resume after conflict resolution |
| `--force` | Skip already-backported check |
| `--json` | Structured JSON output to stdout |
| `--auto-approve` | Skip confirmation prompts |
| `--repo REPO` | Override plugins repo |
| `--overlays-repo REPO` | Override overlays repo |

---

## Special Cases

### Yarn.lock-only changes (CVE fixes)

When the PR only changes `yarn.lock` files (e.g., CVE dependency fix with no code changes),
the script automatically skips Version Packages (step 7) and changelog (step 9).
No npm release is needed — the overlays update (step 8) uses the merge commit directly as `repo-ref`.

### Stale maintenance-changesets-release branch

The Version Packages workflow fails if a stale `maintenance-changesets-release/{release-branch}` branch
exists from a previous cycle. The script automatically detects and deletes stale branches before step 7.

---

## When NOT to Use

- **Multi-plugin PRs** — If PR touches multiple plugins, split into separate backports
- **Non-workspace changes** — If PR only changes CI, docs, or root-level files
- **Already backported** — Script will detect and exit early
- **Breaking changes** — Requires manual review and potential code adjustments

---

<reference_index>

## Reference Index

| Reference | Used for |
|-----------|----------|
| `references/ai-conflict-resolution.md` | AI conflict resolution strategies (agent reads on exit code 2) |
| `references/pr-detection.md` | PR source format documentation |
| `references/plugin-detection.md` | Plugin auto-detection logic |
| `references/overlays-lookup.md` | Overlays repo structure |
| `references/overlays-update.md` | Overlays update + /publish flow |
| `references/ci-monitoring.md` | CI monitoring and merge logic |
| `references/version-packages-detection.md` | Version Packages PR detection |
| `references/pr-creation.md` | PR templates and patterns |

</reference_index>
