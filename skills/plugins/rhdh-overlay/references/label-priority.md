# Reference: PR Label Priority

How to classify overlay repository PRs by their labels.

<overview>
Not all PRs are equal. Labels tell us what matters for RHDH releases vs. what's community/optional.
</overview>

## Priority Tiers

| Priority | Labels | Meaning | SLA |
|----------|--------|---------|-----|
| 🔴 **Critical** | `mandatory-workspace` + `workspace-update` | Updates to plugins in RHDH catalog | Review within 2 days |
| 🟡 **Medium** | `mandatory-workspace` + `workspace-addition` | New plugins targeting RHDH catalog | Review within 5 days |
| 🟢 **Low** | `workspace-addition` (no mandatory) | Community plugins, not in catalog | Best effort |
| ⚫ **Skip** | `do-not-merge` | OCI artifact generation only | Do not merge |

---

## Label Definitions

### `mandatory-workspace`

**Meaning:** This workspace is part of the RHDH release catalog.

**Source:** Derived from productization files:

- `rhdh-supported-packages.txt` → GA plugins
- `rhdh-techpreview-packages.txt` → Tech Preview plugins

**Impact:** These plugins MUST be compatible before cutting a release branch.

### `workspace-update`

**Meaning:** PR updates an existing workspace to a new upstream version.

**Typical trigger:** Automated discovery found new commit in upstream repo.

**Review focus:**

- Does it still build?
- Any breaking changes upstream?
- Backstage version compatibility?

### `workspace-addition`

**Meaning:** PR adds a new workspace (new plugin to overlay).

**Typical trigger:** Contributor or automation proposing new plugin.

**Review focus:**

- License compatible?
- Upstream maintained?
- CODEOWNERS added?
- Smoke test config present?

### `do-not-merge`

**Meaning:** PR exists only to generate OCI artifacts for testing.

**Typical user:** Orchestrator team uses this for test images.

**Action:** Skip in triage, never merge.

### `release-branch-patch`

**Meaning:** PR targets a release branch (e.g., `release-1.8`), not `main`.

**Review focus:**

- Is this a valid backport?
- Does it fix a release blocker?

---

## Priority Logic (Pseudocode)

```python
def classify_pr(labels):
    label_names = [l.name for l in labels]

    if "do-not-merge" in label_names:
        return "skip"

    is_mandatory = "mandatory-workspace" in label_names
    is_update = "workspace-update" in label_names
    is_addition = "workspace-addition" in label_names

    if is_mandatory and is_update:
        return "critical"
    elif is_mandatory and is_addition:
        return "medium"
    elif is_addition:
        return "low"
    else:
        return "unknown"  # Manual review needed
```

---

## CLI Filters

```bash
REPO="redhat-developer/rhdh-plugin-export-overlays"

# Critical
gh pr list --repo $REPO --state open \
  --label mandatory-workspace --label workspace-update

# Medium
gh pr list --repo $REPO --state open \
  --label mandatory-workspace --label workspace-addition

# Low (addition but not mandatory)
gh pr list --repo $REPO --state open --label workspace-addition \
  --json number,title,labels \
  --jq '.[] | select(.labels | map(.name) | index("mandatory-workspace") | not)'

# Skip
gh pr list --repo $REPO --state open --label do-not-merge
```

---

## Staleness Thresholds

| Priority | Warn After | Alert After | Escalate |
|----------|------------|-------------|----------|
| 🔴 Critical | 2 days | 5 days | Ping in Slack |
| 🟡 Medium | 5 days | 10 days | Mention in standup |
| 🟢 Low | 14 days | 30 days | Consider closing |

---

## Edge Cases

### No Labels

**Situation:** PR has no workspace-related labels.

**Action:** Check files to determine type:

```bash
gh pr view <number> --repo $REPO --json files \
  --jq '.files[].path | select(startswith("workspaces/"))'
```

If workspaces modified → should have labels, flag for review.

### Conflicting Labels

**Situation:** PR has both `workspace-update` and `workspace-addition`.

**Action:** Treat as medium priority, review to understand scope.

### Manual Source Changes

**Situation:** `workspace-update` label but source.json manually edited (not from automation).

**Action:** Check for compatibility bypass (see `analyze-pr.md` workflow).
