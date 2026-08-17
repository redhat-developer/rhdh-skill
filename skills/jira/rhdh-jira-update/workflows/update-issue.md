# Update a Jira issue with session progress

Detect the related issue, add a status comment summarizing the session, propose
status transitions, and check upward through the hierarchy for parent
transitions. On-demand — run at a natural stopping point, never proactively.

Use `acli` through its native credential store. Use the authenticated host
adapter only for what `acli` cannot do. `/rhdh-jira-api` owns both.

## Step 1 — Detect the issue

Check in priority order and stop at the first match:

1. **Conversation context** — issue keys already mentioned (RHIDP-1234,
   RHDHPLAN-567, RHDHBUGS-890, RHDHSUPP-456).
2. **Git branch name:**

   ```bash
   git branch --show-current 2>/dev/null | grep -oE '(RHIDP|RHDHPLAN|RHDHBUGS|RHDHSUPP)-[0-9]+'
   ```

3. **PR title or description:**

   ```bash
   gh pr view --json title,body 2>/dev/null
   ```

4. **Recent commits:**

   ```bash
   git log --oneline -10 2>/dev/null | grep -oE '(RHIDP|RHDHPLAN|RHDHBUGS|RHDHSUPP)-[0-9]+'
   ```

5. **Keyword search** — extract topic keywords and search:

   ```bash
   jql: "project in (RHIDP, RHDHPLAN, RHDHSUPP, RHDHBUGS) AND summary ~ \"KEYWORD1 KEYWORD2\" AND status != Closed AND assignee = currentUser() ORDER BY updated DESC"
   ```

   Present candidates: "I found these possibly related issues — which one?"

If several distinct keys turn up, ask which to update. If nothing matches, offer
`/rhdh-jira-create`.

Detection is best-effort — branch naming varies — so always confirm before
acting.

## Step 2 — Read the current state

```bash
acli jira workitem view ISSUE_KEY --json
acli jira workitem view ISSUE_KEY --fields "*all" --json   # when custom fields matter
```

Note the current status; it determines which transitions exist. Note whether the
issue has a parent — if it does not, skip Step 6 entirely.

## Step 3 — Compose the status comment

Two to five sentences. What was done, where it stands, what is next. Factual, not
a session log and not a self-assessment.

| Situation | Shape |
|---|---|
| Work in progress | "Started implementation. {approach}. Next: {what remains}." |
| Blocked | "Blocked on {dependency}. {what was tried}. Waiting for {person or resolution}." |
| PR up | "Implementation complete. PR: {link}. {brief description}." |
| PR merged | "PR merged and verified. {any follow-up}." |
| Abandoned approach | "Investigated {approach}. Abandoned because {reason}. Switching to {alternative}." |
| Scope discovery | "Investigation revealed {finding}. Scope is {larger/smaller/different}. {recommendation}." |

Confirm before posting: "Proposed comment: {comment}. Post this? [y/N/edit]"

```bash
acli jira workitem comment create --key ISSUE_KEY --body "comment text"
```

## Step 4 — Propose a transition

| Session activity | Transition |
|---|---|
| Started working | New / To Do → In Progress |
| PR up for review | In Progress → Review |
| PR merged | Review → Closed |
| Work done, awaiting release | In Progress / Review → Release Pending |
| Descoped or won't fix | Any → Closed, with a resolution |

Check the target status's exit criteria in `/rhdh-jira-api` **before** proposing.
If something is missing, say what: "To move to Review, you need: {fields}. Set
them first?"

**Closing requires a rationale.** Closing or descoping means setting the
resolution field — `Won't Do`, `Duplicate`, or `Done` — and adding a comment
saying why. Both go in the same approval as the transition. A closed issue with
no resolution and no comment loses the decision trail, and the next person to
find it has to reconstruct it from nothing. `/rhdh-jira-refine` applies the same
rule when it closes stale issues.

**Check for Jira automation first.** Automation rules cascade: a child moving to
In Progress moves the parent Epic to In Progress, and an Epic moving moves the
parent Feature. Fetch the parent's current status before suggesting anything for
it — the transition may already have happened. `/rhdh-jira-api` lists the rules.

Confirm, then apply:

```bash
acli jira workitem transition --key ISSUE_KEY --status "TARGET" --yes
```

If no transition applies, skip this step silently.

## Step 5 — Propose links

If the session revealed dependencies not yet tracked, offer them:

```bash
acli jira workitem link create --out ISSUE_KEY --in TARGET_KEY --type "Blocks" --yes
```

An **external URL** — a pull request, a design document, a support case — is not
an issue link. It is a *remote link*, and `acli` cannot create one. Use the
remote-link operation in `/rhdh-jira-api`, which takes the issue key plus a URL
and a title. A second link with the same URL replaces the first rather than
duplicating it.

Bundle the comment, the transition, and the remote link into one approval when
they all belong to the same PR handover.

## Step 6 — Upward cascade

One level at a time, each confirmed separately.

**Parent Epic.** Query the siblings:

```bash
jql: "parent = {epic_key}"
```

If every sibling is terminal for its type — Closed for Stories and Tasks, Closed
or Release Pending for Bugs — offer: "All stories under {epic_key} are complete.
Transition the Epic to Dev Complete? [y/N]" On confirmation, transition and add a
comment recording why.

**Parent Feature.** If the Epic transitioned, query its siblings:

```bash
jql: "parent = {feature_key} AND issuetype = Epic"
```

If every sibling Epic is in Release Pending or Closed — Dev Complete is not
enough, since Epics still need Release Notes fields and demo links — do **not**
transition the Feature. Say: "All Epics under {feature_key} are complete. The
Feature Owner is {owner}. Recommend reaching out to {owner} to move it to Release
Pending." Transitioning a Feature is the Feature Owner's call.

## Error handling

| Error | Action |
|---|---|
| No issue detected | Offer keyword search; then offer `/rhdh-jira-create` |
| `git` unavailable | Skip git detection; continue with context and keyword search |
| `gh` unavailable | Skip PR detection |
| Issue already Closed | "This is already Closed. Open a new issue, or reopen it?" |
| Transition rejected | Report which exit criteria are unmet |
| Comment failed | Report it. Issue state is unchanged. |
| Parent query returns no siblings | Skip the cascade — the issue may be unlinked |

## Caveats

1. **On-demand only.** Do not proactively suggest status updates.
2. **Multiple issues per session.** If the session touched several, ask which to
   update and run this workflow independently for each.
3. **The cascade stops at Feature.** Suggest it; the Feature Owner applies it.
