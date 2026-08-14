# Workflow: Analyze Specific PR

Deep-dive analysis of a single overlay repository PR — assignment, checks,
compatibility, and merge readiness.

```bash
python scripts/analyze-pr.py <pr-number>           # markdown report
python scripts/analyze-pr.py <pr-number> --json     # structured JSON
```

One run collects the PR metadata, labels, files, assignees, reviews, check
rollup, CODEOWNERS, and staleness, then classifies priority and merge readiness.
Consume its output rather than re-fetching the same fields; the interpretation
below is what the numbers mean.

<required_reading>
**Read this reference NOW:**

1. `references/label-priority.md` — priority classification
</required_reading>

<prerequisites>
| Requirement | Details |
|-------------|---------|
| **Input** | PR number |
| **Access** | Read access to the overlay repo |
| **Tools** | `gh` CLI authenticated |
</prerequisites>

For any read the script does not cover — a file from the PR branch, a workflow
run's failed log, a check the rollup omitted — invoke `/rhdh-forge`. It owns the
`gh` and `jq` read patterns, including the reason a rollup disagrees with the
runs on the head branch. Do not add ad-hoc `gh` recipes here.

<process>

## Step 1: Classification

| Labels present | Priority |
|----------------|----------|
| `mandatory-workspace` + `workspace-update` | 🔴 Critical |
| `mandatory-workspace` + `workspace-addition` | 🟡 Medium |
| `workspace-addition` only | 🟢 Low |
| `do-not-merge` | ⚫ Skip |

PR type follows from the same labels: an **update** bumps an existing
workspace's version, an **addition** introduces a new workspace, and a **patch**
targets a release branch.

---

## Step 2: Assignment

| Condition | Status | Action |
|-----------|--------|--------|
| Individual assignee exists | ✅ Clear owner | None |
| Only a team requested | ⚠️ Diluted | Suggest an individual |
| No assignee or reviewer | ❌ Orphan | Assign from CODEOWNERS |

The script reports the CODEOWNERS entry matching each workspace touched by the
PR. Use it to name a candidate owner; assigning one is a write, so plan it.

---

## Step 3: Checks

| Check | Required | Meaning |
|-------|----------|---------|
| `publish` | Yes | Must pass before merge |
| `workspace-tests` | If configured | Smoke test results |
| `check-backstage-compatibility` | Yes | Version alignment |

A check missing from the rollup never ran, which is a different problem from a
check that failed. A missing `publish` needs the guarded `/publish` procedure in
`SKILL.md`; a failing one needs its log. Before reporting either verdict,
confirm the rollup against the head branch's runs through `/rhdh-forge` — the
rollup is cached and goes stale after a rerun or a force push.

---

## Step 4: Compatibility

The overlay's target Backstage version lives in `versions.json` at the
repository root. When the PR modifies a `source.json`:

1. Read the new commit hash from the PR diff.
2. Read upstream's Backstage version at that commit.
3. Compare it to the overlay target.
4. Flag the PR when upstream is ahead of the overlay target — merging it bypasses
   the compatibility gate rather than satisfying it.

---

## Step 5: CODEOWNERS for additions

A `workspace-addition` PR must modify `CODEOWNERS`. The script reports whether
it did. If not, the addition arrives without an owner: request the entry from
the contributor before merge.

---

## Step 6: Merge readiness

| Requirement | Check |
|-------------|-------|
| PR is open | `state == "OPEN"` |
| Publish passed | `publish.conclusion == "success"` |
| Smoke test passed (if present) | `workspace-tests.conclusion == "success"` |
| Individual assignee | `assignees.length > 0` |
| CODEOWNERS entry (additions) | CODEOWNERS modified |
| Approved | At least one approving review |
| No conflicts | `mergeable != "CONFLICTING"` |

```
✅ Ready to merge — all checks passing
⚠️ Almost ready — needs: [list missing items]
❌ Blocked — [reason]
```

---

## Step 7: Output summary

```markdown
## PR #1234 Analysis

**Title:** Update aws-ecs workspace to commit abc123
**Author:** @contributor
**Priority:** 🔴 Critical (mandatory-workspace + workspace-update)
**Created:** 5 days ago
**Last Activity:** 2 days ago

### Assignment
| Status | Details |
|--------|---------|
| Assignee | @johndoe |
| Reviewers | @janedoe, @rhdh-plugins (team) |
| Verdict | ✅ Clear ownership |

### Checks
| Check | Status |
|-------|--------|
| publish | ✅ success (confirmed against run 123456) |
| workspace-tests | ✅ success |
| compatibility | ✅ aligned (1.42.5) |

### Merge Readiness
✅ **Ready to merge**

### Suggested Action
Merge when ready, or wait for additional review if desired.
```

</process>

## Follow-up record

Return a compact record containing the PR number, head SHA, classification,
checks, actions taken, and any owner or compatibility follow-up. Analysis is
read-only; every suggested action stays a suggestion until it is planned and
approved under the mutation contract in `SKILL.md`. Do not cache this
discoverable state inside the skill directory.

<success_criteria>
Analysis is complete when:

- [ ] Priority classified
- [ ] Assignment evaluated
- [ ] All checks assessed against the head branch's runs
- [ ] Compatibility verified (if source.json changed)
- [ ] CODEOWNERS checked (if addition)
- [ ] Merge readiness determined
- [ ] Clear action recommended
</success_criteria>
