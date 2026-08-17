# Linking a PR raised by `/rhdh-pr-create`

`/rhdh-pr-create` invokes this skill by name for the Web link + comment, then
runs its own **Review** transition. It passes the PR URL, title, and Jira key;
it never runs the script in this directory itself.

```bash
# After PR_URL and PR_TITLE are known from /rhdh-pr-create:
REPO_SHORT="$(basename "$(git rev-parse --show-toplevel)")"
PR_NUM=…   # from gh pr create output / API

LINK_OUT="$(node "$SKILL/scripts/link-pr-mr.js" link \
  --issue "$JIRA_KEY" \
  --url "$PR_URL" \
  --title "${REPO_SHORT} #${PR_NUM}: ${PR_TITLE}" \
  --host github \
  --no-defaults)"
echo "$LINK_OUT"
# RHDHPLAN Epic/Story/Task may have been moved to RHIDP — use post-move key:
EFFECTIVE_KEY="$(printf '%s\n' "$LINK_OUT" | awk -F': ' '/^issue:/{print $2; exit}')"
EFFECTIVE_KEY="${EFFECTIVE_KEY:-$JIRA_KEY}"

acli jira workitem transition --key "$EFFECTIVE_KEY" --status "Review" --yes
```

Why `--no-defaults`: the linker's default status target is **In Progress**;
`/rhdh-pr-create` wants **Review** after PR submit. Defaults (story points,
team, etc.) remain available for general agent sessions that use
`create-pr-mr.js` alone.
