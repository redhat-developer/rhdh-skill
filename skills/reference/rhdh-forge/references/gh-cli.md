# gh reads

Read patterns for GitHub pull requests, checks, workflow runs, and repository
content, plus the behaviours that catch a caller out. Everything here is
read-only; see the mutation boundary in `SKILL.md` before any payload is
executed, and `references/glab-cli.md` for the GitLab equivalents.

## Shape the query

Ask for `--json` with `--jq` rather than parsing the human table. The table
column order is not an interface.

```bash
gh pr list --repo <owner/repo> --state open --limit 100 \
  --json number,title,labels,assignees,updatedAt,author
```

Always pass `--limit`. `--state all` without one walks the entire history.

Filters compose as AND across repeated `--label`; use `--search` for OR:

```bash
gh pr list --repo <owner/repo> --label mandatory-workspace --label workspace-update
gh pr list --repo <owner/repo> --search "label:mandatory-workspace label:workspace-update"
gh pr list --repo <owner/repo> --author "github-actions[bot]"
```

### The `!=` trap

Bash reads `!` inside double quotes as history expansion, so a `--jq` filter
containing `!=` fails before `gh` ever sees it. Invert with `not` instead:

```bash
# Breaks: bash expands !=
gh pr view 1 --jq '.reviews | map(select(.state != "COMMENTED"))'

# Works
gh pr view 1 --jq '.reviews | map(select(.state == "COMMENTED" | not))'
```

The same applies to `index("do-not-merge") != null`; write
`index("do-not-merge") == null | not`, or test the truthiness directly.

## Read a pull request

```bash
gh pr view <number> --repo <owner/repo> \
  --json number,title,state,author,labels,assignees,reviewRequests,reviews,statusCheckRollup,files,updatedAt,createdAt,mergeable,body
```

Narrower reads:

```bash
gh pr view <number> --repo <owner/repo> --json labels --jq '.labels[].name'
gh pr view <number> --repo <owner/repo> --json assignees --jq '.assignees[].login'
gh pr view <number> --repo <owner/repo> --json files --jq '.files[].path'
gh pr view <number> --repo <owner/repo> --json updatedAt \
  --jq '((now - (.updatedAt | fromdateiso8601)) / 86400 | floor)'
```

Workspace names from a plugin-export style PR:

```bash
gh pr view <number> --repo <owner/repo> --json files \
  --jq '.files[].path | select(startswith("workspaces/")) | split("/")[1]' | sort -u
```

For a full review context rather than an ad-hoc read, invoke `/rhdh-pr-review`,
which owns the deterministic fetch.

## Checks go stale

`gh pr checks` and `statusCheckRollup` serve a cached rollup. A rerun, a force
push, or a check that was never triggered all produce a rollup that disagrees
with reality. Confirm against the runs on the head branch:

```bash
BRANCH=$(gh pr view <number> --repo <owner/repo> --json headRefName --jq '.headRefName')
gh run list --repo <owner/repo> --branch "$BRANCH" --limit 3 \
  --json databaseId,conclusion,status,workflowName
```

A check absent from the rollup means it never ran, which is a different problem
from a check that failed. Distinguish the two before reporting a verdict.

### Read the failure

```bash
gh run view <run-id> --repo <owner/repo> --log-failed
```

Logs are large. Narrow before reading the whole thing:

```bash
gh run view <run-id> --repo <owner/repo> --log-failed 2>&1 | grep -A 5 "Error\|FAIL" | head -50
```

### Overlay repository failures

`redhat-developer/rhdh-plugin-export-overlays` produces a small set of recurring
failures:

| Log pattern | Cause | Fix |
|---|---|---|
| `source.json: backstage version mismatch` | `repo-backstage-version` disagrees with the upstream source | Set it to the upstream commit's actual Backstage version |
| `CODEOWNERS: no entry for workspace` | A workspace addition landed without an owner | Add the CODEOWNERS entry |
| `plugins-list.yaml: invalid format` | YAML syntax error | Validate the structure |
| `smoke test failed` | The plugin does not load | Check the `backstage.json` compatibility override |

### `/publish` on the overlay repository

Publication runs from a `/publish` comment. Check whether it already ran:

```bash
gh pr view <number> --repo <owner/repo> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | select(.name | contains("publish"))'
```

Bot-authored PRs cannot trigger it. GitHub suppresses workflow triggers from
`github-actions[bot]` events, so those PRs sit without a publish check until a
human comments. Find them:

```bash
gh pr list --repo <owner/repo> --author "github-actions[bot]" \
  --json number,title,statusCheckRollup \
  --jq '.[] | select(.statusCheckRollup | map(.name) | index("publish") == null)'
```

Posting the comment is a write. Plan it first.

## Read repository content

The contents API returns base64:

```bash
gh api repos/<owner/repo>/contents/<path> --jq '.content' | base64 -d
gh api repos/<owner/repo>/contents/versions.json --jq '.content' | base64 -d | jq '.'
```

From a PR branch rather than the default branch:

```bash
BRANCH=$(gh pr view <number> --repo <owner/repo> --json headRefName --jq '.headRefName')
gh api "repos/<owner/repo>/contents/<path>?ref=$BRANCH" --jq '.content' | base64 -d
```

On Windows, run these through Git Bash or replace `base64 -d` with an
equivalent; PowerShell has no `base64` command.

## Budget

Batch reads share one rate limit. Check it before a wide sweep, and pause
between iterations of a loop:

```bash
gh api rate_limit --jq '.rate | "Remaining: \(.remaining)/\(.limit)"'
```
