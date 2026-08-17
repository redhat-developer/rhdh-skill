# Domain Docs

How the engineering skills should consume this repo's domain documentation.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — domain language for the RHDH skill project
- **`docs/adr/`** — read ADRs that touch the area you're about to work in

If any of these files don't exist, proceed silently. Don't flag their absence.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
└── docs/adr/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need is absent, decide whether it is unnecessary new language
or a real domain gap. For a real gap, define it in `CONTEXT.md` as part of the
current change before using the term elsewhere.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0002 (stdlib-only Python CLIs) — but worth reopening because…_
