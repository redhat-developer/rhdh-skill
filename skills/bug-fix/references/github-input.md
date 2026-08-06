# GitHub Issue Input Parsing & CLI Patterns

Shared reference for resolving GitHub issue references from user input and fetching issue details. Used by `bug-fix` (Step 0, Step 2.5) and `raise-pr` (Step 1.5).

## Parsing GitHub References

Accept any of these formats and normalize to a number + repo pair:

| Input format | Example | Extraction |
|-------------|---------|------------|
| Full URL | `https://github.com/redhat-developer/rhdh-plugins/issues/607` | Extract `owner/repo` and issue number from path |
| URL without scheme | `github.com/backstage/community-plugins/issues/3574` | Same as above, prepend `https://` |
| URL with fragment/query | `https://github.com/redhat-developer/rhdh-plugins/issues/607#issuecomment-123` | Strip fragment/query, extract number |
| Bare `#N` in checkout | `#123` | Resolve repo from `git remote -v` |

### Extraction rules

1. If the input contains `github.com/`, extract the path segments: `/<owner>/<repo>/issues/<number>`.
2. If the input matches `#\d+`, resolve the repo from `git remote -v` using the same detection logic as `raise-pr/references/repo-profiles.md`.
3. If neither matches, the input is not a GitHub issue — fall through to Jira parsing.

### Normalization

Once extracted:

```
github_issue_number = 607
github_issue_repo   = "redhat-developer/rhdh-plugins"
github_issue_url    = "https://github.com/redhat-developer/rhdh-plugins/issues/607"
```

Always construct `github_issue_url` from the repo and number — do not store the user's raw URL (it may have fragments or query params).

### Repo profile detection from URL

| URL contains | Profile |
|-------------|---------|
| `rhdh-plugins` (but NOT `community-plugins`) | **rhdh-plugins** |
| `community-plugins` | **community-plugins** |
| Bare `#N` (no URL) | Detect from `git remote -v` |

## Fetching Issue Details

Use the `gh` CLI to fetch full issue details:

```bash
gh issue view <NUMBER> --repo <owner/repo> --json title,body,labels,state,comments
```

### Field extraction

Parse the JSON output to store:

| Field | JSON path | Description |
|-------|-----------|-------------|
| `github_issue_title` | `.title` | Issue title |
| `github_issue_body` | `.body` | Full issue body (markdown) |
| `github_issue_labels` | `.labels[].name` | Array of label names |
| `github_issue_state` | `.state` | `OPEN` or `CLOSED` |

### Workspace detection from issue

Extract the workspace from the fetched issue using these strategies (in order):

1. **Labels** — look for a label matching `workspace/<name>` (e.g., `workspace/rbac`, `workspace/report-portal`). Extract the part after `workspace/`.
2. **Body field** — scan for a `### Workspace` heading followed by the workspace name (community-plugins bug template includes this).
3. **Title prefix** — community-plugins titles often follow `plugin-<name>: description` or `<workspace>: description`. Extract the prefix before the first `:`.
4. **Package name** — scan body for `@red-hat-developer-hub/backstage-plugin-<name>` or `@backstage-community/plugin-<name>` and derive workspace from the plugin name.
5. **Fallback** — ask the user which workspace to target.

## Issue Interaction Patterns

### Add comment

```bash
gh issue comment <NUMBER> --repo <owner/repo> --body "Fix submitted: <PR_URL>"
```

### Add label

```bash
gh issue edit <NUMBER> --repo <owner/repo> --add-label "<label>"
```

### Remove label

```bash
gh issue edit <NUMBER> --repo <owner/repo> --remove-label "<label>"
```

## Error Handling

| Scenario | Action |
|----------|--------|
| `gh` not authenticated | STOP at readiness check — `gh auth login` required |
| Issue not found (404) | Warn user: "Issue #N not found in <repo>. Verify the number and repo." |
| No write access to repo | Label/comment operations will fail silently — warn user but continue with the fix |
| Issue is closed | Warn user: "Issue #N is already closed. Proceed anyway? (Yes/No)" |
