---
name: rhdh-pr-review
description: >
  Review pull requests: code-level analysis with inline comments, and live cluster testing for rhdh-operator PRs. Supports GitHub (GitLab planned). Use when asked to review a PR, review code, post review comments, test PR changes on a cluster, deploy PR images for testing, or do a full PR review. Also use when given a PR URL or number and asked for feedback, or when user mentions "review this PR", "PR review", "code review", or "test this PR on my cluster".
---

<cli_setup>

For cluster testing workflows, set up the orchestrator CLI:

```bash
RHDH=../rhdh/scripts/rhdh
```

</cli_setup>

<essential_principles>

<principle name="layered_architecture">
Reviews follow a three-layer pipeline: **fetch** (forge-specific) → **analyze** (agnostic) → **post** (forge-specific). Each layer produces a structured artifact for the next. The analyze layer never calls forge-specific CLIs.
</principle>

<principle name="verify_findings">
Reviewers will produce false positives. Verify every finding against actual code at HEAD before including it. Drop findings that reference non-existent code, duplicate existing comments, misread the code, or conflict with codebase conventions.
</principle>

<principle name="user_confirms_before_posting">
Present the full review draft — summary, inline comments with file:line, and event type — to the user before posting. Proceed only after confirmation.
</principle>

<principle name="deploy_full_bundle">
For cluster testing: deploy the full PR bundle/manifests, not just the operator binary image. PR changes to CRDs, RBAC, default config, or bundle metadata are baked into the OLM bundle or install.yaml — a binary-only image swap misses them.
</principle>

<principle name="deploy_full_chart">
Deploy the full chart from the PR branch, not just a values override.
PR changes to templates, helpers, schema, or dependencies are baked into the chart itself — a values-only change would miss them.
Use `helm upgrade` pointing at the local chart directory from the PR branch with `--reuse-values` to preserve existing user configuration.
See `references/chart-pr-testing.md` for deployment commands.
</principle>

</essential_principles>

<intake>

## What would you like to do?

### Code Review

1. **Review PR code** — Analyze a PR diff, generate findings, and post inline comments
2. **Review PR code (analysis only)** — Analyze without posting (e.g., to review locally or post later)

### Cluster Testing (rhdh-operator PRs)

3. **Test PR on cluster** — Deploy PR operator bundle on a live RHDH cluster and verify changes

### Combined

4. **Full review** — Code review + post to GitHub + cluster testing

**Wait for response before proceeding.**

</intake>

<routing>

| Response | Workflow |
|----------|----------|
| 1, "review", "review PR", "code review", a PR URL or number | `workflows/fetch-github.md` → `workflows/review-code.md` → `workflows/post-to-github.md` |
| 2, "analyze", "analysis only", "review locally" | `workflows/fetch-github.md` → `workflows/review-code.md` (stop after findings) |
| 3, "test", "cluster", "deploy", "operator PR", "test on cluster" | `workflows/fetch-github.md` → `workflows/review-operator-pr.md` |
| 4, "full", "full review", "both" | `workflows/fetch-github.md` → `workflows/review-code.md` → `workflows/post-to-github.md` → `workflows/review-operator-pr.md` |

### Routing rules

1. **PR URL or number with no other context**: default to route 1 (code review + post).
2. **rhdh-operator PR detected** (repo is `redhat-developer/rhdh-operator`): suggest route 4 (full review) but let the user choose.
3. **"review" without "post" or "cluster"**: route 1.
4. **All routes start with fetch.** The fetch workflow produces a context artifact consumed by all downstream workflows.

### Forge detection

Currently GitHub only. Detect from URL pattern or `gh` CLI availability.

When GitLab support is added: `fetch-gitlab.md` and `post-to-gitlab.md` will slot into the same pipeline. The analyze workflow (`review-code.md`) is forge-agnostic and needs no changes.

</routing>

<artifact_contracts>

## Context artifact (fetch → analyze / cluster test)

Produced by the fetch workflow, consumed by all downstream workflows:

```
context artifact
├── forge: "github"
├── repo: "owner/repo"
├── pr_number: 123
├── head_sha: "abc123..."
├── base_ref, head_ref, title, body, author, state, url
├── labels: [...]
├── files: [{path, additions, deletions}, ...]
├── total_additions, total_deletions
├── diff: "full unified diff"
├── linked_issues: [{number, title, body, labels, state}, ...]
├── jira_keys: ["RHIDP-1234", ...]
├── existing_comments: [{user, path, line, body, created_at}, ...]
├── existing_reviews: [{user, state, body}, ...]
└── ci_status: "pass" | "fail" | "pending" | "unknown"
```

## Findings artifact (analyze → post)

Produced by the analysis workflow, consumed by the posting workflow:

```
findings artifact
├── pr: {repo, number, head_sha}
├── summary: "top-level review text"
├── event: "COMMENT" | "APPROVE" | "REQUEST_CHANGES"
└── findings[]
    ├── path, line, start_line
    ├── type: "suggestion" | "question" | "observation"
    └── body: "comment text"
```

</artifact_contracts>

<reference_index>

| Reference | Purpose | Load when... | Path |
|-----------|---------|--------------|------|
| review-perspectives | Review perspective examples and signal hints | Running `review-code.md` | `references/review-perspectives.md` |
| operator-pr-images | CI image extraction and validation | Running `review-operator-pr.md` | `references/operator-pr-images.md` |
| github-reference | gh CLI patterns, PR queries | Running any GitHub workflow | `../rhdh/references/github-reference.md` (if available) |
| rhdh-repos | RHDH ecosystem repository map | Cluster testing | `../rhdh/references/rhdh-repos.md` (if available) |

</reference_index>

<skills_index>

| Skill | Purpose | Path |
|-------|---------|------|
| rhdh | Orchestrator, environment status, activity tracking | `../rhdh/SKILL.md` |

</skills_index>

<success_criteria>

### Code review

- [ ] PR context fetched (metadata, diff, linked issues, existing comments)
- [ ] Review perspectives chosen based on PR content
- [ ] Findings verified against actual code at HEAD
- [ ] False positives dropped with reasoning shown
- [ ] Review draft presented to user with event type choice
- [ ] Review posted to forge (if posting route selected)

### Cluster testing

See `workflows/review-operator-pr.md` `<success_criteria>` for the full checklist.

### Full review

All code review criteria + all cluster testing criteria.

</success_criteria>
