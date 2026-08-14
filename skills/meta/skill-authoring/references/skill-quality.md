# Skill Quality Vocabulary

Slim local vocabulary for predictable skills. Inspired by writing-great-skills principles; self-contained — do not require installing that skill.

**Predictability** is the root virtue: the agent takes the same *process* every run (not the same output). Every lever below serves it.

## Information hierarchy / progressive disclosure

Rank content by how immediately the agent needs it:

1. **In-skill steps** — ordered actions in `SKILL.md` (primary)
2. **In-skill reference** — definitions/rules consulted on demand
3. **External reference** — material behind a **context pointer**, loaded only when the pointer fires

**Progressive disclosure** moves reference down the ladder so the top stays legible. Inline what every branch needs; push behind a pointer what only some branches reach.

## Context pointers

A pointer names out-of-context material *and* the condition for loading it. Wording decides reliability — "Read `references/api-errors.md` if the API returns non-200" beats "see references/ for details." A must-have target behind a weak pointer is a variance bug: sharpen the wording before inlining.

## Completion criteria

Every step ends on a checkable done condition. Prefer exhaustive bars ("every modified model accounted for") over vague ones ("produce a change list"). Vague criteria invite **premature completion**.

## Leading words

Compact concepts already in the model's pretraining (`relentless`, `tracer bullets`, `fog of war`) that anchor behaviour in few tokens. Use them in the body for execution and in the **description** for invocation. Prefer a strong pretrained word over a long restatement.

## Pruning

- Keep each meaning in a **single source of truth**
- Check **relevance**: does this line still bear on what the skill does?
- Hunt **no-ops** sentence by sentence — if it doesn't change behaviour vs the default, delete it

## Failure modes

| Mode | Meaning | Cure |
|------|---------|------|
| **Premature completion** | Ending a step before it's done | Sharpen the completion criterion; only then hide later steps |
| **Duplication** | Same meaning in multiple places | Single-source; collapse synonyms in descriptions |
| **Sediment** | Stale layers that accumulate | Prune on every edit; removing is safer than it feels |
| **Sprawl** | Skill too long even when all lines are live | Disclose reference; split by branch/sequence |
| **No-op** | Instruction the model already obeys | Delete, or replace a weak leading word with a stronger one |
| **Negation** | Steering by prohibition ("don't X") | Prompt the positive target; keep bans only as hard guardrails paired with what to do instead |

## When to apply

- **Create (Phases 2–5):** Check hierarchy, pointers, completion criteria, and failure modes while drafting and reviewing
- **Audit:** Map findings to these modes when diagnosing why a skill misfires or bloats
- **Descriptions:** Front-load leading words; one trigger per branch
