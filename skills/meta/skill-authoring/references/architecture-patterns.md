# Architecture patterns

Read this when a skill needs more than a linear workflow: a precondition it
cannot produce for itself, project context every branch shares, behaviour that
varies by task type, or output another skill consumes.

## The sub-command router is retired

A skill whose body is a menu of modes over a table of sub-commands is the thing
to avoid. One collection ran on that architecture until it broke, and the
measurement that ended it is worth carrying: the largest router reached 7,784
lines across 45 references that partitioned into seven components with almost no
citation edges between them. A caller had to learn whichever of seven
vocabularies its request happened to land in.

That is a **shallow module** — the interface costs as much to learn as the thing
it hides. Depth is the goal instead: one small trigger over substantial
behaviour.

Every row of such a table is a phrase a user would say on its own, and a trigger
phrase is a skill. Split the rows.

Each of these means the skill is several skills:

- The body opens by asking which mode the user wants. Routing is the host's job,
  decided before the skill loads.
- Two rows share no domain model, no preconditions, and no completion criterion.
- A row maps one-to-one onto a sub-command of a bundled script, so the table is a
  second copy of `--help`.
- The `compatibility:` line is the union of unrelated toolchains.

What replaces it: one skill per trigger phrase, named domain-then-verb, composed
by name. Material that two or more of the resulting skills
need becomes a reference skill each of them invokes — see Duplication between
skills below.

## Conditional references, not routes

A skill with one trigger still has branches, and disclosing them is progressive
disclosure rather than routing. The difference is who decides: a conditional
pointer fires on something the request already settled; a route asks.

Word the pointer so it names the material and the condition for reaching it —
"Read `references/openshift.md` when the target cluster is OpenShift" beats "see
`references/` for details". A table is fine when several pointers share a shape,
as long as every row names a load condition and every row sits inside the skill's
one domain model, gates, and completion criterion. Rows that sit outside those
are not branches.

Keep in `SKILL.md` what every branch needs: the domain statement, the gates, the
boundary with neighbouring skills, and the completion criterion. Push branch-only
detail one level down into `references/` or `workflows/`, and keep each file
independently loadable.

Descriptions live in skill frontmatter. A skill carries no second description
registry for its branches: a branch is not separately discoverable, so a
description written for one is load nobody reads.

Use ordinary Markdown. Structure is an authoring aid — never make headings, menu
numbering, or XML tags part of a tested interface.

## Shared material inside one skill

When several branches share an interaction pattern, an error row, or a domain
rule, state it once in `SKILL.md` and have the branches point at it. The signal
is the moment you copy the same text into a second branch file and realize a
change would mean editing both.

Common candidates:

- **Confirmation flow**: define `"Apply changes? [y/N/edit]"` once; branches say
  "use the confirmation flow in `SKILL.md`".
- **Error rows**: when the same error and action appear in two branch files, move
  the row up to the `SKILL.md` error table.
- **Domain conventions**: rules that hold everywhere, such as "Release Pending
  counts as completed for velocity".

When branches reuse each other's analysis — sprint planning reusing the roster
built for assignment — say so in `SKILL.md` so the agent loads the pair together
and does not repeat the API calls.

When the copy would land in another *skill*, this remedy is unavailable. Read the
next section before copying anything across that boundary.

## Duplication between skills

Centralizing in `SKILL.md` is the remedy inside one skill, and it disappears at
the skill boundary: skills compose by name and never read each other's files, so
there is no shared file to move the text into.

Extract, enforce, or document — the rule and the three moves are in `SKILL.md` →
Duplication. What follows is how to carry them out.

Deciding between them is a question about ownership, not about volume. Ask which
module owns the material: nothing yet (extract), a module whose interface the
caller bypassed (enforce), or no module at all because it is a rule rather than a
capability (document).

Code is the exception that needs no remedy. A bundled script is self-contained so
its skill installs alone, and a sibling carrying a similar helper is not a defect;
there is no shared runtime package. The sharp edge is data that looks like code —
a field ID copied into two scripts goes stale silently — so validate that data
against its live source rather than reaching for a package.

### Reference skills

A reference skill exists because two or more skills would otherwise copy the same
material. It is model-invoked and reached by name like any other skill, and it
carries an ordinary description that may also fire on user intent — the external
`grilling` skill is the pattern, composed by several callers without any of them
owning a copy of the interview.

Its description competes for routing against every other skill on the machine.
Keep it narrow, name the material rather than the domain, and prefer one
reference skill over two whose triggers overlap.

Two callers is the threshold. One caller means the material belongs inside its
single owner, and a reference skill nobody invokes is an extraction that failed.
Name the dependency in each calling `SKILL.md` and declare it in the machine
catalog; validation fails the build when the two disagree.

## Setup and capability gates

### When to use

Use a gate when a branch cannot produce its stated outcome without a
precondition: project context, configuration, or a ready tool or adapter. Gates
turn "the output was mediocre" into "the agent tells you what is missing".

### The gate contract

One contract covers every gate. When a required precondition is missing, stop
that branch, say what is missing, and name the exact setup entry point and route
that supplies it — whichever human-invoked skill or command the collection
publishes for setup. Branches that do not need the capability continue. A
model-invoked skill detects capability and stops there — installing,
authenticating, and probing host skill directories belong to that setup entry
point.

If you find yourself writing "skip the step and proceed anyway", the precondition
was not required. Delete the gate. A step whose absence does not change the
branch's completion criterion is not a gate, and dressing it as one teaches the
agent that gates are advisory.

### Gate table pattern

Define gates as a table with a required check and a fail action:

```markdown
## Setup (non-optional)

| Gate | Required check | If fail |
|---|---|---|
| Context | Project context loaded via `python scripts/load_context.py` | Run the loader |
| Config | Config file exists and is not placeholder | Stop the branch and name the exact setup route |
| Capability | Required adapter or CLI is ready, checked without inspecting credential material | Stop the branch and name the exact setup route |
| Plan | The user confirmed the plan | Present it and wait |
| Mutation | All gates above pass | Do not edit project files |
```

`scripts/load_context.py` above is **example only** — name the loader to match the
skill you are building. A skill needs only the rows that bear on its work; the
**Mutation** gate is always the last of them, and no file is edited until every
gate above it passes.

### Preflight declaration

For environments that support it, require the agent to state gate status before
editing files:

```text
SKILL_PREFLIGHT: context=pass config=pass mutation=open
```

This forces the agent to evaluate each gate out loud rather than skipping
silently.

## The write gate

A skill that writes to an issue tracker, a forge, or a cluster names what counts
as a mutation in its own domain, then invokes by name whichever skill owns the
write protocol for the rest: stating the operations, taking approval, and
reporting every outcome. One skill owns that protocol, so a writing skill carries
a pointer to it rather than a copy of it.

Approval happens in the conversation, where the user already is. The plan is
prose in the transcript — a compact table, one row per operation.

Reading, analysis, dry runs, and drafting in chat are not mutations, and a
request to triage or analyse approves no write.

## Register and mode systems

### When to use

Use when behaviour varies sharply by task type while every type shares the same
trigger, prerequisites, and completion criterion. The register classifies the
task, then loads different reference material. When the two registers share none
of that, they are two skills — see the retired router above.

### Pattern

Define two to four registers with clear criteria:

```markdown
## Register

Every task is **library** (published, API-stable) or **application** (internal,
can break).

Identify before acting. Priority: (1) cue in the task itself; (2) the target in
focus; (3) explicit field in config. First match wins.

Load the matching reference: [references/library.md](references/library.md) or
[references/application.md](references/application.md).
```

Each register gets its own reference file. Branch files add a short `## Register`
section only where behaviour diverges, and link to the register file instead of
restating it.

More examples:

- **Documentation**: `tutorial` (learning-focused, guided) vs `reference`
  (lookup-focused, exhaustive)
- **Testing**: `unit` (isolated, fast, mock-heavy) vs `integration` (realistic,
  slow, infra-dependent)
- **Deployment**: `development` (fast feedback, verbose) vs `production`
  (optimized, hardened)

## Context file system

### When to use

Use when every branch of the skill needs the same project background. Without it,
the agent asks the same questions every session, or produces generic output.

### Pattern

Define one or two context files at the project root:

| File | Purpose | Required? |
|---|---|---|
| `PROJECT.md` | Strategic context: users, goals, constraints, principles | Yes |
| `CONVENTIONS.md` | Technical context: patterns, naming, structure | Recommended |

Match the names to the domain. A design skill uses `PRODUCT.md` and `DESIGN.md`;
a deployment skill might use `INFRA.md`. Pick names that are obvious to the user.

### Loader script

Write a script that finds, reads, and returns context as JSON. The
`load_context` / `load_context.py` names below are **example only**.

```python
#!/usr/bin/env python3
"""Load project context files and return structured JSON."""

import argparse
import json
import os
import sys
from pathlib import Path

CONFIG_NAMES = ["PROJECT.md", "Project.md", "project.md"]
FALLBACK_DIRS = [".agents/context", "docs"]


def load_context(cwd=None):
    cwd = Path(cwd or os.getcwd())
    # 1. Check env override (SKILL_CONTEXT_DIR)
    # 2. Check cwd for context files
    # 3. Fallback to subdirectories (.agents/context/, docs/)
    # 4. Return structured JSON
    config_path = ...  # resolve from cwd + fallbacks
    config = config_path.read_text(encoding="utf-8") if config_path else None
    return {
        "hasConfig": config is not None,
        "config": config,
        "configPath": str(config_path.relative_to(cwd)) if config_path else None,
        "contextDir": str(cwd),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Load project context files and return structured JSON."
    )
    parser.add_argument("--dir", default=".", help="Project root directory")
    args = parser.parse_args()

    result = load_context(args.dir)
    if sys.stdout.isatty():
        print(json.dumps(result, indent=2))
    else:
        json.dump(result, sys.stdout)
    sys.exit(0 if result["hasConfig"] else 1)


if __name__ == "__main__":
    main()
```

Key behaviours:

- **Case-insensitive filename matching**: accept `PROJECT.md`, `Project.md`,
  `project.md`
- **Env override**: `SKILL_CONTEXT_DIR=path/to/dir` for non-standard layouts
- **Fallback directories**: check `.agents/context/` and `docs/` if the root is
  clean
- **Full JSON output**: never pipe through `head`, `tail`, `grep`, or `jq`

### Context validation

Handle missing, empty, or placeholder files: when `PROJECT.md` is absent or still
carries `[TODO]` markers, stop the branch, name the exact setup route, and resume
the original task once the human reports setup complete.

### Session caching

Don't re-run the loader when context is already in the conversation. The
exceptions are a setup command that just rewrote the files and a user who edited
them by hand.

## Creation workflows

### When to use

Use when a skill creates structured artifacts through conversation — Jira issues,
PRDs, design docs, config files. The goal is a conversation with a smart
colleague, not a form.

### Draft-then-grill

Don't ask every question from scratch. Synthesize what the conversation already
established into a draft, present it for review, then ask only about gaps:

1. **Draft from context** — fill in as many template sections as possible from
   what is already known
2. **Present for review** — "Here's what I have so far. What's missing or wrong?"
3. **Fill gaps** — ask targeted questions only for unfilled sections
4. **Challenge** — probe sizing, completeness, scope, and risks on the completed
   draft

This respects the user's time. Someone who spent ten minutes describing the
problem does not want to re-answer it as seven template questions.

### Field inference

When the artifact has metadata fields — priority, owner, category, labels, sizing
— infer them from the conversation instead of asking one at a time. Propose all
of them at once with the rationale, and let the user adjust.

Examples across domains:

- **Issue tracker**: "Priority Major (functional gap, not a regression). Team
  inferred from component. Size M based on AC count."
- **Design doc**: "Category: API Design. Reviewer: inferred from module
  ownership. Status: Draft."
- **Config file**: "Environment: staging — you mentioned testing. Region:
  us-east-1 — matches existing infra."

Inference signals depend on the domain: conversation keywords, the file paths
being edited, parent artifact inheritance, historical patterns, org conventions.

### Review gate with preview

Before creating the artifact, render a preview so the user sees the complete
picture:

```markdown
## {Type}: {summary}

### Description
{filled template}

### Fields
- **Priority**: Major — rationale
- **Team**: COPE
...
```

A preview is not the write gate. When the next step writes to an external system,
invoke the skill that owns the write gate and follow it — the preview shows the
content, the gate states the operations and collects the approval.

### Chained decomposition

When artifacts form a hierarchy — PRD to issues, design doc to tasks, Feature to
Epic to Story — offer to continue down the chain after each creation:

- Context carries down; don't re-ask what is already established
- The grill narrows at each level, from scope to delivery plan to implementation
- Each level is a separate confirmation, and the user can stop at any point
- Parent and child link automatically where the target system supports it

## Handoffs between skills

### When to use

Use when one skill produces work another skill consumes: a review that becomes a
posted comment, an analysis that becomes a plan.

### Pattern

The producer states its result in the conversation, structured enough to act on:

```markdown
### Plan structure

**1. Summary** (2-3 sentences)
**2. Primary goal**
**3. Approach**
**4. Scope** (breadth, depth, time intent)
**5. Key scenarios** (default, error, edge cases)
**6. Open questions**
```

The consumer states what it requires before it starts:

```markdown
## Build gate

Build cannot start until:
1. Context is valid and current.
2. The plan is explicitly confirmed by the user.
3. The references the plan names are loaded.
```

Two rules make the seam hold. The plan must be **user-confirmed** rather than
self-authored — a separate user response approving it, not the agent's own
summary. And the handoff stays in the conversation, as prose both sides can read;
a user who needs context to survive into a later session runs a session-handoff
skill.

Skills compose by name, so the handoff interface is what the producer said. A
reference file or script path is not a handoff interface.

## Self-critique loops

### When to use

Use for any branch that produces an artifact — code, documents, configs. The
first pass is never the final pass.

### Pattern

```markdown
### Critique and fix loop

After the first pass, write a short self-critique and patch. Repeat until no
material issues remain:

1. Does it match the requirements?
2. Does it pass the quality checks? (define explicitly)
3. Check every expected scenario.
4. Check against the absolute bans list.

The exit bar is not "it works." It is: [specific, measurable quality threshold].
```

Define the exit bar explicitly. "Looks good" is not a bar. "All tests pass, all
expected scenarios are handled, no placeholders remain, and the output would
survive code review" is a bar.

---

Read `anti-patterns.md` for the failure catalog these patterns exist to prevent,
including the ones that misapply the patterns above.
