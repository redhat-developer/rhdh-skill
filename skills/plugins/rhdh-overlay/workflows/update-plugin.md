# Workflow: Update Plugin Version

Bump a plugin to a newer upstream commit or tag.

<required_reading>
**Read these reference files NOW:**

1. `references/overlay-repo.md` — Workspace patterns
2. `references/ci-feedback.md` — Interpreting publish output
</required_reading>

<prerequisites>
- Existing workspace in overlay repo
- New upstream version identified (commit SHA or tag)
</prerequisites>

<process>

## Step 1: Identify New Version

```bash
# Check upstream releases
gh release list -R <owner>/<repo> --limit 10

# Or recent commits
gh api repos/<owner>/<repo>/commits?per_page=5 --jq '.[].sha'
```

- [ ] Note new commit SHA or tag
- [ ] Check upstream's `backstage.json` at that commit

## Step 2: Update source.json

```bash
cd workspaces/<name>/
```

Update `source.json`:

- `repo-ref` → new commit SHA or tag
- `repo-backstage-version` → upstream's Backstage version at that commit

## Step 3: Update backstage.json (if needed)

If upstream's Backstage version changed significantly, may need to update override.

## Step 4: Create PR

Prepare the local branch and commit, then follow the mutation contract in
`SKILL.md`. The exact push is one approved operation. Once its head SHA is
known, plan the exact PR title and body, obtain approval of the new material
hash, and only then create the PR. Return a receipt for each batch.

Invoke `/prose-editing` once on the final PR title and body in the **flavored**
register before presenting that material hash. Preserve plugin names, versions,
commit refs, links, headings, and checklists. `gh` only transports the result.

```bash
git checkout -b update-<plugin-name>-<version>
git add .
git commit -m "Update <plugin-name> to <version>"
git push -u origin update-<plugin-name>-<version>

gh pr create \
  --title "Update <plugin-name> to <version>" \
  --body "Bumps <plugin-name> from <old> to <new>."
```

## Step 5: Trigger Build

Follow the guarded publish in `SKILL.md`. Get approval for the stated operation,
then comment `/publish` and verify success from the returned check URL.

## Step 6: Test and Merge

Read `references/rhdh-local.md`, then invoke `/rhdh-local` by name with the exact
PR artifact references, plugin config, environment variable names, and checks.
Take back its per-check results. Add them to the PR only through an approved
comment operation. Compose the final verification comment and invoke
`/prose-editing` once on it in the **flavored** register; preserve check names,
results, artifact references, and quoted errors. State review requests, feedback comments, re-publish
triggers, and merge as their own operations once their exact targets and payloads
are known. Merge only after local verification and the current-head publish check
pass, then report the outcome of every operation alongside the workspace changes.

</process>

## Follow-up record

Report old and new refs, PR URL, publish result, compatibility blockers,
breaking changes, and any post-release verification still needed.

<success_criteria>

- [ ] source.json updated with new ref
- [ ] `/publish` succeeds
- [ ] PR merged
</success_criteria>
