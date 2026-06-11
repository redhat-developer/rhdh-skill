# Bridge: Jira-to-GitHub Issue Workflow

Create GitHub Issues from Jira tickets so fullsend agents can pick them up and
implement them. This is the second step after `groom` — it assumes the ticket
is already agent-ready (score 10+ on the readiness rubric).

Three things happen:

1. Read the Jira ticket and extract structured information
2. Create a GitHub Issue with fullsend-compatible formatting
3. Link both sides (Jira comment with GH link, GH issue body with Jira link)

## Usage

```
/fullsend bridge <KEY>                    # Bridge to auto-detected repo
/fullsend bridge <KEY> --repo owner/name  # Bridge to specific repo
/fullsend bridge <KEY> --dry-run          # Preview, no mutations
/fullsend bridge --batch <JQL> --repo owner/name  # Bridge multiple tickets
```

## Workflow

### Step 1 — Fetch and Validate the Jira Ticket

```bash
acli jira workitem view <KEY> --json
```

Fall back to `jira issue view <KEY>` if acli is unavailable.

**Validate agent-readiness**: Run a quick score against the groom rubric
(see `references/groom.md`). If score < 7:

> "This ticket scores {score}/12 on agent-readiness. Run `/fullsend groom <KEY>`
> first to improve it, or proceed anyway? [groom/proceed/cancel]"

If score is 7–9, note the weak dimensions but proceed.

### Step 2 — Detect Target Repository

Resolution order:

1. **`--repo` flag**: Use as-is.
2. **`repo:` label on Jira ticket**: Extract repo name, map to full `owner/name`
   using `references/repo-mapping.md`.
3. **Component field**: Map Jira component to a repo using `references/repo-mapping.md`.
4. **Ask the user**: Present known repos from the mapping file, let them pick.

Verify the repo exists and the user has access:

```bash
gh repo view <owner/name> --json name,owner
```

### Step 3 — Check for Existing GitHub Issues

Search for duplicates before creating:

```bash
gh issue list --repo <owner/name> --state open --search "<jira key OR summary keywords>"
```

If a match exists:

> "Found existing issue #N: 'title'. Is this the same work? [skip/link/create-anyway]"

- **skip**: Don't create. Optionally add Jira link to existing issue.
- **link**: Link Jira ticket to existing issue (comment on both sides). Done.
- **create-anyway**: Proceed with new issue.

Also check Jira comments for existing "Bridged to GitHub" links. If found, ask
before creating a second issue.

### Step 4 — Create the GitHub Issue

Build the issue using the template below.

```bash
gh issue create --repo <owner/name> \
  --title "<title>" \
  --label "fullsend" \
  --body "$(cat <<'EOF'
<body>
EOF
)"
```

**Labels**: Always add `fullsend`. Add additional labels based on ticket type:

| Jira type | GitHub labels |
|-----------|--------------|
| Bug | `fullsend`, `bug` |
| Story/Task | `fullsend`, `enhancement` |
| Vulnerability/CVE | `fullsend`, `security` |
| Investigation (`needs-investigation`) | `fullsend`, `needs-investigation` |

### Step 5 — Link Both Sides

**On Jira** — add a comment:

```bash
acli jira workitem comment --key <KEY> --comment "Bridged to GitHub: <issue-url>" --yes
```

**On GitHub** — the Jira link is already in the issue body (from the template).

### Step 6 — Report

```markdown
Bridged: <JIRA-KEY> → <owner/name>#<number>
  Jira:   https://redhat.atlassian.net/browse/<KEY>
  GitHub: <issue-url>
  Score:  <readiness-score>/12
```

---

## GitHub Issue Template

```markdown
## Problem

{problem_description}

## Context

{context}

**Jira ticket**: [{jira_key}]({jira_url})
**Type**: {issue_type}
**Priority**: {priority}

## Location

{location_hints}

## Acceptance Criteria

{acceptance_criteria}

## Notes for the Agent

{agent_notes}

---
*Bridged from Jira by `/fullsend bridge`*
```

### Field Mapping

How to populate each section from the Jira ticket:

| Template section | Jira source | Fallback |
|-----------------|-------------|----------|
| `problem_description` | Description — extract "Problem" or "Current vs Expected" section | Full description if unstructured |
| `context` | Description — extract "Context" section, plus linked issues | Summary + priority as minimal context |
| `jira_key` | Issue key (e.g., RHIDP-1234) | — |
| `jira_url` | `https://redhat.atlassian.net/browse/{key}` | Use `issues.redhat.com` if JQL source differs |
| `issue_type` | Issue type field (Bug, Story, Task, etc.) | — |
| `priority` | Priority field | "Undefined" if not set |
| `location_hints` | Description — extract "Location" section, or `repo:` labels, or component field | Omit section if no location info |
| `acceptance_criteria` | Description — extract "Acceptance Criteria" section | Omit section if none |
| `agent_notes` | Description — extract "Notes for the Agent" section, plus any agent-relevant comments | Omit section if none |

### Title Rules

- Use the Jira summary as the GitHub Issue title
- If the Jira summary is too vague, prepend the type: `fix: {summary}`, `feat: {summary}`
- Keep under 80 characters
- Don't include the Jira key in the title (it's in the body)

### Label Mapping

| Condition | Labels to add |
|-----------|--------------|
| Always | `fullsend` |
| Jira type = Bug | `bug` |
| Jira type = Story or Task | `enhancement` |
| Jira type = Vulnerability | `security` |
| Jira label `needs-investigation` | `needs-investigation` |
| Jira priority = Blocker or Critical | `priority/critical` |

### Idempotency

Before creating, check if the issue already exists:

1. Search for `{jira_key}` in open issues (the Jira link in the body makes this searchable)
2. If found, report "Already bridged" with the existing issue URL
3. If the user wants to re-bridge (ticket was updated), close the old issue with a comment and create a new one

---

## Batch Mode

When bridging multiple tickets (`--batch`):

1. Fetch all matching Jira tickets
2. Score each against agent-readiness
3. Present a summary table:

```markdown
| # | Jira Key | Summary | Score | Target Repo | Action |
|---|----------|---------|-------|-------------|--------|
| 1 | RHIDP-123 | Fix auth redirect | 11/12 | owner/repo | Bridge |
| 2 | RHIDP-456 | Update notification | 6/12 | owner/repo | Needs grooming |
| 3 | RHIDP-789 | Add dark mode | 10/12 | owner/repo | Bridge |
```

4. Ask: "Bridge {n} ready tickets? [y/N]"
5. Create issues sequentially, report each URL

---

## Error Handling

| Error | Action |
|-------|--------|
| Jira ticket not found | "Ticket <KEY> not found." |
| Target repo not found | "Repository <owner/name> not found or no access." |
| `gh issue create` fails | Show error. Common cause: missing labels (create them first). |
| No repo detected | Ask user to specify with `--repo`. |
| Ticket already bridged | Check Jira comments for existing "Bridged to GitHub" link. Ask before creating a second issue. |
