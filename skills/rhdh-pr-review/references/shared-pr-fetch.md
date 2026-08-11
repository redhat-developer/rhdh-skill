# Reference: Fetch PR Context (Shared)

Shared Phase 1 for all PR review workflows. The calling workflow must set `REPO` and `PR_NUMBER` before referencing this file.

<fetch_pr>

## Fetch PR Context

```bash
gh pr view $PR_NUMBER --repo $REPO \
  --json number,title,state,author,body,files,createdAt,headRefOid,baseRefName
```

Validate:
- PR state is `OPEN` (warn if merged or closed — artifacts may still work but PR is not active)
- PR belongs to the expected `$REPO`

Fetch the diff for later checklist generation:

```bash
gh pr diff $PR_NUMBER --repo $REPO
```

Save the changed file list for Phase 5:

```bash
gh pr view $PR_NUMBER --repo $REPO --json files --jq '.files[].path'
```

</fetch_pr>
