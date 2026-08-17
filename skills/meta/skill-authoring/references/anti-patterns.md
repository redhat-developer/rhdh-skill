# Skill Anti-Patterns

Common failures and how to fix them. Read this during Phase 2 (drafting) to avoid known pitfalls.

For the shared quality vocabulary (predictability, progressive disclosure, completion criteria, failure modes like sediment/sprawl/no-op/negation), see `skill-quality.md`.

## Discovery Failures

### Context Selection Omission (CSO)

The description matches how the *author* thinks about the skill, not how *users* phrase requests.

**Symptom:** Skill exists but never triggers. Users rephrase until they give up.

**Example:**

```yaml
# BAD — author's mental model
description: Manages Kubernetes pod lifecycle annotations

# GOOD — how users actually ask
description: |
  Manage Kubernetes pod annotations and labels. Use when deploying,
  updating pod metadata, debugging pod scheduling, or when the user
  mentions annotations, labels, taints, tolerations, or pod spec changes.
```

**Fix:** Write should-trigger queries first (Phase 3), then write the description to match them.

### Description Summarizes the Workflow

The description explains *how* the skill works instead of *when* to use it.

**Symptom:** Description is accurate but doesn't contain the words users would say.

**Example:**

```yaml
# BAD — describes internals
description: |
  Loads project config, runs validation checks, generates a report
  with findings, and offers auto-fixes.

# GOOD — describes when to use it
description: |
  Audit agent skills for spec violations, structural issues, and
  content quality. Use when reviewing a SKILL.md, checking why a
  skill never triggers, or improving an existing skill.
```

**Fix:** Lead with the task the user wants done, not the steps the skill takes.

### Colliding Descriptions

Two skills claim the same utterance, so which one fires is a coin toss.

**Symptom:** The wrong skill activates, or the right one activates only when the user names it. Bare names are the usual cause — `plugin-development` competes with the host's own "create a plugin" skills, `raise-pr` with every PR skill on the machine.

**Fix:** Name domain-then-verb, and carry whatever name prefix the publishing collection uses so the name survives a flat install alongside every other pack. Read the neighbouring descriptions side by side and give each one the literal proper nouns it owns — an issue key such as `RHIDP-1234`, a repository name such as `rhdh-operator`, a tool name such as `acli`. If two descriptions still claim one phrase, they are one skill.

## Structure Failures

### Monolithic Skill

**Symptom:** Single SKILL.md over 500 lines covering multiple distinct workflows.

**Fix:** Ask first whether those workflows answer different utterances. If they do, they are separate skills. If they are branches of one trigger, extract them into self-contained `references/` files reached by conditional pointers.

### Mixed Concerns

**Symptom:** Procedures and domain knowledge interleaved in the same file.

**Fix:** Procedures (step-by-step workflows) stay in SKILL.md or `references/` workflow files. Domain knowledge (patterns, rules, examples) goes in separate `references/` files with conditional loading.

### Nested Reference Chains

**Symptom:** Reference A says "read reference B", which says "read reference C." The agent loads three files to answer one question.

**Fix:** Each reference should be self-contained. If two references need the same data, either duplicate it with a note ("Same pattern as X.md — duplicated to avoid transitive loading") or extract the shared data into a third file that both reference directly.

### Eager Reference Loading

**Symptom:** "Before starting, read all reference files." Every run pays for material most runs never use.

**Fix:** Load conditionally. "Read `references/aws.md` if deploying to AWS."

## Content Failures

### Explaining What the Agent Already Knows

**Symptom:** Skill explains basic programming concepts, standard library usage, or well-known tools.

**Fix:** Trust the agent's training data. Only add context the agent doesn't already have — project-specific conventions, non-obvious tool behavior, domain-specific gotchas.

```markdown
# BAD (~150 tokens wasted)
PDF files are a common document format. To extract text from PDFs,
we use pdfplumber, a Python library. First, import it at the top
of your file. Then open the file using a context manager...

# GOOD (~30 tokens)
Extract text with pdfplumber:
  with pdfplumber.open("file.pdf") as pdf:
      text = pdf.pages[0].extract_text()
```

### Rigid Rules Without Reasoning

**Symptom:** ALWAYS/NEVER rules in all caps with no explanation of why.

**Fix:** Explain the reasoning. Agents generalize from principles better than from rigid rules. Rigid rules also break at edge cases; principles adapt.

```markdown
# BAD
ALWAYS use pdfplumber. NEVER use PyPDF2.

# GOOD
Use pdfplumber over PyPDF2 — it handles malformed PDFs more gracefully
and preserves layout metadata needed for table extraction.
```

### Vague Steps

**Symptom:** Instructions like "handle errors appropriately" or "ensure quality."

**Fix:** Be specific. Name the errors. Define the quality bar. Show the expected output.

```markdown
# BAD
Handle API errors appropriately.

# GOOD
If the API returns 401, re-check credentials. If 429, wait 60 seconds
and retry once. If 5xx, report the status code and body to the user.
```

### Untestable Success Criteria

**Symptom:** "The skill works correctly" or "output is high quality."

**Fix:** Define observable, verifiable outcomes.

```markdown
# BAD
The migration is successful.

# GOOD
Migration is complete when: all tests pass, no deprecated imports remain
(grep -rn 'old_module'), and the changelog entry exists.
```

### Offering Too Many Options

**Symptom:** Skill presents 5+ approaches and asks the user to choose.

**Fix:** Recommend the best default. Present alternatives only when the tradeoffs genuinely depend on the user's situation. Two options is usually the right number — a default and an escape hatch.

### Dumping All Interview Questions

**Symptom:** The agent asks 15 questions at once and the user abandons.

**Fix:** Ask one question at a time and adapt to the answer. Every question earns its place — anything the codebase can answer is explored, not asked.

## Gate Failures

### Missing Setup Gates

**Symptom:** The agent produces generic output because it never checked for project context, config, or a ready tool.

**Fix:** A gate table with an explicit fail action per row, and the mutation gate last. See `architecture-patterns.md` → Setup and capability gates.

### Self-Authored Plans

**Symptom:** The agent writes a plan, approves its own plan, and builds from it. The user's original request is treated as the approval.

**Fix:** Require a separate user response approving the stated plan before anything executes. Intent to publish is not approval of a plan.

## Script Failures

### Interactive Prompts

**Symptom:** Script blocks waiting for user input; agent hangs.

**Fix:** Accept all input via flags, env vars, or stdin. Scripts must be fully non-interactive.

### Opaque Error Messages

**Symptom:** Script prints "Error" or exits silently on failure.

**Fix:** Print what went wrong, what was expected, and what the user can do about it. Use structured output (JSON with an `error` field) when the consumer is an agent.

### Absolute Script Paths

**Symptom:** Script references `/Users/alice/.skills/mything/scripts/helper.py`.

**Fix:** For a script owned by the current skill, use a skill-local path such as
`scripts/helper.py` in `SKILL.md`. For work another skill owns, invoke that skill
by its stable name and use what it reports back; never reference its path.

## Disclosure Failures

### The sub-command router

**Symptom:** The skill opens with "What would you like to do?" and a numbered menu
of modes, each with its own reference file. The user has to pick a lane before the
skill does anything.

**Fix:** Each row is a phrase a user would say on its own, so each row is a skill.
Split them, name them domain-then-verb, and let them compose by name.
This is a shape collections retire, not one to reach for — read
`architecture-patterns.md` → The sub-command router is retired for the symptoms
that identify one, including a table whose rows share no domain model and a
`compatibility:` line that unions unrelated toolchains.

### Ambiguous branch selection

**Symptom:** A skill with genuine branches guesses one even though the request
never settled it.

**Fix:** Word the pointer to fire on something the request already contains —
"Add `references/support-intake.md` when the work originates from a support case."
When nothing in the request settles it, ask one focused question about the
*subject*, not about which mode to run.

### Broken References

**Symptom:** A pointer names a file that doesn't exist, or the path is wrong.

**Fix:** After writing the pointers, verify every referenced file exists. Use consistent paths (`references/command.md`, not `./references/command.md` or `references/commands/command.md`).

### Redundant Content

**Symptom:** Same instructions appear in SKILL.md and in a referenced workflow file.

**Fix:** Single-source everything. If principles must always apply, they live in SKILL.md. If instructions are branch-specific, they live in the reference file. Never both.
