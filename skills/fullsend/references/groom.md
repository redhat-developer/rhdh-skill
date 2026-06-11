# Groom: Agent-Readiness Workflow

Prepare Jira tickets so an autonomous agent can pick them up and implement them
successfully. This is NOT sprint readiness or workflow field validation (use
`rhdh-jira refine` for that). This checks whether the ticket contains enough
information for an agent to:

1. Understand what to change
2. Find the right files
3. Know when it's done
4. Stay within scope

The output is an improved ticket description that a bot can act on without
asking humans for clarification.

## Usage

```
/fullsend groom <KEY>           # Interactive grooming session
/fullsend groom <KEY> --quick   # Score + recommendations only
/fullsend groom --batch <JQL>   # Score multiple tickets, flag worst ones
```

## Workflow

### Step 1 — Fetch the Ticket

```bash
acli jira workitem view <KEY> --json
```

Extract: summary, description, labels, components, issue links, comments.
Fall back to `jira issue view <KEY>` if acli is unavailable.
If neither tool is available, ask the user to paste the ticket description.

### Step 2 — Score Against Agent-Readiness Rubric

Score each dimension 0–2:

| Dimension | 0 (Fail) | 1 (Partial) | 2 (Pass) |
|-----------|----------|-------------|----------|
| **Problem clarity** | Vague or missing | Has description but ambiguous | Clear current vs expected behavior |
| **Repo identification** | No repo mentioned | Repo implied but not explicit | `repo:` label or explicit repo name |
| **File/path hints** | No file paths | General area mentioned | Specific files, components, or URL paths |
| **Acceptance criteria** | None | Implicit in description | Explicit checklist |
| **Scope** | Unclear or multi-PR | Likely single PR but not stated | Clearly scoped to one PR |
| **Type clarity** | Can't tell bug vs feature | Inferable from context | Explicit (bug with repro, feature with spec, CVE with ID) |

**Total**: 0–12. Thresholds:

- **10–12**: Agent-ready. Proceed.
- **7–9**: Needs minor improvement. Suggest fixes.
- **0–6**: Not agent-ready. Conversational grooming required.

### Step 3 — Conversational Grooming (interactive mode only)

For each dimension that scored 0 or 1, ask the user targeted questions.
**One question at a time** — don't dump all at once.

**Rules:**

- If the user is vague, push back. A vague ticket wastes agent time and compute.
- If the work spans 3+ repos, suggest splitting into multiple tickets.
- If the work requires human judgment (design decisions, UX direction), suggest
  marking it `needs-investigation` so the agent reports findings instead of guessing.
- If the user doesn't know which files are affected, help them narrow it down by
  asking about the feature/page/service.

Skip this step for `--quick` and `--batch` modes.

### Step 4 — Produce Improved Ticket

Generate an updated description using the template below. Present to user:

```markdown
## Suggested update

**Title**: <improved title — short, specific>

**Description**:
<structured description>

**Labels to add**:
- repo:<name> (if identified)
- <any routing labels>

**Score**: X/12 → Y/12
```

Ask: "Apply this update to the ticket? [y/N/edit]"

- **y**: Update via `acli jira workitem edit --key <KEY> --summary "..." --yes`
  and description update via REST/ADF
- **N**: Done, no changes
- **edit**: Let user modify before applying

### Step 5 — Investigation Check

If the ticket's problem is unclear, spans many repos, or requires human judgment
(design decisions, UX direction, architecture choices), recommend the
`needs-investigation` label instead of trying to groom it into an implementation
ticket.

**Investigation tickets are fundamentally different from implementation tickets:**

- The agent should **analyze and report findings**, not implement code
- The output is a detailed comment on the Jira ticket (root cause, affected
  repos/files, suggested fix, blockers) — not a PR
- The ticket stays `In Progress` until a human confirms the findings or asks
  follow-up questions — never auto-archive
- Remove the `needs-investigation` label only after posting the report, not
  before

**When to suggest investigation:**

- User says "I don't know what's wrong" or "something is broken but I'm not sure where"
- Problem spans 3+ repos with no clear entry point
- Ticket involves a design decision or UX direction the agent shouldn't make
- User wants the agent to explore options, not implement a specific fix

If investigation is not needed and the ticket scores 10+ after grooming:

> "This ticket is agent-ready. Run `/fullsend bridge <KEY>` to create a
> GitHub Issue for fullsend."

---

## Agent-Readiness Question Guide

### 1. Problem Clarity

**Questions at score 0–1:**

- "What's the current behavior? What do you see happening now?"
- "What should happen instead? What does 'fixed' look like?"
- "Is this a bug (something broken), a feature (something new), or a change (something works but should work differently)?"
- For bugs: "Can you reproduce it? What are the steps?"
- For CVEs: "What's the CVE ID? Which package/dependency is affected?"

### 2. Repo Identification

**Questions at score 0–1:**

- "Which repository does this change belong in?"
- "Which page or URL is affected?" (narrow down frontend repo)
- "Which service handles this?" (narrow down backend repo)
- "Does the fix span multiple repos? If so, which ones?"

### 3. File/Path Hints

**Questions at score 0–1:**

- "Do you know which file(s) need to change?"
- "What's the URL path where this issue is visible?" (for frontend)
- "Which component or module is involved?"
- "If you've debugged this before, what did you find?"

Score 1 is acceptable for many tickets — the agent can find files from
component names. Score 0 means the agent will spend significant time
just locating the right code.

### 4. Acceptance Criteria

**Questions at score 0–1:**

- "How will you verify this is done? What should a reviewer check?"
- "Are there edge cases to handle?"
- "Should there be tests? What should they cover?"
- "Is there a visual change? Can you attach a screenshot or mockup?"

### 5. Scope

**Questions at score 0:**

- "How big do you think this change is? A few lines, a few files, or a larger refactor?"
- "Can this be done in a single PR, or should we split it?"
- "Are there dependencies — does something else need to land first?"

**When to suggest splitting:**

- Work spans 3+ repos
- Description contains "and also..." or "while we're at it..."
- Estimated change touches 10+ files across unrelated modules
- Mix of bug fix + feature work

### 6. Type Clarity

**Questions at score 0:**

- "Is this a bug fix, a new feature, a refactor, or a security fix?"
- For unclear bugs: "Can you describe the steps to reproduce?"
- For unclear features: "Is there a design or mockup?"

---

## Description Template

Use this when rewriting the ticket description. Omit sections that aren't relevant.

```markdown
## Problem

<What is wrong or what needs to change. For bugs: current behavior vs expected
behavior. For features: what should exist that doesn't. For CVEs: CVE ID,
affected package, version.>

## Context

<Why this matters. Impact on users, systems, or other teams. Any relevant
history or prior attempts.>

## Location

<Which repo(s), file(s), component(s), URL path(s) are involved.>

## Acceptance Criteria

- [ ] <Verifiable criterion 1>
- [ ] <Verifiable criterion 2>
- [ ] <Tests: what should be tested>
- [ ] <Edge cases to handle>

## Notes for the Agent

<Anything that helps the agent avoid wrong turns: "Don't touch the legacy auth
flow", "The test suite uses vitest not jest", "This component uses PatternFly 6".
Only include if non-obvious.>
```

---

## Batch Scoring Output

When running `--batch`:

```markdown
## Agent-Readiness Scores

| # | Key | Summary | Score | Problem | Repo | Files | AC | Scope | Type | Verdict |
|---|-----|---------|-------|---------|------|-------|----|-------|------|---------|
| 1 | KEY-123 | Fix notification... | 4/12 | 0 | 1 | 0 | 1 | 1 | 1 | Needs grooming |
| 2 | KEY-456 | Add dark mode... | 11/12 | 2 | 2 | 2 | 2 | 1 | 2 | Agent-ready |

### Summary
- Agent-ready (10+): N tickets
- Needs minor work (7–9): N tickets
- Needs grooming (0–6): N tickets

### Worst offenders (groom these first)
1. KEY-123 (4/12): Missing problem description and file paths
```

---

## Anti-patterns

Things that make tickets bad for agents:

| Anti-pattern | Why it's bad | Fix |
|--------------|-------------|-----|
| "Fix the X page" | Agent doesn't know what's broken | Add current vs expected behavior |
| Screenshot-only description | Agent can't read screenshots reliably | Add text description alongside screenshot |
| "See Slack thread" with link | Agent may not have Slack access | Copy relevant context into ticket |
| "Similar to PROJ-999" | Agent needs self-contained tickets | Copy the relevant parts, don't just reference |
| Multi-concern tickets | Agent produces unfocused PRs | Split into separate tickets |
| "Refactor X while fixing Y" | Mixes cleanup with bugfix | Separate tickets: fix first, refactor second |
| Implementation instructions | Over-constrains the agent, may be wrong | Describe the problem and outcome, not the solution |

---

## Error Handling

| Error | Action |
|-------|--------|
| Ticket not found | "Ticket <KEY> not found. Check the key and project." |
| acli not available | Fall back to `jira issue view`. If neither available, ask user to paste the ticket description. |
| Description is empty | Score Problem clarity as 0. Ask user to describe the problem from scratch. |
| Ticket is already closed | "This ticket is already closed. Nothing to groom." |
